"""State reconciliation for follow-up chat turns.

Follow-up messages can both ask questions and add or correct facts. This
module keeps document selections in sync with parsed facts so an old
"not sure" / "none" answer does not overwrite a newly stated fact when the
policy engine is rerun.
"""

from __future__ import annotations

import re
from dataclasses import fields

from .document_catalog import DOCUMENT_CATEGORIES
from .models import DocumentSelections, FactState, ParseResult
from .parser import normalize_text


DOCUMENT_FACT_TO_CATEGORY = {
    "has_identity_doc": "identity",
    "has_social_security": "social_security",
    "has_texas_residency_docs": "residency",
}


OPTION_PATTERNS: dict[str, list[tuple[str, tuple[str, ...]]]] = {
    "identity": [
        ("us_passport", ("passport", "passport card")),
        ("us_birth_certificate", ("birth certificate",)),
        ("certificate_of_citizenship", ("certificate of citizenship", "citizenship certificate")),
        ("certificate_of_naturalization", ("certificate of naturalization", "naturalization certificate")),
        ("permanent_resident_card", ("permanent resident card", "green card", "i 551", "i-551")),
        ("us_military_id", ("military id",)),
        ("out_of_state_license", ("out of state license", "out-of-state license")),
        ("foreign_passport_with_i94", ("foreign passport", "i 94", "i-94", "i94")),
        ("employment_authorization", ("employment authorization", "i 766", "i-766")),
        ("school_id_with_records", ("school id", "school records")),
        ("social_security_card_id", ("social security card", "ss card")),
        ("medicare_or_medicaid_card", ("medicare card", "medicaid card")),
    ],
    "social_security": [
        ("ssn_card", ("social security card", "ss card")),
        ("w2_form", ("w2", "w 2", "w-2")),
        ("ssa_1099", ("1099", "ssa 1099", "ssa-1099")),
        ("paystub_with_ssn", ("paystub", "pay stub")),
        ("knows_ssn_only", ("know my ssn", "know my social security", "know the ssn")),
        ("not_eligible_for_ssn", ("not eligible for an ssn", "not eligible for social security")),
    ],
    "residency": [
        ("texas_lease_or_mortgage", ("lease", "mortgage", "deed")),
        ("texas_utility_bill", ("utility bill", "electric bill", "gas bill", "water bill", "internet bill")),
        ("texas_bank_statement", ("bank statement", "credit card statement")),
        ("texas_voter_registration", ("voter registration",)),
        ("texas_vehicle_registration_doc", ("vehicle registration", "title")),
        ("texas_insurance_policy", ("insurance policy", "renters insurance", "home insurance", "auto insurance")),
        ("texas_employer_letter", ("employer letter", "school letter")),
        ("texas_w2_or_paystub", ("w2", "w 2", "w-2", "paystub", "pay stub")),
        ("texas_government_mail", ("government mail",)),
        ("texas_school_records", ("school records", "transcript")),
    ],
}


LAWFUL_PRESENCE_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("us_citizen", ("us citizen", "u s citizen", "united states citizen", "i am a citizen")),
    ("permanent_resident", ("permanent resident", "green card", "i 551", "i-551")),
    ("asylee_or_refugee", ("asylee", "refugee")),
    ("visa_holder_with_i94", ("visa", "i 94", "i-94", "i94")),
    ("employment_authorization_holder", ("employment authorization", "i 766", "i-766")),
    ("daca_recipient", ("daca",)),
]


ASSERTION_PATTERNS = (
    r"\b(update|change|correct|actually|now|turns out)\b",
    r"\b(i have|i do have|i got|i can show|i am|i'm|im|i completed|i own|i know)\b",
    r"\b(i do not|i don't|i dont|i no longer|i am not|i'm not|im not)\b",
    r"\b(my .{0,30} is|my .{0,30} are)\b",
)

QUESTION_START = re.compile(r"^(what|which|how|why|when|where|do|does|can|could|should|is|are|will|would)\b")


def reconcile_followup_documents(
    user_text: str,
    parsed_facts: FactState,
    documents: DocumentSelections,
) -> DocumentSelections:
    """Return document selections updated from a follow-up utterance.

    The deterministic/Gemini parsers operate at the fact level. This helper
    mirrors those fact updates into the document selector state so later calls
    to ``apply_document_selections`` preserve the user's new answer.
    """

    updated = _copy_documents(documents)
    text = normalize_text(user_text)

    for field_name, category_key in DOCUMENT_FACT_TO_CATEGORY.items():
        value = getattr(parsed_facts, field_name)
        if category_key == "residency" and parsed_facts.texas_residency_doc_count is not None:
            count = parsed_facts.texas_residency_doc_count
            if count <= 0:
                _mark_category_none(updated, category_key)
            else:
                _clear_negative_category_state(updated, category_key)
                for option_key in _matching_options(text, category_key):
                    _add_selection(updated, category_key, option_key)
            continue
        if value is True:
            _clear_negative_category_state(updated, category_key)
            for option_key in _matching_options(text, category_key):
                _add_selection(updated, category_key, option_key)
        elif value is False:
            _mark_category_none(updated, category_key)

    lawful_choice = _lawful_presence_choice(text, parsed_facts)
    if lawful_choice:
        updated.lawful_presence_choice = lawful_choice

    return updated


def should_apply_followup_facts(
    user_text: str,
    parse_result: ParseResult,
    next_question: str | None = None,
) -> bool:
    """Decide whether a follow-up turn should mutate stored state.

    The parser intentionally recognizes document and eligibility phrases, but
    a phrase inside a question is often not a user assertion. This keeps report
    questions read-only while still allowing explicit corrections and answers
    to the rule engine's current question.
    """

    if not _has_fact_updates(parse_result.facts):
        return False

    text = normalize_text(user_text)
    if not text:
        return False

    if next_question and _is_direct_contextual_answer(text):
        return True

    if text.startswith("what if"):
        return any(re.search(pattern, text) for pattern in ASSERTION_PATTERNS[:1])

    is_question = "?" in user_text or QUESTION_START.search(text) is not None
    has_assertion = any(re.search(pattern, text) for pattern in ASSERTION_PATTERNS)
    if is_question and not has_assertion:
        return False

    return True


def _copy_documents(documents: DocumentSelections) -> DocumentSelections:
    return DocumentSelections(
        selected={key: list(values) for key, values in documents.selected.items()},
        other_text=dict(documents.other_text),
        unsure=dict(documents.unsure),
        none=dict(documents.none),
        lawful_presence_choice=documents.lawful_presence_choice,
    )


def _has_fact_updates(facts: FactState) -> bool:
    for field_info in fields(FactState):
        if field_info.name == "source_notes":
            continue
        if getattr(facts, field_info.name) is not None:
            return True
    return False


def _is_direct_contextual_answer(text: str) -> bool:
    return (
        text in {"yes", "y", "yeah", "yep", "no", "n", "nope"}
        or re.fullmatch(r"\d{1,3}", text) is not None
    )


def _clear_negative_category_state(documents: DocumentSelections, category_key: str) -> None:
    documents.unsure[category_key] = False
    documents.none[category_key] = False


def _mark_category_none(documents: DocumentSelections, category_key: str) -> None:
    documents.selected[category_key] = []
    documents.other_text[category_key] = ""
    documents.unsure[category_key] = False
    documents.none[category_key] = True


def _add_selection(documents: DocumentSelections, category_key: str, option_key: str) -> None:
    if category_key not in DOCUMENT_CATEGORIES:
        return
    valid_keys = {option.key for option in DOCUMENT_CATEGORIES[category_key].options}
    if option_key not in valid_keys:
        return
    selections = documents.selected.setdefault(category_key, [])
    if option_key not in selections:
        selections.append(option_key)


def _matching_options(text: str, category_key: str) -> list[str]:
    matches: list[str] = []
    for option_key, phrases in OPTION_PATTERNS.get(category_key, []):
        if any(phrase in text for phrase in phrases):
            matches.append(option_key)
    return matches


def _lawful_presence_choice(text: str, facts: FactState) -> str | None:
    if facts.us_citizen is True:
        return "us_citizen"
    for option_key, phrases in LAWFUL_PRESENCE_PATTERNS:
        if any(phrase in text for phrase in phrases):
            return option_key
    if facts.lawful_presence_category_known is True:
        return None
    if facts.lawful_presence_category_known is None and "not sure" in text:
        return "not_sure"
    return None
