"""
The fields an uploaded customer file can provide, in the user's terms.

Each field knows its type, whether it is required, the column names it is usually called (for
auto-matching), and the raw dataset column it becomes. Some needs can be met in more than one way,
for example a birth year or an age; those are expressed as `REQUIRED_GROUPS`.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Literal

Kind = Literal["id", "int", "float", "date", "category", "flag"]
FileRole = Literal["customers", "history"]


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    group: str
    kind: Kind
    description: str
    aliases: tuple[str, ...] = ()
    required: bool = False
    default: float | str | None = None  # used when an optional field is not mapped
    file: FileRole = "customers"  # where this field is usually found
    history: bool = False  # campaign history: switches to the full model when mapped

    def to_dict(self) -> dict:
        d = asdict(self)
        d["aliases"] = list(self.aliases)
        return d


SPEND = {
    "wine": "Wine",
    "fruit": "Fruit",
    "meat": "Meat",
    "fish": "Fish",
    "sweet": "Sweets",
    "gold": "Gold and premium",
}
CHANNELS = {"web": "Website", "catalog": "Catalog", "store": "In store", "deals": "On discount"}

FIELDS: list[Field] = [
    Field(
        "customer_id",
        "Customer ID",
        "Identity",
        "id",
        "Unique ID for each customer, used to join files and in exports.",
        ("id", "customer_id", "customerid", "cust_id", "client_id", "customer", "customer_number", "member_id"),
        required=True,
    ),
    # Household
    Field(
        "year_birth",
        "Birth year",
        "Household",
        "int",
        "Year of birth. Map this or Age.",
        ("year_birth", "birth_year", "yob", "birthyear", "dob_year", "year_of_birth"),
    ),
    Field("age", "Age", "Household", "int", "Age in years. Used when no birth year is given.", ("age", "customer_age")),
    Field(
        "income",
        "Household income",
        "Household",
        "float",
        "Yearly household income.",
        ("income", "annual_income", "household_income", "yearly_income", "salary"),
        required=True,
    ),
    Field(
        "education",
        "Education",
        "Household",
        "category",
        "Highest education, any wording (Bachelor, Master, PhD, High school...).",
        ("education", "education_level", "degree", "qualification"),
        default="Graduate",
    ),
    Field(
        "marital_status",
        "Marital status",
        "Household",
        "category",
        "Married, together, single, divorced... any wording.",
        ("marital_status", "maritalstatus", "marital", "relationship_status", "civil_status"),
        default="Partnered",
    ),
    Field(
        "kids",
        "Children at home",
        "Household",
        "int",
        "Number of young children at home.",
        ("kidhome", "kids", "children", "num_children", "kids_home", "young_children"),
        default=0,
    ),
    Field(
        "teens",
        "Teenagers at home",
        "Household",
        "int",
        "Number of teenagers at home.",
        ("teenhome", "teens", "teenagers", "teens_home"),
        default=0,
    ),
    # Relationship
    Field(
        "customer_since",
        "Customer since",
        "Relationship",
        "date",
        "Date the customer joined or first bought.",
        (
            "dt_customer",
            "customer_since",
            "signup_date",
            "join_date",
            "joined",
            "first_purchase_date",
            "registration_date",
            "created_at",
        ),
        required=True,
    ),
    Field(
        "recency",
        "Days since last purchase",
        "Relationship",
        "int",
        "Days since the last purchase. Map this or Last purchase date.",
        ("recency", "days_since_last_purchase", "days_since_purchase", "last_purchase_days"),
    ),
    Field(
        "last_purchase_date",
        "Last purchase date",
        "Relationship",
        "date",
        "Date of the last purchase. Used when days since last purchase is not given.",
        ("last_purchase_date", "last_purchase", "last_order_date", "last_order"),
    ),
    Field(
        "web_visits",
        "Website visits last month",
        "Relationship",
        "int",
        "Visits to the website in the last month.",
        ("numwebvisitsmonth", "web_visits", "website_visits", "visits_last_month", "monthly_visits"),
        default=5,
    ),
    Field(
        "complain",
        "Complained recently",
        "Relationship",
        "flag",
        "Complained in the last two years (yes/no or 1/0).",
        ("complain", "complaint", "complained", "has_complaint"),
        default=0,
    ),
    # Spend
    *[
        Field(
            f"spend_{k}",
            f"Spend: {label}",
            "Spend",
            "float",
            f"Amount spent on {label.lower()} in the last two years.",
            (
                f"mnt{k}s",
                f"mnt{k}",
                f"mnt{k}products",
                f"mnt{k}prods",
                f"{k}_spend",
                f"spend_{k}",
                f"{k}_amount",
                f"{k}",
            ),
            default=0,
        )
        for k, label in SPEND.items()
    ],
    # Purchases
    *[
        Field(
            f"purchases_{k}",
            f"Purchases: {label}",
            "Purchases",
            "int",
            f"Number of purchases {label.lower()}.",
            (f"num{k}purchases", f"{k}_purchases", f"purchases_{k}", f"{k}_orders", f"num_{k}_purchases")
            + (
                ("discount_purchases", "discounted_purchases", "deal_purchases", "promo_purchases")
                if k == "deals"
                else ()
            ),
            default=0,
        )
        for k, label in CHANNELS.items()
    ],
    # Campaign history (switches to the full model)
    *[
        Field(
            f"accepted_cmp{i}",
            f"Accepted campaign {i}",
            "Campaign history",
            "flag",
            f"Accepted your {['oldest', 'second', 'third', 'fourth', 'most recent'][i - 1]} of five earlier campaigns (yes/no or 1/0).",
            (f"acceptedcmp{i}", f"accepted_cmp{i}", f"campaign_{i}", f"cmp{i}", f"campaign{i}_accepted"),
            file="history",
            history=True,
        )
        for i in range(1, 6)
    ],
    Field(
        "offers_accepted",
        "Earlier offers accepted (count)",
        "Campaign history",
        "int",
        "How many of the last five campaigns the customer accepted. Use when per-campaign columns are not available.",
        ("offers_accepted", "campaigns_accepted", "total_accepted", "accepted_count", "prior_accepts", "acceptedcmps"),
        file="history",
        history=True,
    ),
    # Outcome (optional): lets the app check its ranking on your data
    Field(
        "response",
        "Responded to the latest campaign",
        "Outcome",
        "flag",
        "Optional. If you know who responded to your latest campaign, the app measures how well it would have ranked them.",
        ("response", "responded", "converted", "conversion", "accepted_last_campaign", "responded_last_campaign"),
        file="history",
    ),
]

FIELD_BY_KEY = {f.key: f for f in FIELDS}
SPEND_KEYS = [f"spend_{k}" for k in SPEND]
PURCHASE_KEYS = [f"purchases_{k}" for k in CHANNELS]
CAMPAIGN_KEYS = [f"accepted_cmp{i}" for i in range(1, 6)]
HISTORY_KEYS = [f.key for f in FIELDS if f.history]


@dataclass(frozen=True)
class RequiredGroup:
    keys: tuple[str, ...]
    message: str


REQUIRED_GROUPS = [
    RequiredGroup(("year_birth", "age"), "Map a birth year or an age column."),
    RequiredGroup(("recency", "last_purchase_date"), "Map days since last purchase or a last purchase date."),
    RequiredGroup(tuple(SPEND_KEYS), "Map at least one spend column."),
    RequiredGroup(tuple(PURCHASE_KEYS), "Map at least one purchases column."),
]


def normalise(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


@dataclass
class ColumnRef:
    file: FileRole
    column: str


@dataclass
class Suggestion:
    mapping: dict[str, ColumnRef] = field(default_factory=dict)
    history_id_column: str | None = None


def suggest_mapping(columns: dict[str, list[str]]) -> Suggestion:
    """
    Match uploaded column names to fields: exact alias match first, then an alias contained in the
    column name. Each column is used at most once, and a field prefers its usual file.
    """
    used: set[tuple[str, str]] = set()
    out = Suggestion()
    norm = {f: {c: normalise(c) for c in cols} for f, cols in columns.items()}

    def find(fld: Field, exact: bool) -> ColumnRef | None:
        files = sorted(norm, key=lambda f: f != fld.file)  # usual file first
        aliases = [normalise(a) for a in fld.aliases]
        for f in files:
            for col, n in norm[f].items():
                if (f, col) in used:
                    continue
                loose = not exact and fld.kind != "id" and any(len(a) > 3 and a in n for a in aliases)
                if (exact and n in aliases) or loose:
                    return ColumnRef(f, col)  # type: ignore[arg-type]
        return None

    for exact in (True, False):
        for fld in FIELDS:
            if fld.key in out.mapping:
                continue
            ref = find(fld, exact)
            if ref:
                out.mapping[fld.key] = ref
                used.add((ref.file, ref.column))

    # The history file is joined on its own ID column.
    if "history" in norm:
        id_aliases = {normalise(a) for a in FIELD_BY_KEY["customer_id"].aliases}
        out.history_id_column = next((c for c, n in norm["history"].items() if n in id_aliases), None)
        cid = out.mapping.get("customer_id")
        if cid and cid.file == "history":  # the customer ID belongs to the customers file
            del out.mapping["customer_id"]
            cust = next((c for c, n in norm["customers"].items() if n in id_aliases), None)
            if cust:
                out.mapping["customer_id"] = ColumnRef("customers", cust)
    return out


def missing_requirements(mapped: set[str]) -> list[str]:
    problems = [f"Map {FIELD_BY_KEY[f.key].label}." for f in FIELDS if f.required and f.key not in mapped]
    problems += [g.message for g in REQUIRED_GROUPS if not mapped.intersection(g.keys)]
    return problems
