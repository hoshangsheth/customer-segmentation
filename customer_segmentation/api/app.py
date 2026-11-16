"""
FastAPI application factory. Artifacts are loaded once at startup; the LLM is optional.

    uvicorn customer_segmentation.api.main:app --reload
"""

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from customer_segmentation.api import schemas
from customer_segmentation.api.routes import analytics, batch, insights, scoring
from customer_segmentation.api.service import AnalyticsService
from customer_segmentation.artifacts import store
from customer_segmentation.batch.jobs import JobStore
from customer_segmentation.config import Settings, get_settings
from customer_segmentation.llm.contracts import LLMProvider
from customer_segmentation.llm.factory import build_provider
from customer_segmentation.llm.insights import InsightsService

log = logging.getLogger(__name__)

_UNSET = object()


def create_app(
    settings: Settings | None = None,
    bundle: store.Bundle | None = None,
    provider: LLMProvider | None | object = _UNSET,
) -> FastAPI:
    """`bundle` and `provider` can be injected (tests); otherwise they come from disk and settings."""
    settings = settings or get_settings()
    app = FastAPI(
        title="Customer Segmentation and Campaign Targeting",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )

    if bundle is None:
        try:
            bundle = store.load(settings.artifacts_dir, settings.artifact_version)
        except store.ArtifactsNotFound as e:
            log.warning("%s", e)
    llm = build_provider(settings) if provider is _UNSET else provider

    app.state.analytics = AnalyticsService(bundle) if bundle else None
    app.state.insights = InsightsService(llm, bundle.version) if bundle else None
    app.state.jobs = JobStore()
    if bundle:
        log.info("loaded model %s; AI insights %s", bundle.version, "on" if llm else "off")

    @app.get("/api/health", response_model=schemas.Health, tags=["health"])
    def health():
        return schemas.Health(
            status="ok",
            model_version=bundle.version if bundle else "",
            ai_available=llm is not None,
            ai_provider=getattr(llm, "name", None),
        )

    for router in (analytics.router, scoring.router, insights.router, batch.router):
        app.include_router(router)
    serve_frontend(app, settings.frontend_dist)
    return app


def serve_frontend(app: FastAPI, dist: Path) -> None:
    """Serve the built web app (npm run build) from the API, so production is one process and one URL."""
    index = dist / "index.html"
    if not index.exists():
        return
    app.mount("/assets", CachedStatic(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Not found")
        file = (dist / path).resolve()
        if path and file.is_file() and file.is_relative_to(dist.resolve()):
            return FileResponse(file)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})


class CachedStatic(StaticFiles):
    """Hashed build assets never change, so browsers may keep them for a year."""

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response
