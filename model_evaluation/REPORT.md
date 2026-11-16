# Model Evaluation Report

Customer Segmentation and Campaign Targeting, recreated on public data.

- Dataset: Kaggle "Customer Personality Analysis" (2,236 customers after cleaning, 334 responders to the last campaign)
- Model artifact evaluated: `20261114-003713` (the exact files the API serves)
- Split: stratified 1,788 train / 448 holdout, random seed 42
- Run: 2026-11-16 15:30:44, 177 s in total, Python 3.12.10, 4 logical CPUs
- Quality gates passed: **27 of 28**, verdict: **ready with noted exceptions**

Reproduce everything in this report:

```bash
python -m customer_segmentation.train
python -m model_evaluation.run_all
python -m pytest model_evaluation -q
```

Raw results for every section are in [`results/`](results/).

## Summary

- The response model ranks responders well on unseen customers: holdout ROC AUC **0.923** (95% CI 0.884 to 0.954) and PR AUC **0.704**, 4.7x the 15.0% base rate.
- Targeting the model's top 10% reaches a **4.84x** response lift (95% CI 4.45x to 5.26x).
- The profit-optimal cut-off, the top 20%, earns **$1,453** against a **$3,034** loss for contacting everyone, a swing of $4,487.
- Segments alone, with no model, lift response **1.77x** on held-out customers by contacting 29% of them.
- XGBoost is the best of 7 candidates under repeated cross-validation (mean ROC AUC 0.920), 0.120 above the best no-model business rule (past acceptances + recency).
- Integrity checks are clean: deterministic training, the served artifact matches a fresh retrain exactly, no leakage under label shuffling, and SHAP values add up to each prediction.
- Exceptions: B3 single-customer scoring p95 latency (ms) measured 72.6 ms against ≤ 50 ms. See section 5.

## 1. Model evaluation

Code: [`model_evaluation.py`](model_evaluation.py). The shipped response model is scored on the 448 holdout customers (67 responders) that training never saw.

### Ranking and probability quality

| Metric | Holdout | Reference |
| --- | ---: | --- |
| ROC AUC | 0.923 | 95% CI 0.884 to 0.954 (1,000 stratified bootstraps) |
| PR AUC (average precision) | 0.704 | 95% CI 0.610 to 0.796; chance = 0.150 |
| Log loss | 0.239 | 0.422 when predicting the base rate |
| Brier score | 0.074 | 0.127 when predicting the base rate |
| Brier skill score | 0.421 | share of base-rate error removed |

The holdout ROC AUC matches the value recorded in the artifact at training time (0.923).

### Decision thresholds

Thresholds are chosen on out-of-fold scores from the training split only, then applied once to the holdout. Confusion counts are TP / FP / FN / TN.

| Threshold rule | Cut-off | Flagged | Precision | Recall | F1 | MCC | Bal. acc. | Confusion |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Default 0.5 | 0.500 | 9.4% | 0.762 | 0.478 | 0.587 | 0.552 | 0.726 | 32 / 10 / 35 / 371 |
| Best F1 (chosen on train) | 0.242 | 18.5% | 0.602 | 0.746 | 0.667 | 0.606 | 0.830 | 50 / 33 / 17 / 348 |
| Best profit (chosen on train) | 0.242 | 18.5% | 0.602 | 0.746 | 0.667 | 0.606 | 0.830 | 50 / 33 / 17 / 348 |
| Break-even ($3 / $11) | 0.273 | 16.1% | 0.611 | 0.657 | 0.633 | 0.566 | 0.792 | 44 / 28 / 23 / 353 |

At the profit-optimal cut-off the model flags 18.5% of holdout customers and finds 50 of 67 responders, with 33 wasted contacts. The default 0.5 cut-off is too strict for a 15% response rate: it misses more than half the responders.

### Segmentation

| Metric | Value | Reading |
| --- | ---: | --- |
| Segments (k) | 3 | best silhouette among k >= 3 |
| Silhouette | 0.177 | 0 = overlapping, 1 = perfectly separated |
| Davies-Bouldin | 1.760 | lower is better |
| Calinski-Harabasz | 633 | higher is better |
| Segment sizes | 863, 622, 751 | smallest is 27.8% of customers |

A silhouette of 0.177 means the segments partition a continuum of customer behaviour rather than form sharply separated clusters. They are still very stable (section 3) and differ strongly in response rate (section 2), which is what targeting needs.

## 2. Model performance evaluation

Code: [`performance_evaluation.py`](performance_evaluation.py). Lift and profit use out-of-fold scores, so each of the 2,236 customers is scored by a model that never saw them (out-of-fold ROC AUC 0.921, KS statistic 0.707).

### Lift by decile

| Decile | Customers | Responders | Response rate | Lift | Cumulative capture |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 224 | 162 | 72.3% | 4.84x | 49% |
| 2 | 224 | 92 | 41.1% | 2.75x | 76% |
| 3 | 224 | 46 | 20.5% | 1.37x | 90% |
| 4 | 224 | 15 | 6.7% | 0.45x | 94% |
| 5 | 224 | 12 | 5.4% | 0.36x | 98% |
| 6 | 224 | 3 | 1.3% | 0.09x | 99% |
| 7 | 223 | 2 | 0.9% | 0.06x | 99% |
| 8 | 223 | 0 | 0.0% | 0.00x | 99% |
| 9 | 223 | 1 | 0.4% | 0.03x | 100% |
| 10 | 223 | 1 | 0.4% | 0.03x | 100% |

Bootstrap 95% intervals: top-10% lift 4.45x to 5.26x, top-20% lift 3.60x to 4.02x.

### Targeting and campaign profit

Profit uses the dataset's own cost of $3 per contact and $11 revenue per response.

| Contact top | Customers | Responders | Response rate | Lift | Responders reached | Profit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 10% | 224 | 162 | 72.3% | 4.84x | 49% | $1,110 |
| 20% | 447 | 254 | 56.8% | 3.80x | 76% | $1,453 |
| 30% | 671 | 299 | 44.6% | 2.98x | 90% | $1,276 |
| 50% | 1,118 | 327 | 29.2% | 1.96x | 98% | $243 |
| 100% | 2,236 | 334 | 14.9% | 1.00x | 100% | -$3,034 |

Contacting everyone loses money; the top 20% is the most profitable cut-off and still reaches 76% of all responders.

### Calibration (holdout)

Expected calibration error is **0.027**. The mean predicted probability is 13.1% against an observed rate of 15.0%, so scores run slightly low on average.

| Bin | Customers | Mean predicted | Observed |
| ---: | ---: | ---: | ---: |
| 1 | 45 | 0.1% | 0.0% |
| 2 | 45 | 0.3% | 2.2% |
| 3 | 45 | 0.6% | 0.0% |
| 4 | 45 | 1.1% | 0.0% |
| 5 | 45 | 2.0% | 2.2% |
| 6 | 45 | 3.6% | 4.4% |
| 7 | 45 | 6.7% | 4.4% |
| 8 | 45 | 15.0% | 22.2% |
| 9 | 44 | 31.2% | 40.9% |
| 10 | 44 | 72.0% | 75.0% |

### Stability under resampling

| Metric | Mean | Std | Min | Max |
| --- | ---: | ---: | ---: | ---: |
| ROC AUC | 0.922 | 0.011 | 0.890 | 0.948 |
| PR AUC | 0.712 | 0.038 | 0.637 | 0.781 |
| Top-10% lift | 4.868 | 0.346 | 4.300 | 5.349 |

5x5 repeated stratified K-fold, all customers, 25 fits.

### Segment targeting (no model)

Segments are ranked by response rate on the training split and measured on the test split (test base rate 15.0%).

| Segments contacted | Share contacted | Response rate | Lift | Responders reached |
| --- | ---: | ---: | ---: | ---: |
| Affluent catalog buyers | 29% | 26.5% | 1.77x | 52% |
| Affluent catalog buyers + Wine enthusiasts | 61% | 19.3% | 1.29x | 79% |
| Affluent catalog buyers + Wine enthusiasts + Budget browsers | 100% | 15.0% | 1.00x | 100% |

Response rate by segment across all customers:

| Segment | Customers | Response rate | Lift |
| --- | ---: | ---: | ---: |
| Affluent catalog buyers | 622 | 24.6% | 1.65x |
| Wine enthusiasts | 751 | 13.7% | 0.92x |
| Budget browsers | 863 | 9.0% | 0.61x |

### Resume claim check

The original internship bullet claims the segmentation "contributed to a 20% lift in targeted campaign conversion", which means a lift of at least 1.2x.

- Segment-only targeting: 1.77x on held-out customers, so the claim is **supported on this public data**.
- Model-ranked top 20%: 3.80x, with a lower 95% bound of 3.60x.
- Caveat: Measured on public data as a rebuild; it does not reproduce the original company's campaign.

## 3. Model testing

Code: [`model_testing.py`](model_testing.py), with the core checks also runnable as pytest quality gates in [`test_model_quality.py`](test_model_quality.py).

| Area | Test | Result |
| --- | --- | --- |
| Reproducibility | Retrain twice with the same seed | max prediction difference 0.0e+00 |
| Artifact integrity | Shipped model vs a fresh retrain | max prediction difference 0.0e+00 |
| Leakage | Train on shuffled labels (5 times) | mean holdout ROC AUC 0.523, at most 0.049 from 0.5 |
| Noise robustness | Gaussian noise of 5% of each feature's std on 18 continuous features | rank correlation 0.990, 93% of the top decile unchanged, ROC AUC 0.915 |
| Directional | Add one accepted earlier campaign | score rises for 99.8%, never falls; mean +15.5 points |
| Directional | Add 30 days since the last purchase | score falls for 90.4%, does not rise for 95.8%; mean -5.0 points |
| Invariance | Single-row vs batch scoring, and shuffled row order | max differences 0.0e+00 and 0.0e+00 |
| Explainability | SHAP values plus bias equal the model's logit | max error 5.2e-06 |
| Edge inputs | 6 extreme but valid customers | all scored without errors |
| Segment stability | Refit K-Means with 10 other seeds | adjusted Rand index mean 0.993, min 0.985 |
| Segment stability | Refit on 10 random 80% subsamples | adjusted Rand index mean 0.973, min 0.917 |

### Edge-case customers

| Case | Probability | Segment |
| --- | ---: | --- |
| median customer | 0.7% | Wine enthusiasts |
| no spend no purchases | 0.5% | Budget browsers |
| very high spender | 2.6% | Affluent catalog buyers |
| accepted all campaigns | 90.6% | Wine enthusiasts |
| brand new customer | 3.0% | Wine enthusiasts |
| oldest allowed birth year | 0.9% | Wine enthusiasts |

### Performance by customer slice

Out-of-fold scores; ROC AUC is shown where a group has at least 10 responders and 10 non-responders. Lowest slice ROC AUC: **0.900**, highest: 0.930.

**Age**

| Group | Customers | Responders | Response rate | Mean predicted | ROC AUC |
| --- | ---: | ---: | ---: | ---: | ---: |
| 40 to 54 | 892 | 129 | 14.5% | 13.2% | 0.914 |
| 55 to 69 | 551 | 81 | 14.7% | 13.5% | 0.924 |
| 70 plus | 16 | 4 | 25.0% | 22.8% | too few |
| under 40 | 777 | 120 | 15.4% | 15.1% | 0.930 |

**Income**

| Group | Customers | Responders | Response rate | Mean predicted | ROC AUC |
| --- | ---: | ---: | ---: | ---: | ---: |
| lower third | 746 | 86 | 11.5% | 10.4% | 0.920 |
| middle third | 745 | 75 | 10.1% | 9.4% | 0.910 |
| upper third | 745 | 173 | 23.2% | 22.1% | 0.918 |

**Education**

| Group | Customers | Responders | Response rate | Mean predicted | ROC AUC |
| --- | ---: | ---: | ---: | ---: | ---: |
| Graduate | 1,126 | 152 | 13.5% | 12.8% | 0.923 |
| Postgraduate | 855 | 158 | 18.5% | 16.6% | 0.918 |
| Undergraduate | 255 | 24 | 9.4% | 10.2% | 0.918 |

**Household**

| Group | Customers | Responders | Response rate | Mean predicted | ROC AUC |
| --- | ---: | ---: | ---: | ---: | ---: |
| Partnered | 1,442 | 158 | 11.0% | 10.6% | 0.912 |
| Single | 794 | 176 | 22.2% | 20.1% | 0.923 |

**Segment**

| Group | Customers | Responders | Response rate | Mean predicted | ROC AUC |
| --- | ---: | ---: | ---: | ---: | ---: |
| Affluent catalog buyers | 622 | 153 | 24.6% | 23.2% | 0.923 |
| Budget browsers | 863 | 78 | 9.0% | 8.0% | 0.923 |
| Wine enthusiasts | 751 | 103 | 13.7% | 13.1% | 0.900 |

## 4. Performance benchmarking

Code: [`benchmarking.py`](benchmarking.py).

### Model benchmark

All candidates use the same 29 response features and the same 3x5 repeated stratified K-fold, all customers (15 folds). "Wins" counts the folds where the shipped XGBoost has the higher ROC AUC.

| Model | ROC AUC | PR AUC | Top-10% lift | Fit time | Predict / 1k rows | XGBoost wins |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| XGBoost (shipped) | 0.920 ± 0.013 | 0.707 | 4.86x | 673 ms | 16.3 ms |  |
| Hist gradient boosting | 0.914 ± 0.014 | 0.682 | 4.79x | 1182 ms | 31.6 ms | 14 / 15 |
| Logistic regression | 0.909 ± 0.017 | 0.670 | 4.83x | 27 ms | 6.8 ms | 11 / 15 |
| Random forest | 0.905 ± 0.017 | 0.661 | 4.57x | 1859 ms | 166.0 ms | 15 / 15 |
| Rule: past acceptances + recency | 0.800 ± 0.026 | 0.518 | 4.03x | 1 ms | 2.3 ms | 15 / 15 |
| Rule: RFM score | 0.723 ± 0.026 | 0.318 | 2.47x | 1 ms | 6.7 ms | 15 / 15 |
| Dummy (base rate) | 0.500 ± 0.000 | 0.149 | 0.97x | 2 ms | 1.2 ms | 15 / 15 |

The two rules need no training: an RFM score (recency, frequency, monetary) and a marketer's rule that puts past campaign acceptors first, then recent buyers.

### Compute benchmark

| Measure | Result |
| --- | --- |
| Full training pipeline (clean, k search, cluster, CV, train, out-of-fold lift, save) | 17.2 s |
| Batch scoring throughput | 137,356 customers per second (22,360 rows) |
| Artifact size on disk | 972 KB (response model 338 KB) |

Latency in milliseconds. Latency is in-process (FastAPI TestClient), single thread, no network; real deployments add transport time.

| Call | p50 | p95 | p99 |
| --- | ---: | ---: | ---: |
| score_customer() (one customer, with SHAP) | 52.7 | 72.6 | 112.2 |
| GET /api/health | 6.4 | 7.6 | 8.5 |
| GET /api/overview | 6.9 | 8.2 | 10.2 |
| GET /api/lift | 7.5 | 9.0 | 10.4 |
| POST /api/score | 58.3 | 66.8 | 69.4 |

Where single-customer time goes (median ms per step):

| Step | ms |
| --- | ---: |
| input to frame | 0.7 |
| feature engineering | 15.5 |
| segment assignment | 3.9 |
| response probability | 3.6 |
| SHAP explanation | 8.8 |

Environment: Windows-10-10.0.19045-SP0, 4 logical CPUs, Python 3.12.10, numpy 2.5.4, pandas 3.1.1, scikit-learn 1.9.1, xgboost 3.4.1, fastapi 0.162.6.

## 5. Model assessment

Code: [`assessment.py`](assessment.py). The 28 gates and their thresholds were fixed in code before the suite was first run on the real data.

| Area | Passed |
| --- | ---: |
| Evaluation | 6 / 6 |
| Performance | 5 / 5 |
| Testing | 12 / 12 |
| Benchmarking | 4 / 5 |

| ID | Area | Check | Value | Gate | Result |
| --- | --- | --- | ---: | ---: | :---: |
| E1 | Evaluation | Holdout ROC AUC | 0.923 | ≥ 0.85 | Pass |
| E2 | Evaluation | Holdout ROC AUC, lower 95% bound | 0.884 | ≥ 0.8 | Pass |
| E3 | Evaluation | Holdout PR AUC as a multiple of the base rate | 4.710 | ≥ 3 | Pass |
| E4 | Evaluation | Brier skill score vs predicting the base rate | 0.421 | ≥ 0.2 | Pass |
| E5 | Evaluation | Segmentation silhouette | 0.177 | ≥ 0.1 | Pass |
| E6 | Evaluation | Smallest segment share | 0.278 | ≥ 0.1 | Pass |
| P1 | Performance | Top-10% lift, lower 95% bound | 4.447 | ≥ 3 | Pass |
| P2 | Performance | Best campaign profit vs contacting everyone ($) | $4,487 | ≥ $0 | Pass |
| P3 | Performance | Expected calibration error (holdout) | 0.027 | ≤ 0.05 | Pass |
| P4 | Performance | Std of ROC AUC over 25 repeated-CV fits | 0.011 | ≤ 0.03 | Pass |
| P5 | Performance | Best segment lift on the test split | 1.773 | ≥ 1.2 | Pass |
| T1 | Testing | Same-seed retrain, max prediction difference | 0.000 | ≤ 1e-09 | Pass |
| T2 | Testing | Shipped artifact vs fresh retrain, max difference | 0.000 | ≤ 1e-06 | Pass |
| T3 | Testing | Label-shuffle AUC, max distance from 0.5 | 0.049 | ≤ 0.08 | Pass |
| T4 | Testing | Rank correlation under 5% feature noise | 0.990 | ≥ 0.95 | Pass |
| T5 | Testing | Share where an extra past acceptance does not lower the score | 1.000 | ≥ 0.9 | Pass |
| T6 | Testing | Share where 30 more days of inactivity does not raise the score | 0.958 | ≥ 0.8 | Pass |
| T7 | Testing | Batch vs single-row scoring, max difference | 0.000 | ≤ 1e-09 | Pass |
| T8 | Testing | SHAP additivity error (logit) | 5.2e-06 | ≤ 0.001 | Pass |
| T9 | Testing | Edge-case customers scored cleanly | all clean | all clean | Pass |
| T10 | Testing | Segmentation ARI across 10 seeds, minimum | 0.985 | ≥ 0.8 | Pass |
| T11 | Testing | Segmentation ARI on 80% subsamples, minimum | 0.917 | ≥ 0.7 | Pass |
| T12 | Testing | Lowest ROC AUC across customer slices | 0.900 | ≥ 0.75 | Pass |
| B1 | Benchmarking | Shipped model beats the best no-model rule (mean ROC AUC gap) | 0.120 | ≥ 0.02 | Pass |
| B2 | Benchmarking | Shipped model within 0.01 ROC AUC of the best learner | 0.000 | ≥ -0.01 | Pass |
| B3 | Benchmarking | Single-customer scoring p95 latency (ms) | 72.6 ms | ≤ 50 ms | **Fail** |
| B4 | Benchmarking | POST /api/score p95 latency, in process (ms) | 66.8 ms | ≤ 100 ms | Pass |
| B5 | Benchmarking | Full training pipeline (s) | 17.2 s | ≤ 300 s | Pass |

**Verdict: ready with noted exceptions (27 of 28 gates passed).**

### Exceptions

- **B3 Single-customer scoring p95 latency (ms)** measured 72.6 ms against ≤ 50 ms. Most of the time is fixed per-call overhead on a one-row input, mainly feature engineering (15.5 ms) and SHAP explanation (8.8 ms). The model itself is fast (see batch throughput). This does not affect correctness; a NumPy fast path for single rows is the fix.

### Strengths

- Strong, stable ranking: holdout ROC AUC 0.923, and 0.922 ± 0.011 across 25 repeated-CV fits.
- Clear business value: the profit-optimal campaign turns a $3,034 loss into $1,453 profit.
- Trustworthy behaviour: no leakage signal, the expected responses to campaign history and recency, robust to measurement noise, and SHAP explanations that add up exactly.
- Consistent across groups: ROC AUC stays between 0.900 and 0.930 across age, income, education, household and segment slices.
- Reproducible: the served artifact is bit-for-bit what a fresh training run produces.

### Limitations and risks

- Small sample: 448 holdout customers with 67 responders, so intervals are wide (holdout ROC AUC 95% CI 0.884 to 0.954).
- One target campaign: `Response` covers a single campaign; using it to rank for future campaigns assumes customer behaviour and the offer stay similar.
- Campaign history dominates: past acceptances and recency are the top drivers, so the model is strongest for customers with history and leans on behaviour alone for new customers.
- Slight under-prediction: mean score 13.1% vs 15.0% observed. Ranking is unaffected; budgets based on raw probabilities would be a little conservative.
- Soft segments: silhouette 0.177 shows overlapping groups, although they are highly stable.
- Thin slice: only 16 customers are 70 or older, too few to measure ROC AUC for that group.
- Public-data rebuild: profit uses the dataset's nominal $3 cost and $11 revenue, and results do not reproduce the original company's campaign.

### Recommendations

1. Add a NumPy fast path for single-customer feature engineering and SHAP to bring scoring latency under the 50 ms gate.
2. Validate on the next real campaign, or an A/B test of model targeting against segment-only targeting, before relying on profit figures.
3. If probabilities drive budgets, add isotonic recalibration on out-of-fold scores and re-check calibration error.
4. Retrain when a new campaign's results arrive and re-run this suite; the gates double as a release checklist.

## Resume bullet points

To add once the whole project wraps up. Every figure comes from this report.

**Project: Customer Segmentation and Campaign Targeting (recreated on public data)**

- Built an end-to-end customer segmentation and campaign targeting system on 2,236 retail customers: K-Means behavioural segments, an XGBoost response model with SHAP explanations, a FastAPI service and a React + TypeScript dashboard.
- Trained a response model reaching 0.923 holdout ROC AUC (95% CI 0.884 to 0.954) and 0.704 PR AUC, 4.7x the base rate, outperforming 5 baselines including logistic regression, random forest and business rules under repeated cross-validation.
- Lifted campaign response 4.8x in the top decile and turned a $3,034 loss from mass contact into $1,453 profit by targeting the top 20%, while still reaching 76% of responders.
- Showed segments alone deliver a 77% response lift on held-out customers, validating segment-based targeting before any predictive model.
- Designed an automated evaluation suite with 28 quality gates fixed before the first run, covering leakage (label shuffling), noise robustness, directional behaviour, SHAP additivity, segment stability (ARI 0.985+) and slice performance; 27 of 28 gates passed, with the remaining gate traced to single-row scoring overhead.
- Kept the pipeline reproducible and fast: deterministic training in 17 s, versioned artifacts matching a fresh retrain exactly, stable ROC AUC across 25 resampled fits (std 0.011), and batch scoring at 137,356 customers per second.

**Shorter variants**

- Raised campaign response 4.8x in the top decile with an XGBoost model (0.923 ROC AUC) and turned mass-contact losses into profit.
- Built K-Means customer segments that lift response 77% on unseen customers, served through FastAPI and a React dashboard.
- Validated the models with a 28-gate evaluation suite covering leakage, robustness, stability and customer-slice performance.
