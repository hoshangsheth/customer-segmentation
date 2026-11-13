"""Score a new customer."""

from fastapi import APIRouter, Depends

from customer_segmentation.api import schemas
from customer_segmentation.api.dependencies import get_analytics
from customer_segmentation.api.service import AnalyticsService

router = APIRouter(prefix="/api/score", tags=["scoring"])


@router.get("/defaults", response_model=schemas.CustomerIn)
def defaults(svc: AnalyticsService = Depends(get_analytics)):
    """The median customer, to prefill a form."""
    return svc.score_defaults()


@router.post("", response_model=schemas.ScoreOut)
def score(customer: schemas.CustomerIn, svc: AnalyticsService = Depends(get_analytics)):
    return svc.score(customer)
