import json

import pytest

from customer_segmentation.artifacts import store
from customer_segmentation.scoring import CustomerRecord, score_customer


def test_training_writes_a_versioned_bundle(settings, bundle):
    root = settings.artifacts_dir
    assert (root / store.LATEST).read_text() == bundle.version
    report = json.loads((root / bundle.version / "report.json").read_text())
    assert report["data"]["customers"] == 398
    assert report["data"]["cost_per_contact"] == 3 and report["data"]["revenue_per_response"] == 11
    k = report["segmentation"]["k_selection"]
    assert [s["k"] for s in k["scores"]] == list(range(2, 7))
    assert len(report["segmentation"]["segments"]) == k["chosen_k"]
    assert len(report["segmentation"]["projection"]["points"]) == 398
    assert 0 <= report["model"]["holdout"]["roc_auc"] <= 1
    assert report["lift"]["curve"][-1]["lift"] == pytest.approx(1.0)


def test_load_round_trip(settings, bundle):
    loaded = store.load(settings.artifacts_dir)
    assert loaded.version == bundle.version
    assert loaded.report == json.loads(json.dumps(bundle.report))


def test_load_without_training_explains_what_to_run(tmp_path):
    with pytest.raises(store.ArtifactsNotFound, match="customer_segmentation.train"):
        store.load(tmp_path)
    (tmp_path / store.LATEST).write_text("missing")
    with pytest.raises(store.ArtifactsNotFound):
        store.load(tmp_path)


def test_score_customer(bundle):
    defaults = bundle.report["score_defaults"]
    result = score_customer(bundle, CustomerRecord(**defaults))
    assert 0 <= result.probability <= 1
    assert result.segment_name
    assert len(result.reasons) == 6
