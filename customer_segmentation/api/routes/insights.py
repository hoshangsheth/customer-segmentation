"""AI insights. Always answer: rule-based text when no LLM is configured or it fails."""

from fastapi import APIRouter, Depends, HTTPException

from customer_segmentation.api import schemas
from customer_segmentation.api.dependencies import get_analytics, get_insights
from customer_segmentation.api.service import AnalyticsService, SegmentNotFound
from customer_segmentation.llm.insights import InsightsService

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("/segments/{segment_id}", response_model=schemas.Persona)
def segment_persona(
    segment_id: int,
    svc: AnalyticsService = Depends(get_analytics),
    insights: InsightsService = Depends(get_insights),
):
    try:
        profile = svc.segment(segment_id)
    except SegmentNotFound:
        raise HTTPException(404, f"segment {segment_id} not found") from None
    population = svc.segments().population
    result = insights.segment_persona(profile.model_dump(), population)
    return schemas.Persona(segment_id=profile.segment_id, segment_name=profile.name, **result)


@router.post("/explain", response_model=schemas.Explanation)
def explain(
    customer: schemas.CustomerIn,
    svc: AnalyticsService = Depends(get_analytics),
    insights: InsightsService = Depends(get_insights),
):
    score = svc.score(customer)
    result = insights.explain_score(score.model_dump())
    return schemas.Explanation(score=score, **result)
