"""API routes for universal GPT-first construction proposal extraction and exports."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.schemas.takeoff import (
    TakeoffExportRequest,
    TakeoffExtractionResponse,
    TakeoffReviewRequest,
)
from app.services.export_service import export_service
from app.services.openai_service import OpenAIServiceError, openai_service

router = APIRouter()


class HealthResponse(BaseModel):
    status: str = "healthy"
    service: str = settings.APP_NAME
    version: str = settings.APP_VERSION
    environment: str = settings.ENVIRONMENT
    openai_configured: bool
    openai_model: str


class OpenAITestResponse(BaseModel):
    status: str
    model: str
    latency_ms: float
    message: str
    usage: Dict[str, Any] = Field(default_factory=dict)


def _safe_filename(name: Optional[str], default: str = "takeoff") -> str:
    clean = re.sub(r'[\\/*?:"<>|]', "", name or "").strip()
    if clean.lower().endswith((".pdf", ".xlsx", ".csv")):
        clean = clean.rsplit(".", 1)[0]
    return clean or default


def _raise_ai_error(exc: OpenAIServiceError) -> None:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"status": "error", "error_code": exc.error_code, "message": exc.message},
    ) from exc


async def _read_pdf(file: UploadFile) -> tuple[str, bytes]:
    filename = file.filename or "proposal.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail={"status": "error", "error_code": "invalid_file_type", "message": "Only PDF files are accepted."})
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail={"status": "error", "error_code": "empty_file", "message": "The uploaded PDF is empty."})
    if len(file_bytes) > settings.max_upload_size_bytes:
        raise HTTPException(status_code=413, detail={"status": "error", "error_code": "file_too_large", "message": f"PDF exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB upload limit."})
    return filename, file_bytes


@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    return HealthResponse(openai_configured=settings.is_openai_configured, openai_model=settings.OPENAI_MODEL)


@router.get("/api/health", response_model=HealthResponse, include_in_schema=False)
async def api_health_check() -> HealthResponse:
    return await health_check()


@router.get("/api/openai/test", response_model=OpenAITestResponse, tags=["OpenAI Integration"])
async def test_openai_connection() -> OpenAITestResponse:
    try:
        return OpenAITestResponse(**openai_service.verify_connection())
    except OpenAIServiceError as exc:
        _raise_ai_error(exc)


@router.post(
    "/api/takeoff/extract",
    response_model=TakeoffExtractionResponse,
    summary="Extract a construction takeoff directly from a PDF with GPT",
    tags=["Takeoff Extraction"],
)
async def extract_takeoff(file: UploadFile = File(...)) -> TakeoffExtractionResponse:
    filename, file_bytes = await _read_pdf(file)
    try:
        result = openai_service.extract_pdf(file_bytes, filename)
        return TakeoffExtractionResponse.model_validate(result)
    except OpenAIServiceError as exc:
        _raise_ai_error(exc)


@router.post("/api/takeoff/review", response_model=TakeoffExtractionResponse, tags=["Takeoff Review"])
async def review_takeoff(payload: TakeoffReviewRequest) -> TakeoffExtractionResponse:
    """Rebuild summary data from edited items without trade-specific classification rules."""
    items = payload.items
    sections: Dict[str, Dict[str, Any]] = {}
    warnings: List[str] = []
    for index, item in enumerate(items, 1):
        section_key = item.section.strip() or "uncategorized"
        entry = sections.setdefault(section_key, {"items": [], "title": section_key.replace("_", " ").title()})
        item.review_reasons = list(item.review_reasons or [])
        entry["items"].append(item)
    from app.schemas.takeoff import SectionSummary, TakeoffExtractionSummary
    section_models = {}
    for key, entry in sections.items():
        grouped = entry["items"]
        section_models[key] = SectionSummary(
            section_key=key,
            section_title=entry["title"],
            item_count=len(grouped),
            items_with_quantity=sum(x.quantity is not None for x in grouped),
            items_without_quantity=sum(x.quantity is None for x in grouped),
            items_needing_review=sum(bool(x.review_required) for x in grouped),
            items=grouped,
        )
    warnings.extend(f"Item {item.item_number or idx}: requires review — {'; '.join(item.review_reasons)}" for idx, item in enumerate(items, 1) if item.review_required)
    summary = TakeoffExtractionSummary(
        total_items=len(items),
        total_sections=len(section_models),
        total_items_with_quantity=sum(x.quantity is not None for x in items),
        total_items_missing_quantity=sum(x.quantity is None for x in items),
        total_review_required=sum(bool(x.review_required) for x in items),
        total_warnings=len(warnings),
    )
    return TakeoffExtractionResponse(
        status="success",
        filename=payload.filename or "takeoff.pdf",
        total_pages_processed=payload.total_pages_processed or max((x.source_page for x in items if x.source_page is not None), default=1),
        project_metadata=payload.project_metadata,
        summary=summary,
        sections=section_models,
        all_items=items,
        warnings=warnings,
        proposal_terms=payload.proposal_terms,
        raw_model_info={"provider": "openai", "note": "Manual review changes; source PDF was not resubmitted for AI verification."},
    )


@router.post("/api/takeoff/export/excel", tags=["Takeoff Export"])
async def export_takeoff_excel(payload: TakeoffExportRequest) -> Response:
    try:
        content = export_service.generate_excel(payload)
        name = _safe_filename(payload.filename or payload.project_metadata.project_name)
        return Response(content=content, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{name}_takeoff.xlsx"', "Access-Control-Expose-Headers": "Content-Disposition", "Cache-Control": "no-store"})
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"status": "error", "error_code": "export_failed", "message": "Failed to generate Excel export."}) from exc


@router.post("/api/takeoff/export/csv", tags=["Takeoff Export"])
async def export_takeoff_csv(payload: TakeoffExportRequest) -> Response:
    try:
        content = export_service.generate_csv(payload).encode("utf-8-sig")
        name = _safe_filename(payload.filename or payload.project_metadata.project_name)
        return Response(content=content, media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{name}_takeoff.csv"', "Access-Control-Expose-Headers": "Content-Disposition", "Cache-Control": "no-store"})
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"status": "error", "error_code": "export_failed", "message": "Failed to generate CSV export."}) from exc


@router.post("/api/takeoff/extract-and-export", tags=["Takeoff Export"])
async def extract_and_export(file: UploadFile = File(...), format: str = Query("xlsx", pattern="^(xlsx|csv)$")) -> Response:
    filename, file_bytes = await _read_pdf(file)
    try:
        result = TakeoffExtractionResponse.model_validate(openai_service.extract_pdf(file_bytes, filename))
    except OpenAIServiceError as exc:
        _raise_ai_error(exc)
    try:
        content = export_service.generate_csv(result).encode("utf-8-sig") if format == "csv" else export_service.generate_excel(result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"status": "error", "error_code": "export_failed", "message": "Extraction succeeded but export generation failed."}) from exc
    name = _safe_filename(filename)
    if format == "csv":
        return Response(content=content, media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{name}_takeoff.csv"'})
    return Response(content=content, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{name}_takeoff.xlsx"'})


@router.post("/api/takeoff/extract-batch", tags=["Takeoff Extraction"])
async def extract_batch(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    documents = []
    for upload in files:
        filename, file_bytes = await _read_pdf(upload)
        try:
            result = openai_service.extract_pdf(file_bytes, filename)
            documents.append(result)
        except OpenAIServiceError as exc:
            documents.append({"status": "error", "filename": filename, "error_code": exc.error_code, "message": exc.message})
    return {"status": "success", "total_files_received": len(files), "documents": documents}


