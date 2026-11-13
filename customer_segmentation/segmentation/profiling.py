"""
Segment profiles in business terms.

Each segment gets averages, its spend and channel mix, its historical response rate, and a name
picked from a fixed set of archetypes by how well the segment's z-scores fit each one (greedy,
one archetype per segment). The names are deterministic; the LLM layer can add a richer persona.
"""

from collections.abc import Callable
from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

from customer_segmentation.data.schema import PURCHASE_CHANNELS, SPEND_COLUMNS
from customer_segmentation.features.engineering import FEATURE_LABELS

PROFILE_METRICS = [
    "income",
    "age",
    "children",
    "tenure_days",
    "recency",
    "frequency",
    "monetary",
    "avg_order_value",
    "deal_share",
    "web_visits",
]
SPEND_CATEGORIES = ["wine", "fruit", "meat", "fish", "sweet", "gold"]
CHANNELS = ["web", "catalog", "store"]

Z = dict[str, float]
ARCHETYPES: dict[str, tuple[Callable[[Z], float], str]] = {
    "High-value loyalists": (
        lambda z: z["monetary"] + z["frequency"] - 0.5 * z["recency"],
        "Top spenders who buy often; protect and reward them.",
    ),
    "Affluent catalog buyers": (
        lambda z: z["catalog_share"] + z["income"] + 0.5 * z["avg_order_value"],
        "High-income customers with large baskets and a taste for the catalog.",
    ),
    "Deal-seeking families": (
        lambda z: z["deal_share"] + z["children"] - 0.3 * z["income"],
        "Households with children who respond to discounts.",
    ),
    "Budget browsers": (
        lambda z: -z["monetary"] + z["web_visits"] - z["income"],
        "Lower-income, low-spend customers who visit the website often.",
    ),
    "Wine enthusiasts": (
        lambda z: 1.5 * z["wine_share"] - 0.5 * z["meat_share"],
        "Spend is concentrated on wine.",
    ),
    "Lapsing customers": (
        lambda z: 1.5 * z["recency"] - 0.5 * z["frequency"],
        "Have not bought for a while; at risk of churning.",
    ),
    "Steady mid-spenders": (
        lambda z: -2.0 * float(np.mean(np.abs(list(z.values())))),
        "Close to the average on most measures.",
    ),
}


@dataclass
class SegmentProfile:
    segment_id: int
    name: str
    tagline: str
    size: int
    share: float
    response_rate: float
    prior_accept_rate: float
    means: dict[str, float]
    spend_mix: dict[str, float]
    channel_mix: dict[str, float]
    traits: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _zscores(features: pd.DataFrame, labels: np.ndarray) -> dict[int, Z]:
    cols = [*PROFILE_METRICS, "wine_share", "meat_share", "gold_share", "web_share", "catalog_share", "store_share"]
    pop_mean, pop_std = features[cols].mean(), features[cols].std(ddof=0).replace(0, 1)
    seg_means = features[cols].groupby(labels).mean()
    return {int(s): ((seg_means.loc[s] - pop_mean) / pop_std).to_dict() for s in seg_means.index}


def assign_names(zscores: dict[int, Z]) -> dict[int, str]:
    """Greedy best-fit: highest (segment, archetype) score first, each used once."""
    pairs = sorted(
        ((fn(z), seg, name) for seg, z in zscores.items() for name, (fn, _) in ARCHETYPES.items()),
        reverse=True,
    )
    names: dict[int, str] = {}
    used: set[str] = set()
    for _, seg, name in pairs:
        if seg not in names and name not in used:
            names[seg] = name
            used.add(name)
    for seg in zscores:  # more segments than archetypes
        names.setdefault(seg, f"Segment {seg + 1}")
    return names


def _traits(seg_means: pd.Series, pop_means: pd.Series, z: Z, limit: int = 4) -> list[str]:
    """Plain-language statements for the measures that differ most from the average."""
    ratio_metrics = {"income", "monetary", "frequency", "avg_order_value"}
    ranked = sorted(z, key=lambda k: abs(z[k]), reverse=True)
    traits = []
    for key in ranked[:limit]:
        label = FEATURE_LABELS.get(key, key).lower()
        if key in ratio_metrics and pop_means[key] > 0:
            traits.append(f"{seg_means[key] / pop_means[key]:.1f}x the average {label}")
        else:
            traits.append(f"{'Higher' if z[key] > 0 else 'Lower'} {label} than average")
    return traits


def profile_segments(
    features: pd.DataFrame, raw: pd.DataFrame, labels: np.ndarray, target: pd.Series
) -> list[SegmentProfile]:
    """`raw` is the cleaned frame (for spend and channel totals); all frames share an index."""
    zscores = _zscores(features, labels)
    names = assign_names(zscores)
    pop_means = features[list(zscores[next(iter(zscores))])].mean()
    profiles = []
    for seg in sorted(zscores):
        mask = labels == seg
        seg_feat = features[mask]
        spend = raw.loc[mask, list(SPEND_COLUMNS.values())].sum()
        channels = raw.loc[mask, list(PURCHASE_CHANNELS.values())].sum()
        seg_means = seg_feat[pop_means.index].mean()
        profiles.append(
            SegmentProfile(
                segment_id=seg,
                name=names[seg],
                tagline=ARCHETYPES[names[seg]][1] if names[seg] in ARCHETYPES else "",
                size=int(mask.sum()),
                share=float(mask.mean()),
                response_rate=float(target[mask].mean()),
                prior_accept_rate=float((seg_feat["prior_accepts"] > 0).mean()),
                means={m: float(seg_feat[m].mean()) for m in PROFILE_METRICS},
                spend_mix={c: float(spend[SPEND_COLUMNS[c]] / max(spend.sum(), 1)) for c in SPEND_CATEGORIES},
                channel_mix={c: float(channels[PURCHASE_CHANNELS[c]] / max(channels.sum(), 1)) for c in CHANNELS},
                traits=_traits(seg_means, pop_means, zscores[seg]),
            )
        )
    return profiles
