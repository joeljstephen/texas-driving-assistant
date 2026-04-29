"""Reusable scenario chips for the Streamlit UI and tests."""

from __future__ import annotations

QUICK_ACTIONS: dict[str, str] = {
    "First-time application": "I am applying for my first Texas driver license.",
    "Moving to Texas with out-of-state license": "I moved to Texas and have a valid unexpired out-of-state driver license.",
    "Renew license": "I want to renew my Texas driver license.",
    "Replace lost license": "I lost my Texas driver license and need a replacement.",
}


SUPPORTED_SCENARIOS = [
    "First-time adult Texas driver license application",
    "Moving to Texas with a valid, unexpired out-of-state license",
    "Texas driver license renewal",
    "Replacement of a lost, stolen, or damaged Texas license",
]

