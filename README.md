# GPT-First Construction Takeoff

FastAPI + React application that sends the original PDF directly to the OpenAI Responses API. The model reads the proposal (including PDF text and page images), extracts a trade-agnostic takeoff and commercial terms into structured JSON, and the application produces generic Excel/CSV exports from that data.

## What changed

- Removed the Groq SDK and Groq extraction service.
- Removed PyMuPDF from the primary extraction path. The PDF is sent directly to OpenAI as an `input_file`.
- Removed contractor-name, filename, fixed-page, and trade-specific extraction assumptions.
- Replaced contractor/trade-specific Excel layouts with generic exports driven by the extracted sections and terms.
- Removed pre-generated contractor-specific download routes; exports are generated from the uploaded PDF's extraction result.
- GPT is instructed to preserve source wording, return source-page evidence, keep options separate from base scope, and flag uncertain/missing data instead of guessing.

Python still performs deterministic data-shape validation, summary counting, and file generation. These tasks are not PDF extraction and should not be left to probabilistic model output.

## Setup (Windows PowerShell)

```powershell
cd D:\bid_leveling
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set your API key:

```dotenv
OPENAI_API_KEY=your_real_openai_api_key_here
OPENAI_MODEL=gpt-4.1
OPENAI_PDF_DETAIL=high
MAX_UPLOAD_SIZE_MB=45
```

Keep the key in the backend `.env` only. Never place it in React/Vite environment variables or commit `.env`.

## Run backend

```powershell
cd D:\bid_leveling
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

API docs: http://127.0.0.1:8000/docs
Health: http://127.0.0.1:8000/health
OpenAI connection test: http://127.0.0.1:8000/api/openai/test

## Run frontend

In a second terminal:

```powershell
cd D:\bid_leveling\frontend
npm install
npm run dev
```

Open http://localhost:5173.

## Workflow

1. Upload a proposal PDF.
2. The backend validates the file envelope and sends the original PDF directly to the OpenAI Responses API.
3. GPT returns structured JSON using the universal takeoff response schema.
4. Pydantic validates the response shape; the application recalculates summary counts from returned items.
5. Review the source-page evidence and any flagged fields in the UI.
6. Download a generic Excel workbook or CSV generated from the same extraction data.

## API key and usage

PDF processing sends the full PDF to OpenAI. PDF text and page-image processing can consume substantial tokens, especially for long PDFs and dense drawings. `OPENAI_PDF_DETAIL=high` favors detail for small print and tables; `low` may reduce image token use. Use a model available to your API account and review current pricing/limits before processing large batches.

## Important limitations

- Structured output enforces the response shape, not factual accuracy. Always compare quantities, model numbers, source pages, and financial totals against the PDF before relying on the workbook.
- Missing values should remain null and flagged. The app does not calculate missing proposal totals or invent contractor terms.
- The review endpoint recalculates review summaries for user-edited data but cannot independently re-verify edits against the source unless the PDF is submitted again.
- This implementation does not use PyMuPDF/OCR as a fallback. If the API cannot process a PDF, the API error is returned for the user to address.
