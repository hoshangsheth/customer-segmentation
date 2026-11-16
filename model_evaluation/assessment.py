"""
5. Model assessment: a pass or fail scorecard against quality gates fixed in advance.

The thresholds below were written before the suite was first run on the real data and are not tuned to
the results. A failed gate is reported as failed.
"""

from __future__ import annotations

import operator
from dataclasses import dataclass
from typing import Any

OPS = {">=": operator.ge, "<=": operator.le}


@dataclass(frozen=True)
class Gate:
    id: str
    area: str
    check: str
    path: tuple[str, ...]
    op: str
    threshold: float
    why: str


GATES: list[Gate] = [
    Gate(
        "E1",
        "Evaluation",
        "Holdout ROC AUC",
        ("evaluation", "response_model", "ranking", "roc_auc"),
        ">=",
        0.85,
        "Strong ranking of responders on unseen customers",
    ),
    Gate(
        "E2",
        "Evaluation",
        "Holdout ROC AUC, lower 95% bound",
        ("evaluation", "response_model", "ranking", "roc_auc_ci95", "0"),
        ">=",
        0.80,
        "Good ranking even at the pessimistic end of the interval",
    ),
    Gate(
        "E3",
        "Evaluation",
        "Holdout PR AUC as a multiple of the base rate",
        ("derived", "pr_auc_over_base"),
        ">=",
        3.0,
        "Precision far above random on a 15% positive class",
    ),
    Gate(
        "E4",
        "Evaluation",
        "Brier skill score vs predicting the base rate",
        ("evaluation", "response_model", "ranking", "brier_skill_score"),
        ">=",
        0.20,
        "Probabilities carry real information",
    ),
    Gate(
        "E5",
        "Evaluation",
        "Segmentation silhouette",
        ("evaluation", "segmentation", "silhouette"),
        ">=",
        0.10,
        "Segments are separated, not arbitrary slices",
    ),
    Gate(
        "E6",
        "Evaluation",
        "Smallest segment share",
        ("evaluation", "segmentation", "smallest_share"),
        ">=",
        0.10,
        "Every segment is big enough to run a campaign on",
    ),
    Gate(
        "P1",
        "Performance",
        "Top-10% lift, lower 95% bound",
        ("performance", "targeting", "top10_lift_ci95", "0"),
        ">=",
        3.0,
        "Targeting the top decile clearly beats contacting everyone",
    ),
    Gate(
        "P2",
        "Performance",
        "Best campaign profit vs contacting everyone ($)",
        ("derived", "profit_gain"),
        ">=",
        0.0,
        "Model-led targeting pays for itself",
    ),
    Gate(
        "P3",
        "Performance",
        "Expected calibration error (holdout)",
        ("performance", "calibration", "expected_calibration_error"),
        "<=",
        0.05,
        "Scores can be read as response rates",
    ),
    Gate(
        "P4",
        "Performance",
        "Std of ROC AUC over 25 repeated-CV fits",
        ("performance", "stability", "roc_auc", "std"),
        "<=",
        0.03,
        "Performance does not hinge on a lucky split",
    ),
    Gate(
        "P5",
        "Performance",
        "Best segment lift on the test split",
        ("performance", "segment_targeting", "rows", "0", "lift"),
        ">=",
        1.2,
        "Segments alone deliver at least a 20% lift",
    ),
    Gate(
        "T1",
        "Testing",
        "Same-seed retrain, max prediction difference",
        ("testing", "reproducibility", "same_seed_max_abs_diff"),
        "<=",
        1e-9,
        "Training is deterministic",
    ),
    Gate(
        "T2",
        "Testing",
        "Shipped artifact vs fresh retrain, max difference",
        ("testing", "reproducibility", "artifact_vs_retrain_max_abs_diff"),
        "<=",
        1e-6,
        "The served model is exactly the evaluated one",
    ),
    Gate(
        "T3",
        "Testing",
        "Label-shuffle AUC, max distance from 0.5",
        ("testing", "label_shuffle", "max_abs_dev_from_0.5"),
        "<=",
        0.08,
        "No leakage: the model learns nothing from shuffled labels",
    ),
    Gate(
        "T4",
        "Testing",
        "Rank correlation under 5% feature noise",
        ("testing", "noise_robustness", "spearman"),
        ">=",
        0.95,
        "Small measurement noise does not reshuffle the target list",
    ),
    Gate(
        "T5",
        "Testing",
        "Share where an extra past acceptance does not lower the score",
        ("testing", "directional", "extra_prior_acceptance", "share_not_decreased"),
        ">=",
        0.90,
        "Behaves as marketing expects",
    ),
    Gate(
        "T6",
        "Testing",
        "Share where 30 more days of inactivity does not raise the score",
        ("testing", "directional", "recency_plus_30_days", "share_not_increased"),
        ">=",
        0.80,
        "Lapsing customers are scored lower",
    ),
    Gate(
        "T7",
        "Testing",
        "Batch vs single-row scoring, max difference",
        ("testing", "batch_invariance", "batch_vs_single_max_abs_diff"),
        "<=",
        1e-9,
        "API single scores match batch scores",
    ),
    Gate(
        "T8",
        "Testing",
        "SHAP additivity error (logit)",
        ("testing", "shap_additivity", "max_abs_error_logit"),
        "<=",
        1e-3,
        "Explanations add up to the prediction",
    ),
    Gate(
        "T9",
        "Testing",
        "Edge-case customers scored cleanly",
        ("derived", "edge_ok"),
        ">=",
        1.0,
        "No errors or NaNs on extreme valid inputs",
    ),
    Gate(
        "T10",
        "Testing",
        "Segmentation ARI across 10 seeds, minimum",
        ("testing", "segmentation_stability", "seed_ari_min"),
        ">=",
        0.80,
        "Segments do not depend on the random seed",
    ),
    Gate(
        "T11",
        "Testing",
        "Segmentation ARI on 80% subsamples, minimum",
        ("testing", "segmentation_stability", "subsample_ari_min"),
        ">=",
        0.70,
        "Segments survive a change of sample",
    ),
    Gate(
        "T12",
        "Testing",
        "Lowest ROC AUC across customer slices",
        ("testing", "slices", "min_slice_roc_auc"),
        ">=",
        0.75,
        "No customer group where the model fails",
    ),
    Gate(
        "B1",
        "Benchmarking",
        "Shipped model beats the best no-model rule (mean ROC AUC gap)",
        ("derived", "gap_vs_best_rule"),
        ">=",
        0.02,
        "Machine learning adds value over business rules",
    ),
    Gate(
        "B2",
        "Benchmarking",
        "Shipped model within 0.01 ROC AUC of the best learner",
        ("derived", "gap_to_best_model"),
        ">=",
        -0.01,
        "No other tested learner is clearly better",
    ),
    Gate(
        "B3",
        "Benchmarking",
        "Single-customer scoring p95 latency (ms)",
        ("benchmarking", "compute", "single_customer_score", "p95_ms"),
        "<=",
        50.0,
        "Fast enough for interactive scoring",
    ),
    Gate(
        "B4",
        "Benchmarking",
        "POST /api/score p95 latency, in process (ms)",
        ("benchmarking", "compute", "api_latency_in_process", "POST /api/score", "p95_ms"),
        "<=",
        100.0,
        "API answers well within a page interaction",
    ),
    Gate(
        "B5",
        "Benchmarking",
        "Full training pipeline (s)",
        ("benchmarking", "compute", "training_pipeline_seconds"),
        "<=",
        300.0,
        "Retraining is cheap",
    ),
]


def _get(data: Any, path: tuple[str, ...]) -> Any:
    for key in path:
        data = data[int(key)] if isinstance(data, list | tuple) else data[key]
    return data


def derived(results: dict) -> dict:
    ev, perf, test, bench = results["evaluation"], results["performance"], results["testing"], results["benchmarking"]
    rank = ev["response_model"]["ranking"]
    rows = {r["model"]: r for r in bench["models"]["rows"]}
    ship = rows["XGBoost (shipped)"]["roc_auc_mean"]
    rules = [r["roc_auc_mean"] for name, r in rows.items() if name.startswith("Rule")]
    learners = [r["roc_auc_mean"] for name, r in rows.items() if not name.startswith(("Rule", "Dummy"))]
    return {
        "pr_auc_over_base": rank["pr_auc"] / rank["base_rate"],
        "profit_gain": perf["targeting"]["best_profit_point"]["profit"]
        - perf["targeting"]["contact_everyone"]["profit"],
        "edge_ok": 1.0 if test["edge_inputs"]["all_ok"] else 0.0,
        "gap_vs_best_rule": ship - max(rules),
        "gap_to_best_model": ship - max(learners),
    }


def run(results: dict) -> dict:
    results = {**results, "derived": derived(results)}
    scorecard = []
    for g in GATES:
        value = float(_get(results, g.path))
        scorecard.append(
            {
                "id": g.id,
                "area": g.area,
                "check": g.check,
                "value": value,
                "op": g.op,
                "threshold": g.threshold,
                "passed": bool(OPS[g.op](value, g.threshold)),
                "why": g.why,
            }
        )
    by_area: dict[str, dict[str, int]] = {}
    for row in scorecard:
        a = by_area.setdefault(row["area"], {"passed": 0, "total": 0})
        a["total"] += 1
        a["passed"] += row["passed"]
    passed = sum(r["passed"] for r in scorecard)
    return {
        "derived": results["derived"],
        "scorecard": scorecard,
        "by_area": by_area,
        "passed": passed,
        "total": len(scorecard),
        "verdict": "ready"
        if passed == len(scorecard)
        else "ready with noted exceptions"
        if passed >= 0.9 * len(scorecard)
        else "not ready",
    }
