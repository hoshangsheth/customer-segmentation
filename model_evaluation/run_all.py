"""
Run the whole evaluation suite on the real data and the shipped artifacts.

    python -m model_evaluation.run_all [--data PATH] [--artifacts DIR] [--skip-report]

Writes one JSON file per section to model_evaluation/results/, a combined all_results.json, and
renders model_evaluation/REPORT.md from those numbers.
"""

from __future__ import annotations

import argparse
import logging
import time
from datetime import datetime
from pathlib import Path

from model_evaluation import assessment, benchmarking, model_evaluation, model_testing, performance_evaluation
from model_evaluation.common import environment, load_context, to_jsonable, write_json

log = logging.getLogger("model_evaluation")

SECTIONS = [
    ("evaluation", "1. Model evaluation", model_evaluation.run),
    ("performance", "2. Model performance evaluation", performance_evaluation.run),
    ("testing", "3. Model testing", model_testing.run),
    ("benchmarking", "4. Performance benchmarking", benchmarking.run),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the model evaluation suite.")
    parser.add_argument("--data", type=Path, default=None)
    parser.add_argument("--artifacts", type=Path, default=None)
    parser.add_argument("--skip-report", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    for noisy in ("train", "httpx", "httpx2"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    started = time.perf_counter()
    ctx = load_context(args.data, args.artifacts)
    log.info("context ready: %d customers, artifact %s", len(ctx.y), ctx.bundle.version)

    results: dict = {
        "meta": {
            "run_at": datetime.now().isoformat(timespec="seconds"),
            "artifact_version": ctx.bundle.version,
            "data_path": str(args.data or ctx.settings.data_path),
            "customers": int(len(ctx.y)),
            "responders": int(ctx.y.sum()),
            "train_size": int(len(ctx.idx_train)),
            "test_size": int(len(ctx.idx_test)),
            "random_state": ctx.rs,
            "cost_per_contact": ctx.cost,
            "revenue_per_response": ctx.revenue,
            "response_features": int(ctx.X.shape[1]),
            "environment": environment(),
        }
    }
    timings = {}
    for key, title, fn in SECTIONS:
        t0 = time.perf_counter()
        log.info("running %s", title)
        results[key] = to_jsonable(fn(ctx))
        timings[key] = time.perf_counter() - t0
        write_json(f"{key}.json", results[key])
        log.info("%s done in %.1fs", title, timings[key])

    log.info("running 5. Model assessment")
    results["assessment"] = to_jsonable(assessment.run(results))
    write_json("assessment.json", results["assessment"])
    results["meta"]["section_seconds"] = timings
    results["meta"]["total_seconds"] = time.perf_counter() - started
    path = write_json("all_results.json", results)
    a = results["assessment"]
    log.info("gates passed %d/%d (%s); results in %s", a["passed"], a["total"], a["verdict"], path.parent)

    if not args.skip_report:
        from model_evaluation import report

        out = report.write(results)
        log.info("report written to %s", out)


if __name__ == "__main__":
    main()
