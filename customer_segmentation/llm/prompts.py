"""Prompts and JSON schemas for the two AI features. Only computed numbers go in; nothing is invented."""

import json

PERSONA_SYSTEM = (
    "You are a marketing analyst. You write short, concrete customer personas and campaign ideas "
    "for a grocery and wine retailer, using only the statistics you are given. Do not invent numbers. "
    "Plain English, no hype, no emojis."
)

PERSONA_SCHEMA = {
    "type": "object",
    "properties": {
        "persona": {
            "type": "string",
            "description": "One paragraph, 2 to 4 sentences, describing who these customers are.",
        },
        "motivations": {"type": "array", "items": {"type": "string"}, "description": "2 to 4 short items."},
        "campaigns": {
            "type": "array",
            "description": "2 or 3 campaign ideas.",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "channel": {"type": "string", "enum": ["web", "catalog", "store", "email"]},
                    "offer": {"type": "string"},
                    "rationale": {"type": "string", "description": "Which statistic supports it."},
                },
                "required": ["title", "channel", "offer", "rationale"],
            },
        },
        "watch_outs": {"type": "array", "items": {"type": "string"}, "description": "0 to 2 risks."},
    },
    "required": ["persona", "motivations", "campaigns", "watch_outs"],
}

EXPLAIN_SYSTEM = (
    "You explain a machine-learning score to a marketing manager. You are given the predicted "
    "probability that a customer accepts the next campaign and the SHAP contributions behind it "
    "(positive raises the probability, negative lowers it). Explain in plain English using only "
    "these facts. No jargon such as 'log-odds' or 'SHAP'. No emojis."
)

EXPLAIN_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "2 or 3 sentences."},
        "next_best_action": {"type": "string", "description": "One concrete recommendation."},
    },
    "required": ["summary", "next_best_action"],
}


def persona_prompt(segment: dict, population: dict) -> str:
    return (
        "Segment statistics (means are per customer; spend is over two years; mixes are shares):\n"
        f"{json.dumps(segment, indent=1)}\n\n"
        f"Whole customer base for comparison:\n{json.dumps(population, indent=1)}\n\n"
        "Write the persona, motivations, campaign ideas and watch-outs."
    )


def explain_prompt(score: dict) -> str:
    return f"Customer score:\n{json.dumps(score, indent=1)}\n\nExplain this score."
