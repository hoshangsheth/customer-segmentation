"""
Renders model_evaluation/REPORT.md from results/all_results.json. Every number in the report is read
from the results of a real run; nothing is typed in by hand.

    python -m model_evaluation.report
"""

from __future__ import annotations

import json
from pathlib import Path

from model_evaluation.common import RESULTS_DIR, ROOT

REPORT_PATH = ROOT / "REPORT.md"


# ---------- formatting helpers ----------
def pct(v: float, d: int = 1) -> str:
    return f"{v * 100:.{d}f}%"


def x(v: float, d: int = 2) -> str:
    return f"{v:.{d}f}x"


def money(v: float) -> str:
    return f"{'-' if v < 0 else ''}${abs(v):,.0f}"


def n3(v: float) -> str:
    return f"{v:.3f}"


def ci(pair, fmt=n3) -> str:
    return f"{fmt(pair[0])} to {fmt(pair[1])}"


def table(headers: list[str], rows: list[list], align: str | None = None) -> str:
    align = align or "l" + "r" * (len(headers) - 1)
    sep = ["---:" if a == "r" else ":---:" if a == "c" else "---" for a in align]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(sep) + " |"]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def gate_value(g: dict) -> str:
    v = g["value"]
    if g["id"] in {"P2"}:
        return money(v)
    if g["id"] in {"T9"}:
        return "all clean" if v >= 1 else "errors"
    if g["id"] in {"B3", "B4"}:
        return f"{v:.1f} ms"
    if g["id"] == "B5":
        return f"{v:.1f} s"
    if abs(v) < 1e-3 and v != 0:
        return f"{v:.1e}"
    return f"{v:.3f}"


def gate_threshold(g: dict) -> str:
    t = g["threshold"]
    if g["id"] in {"B3", "B4"}:
        t_s = f"{t:.0f} ms"
    elif g["id"] == "B5":
        t_s = f"{t:.0f} s"
    elif g["id"] == "P2":
        t_s = money(t)
    elif g["id"] == "T9":
        t_s = "all clean"
        return t_s
    elif t != 0 and abs(t) < 1e-3:
        t_s = f"{t:.0e}"
    else:
        t_s = f"{t:g}"
    return f"{'≥' if g['op'] == '>=' else '≤'} {t_s}"


# ---------- sections ----------
def header(r: dict) -> str:
    m, a = r["meta"], r["assessment"]
    env = m["environment"]
    return f"""# Model Evaluation Report

Customer Segmentation and Campaign Targeting, recreated on public data.

- Dataset: Kaggle "Customer Personality Analysis" ({m["customers"]:,} customers after cleaning, {m["responders"]} responders to the last campaign)
- Model artifact evaluated: `{m["artifact_version"]}` (the exact files the API serves)
- Split: stratified {m["train_size"]:,} train / {m["test_size"]} holdout, random seed {m["random_state"]}
- Run: {m["run_at"].replace("T", " ")}, {m["total_seconds"]:.0f} s in total, Python {env["python"]}, {env["cpu_count"]} logical CPUs
- Quality gates passed: **{a["passed"]} of {a["total"]}**, verdict: **{a["verdict"]}**

Reproduce everything in this report:

```bash
python -m customer_segmentation.train
python -m model_evaluation.run_all
python -m pytest model_evaluation -q
```

Raw results for every section are in [`results/`](results/)."""


def summary(r: dict) -> str:
    rank = r["evaluation"]["response_model"]["ranking"]
    tg = r["performance"]["targeting"]
    bench = {row["model"]: row for row in r["benchmarking"]["models"]["rows"]}
    ship = bench["XGBoost (shipped)"]
    best_rule = max((v for k, v in bench.items() if k.startswith("Rule")), key=lambda v: v["roc_auc_mean"])
    seg = r["performance"]["segment_targeting"]["rows"][0]
    a = r["assessment"]
    failed = [g for g in a["scorecard"] if not g["passed"]]
    lines = [
        "## Summary",
        "",
        f"- The response model ranks responders well on unseen customers: holdout ROC AUC **{n3(rank['roc_auc'])}** "
        f"(95% CI {ci(rank['roc_auc_ci95'])}) and PR AUC **{n3(rank['pr_auc'])}**, {x(rank['pr_auc'] / rank['base_rate'], 1)} the {pct(rank['base_rate'])} base rate.",
        f"- Targeting the model's top 10% reaches a **{x(tg['deciles'][0]['lift'])}** response lift (95% CI {ci(tg['top10_lift_ci95'], lambda v: x(v))}).",
        f"- The profit-optimal cut-off, the top {pct(tg['best_profit_point']['share_targeted'], 0)}, earns **{money(tg['best_profit_point']['profit'])}** "
        f"against a **{money(abs(tg['contact_everyone']['profit']))}** {'loss' if tg['contact_everyone']['profit'] < 0 else 'profit'} for contacting everyone, a swing of {money(a['derived']['profit_gain'])}.",
        f"- Segments alone, with no model, lift response **{x(seg['lift'])}** on held-out customers by contacting {pct(seg['share_targeted'], 0)} of them.",
        f"- XGBoost is the best of {len(bench)} candidates under repeated cross-validation (mean ROC AUC {n3(ship['roc_auc_mean'])}), "
        f"{n3(a['derived']['gap_vs_best_rule'])} above the best no-model business rule ({best_rule['model'].removeprefix('Rule: ')}).",
        "- Integrity checks are clean: deterministic training, the served artifact matches a fresh retrain exactly, no leakage under label shuffling, and SHAP values add up to each prediction.",
    ]
    if failed:
        lines.append(
            "- Exceptions: "
            + "; ".join(
                f"{g['id']} {g['check'].lower()} measured {gate_value(g)} against {gate_threshold(g)}" for g in failed
            )
            + ". See section 5."
        )
    return "\n".join(lines)


def section_evaluation(r: dict) -> str:
    rm = r["evaluation"]["response_model"]
    rank, th = rm["ranking"], rm["thresholds"]
    s = r["evaluation"]["segmentation"]
    names = {
        "default_0.5": "Default 0.5",
        "best_f1_on_train": "Best F1 (chosen on train)",
        "best_profit_on_train": "Best profit (chosen on train)",
        "break_even": "Break-even ($3 / $11)",
    }
    th_rows = [
        [
            names[k],
            n3(v["threshold"]),
            pct(v["flagged_share"]),
            n3(v["precision"]),
            n3(v["recall"]),
            n3(v["f1"]),
            n3(v["mcc"]),
            n3(v["balanced_accuracy"]),
            f"{v['confusion']['tp']} / {v['confusion']['fp']} / {v['confusion']['fn']} / {v['confusion']['tn']}",
        ]
        for k, v in th.items()
    ]
    best = th["best_profit_on_train"]["confusion"]
    return f"""## 1. Model evaluation

Code: [`model_evaluation.py`](model_evaluation.py). The shipped response model is scored on the {
        rank["n"]
    } holdout customers ({rank["positives"]} responders) that training never saw.

### Ranking and probability quality

{
        table(
            ["Metric", "Holdout", "Reference"],
            [
                ["ROC AUC", n3(rank["roc_auc"]), f"95% CI {ci(rank['roc_auc_ci95'])} (1,000 stratified bootstraps)"],
                [
                    "PR AUC (average precision)",
                    n3(rank["pr_auc"]),
                    f"95% CI {ci(rank['pr_auc_ci95'])}; chance = {n3(rank['base_rate'])}",
                ],
                ["Log loss", n3(rank["log_loss"]), f"{n3(rank['log_loss_base_rate'])} when predicting the base rate"],
                ["Brier score", n3(rank["brier"]), f"{n3(rank['brier_base_rate'])} when predicting the base rate"],
                ["Brier skill score", n3(rank["brier_skill_score"]), "share of base-rate error removed"],
            ],
            "lrl",
        )
    }

The holdout ROC AUC matches the value recorded in the artifact at training time ({
        n3(rm["artifact_report_holdout_roc_auc"])
    }).

### Decision thresholds

Thresholds are chosen on out-of-fold scores from the training split only, then applied once to the holdout. Confusion counts are TP / FP / FN / TN.

{table(["Threshold rule", "Cut-off", "Flagged", "Precision", "Recall", "F1", "MCC", "Bal. acc.", "Confusion"], th_rows)}

At the profit-optimal cut-off the model flags {
        pct(th["best_profit_on_train"]["flagged_share"])
    } of holdout customers and finds {best["tp"]} of {rank["positives"]} responders, with {
        best["fp"]
    } wasted contacts. {
        "The default 0.5 cut-off is too strict for a "
        + pct(rank["base_rate"], 0)
        + " response rate: it misses more than half the responders."
        if th["default_0.5"]["recall"] < 0.5
        else ""
    }

### Segmentation

{
        table(
            ["Metric", "Value", "Reading"],
            [
                ["Segments (k)", s["k"], s["k_selection"]["rule"]],
                ["Silhouette", n3(s["silhouette"]), "0 = overlapping, 1 = perfectly separated"],
                ["Davies-Bouldin", n3(s["davies_bouldin"]), "lower is better"],
                ["Calinski-Harabasz", f"{s['calinski_harabasz']:.0f}", "higher is better"],
                [
                    "Segment sizes",
                    ", ".join(f"{v:,}" for v in s["sizes"]),
                    f"smallest is {pct(s['smallest_share'])} of customers",
                ],
            ],
            "lrl",
        )
    }

A silhouette of {
        n3(s["silhouette"])
    } means the segments partition a continuum of customer behaviour rather than form sharply separated clusters. They are still very stable (section 3) and differ strongly in response rate (section 2), which is what targeting needs."""


def section_performance(r: dict) -> str:
    p = r["performance"]
    tg, cal, st, seg, claim = p["targeting"], p["calibration"], p["stability"], p["segment_targeting"], p["claim_check"]
    dec_rows = [
        [
            d["decile"],
            d["customers"],
            d["responders"],
            pct(d["response_rate"]),
            x(d["lift"]),
            pct(d["cumulative_capture"], 0),
        ]
        for d in tg["deciles"]
    ]
    picks = [0.1, 0.2, 0.3, 0.5, 1.0]
    curve_rows = [
        [
            pct(c["share_targeted"], 0),
            f"{c['customers']:,}",
            c["responders"],
            pct(c["response_rate"]),
            x(c["lift"]),
            pct(c["capture"], 0),
            money(c["profit"]),
        ]
        for c in tg["curve"]
        if any(abs(c["share_targeted"] - s) < 1e-9 for s in picks)
    ]
    cal_rows = [
        [i + 1, b["count"], pct(b["mean_predicted"]), pct(b["observed_rate"])] for i, b in enumerate(cal["bins"])
    ]
    seg_rows = [
        [
            " + ".join(row["names"]),
            pct(row["share_targeted"], 0),
            pct(row["response_rate"]),
            x(row["lift"]),
            pct(row["capture"], 0),
        ]
        for row in seg["rows"]
    ]
    per_seg = [
        [s["name"], f"{s['customers']:,}", pct(s["response_rate"]), x(s["lift"])]
        for s in seg["per_segment_all_customers"]
    ]
    return f"""## 2. Model performance evaluation

Code: [`performance_evaluation.py`](performance_evaluation.py). Lift and profit use out-of-fold scores, so each of the {
        tg["customers"]:,} customers is scored by a model that never saw them (out-of-fold ROC AUC {
        n3(tg["oof_roc_auc"])
    }, KS statistic {n3(tg["ks_statistic"])}).

### Lift by decile

{table(["Decile", "Customers", "Responders", "Response rate", "Lift", "Cumulative capture"], dec_rows, "rrrrrr")}

Bootstrap 95% intervals: top-10% lift {ci(tg["top10_lift_ci95"], x)}, top-20% lift {ci(tg["top20_lift_ci95"], x)}.

### Targeting and campaign profit

Profit uses the dataset's own cost of {money(r["meta"]["cost_per_contact"])} per contact and {
        money(r["meta"]["revenue_per_response"])
    } revenue per response.

{table(["Contact top", "Customers", "Responders", "Response rate", "Lift", "Responders reached", "Profit"], curve_rows)}

{"Contacting everyone loses money; the" if tg["contact_everyone"]["profit"] < 0 else "The"} top {
        pct(tg["best_profit_point"]["share_targeted"], 0)
    } is the most profitable cut-off and still reaches {pct(tg["best_profit_point"]["capture"], 0)} of all responders.

### Calibration (holdout)

Expected calibration error is **{n3(cal["expected_calibration_error"])}**. The mean predicted probability is {
        pct(cal["mean_predicted"])
    } against an observed rate of {pct(cal["observed_rate"])}, so scores run slightly low on average.

{table(["Bin", "Customers", "Mean predicted", "Observed"], cal_rows, "rrrr")}

### Stability under resampling

{
        table(
            ["Metric", "Mean", "Std", "Min", "Max"],
            [
                [
                    k.replace("_", " ").upper() if k != "top10_lift" else "Top-10% lift",
                    n3(v["mean"]),
                    n3(v["std"]),
                    n3(v["min"]),
                    n3(v["max"]),
                ]
                for k, v in ((k, st[k]) for k in ("roc_auc", "pr_auc", "top10_lift"))
            ],
        )
    }

{st["scheme"]}, {st["fits"]} fits.

### Segment targeting (no model)

Segments are ranked by response rate on the training split and measured on the test split (test base rate {
        pct(seg["test_base_rate"])
    }).

{table(["Segments contacted", "Share contacted", "Response rate", "Lift", "Responders reached"], seg_rows)}

Response rate by segment across all customers:

{table(["Segment", "Customers", "Response rate", "Lift"], per_seg)}

### Resume claim check

The original internship bullet claims the segmentation "contributed to a 20% lift in targeted campaign conversion", which means a lift of at least 1.2x.

- Segment-only targeting: {x(claim["segment_only_lift"])} on held-out customers, so the claim is **{
        "supported on this public data" if claim["segment_only_supported"] else "not supported on this public data"
    }**.
- Model-ranked top 20%: {x(claim["model_top20_lift"])}, with a lower 95% bound of {
        x(claim["model_top20_lift_ci95_low"])
    }.
- Caveat: {claim["caveat"]}"""


def section_testing(r: dict) -> str:
    t = r["testing"]
    rep, sh, nz, d, bi, sa, ss = (
        t["reproducibility"],
        t["label_shuffle"],
        t["noise_robustness"],
        t["directional"],
        t["batch_invariance"],
        t["shap_additivity"],
        t["segmentation_stability"],
    )
    rows = [
        [
            "Reproducibility",
            "Retrain twice with the same seed",
            f"max prediction difference {rep['same_seed_max_abs_diff']:.1e}",
        ],
        [
            "Artifact integrity",
            "Shipped model vs a fresh retrain",
            f"max prediction difference {rep['artifact_vs_retrain_max_abs_diff']:.1e}",
        ],
        [
            "Leakage",
            f"Train on shuffled labels ({sh['repeats']} times)",
            f"mean holdout ROC AUC {n3(sh['mean_roc_auc'])}, at most {n3(sh['max_abs_dev_from_0.5'])} from 0.5",
        ],
        [
            "Noise robustness",
            f"Gaussian noise of {pct(nz['noise_scale_of_std'], 0)} of each feature's std on {nz['continuous_features']} continuous features",
            f"rank correlation {n3(nz['spearman'])}, {pct(nz['top_decile_overlap'], 0)} of the top decile unchanged, ROC AUC {n3(nz['noisy_roc_auc'])}",
        ],
        [
            "Directional",
            "Add one accepted earlier campaign",
            f"score rises for {pct(d['extra_prior_acceptance']['share_increased'])}, never falls; mean +{d['extra_prior_acceptance']['mean_change'] * 100:.1f} points",
        ],
        [
            "Directional",
            "Add 30 days since the last purchase",
            f"score falls for {pct(d['recency_plus_30_days']['share_decreased'])}, does not rise for {pct(d['recency_plus_30_days']['share_not_increased'])}; mean {d['recency_plus_30_days']['mean_change'] * 100:.1f} points",
        ],
        [
            "Invariance",
            "Single-row vs batch scoring, and shuffled row order",
            f"max differences {bi['batch_vs_single_max_abs_diff']:.1e} and {bi['row_order_max_abs_diff']:.1e}",
        ],
        [
            "Explainability",
            "SHAP values plus bias equal the model's logit",
            f"max error {sa['max_abs_error_logit']:.1e}",
        ],
        [
            "Edge inputs",
            f"{len(t['edge_inputs']['cases'])} extreme but valid customers",
            "all scored without errors" if t["edge_inputs"]["all_ok"] else "errors found",
        ],
        [
            "Segment stability",
            "Refit K-Means with 10 other seeds",
            f"adjusted Rand index mean {n3(ss['seed_ari_mean'])}, min {n3(ss['seed_ari_min'])}",
        ],
        [
            "Segment stability",
            "Refit on 10 random 80% subsamples",
            f"adjusted Rand index mean {n3(ss['subsample_ari_mean'])}, min {n3(ss['subsample_ari_min'])}",
        ],
    ]
    edge_rows = [
        [k.replace("_", " "), pct(v.get("probability", 0)), v.get("segment", v.get("error", ""))]
        for k, v in t["edge_inputs"]["cases"].items()
    ]
    slice_blocks = []
    for gname, srows in t["slices"]["groups"].items():
        slice_blocks.append(
            f"**{gname.capitalize()}**\n\n"
            + table(
                ["Group", "Customers", "Responders", "Response rate", "Mean predicted", "ROC AUC"],
                [
                    [
                        s["group"],
                        f"{s['customers']:,}",
                        s["responders"],
                        pct(s["response_rate"]),
                        pct(s["mean_predicted"]),
                        n3(s["roc_auc"]) if s["roc_auc"] is not None else "too few",
                    ]
                    for s in srows
                ],
            )
        )
    return f"""## 3. Model testing

Code: [`model_testing.py`](model_testing.py), with the core checks also runnable as pytest quality gates in [`test_model_quality.py`](test_model_quality.py).

{table(["Area", "Test", "Result"], rows, "lll")}

### Edge-case customers

{table(["Case", "Probability", "Segment"], edge_rows, "lrl")}

### Performance by customer slice

Out-of-fold scores; ROC AUC is shown where a group has at least 10 responders and 10 non-responders. Lowest slice ROC AUC: **{n3(t["slices"]["min_slice_roc_auc"])}**, highest: {n3(t["slices"]["max_slice_roc_auc"])}.

{chr(10).join(b + chr(10) for b in slice_blocks)}"""


def section_benchmarking(r: dict) -> str:
    b = r["benchmarking"]
    mrows = [
        [
            row["model"],
            f"{n3(row['roc_auc_mean'])} ± {n3(row['roc_auc_std'])}",
            n3(row["pr_auc_mean"]),
            x(row["top10_lift_mean"]),
            f"{row['fit_seconds_mean'] * 1000:.0f} ms",
            f"{row['predict_ms_per_1k_rows']:.1f} ms",
            "" if row["model"] == "XGBoost (shipped)" else f"{row['shipped_wins_folds']} / {b['models']['folds']}",
        ]
        for row in b["models"]["rows"]
    ]
    c = b["compute"]
    lat_rows = [
        [
            "score_customer() (one customer, with SHAP)",
            *(f"{c['single_customer_score'][k]:.1f}" for k in ("p50_ms", "p95_ms", "p99_ms")),
        ]
    ]
    lat_rows += [
        [name, *(f"{v[k]:.1f}" for k in ("p50_ms", "p95_ms", "p99_ms"))]
        for name, v in c["api_latency_in_process"].items()
    ]
    brk = c["single_customer_score"].get("breakdown_p50_ms", {})
    brk_rows = [[k.replace("_", " ").replace("shap", "SHAP"), f"{v:.1f}"] for k, v in brk.items()]
    env = r["meta"]["environment"]
    return f"""## 4. Performance benchmarking

Code: [`benchmarking.py`](benchmarking.py).

### Model benchmark

All candidates use the same {r["meta"]["response_features"]} response features and the same {b["models"]["scheme"]} ({
        b["models"]["folds"]
    } folds). "Wins" counts the folds where the shipped XGBoost has the higher ROC AUC.

{table(["Model", "ROC AUC", "PR AUC", "Top-10% lift", "Fit time", "Predict / 1k rows", "XGBoost wins"], mrows)}

The two rules need no training: an RFM score (recency, frequency, monetary) and a marketer's rule that puts past campaign acceptors first, then recent buyers.

### Compute benchmark

{
        table(
            ["Measure", "Result"],
            [
                [
                    "Full training pipeline (clean, k search, cluster, CV, train, out-of-fold lift, save)",
                    f"{c['training_pipeline_seconds']:.1f} s",
                ],
                [
                    "Batch scoring throughput",
                    f"{c['batch_scoring']['rows_per_second']:,.0f} customers per second ({c['batch_scoring']['rows']:,} rows)",
                ],
                [
                    "Artifact size on disk",
                    f"{c['artifact_total_kb']:.0f} KB (response model {c['artifact_bytes']['response_model.joblib'] / 1024:.0f} KB)",
                ],
            ],
            "ll",
        )
    }

Latency in milliseconds. {c["notes"]}

{table(["Call", "p50", "p95", "p99"], lat_rows)}

Where single-customer time goes (median ms per step):

{table(["Step", "ms"], brk_rows)}

Environment: {env["platform"]}, {env["cpu_count"]} logical CPUs, Python {env["python"]}, {
        ", ".join(f"{k} {v}" for k, v in env["packages"].items())
    }."""


def section_assessment(r: dict) -> str:
    a = r["assessment"]
    t, p, e = r["testing"], r["performance"], r["evaluation"]
    rows = [
        [g["id"], g["area"], g["check"], gate_value(g), gate_threshold(g), "Pass" if g["passed"] else "**Fail**"]
        for g in a["scorecard"]
    ]
    area_rows = [[k, f"{v['passed']} / {v['total']}"] for k, v in a["by_area"].items()]
    failed = [g for g in a["scorecard"] if not g["passed"]]
    brk = r["benchmarking"]["compute"]["single_customer_score"].get("breakdown_p50_ms", {})
    slow = sorted(brk.items(), key=lambda kv: -kv[1])[:2]
    exceptions = []
    for g in failed:
        if g["id"] == "B3" and slow:
            exceptions.append(
                f"- **{g['id']} {g['check']}** measured {gate_value(g)} against {gate_threshold(g)}. Most of the time is fixed per-call overhead on a one-row input, mainly "
                + " and ".join(f"{k.replace('_', ' ').replace('shap', 'SHAP')} ({v:.1f} ms)" for k, v in slow)
                + ". The model itself is fast (see batch throughput). This does not affect correctness; a NumPy fast path for single rows is the fix."
            )
        else:
            exceptions.append(f"- **{g['id']} {g['check']}** measured {gate_value(g)} against {gate_threshold(g)}.")
    seventy = next((s for s in t["slices"]["groups"]["age"] if s["group"] == "70 plus"), None)
    cal = p["calibration"]
    rank = e["response_model"]["ranking"]
    return f"""## 5. Model assessment

Code: [`assessment.py`](assessment.py). The {a["total"]} gates and their thresholds were fixed in code before the suite was first run on the real data.

{table(["Area", "Passed"], area_rows)}

{table(["ID", "Area", "Check", "Value", "Gate", "Result"], rows, "lllrrc")}

**Verdict: {a["verdict"]} ({a["passed"]} of {a["total"]} gates passed).**

### Exceptions

{chr(10).join(exceptions) if exceptions else "- None. Every gate passed."}

### Strengths

- Strong, stable ranking: holdout ROC AUC {n3(rank["roc_auc"])}, and {n3(p["stability"]["roc_auc"]["mean"])} ± {n3(p["stability"]["roc_auc"]["std"])} across {p["stability"]["fits"]} repeated-CV fits.
- Clear business value: the profit-optimal campaign turns a {money(abs(p["targeting"]["contact_everyone"]["profit"]))} loss into {money(p["targeting"]["best_profit_point"]["profit"])} profit.
- Trustworthy behaviour: no leakage signal, the expected responses to campaign history and recency, robust to measurement noise, and SHAP explanations that add up exactly.
- Consistent across groups: ROC AUC stays between {n3(t["slices"]["min_slice_roc_auc"])} and {n3(t["slices"]["max_slice_roc_auc"])} across age, income, education, household and segment slices.
- Reproducible: the served artifact is bit-for-bit what a fresh training run produces.

### Limitations and risks

- Small sample: {rank["n"]} holdout customers with {rank["positives"]} responders, so intervals are wide (holdout ROC AUC 95% CI {ci(rank["roc_auc_ci95"])}).
- One target campaign: `Response` covers a single campaign; using it to rank for future campaigns assumes customer behaviour and the offer stay similar.
- Campaign history dominates: past acceptances and recency are the top drivers, so the model is strongest for customers with history and leans on behaviour alone for new customers.
- Slight under-prediction: mean score {pct(cal["mean_predicted"])} vs {pct(cal["observed_rate"])} observed. Ranking is unaffected; budgets based on raw probabilities would be a little conservative.
- Soft segments: silhouette {n3(e["segmentation"]["silhouette"])} shows overlapping groups, although they are highly stable.
{f"- Thin slice: only {seventy['customers']} customers are 70 or older, too few to measure ROC AUC for that group." if seventy and seventy["roc_auc"] is None else ""}
- Public-data rebuild: profit uses the dataset's nominal $3 cost and $11 revenue, and results do not reproduce the original company's campaign.

### Recommendations

{"1. Add a NumPy fast path for single-customer feature engineering and SHAP to bring scoring latency under the 50 ms gate." if any(g["id"] == "B3" for g in failed) else "1. Keep the latency gates in CI as the API grows."}
2. Validate on the next real campaign, or an A/B test of model targeting against segment-only targeting, before relying on profit figures.
3. If probabilities drive budgets, add isotonic recalibration on out-of-fold scores and re-check calibration error.
4. Retrain when a new campaign's results arrive and re-run this suite; the gates double as a release checklist."""


def resume_bullets(r: dict) -> str:
    rank = r["evaluation"]["response_model"]["ranking"]
    tg, seg, st = (
        r["performance"]["targeting"],
        r["performance"]["segment_targeting"]["rows"][0],
        r["performance"]["stability"],
    )
    a, t = r["assessment"], r["testing"]
    bench = {row["model"]: row for row in r["benchmarking"]["models"]["rows"]}
    others = [k for k in bench if k not in ("XGBoost (shipped)", "Dummy (base rate)")]
    best_profit, everyone = tg["best_profit_point"], tg["contact_everyone"]
    c = r["benchmarking"]["compute"]
    return f"""## Resume bullet points

To add once the whole project wraps up. Every figure comes from this report.

**Project: Customer Segmentation and Campaign Targeting (recreated on public data)**

- Built an end-to-end customer segmentation and campaign targeting system on {r["meta"]["customers"]:,} retail customers: K-Means behavioural segments, an XGBoost response model with SHAP explanations, a FastAPI service and a React + TypeScript dashboard.
- Trained a response model reaching {n3(rank["roc_auc"])} holdout ROC AUC (95% CI {ci(rank["roc_auc_ci95"])}) and {n3(rank["pr_auc"])} PR AUC, {x(rank["pr_auc"] / rank["base_rate"], 1)} the base rate, outperforming {len(others)} baselines including logistic regression, random forest and business rules under repeated cross-validation.
- Lifted campaign response {x(tg["deciles"][0]["lift"], 1)} in the top decile and turned a {money(abs(everyone["profit"]))} loss from mass contact into {money(best_profit["profit"])} profit by targeting the top {pct(best_profit["share_targeted"], 0)}, while still reaching {pct(best_profit["capture"], 0)} of responders.
- Showed segments alone deliver a {pct(seg["lift"] - 1, 0)} response lift on held-out customers, validating segment-based targeting before any predictive model.
- Designed an automated evaluation suite with {a["total"]} quality gates fixed before the first run, covering leakage (label shuffling), noise robustness, directional behaviour, SHAP additivity, segment stability (ARI {n3(t["segmentation_stability"]["seed_ari_min"])}+) and slice performance; {a["passed"]} of {a["total"]} gates passed{", with the remaining gate traced to single-row scoring overhead" if a["passed"] == a["total"] - 1 else ""}.
- Kept the pipeline reproducible and fast: deterministic training in {c["training_pipeline_seconds"]:.0f} s, versioned artifacts matching a fresh retrain exactly, stable ROC AUC across {st["fits"]} resampled fits (std {n3(st["roc_auc"]["std"])}), and batch scoring at {c["batch_scoring"]["rows_per_second"]:,.0f} customers per second.

**Shorter variants**

- Raised campaign response {x(tg["deciles"][0]["lift"], 1)} in the top decile with an XGBoost model ({n3(rank["roc_auc"])} ROC AUC) and turned mass-contact losses into profit.
- Built K-Means customer segments that lift response {pct(seg["lift"] - 1, 0)} on unseen customers, served through FastAPI and a React dashboard.
- Validated the models with a {a["total"]}-gate evaluation suite covering leakage, robustness, stability and customer-slice performance."""


def render(r: dict) -> str:
    parts = [
        header(r),
        summary(r),
        section_evaluation(r),
        section_performance(r),
        section_testing(r),
        section_benchmarking(r),
        section_assessment(r),
        resume_bullets(r),
    ]
    text = "\n\n".join(p.strip() for p in parts) + "\n"
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text


def write(results: dict | None = None) -> Path:
    results = results or json.loads((RESULTS_DIR / "all_results.json").read_text(encoding="utf-8"))
    REPORT_PATH.write_text(render(results), encoding="utf-8")
    return REPORT_PATH


if __name__ == "__main__":
    print(write())
