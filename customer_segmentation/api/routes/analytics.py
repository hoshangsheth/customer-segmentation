"""Read-only endpoints: overview, segments, projection, model metrics, lift."""

from fastapi import APIRouter, Depends, HTTPException

from customer_segmentation.api import schemas
from customer_segmentation.api.dependencies import get_analytics
from customer_segmentation.api.service import AnalyticsService, SegmentNotFound

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/overview", response_model=schemas.Overview)
def overview(svc: AnalyticsService = Depends(get_analytics)):
    return svc.overview()


@router.get("/segments", response_model=schemas.SegmentsOverview)
def segments(svc: AnalyticsService = Depends(get_analytics)):
    return svc.segments()


@router.get("/segments/{segment_id}", response_model=schemas.SegmentProfile)
def segment(segment_id: int, svc: AnalyticsService = Depends(get_analytics)):
    try:
        return svc.segment(segment_id)
    except SegmentNotFound:
        raise HTTPException(404, f"segment {segment_id} not found") from None


@router.get("/projection", response_model=schemas.Projection)
def projection(svc: AnalyticsService = Depends(get_analytics)):
    return svc.projection()


@router.get("/metrics", response_model=schemas.ModelMetrics)
def metrics(svc: AnalyticsService = Depends(get_analytics)):
    return svc.metrics()


@router.get("/lift", response_model=schemas.Lift)
def lift(svc: AnalyticsService = Depends(get_analytics)):
    return svc.lift()
