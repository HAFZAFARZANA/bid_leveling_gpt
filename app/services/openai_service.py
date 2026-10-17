"""Universal GPT-first PDF extraction using the OpenAI Responses API.

No local PDF text extraction, contractor-specific rules, filename classification,
page-number assumptions, or trade-specific quantity defaults are used here.
"""
from __future__ import annotations

import base64
import json
import logging
import time
from typing import Any, Dict

from openai import OpenAI, APIConnectionError, APIStatusError, APITimeoutError, RateLimitError, OpenAIError
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.takeoff import SectionSummary, TakeoffExtractionResponse

logger = logging.getLogger(__name__)

EXTRACTION_INSTRUCTIONS = """
You are an expert construction proposal and quantity-takeoff document analyst.
Read the complete attached PDF, including its text, tables, scanned pages, footnotes,
headers, and page images. Extract the information that is actually present in this
specific document. The document may be any construction trade and any contractor format.
Do not assume the trade, contractor, page layout, table columns, item types, or section names.

CRITICAL ACCURACY RULES:
- Never invent a quantity, unit, model number, price, date, contractor, project address,
  warranty, exclusion, responsibility, payment term, or page reference.
- Use null for missing/uncertain scalar values and add a clear warning/review reason.
- Preserve the source description and model number exactly where possible; do not merge
  separate line items. Preserve repeated lines if they appear separately in the source.
- Separate base scope items from optional/add-on items. Do not count an option as base scope.
- Keep equipment/material quantities separate from payment milestones, prices, and monthly rates.
- Extract all pages, not only the first pages or pages associated with a presumed trade.
- Every takeoff item must include a 1-indexed source page and a short source_evidence excerpt.
  If the page or evidence cannot be confidently identified, flag it for review.
- Do not infer that a blank quantity means 1, a lump sum, or any other quantity.
- Extract only explicitly stated totals, subtotal, tax rate, tax amount, and grand total. Do not
  calculate missing commercial values. If amounts conflict, preserve the stated values and flag it.
- Preserve all options, exclusions, included scope, customer responsibilities, contractor
  responsibilities, working conditions, warranties, general conditions, and payment milestones.
- Do not add generic industry terms that are not in the source.
- Classify items into logical sections based on this document. Section keys should be concise,
  stable snake_case labels and section titles should describe the actual content. Do not force
  items into a predetermined trade taxonomy.
- Flag unclear, conflicting, approximate, illegible, or unverified values for human review.
- Return the complete output matching the supplied JSON Schema. Do not include commentary
  outside the structured response.
""".strip()


class OpenAIServiceError(Exception):
    def __init__(self, message: str, status_code: int = 500, error_code: str = "openai_error"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code


class OpenAIService:
    def __init__(self) -> None:
        self._client: OpenAI | None = None

    def get_client(self) -> OpenAI:
        if not settings.is_openai_configured:
            raise OpenAIServiceError(
                "OPENAI_API_KEY is missing or not configured. Add your OpenAI API key to the backend .env file.",
                503,
                "openai_not_configured",
            )
        if self._client is None:
            self._client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=180.0, max_retries=2)
        return self._client

    def verify_connection(self) -> Dict[str, Any]:
        started = time.perf_counter()
        try:
            response = self.get_client().responses.create(
                model=settings.OPENAI_MODEL,
                input="Reply with exactly: OpenAI API connection successful.",
                max_output_tokens=30,
            )
            return {
                "status": "connected",
                "model": settings.OPENAI_MODEL,
                "latency_ms": round((time.perf_counter() - started) * 1000, 1),
                "message": (response.output_text or "OpenAI API connected.").strip(),
                "usage": response.usage.model_dump() if response.usage else {},
            }
        except OpenAIServiceError:
            raise
        except RateLimitError as exc:
            raise OpenAIServiceError("OpenAI API rate limit or quota exceeded. Check your API usage and billing.", 429, "openai_rate_limit") from exc
        except (APITimeoutError, APIConnectionError) as exc:
            raise OpenAIServiceError("Could not connect to the OpenAI API. Check network connectivity and try again.", 502, "openai_connection_error") from exc
        except APIStatusError as exc:
            code = 401 if exc.status_code == 401 else 502
            raise OpenAIServiceError(f"OpenAI API returned HTTP {exc.status_code}.", code, "openai_api_error") from exc
        except OpenAIError as exc:
            raise OpenAIServiceError(f"OpenAI API request failed: {type(exc).__name__}.", 502, "openai_api_error") from exc

    def extract_pdf(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        if not file_bytes:
            raise OpenAIServiceError("The uploaded PDF is empty.", 400, "empty_file")
        if len(file_bytes) > settings.max_upload_size_bytes:
            raise OpenAIServiceError(
                f"File exceeds the configured {settings.MAX_UPLOAD_SIZE_MB} MB upload limit.",
                413,
                "file_too_large",
            )
        if not file_bytes.startswith(b"%PDF-"):
            raise OpenAIServiceError("The uploaded file does not appear to be a valid PDF.", 400, "invalid_pdf")

        client = self.get_client()
        encoded_pdf = base64.b64encode(file_bytes).decode("ascii")
        schema = TakeoffExtractionResponse.model_json_schema()
        prompt = (
            f"Analyze the attached PDF named {json.dumps(filename)}. Extract a complete construction takeoff "
            "and proposal summary using the required schema. Set filename to the supplied filename. "
            "Set status to success only if extraction completed; if some information is unclear, still return "
            "the extracted data and add warnings/review flags. Calculate summary counts from the items you return. "
            "For every section, include its actual title and the items assigned to it. all_items must contain "
            "each extracted takeoff item exactly once, including items grouped under sections. If the document "
            "contains no takeoff schedule but does contain commercial or scope information, extract any identifiable "
            "scope lines and flag uncertainty rather than inventing line items."
        )
        started = time.perf_counter()
        try:
            response = client.responses.create(
                model=settings.OPENAI_MODEL,
                input=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "input_file",
                            "filename": filename if filename.lower().endswith(".pdf") else f"{filename}.pdf",
                            "file_data": f"data:application/pdf;base64,{encoded_pdf}",
                            "detail": settings.OPENAI_PDF_DETAIL,
                        },
                        {"type": "input_text", "text": f"{EXTRACTION_INSTRUCTIONS}\n\nTASK:\n{prompt}"},
                    ],
                }],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "construction_takeoff_extraction",
                        "schema": schema,
                        "strict": False,
                    }
                },
                max_output_tokens=30000,
            )
        except RateLimitError as exc:
            raise OpenAIServiceError("OpenAI API rate limit or quota exceeded. Check your API usage and billing.", 429, "openai_rate_limit") from exc
        except (APITimeoutError, APIConnectionError) as exc:
            raise OpenAIServiceError("The OpenAI API connection timed out or failed. Please retry the PDF.", 502, "openai_connection_error") from exc
        except APIStatusError as exc:
            logger.exception("OpenAI API returned HTTP %s", exc.status_code)
            code = 401 if exc.status_code == 401 else 502
            message = "OpenAI API authentication failed. Check OPENAI_API_KEY." if exc.status_code == 401 else f"OpenAI API returned HTTP {exc.status_code}."
            raise OpenAIServiceError(message, code, "openai_api_error") from exc
        except OpenAIError as exc:
            logger.exception("OpenAI API request failed")
            raise OpenAIServiceError(f"OpenAI API request failed: {type(exc).__name__}.", 502, "openai_api_error") from exc

        output_text = response.output_text
        if not output_text:
            raise OpenAIServiceError("The model returned no structured extraction. Try again or use a smaller PDF.", 502, "empty_model_response")
        try:
            parsed = TakeoffExtractionResponse.model_validate_json(output_text)
        except (ValidationError, ValueError) as exc:
            logger.exception("Model output did not validate against the takeoff response schema")
            raise OpenAIServiceError("The model response could not be validated. Please retry this PDF.", 502, "invalid_model_response") from exc

        parsed.filename = filename
        parsed.raw_model_info = {
            "provider": "openai",
            "model": settings.OPENAI_MODEL,
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            "input_tokens": response.usage.input_tokens if response.usage else None,
            "output_tokens": response.usage.output_tokens if response.usage else None,
            "total_tokens": response.usage.total_tokens if response.usage else None,
        }
        # Build section summaries from the canonical flat item list so an item cannot silently
        # disappear from exports because the model grouped it inconsistently.
        items = parsed.all_items
        model_titles = {key: value.section_title for key, value in parsed.sections.items()}
        grouped: Dict[str, list] = {}
        for item in items:
            key = (item.section or "uncategorized").strip() or "uncategorized"
            grouped.setdefault(key, []).append(item)
        parsed.sections = {
            key: SectionSummary(
                section_key=key,
                section_title=model_titles.get(key) or key.replace("_", " ").title(),
                item_count=len(group_items),
                items_with_quantity=sum(item.quantity is not None for item in group_items),
                items_without_quantity=sum(item.quantity is None for item in group_items),
                items_needing_review=sum(bool(item.review_required) for item in group_items),
                items=group_items,
            )
            for key, group_items in grouped.items()
        }
        parsed.summary.total_items = len(items)
        parsed.summary.total_items_with_quantity = sum(item.quantity is not None for item in items)
        parsed.summary.total_items_missing_quantity = sum(item.quantity is None for item in items)
        parsed.summary.total_review_required = sum(item.review_required for item in items)
        parsed.summary.total_sections = len(parsed.sections)
        parsed.summary.total_warnings = len(parsed.warnings)
        return parsed.model_dump(mode="json")


openai_service = OpenAIService()
