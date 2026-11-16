"""Prompts and JSON schemas for the AI features. Only computed numbers go in; nothing is invented."""

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


BRIEF_SYSTEM = (
    "You are a marketing analyst writing a short campaign brief for a retailer from a model's analysis of "
    "their customer file. Use only the numbers you are given; do not invent any. Expected responders are "
    "model estimates, so say 'expected'. Plain English, concrete, no hype, no emojis."
)

BRIEF_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string", "description": "One sentence: who to contact and the expected result."},
        "summary": {"type": "string", "description": "2 or 3 sentences on the opportunity."},
        "actions": {
            "type": "array",
            "description": "2 to 4 actions, one per segment worth contacting, largest expected impact first.",
            "items": {
                "type": "object",
                "properties": {
                    "segment": {"type": "string"},
                    "audience": {"type": "string", "description": "How many customers, from the numbers given."},
                    "channel": {"type": "string", "enum": ["web", "catalog", "store", "email"]},
                    "message": {"type": "string", "description": "The offer or message."},
                    "why": {"type": "string", "description": "Which number supports it."},
                },
                "required": ["segment", "audience", "channel", "message", "why"],
            },
        },
        "budget_note": {"type": "string", "description": "One sentence on cost, expected revenue and profit."},
        "watch_outs": {"type": "array", "items": {"type": "string"}, "description": "0 to 3 caveats."},
    },
    "required": ["headline", "summary", "actions", "budget_note", "watch_outs"],
}


def brief_prompt(context: dict) -> str:
    return f"Analysis of the uploaded customer file:\n{json.dumps(context, indent=1)}\n\nWrite the campaign brief."
