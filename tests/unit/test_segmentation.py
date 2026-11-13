import numpy as np

from customer_segmentation.segmentation.clustering import fit_projection, fit_segmenter, project
from customer_segmentation.segmentation.profiling import ARCHETYPES, assign_names, profile_segments
from customer_segmentation.segmentation.selection import KScore, choose_k, elbow_k, score_k_range


def test_k_scan_records_scores(features):
    scores = score_k_range(features, 2, 5, random_state=0)
    assert [s.k for s in scores] == [2, 3, 4, 5]
    assert all(-1 <= s.silhouette <= 1 for s in scores)
    inertia = [s.inertia for s in scores]
    assert inertia == sorted(inertia, reverse=True)


def test_choose_k_prefers_useful_k_and_honours_override():
    scores = [KScore(2, 100, 0.40, 1.0), KScore(3, 70, 0.30, 1.1), KScore(4, 60, 0.35, 1.2), KScore(5, 55, 0.20, 1.3)]
    assert choose_k(scores).chosen_k == 4  # k=2 has the best silhouette but is excluded
    assert choose_k(scores, forced_k=5).chosen_k == 5
    assert elbow_k(scores) == 3


def test_segmenter_and_projection(features):
    seg = fit_segmenter(features, 4, random_state=0)
    labels = seg.predict(features)
    assert set(labels) == {0, 1, 2, 3}
    coords = project(seg, fit_projection(seg, features, 0), features)
    assert coords.shape == (len(features), 2)


def test_assign_names_is_unique_and_fits_obvious_cases():
    z = {
        k: 0.0
        for k in [
            "monetary",
            "frequency",
            "recency",
            "catalog_share",
            "income",
            "avg_order_value",
            "deal_share",
            "children",
            "web_visits",
            "wine_share",
            "meat_share",
        ]
    }
    big = {**z, "monetary": 2.5, "frequency": 2.0}
    family = {**z, "deal_share": 2.0, "children": 1.5}
    lapsing = {**z, "recency": 2.5}
    names = assign_names({0: big, 1: family, 2: lapsing})
    assert names == {0: "High-value loyalists", 1: "Deal-seeking families", 2: "Lapsing customers"}
    many = assign_names({i: {**z, "monetary": float(i)} for i in range(len(ARCHETYPES) + 2)})
    assert len(set(many.values())) == len(many)


def test_profiles_cover_everyone(cleaned, features):
    df, _ = cleaned
    labels = fit_segmenter(features, 3, 0).predict(features)
    profiles = profile_segments(features, df, labels, df["Response"])
    assert sum(p.size for p in profiles) == len(df)
    assert np.isclose(sum(p.share for p in profiles), 1)
    for p in profiles:
        assert np.isclose(sum(p.spend_mix.values()), 1)
        assert np.isclose(sum(p.channel_mix.values()), 1)
        assert p.traits and p.name
