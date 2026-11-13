"""Read-side service: turns the trained bundle's report into API responses, and scores customers."""

from customer_segmentation.api import schemas
from customer_segmentation.artifacts.store import Bundle
from customer_segmentation.explainability.shap_values import as_dicts
from customer_segmentation.scoring import CustomerRecord, score_customer


class SegmentNotFound(KeyError):
    pass


class AnalyticsService:
    def __init__(self, bundle: Bundle):
        self.bundle = bundle
        self.report = bundle.report
        self._segments = {s["segment_id"]: s for s in self.report["segmentation"]["segments"]}

    @property
    def version(self) -> str:
        return self.bundle.version

    def segment(self, segment_id: int) -> schemas.SegmentProfile:
        if segment_id not in self._segments:
            raise SegmentNotFound(segment_id)
        return schemas.SegmentProfile(**self._segments[segment_id])

    def segments(self) -> schemas.SegmentsOverview:
        seg = self.report["segmentation"]
        return schemas.SegmentsOverview(
            segments=[schemas.SegmentProfile(**s) for s in seg["segments"]],
            population=seg["population"],
            k_selection=schemas.KSelection(**seg["k_selection"]),
        )

    def projection(self) -> schemas.Projection:
        return schemas.Projection(**self.report["segmentation"]["projection"])

    def overview(self) -> schemas.Overview:
        r = self.report
        lift = r["lift"]
        top_seg = lift["segment_targeting"]["rows"][0]
        best = lift["best_profit_point"]
        return schemas.Overview(
            model_version=self.version,
            trained_at=r["created_at"],
            customers=r["data"]["customers"],
            response_rate=r["data"]["response_rate"],
            n_segments=len(self._segments),
            roc_auc=r["model"]["holdout"]["roc_auc"],
            pr_auc=r["model"]["holdout"]["pr_auc"],
            top_decile_lift=lift["deciles"][0]["lift"],
            top_segment_lift=top_seg["lift"],
            top_segment_name=top_seg["names"][0],
            best_profit_share=best["share_targeted"],
            best_profit=best["profit"],
            segments=[
                schemas.SegmentCard(
                    segment_id=s["segment_id"],
                    name=s["name"],
                    tagline=s["tagline"],
                    size=s["size"],
                    share=s["share"],
                    response_rate=s["response_rate"],
                    avg_spend=s["means"]["monetary"],
                    avg_income=s["means"]["income"],
                )
                for s in self._segments.values()
            ],
        )

    def metrics(self) -> schemas.ModelMetrics:
        m = self.report["model"]
        return schemas.ModelMetrics(
            train_size=m["train_size"],
            test_size=m["test_size"],
            cv_xgboost=schemas.CVScores(**m["cv"]["xgboost"]),
            cv_baseline=schemas.CVScores(**m["cv"]["logistic_baseline"]),
            holdout=schemas.Holdout(**m["holdout"]),
            baseline_holdout_roc_auc=m["baseline_holdout"]["roc_auc"],
            baseline_holdout_pr_auc=m["baseline_holdout"]["pr_auc"],
            global_importance=[schemas.Importance(**i) for i in m["global_importance"]],
            cleaning=self.report["data"]["cleaning"],
        )

    def lift(self) -> schemas.Lift:
        lift = self.report["lift"]
        return schemas.Lift(
            method=lift["method"],
            base_rate=lift["base_rate"],
            cost_per_contact=self.report["data"]["cost_per_contact"],
            revenue_per_response=self.report["data"]["revenue_per_response"],
            deciles=lift["deciles"],
            curve=lift["curve"],
            best_profit_point=lift["best_profit_point"],
            segment_targeting=lift["segment_targeting"],
        )

    def score_defaults(self) -> schemas.CustomerIn:
        return schemas.CustomerIn(**self.report["score_defaults"])

    def score(self, customer: schemas.CustomerIn) -> schemas.ScoreOut:
        result = score_customer(self.bundle, CustomerRecord(**customer.model_dump()))
        return schemas.ScoreOut(
            segment_id=result.segment_id,
            segment_name=result.segment_name,
            probability=result.probability,
            base_rate=result.base_rate,
            lift_vs_average=result.probability / result.base_rate if result.base_rate else 0.0,
            reasons=[schemas.Reason(**r) for r in as_dicts(result.reasons)],
        )
