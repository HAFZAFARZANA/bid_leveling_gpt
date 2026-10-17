from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.core.config import settings


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="GPT-first construction proposal extraction, review, and takeoff export API.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router)
    dist_dir = Path("frontend/dist")
    if dist_dir.exists() and (dist_dir / "assets").exists():
        application.mount("/assets", StaticFiles(directory=dist_dir / "assets"), name="assets")
    if dist_dir.exists() and (dist_dir / "samples").exists():
        application.mount("/samples", StaticFiles(directory=dist_dir / "samples"), name="samples")

    @application.get("/")
    async def root():
        index_file = dist_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file, media_type="text/html")
        return await api_status()

    @application.get("/api-status")
    async def api_status() -> JSONResponse:
        return JSONResponse(content={
            "message": "Welcome to the GPT-first Construction Takeoff API",
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "docs": "/docs",
            "health": "/health",
            "openai_test": "/api/openai/test",
            "takeoff_extract": "/api/takeoff/extract",
            "openai_configured": settings.is_openai_configured,
        })

    return application


app = create_application()
