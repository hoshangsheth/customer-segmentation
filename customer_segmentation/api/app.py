"""
FastAPI application factory. Artifacts are loaded once at startup; the LLM is optional.

    uvicorn customer_segmentation.api.main:app --reload
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from customer_segmentation.api import schemas
from customer_segmentation.api.routes import analytics, insights, scoring
from customer_segmentation.api.service import AnalyticsService
from customer_segmentation.artifacts import store
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
    app = FastAPI(title="Customer Segmentation and Campaign Targeting", version="1.0.0")
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origin_list, allow_methods=["GET", "POST"], allow_headers=["*"]
    )

    if bundle is None:
        try:
            bundle = store.load(settings.artifacts_dir, settings.artifact_version)
        except store.ArtifactsNotFound as e:
            log.warning("%s", e)
    llm = build_provider(settings) if provider is _UNSET else provider

    app.state.analytics = AnalyticsService(bundle) if bundle else None
    app.state.insights = InsightsService(llm, bundle.version) if bundle else None
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

    for router in (analytics.router, scoring.router, insights.router):
        app.include_router(router)
    return app
