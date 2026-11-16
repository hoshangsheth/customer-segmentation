"""
AI insights with a rule-based fallback. Every method returns usable text: from the LLM when one is
configured and answers, otherwise from templates built on the same numbers. `source` says which.
Segment personas are cached per artifact version.
"""

import logging
from typing import Any

from customer_segmentation.llm.contracts import LLMError, LLMProvider
from customer_segmentation.llm.prompts import (
    BRIEF_SCHEMA,
    BRIEF_SYSTEM,
    EXPLAIN_SCHEMA,
    EXPLAIN_SYSTEM,
    PERSONA_SCHEMA,
    PERSONA_SYSTEM,
    brief_prompt,
    explain_prompt,
    persona_prompt,
)

log = logging.getLogger(__name__)

# Rule-based campaign ideas per archetype: (title, channel, offer, rationale)
PLAYBOOK: dict[str, list[tuple[str, str, str, str]]] = {
    "High-value loyalists": [
        (
            "VIP early access",
            "email",
            "Early access to new wines and premium cuts",
            "Highest spend and purchase frequency",
        ),
        (
            "Loyalty tier upgrade",
            "store",
            "Points multiplier on in-store visits",
            "Frequent buyers are worth retaining",
        ),
    ],
    "Affluent catalog buyers": [
        ("Curated catalog bundle", "catalog", "Premium wine and gourmet bundle", "High income and catalog share"),
        ("Concierge reorder", "email", "One-click reorder of past baskets", "Large average order value"),
    ],
    "Deal-seeking families": [
        ("Family value pack", "web", "Multi-buy discount on everyday items", "High share of purchases on discount"),
        ("Back-to-school coupons", "email", "Coupons on snacks and sweets", "More children at home"),
    ],
    "Budget browsers": [
        ("Browse-to-buy nudge", "web", "Small first-order discount after a site visit", "Many web visits, low spend"),
    ],
    "Wine enthusiasts": [
        ("Wine club", "email", "Monthly tasting selection", "Spend concentrated on wine"),
        ("Pairing promotion", "store", "Discount on cheese and meat with wine", "Cross-sell from the main category"),
    ],
    "Lapsing customers": [
        (
            "Win-back offer",
            "email",
            "Time-limited voucher on their favourite category",
            "Long time since last purchase",
        ),
    ],
    "Steady mid-spenders": [
        ("Category discovery", "web", "Discount on a category they have not tried", "Average spend with room to grow"),
    ],
}


class InsightsService:
    def __init__(self, provider: LLMProvider | None, version: str):
        self.provider = provider
        self.version = version
        self._persona_cache: dict[int, dict[str, Any]] = {}

    @property
    def ai_available(self) -> bool:
        return self.provider is not None

    def _ask(self, system: str, user: str, schema: dict) -> dict | None:
        if self.provider is None:
            return None
        try:
            return self.provider.complete_json(system=system, user=user, schema=schema)
        except LLMError as e:
            log.warning("LLM call failed, using rule-based text: %s", e)
            return None

    def segment_persona(self, segment: dict, population: dict) -> dict[str, Any]:
        sid = segment["segment_id"]
        if sid in self._persona_cache:
            return self._persona_cache[sid]
        data = self._ask(PERSONA_SYSTEM, persona_prompt(segment, population), PERSONA_SCHEMA)
        if data is not None:
            result = {**data, "source": "llm", "model": getattr(self.provider, "model", "")}
            self._persona_cache[sid] = result  # cache only real answers so a later retry can succeed
            return result
        return {**self._persona_fallback(segment), "source": "rule-based", "model": ""}

    def explain_score(self, score: dict) -> dict[str, Any]:
        data = self._ask(EXPLAIN_SYSTEM, explain_prompt(score), EXPLAIN_SCHEMA)
        if data is not None:
            return {**data, "source": "llm", "model": getattr(self.provider, "model", "")}
        return {**self._explain_fallback(score), "source": "rule-based", "model": ""}

    def campaign_brief(self, context: dict) -> dict[str, Any]:
        data = self._ask(BRIEF_SYSTEM, brief_prompt(context), BRIEF_SCHEMA)
        if data is not None:
            return {**data, "source": "llm", "model": getattr(self.provider, "model", "")}
        return {**self._brief_fallback(context), "source": "rule-based", "model": ""}

    @staticmethod
    def _brief_fallback(ctx: dict) -> dict[str, Any]:
        t = ctx["target"]
        share = round(t["share"] * 100)
        actions = []
        for seg in ctx["target_segments"][:4]:
            title, channel, offer, rationale = PLAYBOOK.get(seg["segment"], PLAYBOOK["Steady mid-spenders"])[0]
            actions.append(
                {
                    "segment": seg["segment"],
                    "audience": f"{seg['customers']:,} customers in the target list",
                    "channel": channel,
                    "message": f"{title}: {offer}",
                    "why": f"{seg['expected_responders']:.0f} expected responders; {rationale.lower()}",
                }
            )
        watch = []
        if not ctx["model"]["uses_history"]:
            watch.append(
                "No campaign history was provided, so the behaviour-only model was used; adding history usually sharpens the ranking."
            )
        if ctx["data_fit_flags"]:
            watch.append(
                "Some customer values sit outside the range the model was trained on: "
                + ", ".join(ctx["data_fit_flags"][:3])
                + "."
            )
        watch.append("Expected responders are model estimates; compare them with actual results after the campaign.")
        return {
            "headline": f"Contact the top {share}% of customers ({t['contacts']:,}) for about {t['expected_responders']:.0f} expected responders.",
            "summary": (
                f"The model ranked {ctx['customers']:,} customers. Contacting the top {share}% is expected to reach "
                f"{t['expected_responders']:.0f} responders, against {ctx['expected_responders_all']:.0f} if everyone were contacted."
            ),
            "actions": actions,
            "budget_note": (
                f"At {t['cost_per_contact']:g} per contact and {t['revenue_per_response']:g} per response, the expected cost is "
                f"{t['cost']:,.0f}, expected revenue {t['revenue']:,.0f} and expected profit {t['profit']:,.0f}."
            ),
            "watch_outs": watch[:3],
        }

    @staticmethod
    def _persona_fallback(segment: dict) -> dict[str, Any]:
        name = segment["name"]
        traits = segment.get("traits", [])
        persona = segment.get("tagline", "") or name
        if traits:
            joined = "; ".join(t[:1].lower() + t[1:] for t in traits)
            persona += f" Compared with the average customer: {joined}."
        campaigns = [
            {"title": t, "channel": c, "offer": o, "rationale": r}
            for t, c, o, r in PLAYBOOK.get(name, PLAYBOOK["Steady mid-spenders"])
        ]
        return {
            "persona": persona,
            "motivations": [],  # traits are already in the persona text; motivations need the LLM
            "campaigns": campaigns,
            "watch_outs": [],
        }

    @staticmethod
    def _explain_fallback(score: dict) -> dict[str, Any]:
        reasons = score.get("reasons", [])
        up = [r["label"].lower() for r in reasons if r["shap"] > 0][:2]
        down = [r["label"].lower() for r in reasons if r["shap"] < 0][:2]
        prob = score["probability"]
        parts = [f"Estimated chance of accepting the next campaign: {prob:.0%}."]
        if up:
            parts.append(f"It is pushed up mainly by {' and '.join(up)}.")
        if down:
            parts.append(f"It is held down by {' and '.join(down)}.")
        action = (
            "Include this customer in the next campaign."
            if prob >= score.get("base_rate", 0.15)
            else "Leave this customer out of paid contact and use low-cost channels."
        )
        return {"summary": " ".join(parts), "next_best_action": action}
