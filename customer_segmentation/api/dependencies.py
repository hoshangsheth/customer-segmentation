"""FastAPI dependencies: the services live on app.state, built once at startup."""

from fastapi import HTTPException, Request

from customer_segmentation.api.service import AnalyticsService
from customer_segmentation.llm.insights import InsightsService


def get_analytics(request: Request) -> AnalyticsService:
    service = getattr(request.app.state, "analytics", None)
    if service is None:
        raise HTTPException(503, "No trained model is loaded. Run: python -m customer_segmentation.train")
    return service


def get_insights(request: Request) -> InsightsService:
    service = getattr(request.app.state, "insights", None)
    if service is None:
        raise HTTPException(503, "No trained model is loaded. Run: python -m customer_segmentation.train")
    return service
