"""Deterministic parser for extracting driver-license facts from free text."""

from __future__ import annotations

import re
from dataclasses import fields

from .models import FactState, ParseResult


GOAL_PATTERNS: list[tuple[str, str, str]] = [
    (
        r"\b(first[- ]?time|first(?: texas| tx)?(?: driver)? license|never had (a )?license|new driver)\b",
        "first_time",
        "first-time application",
    ),
    (r"\b(renew|renewal|expir(?:e|es|ing|ed))\b", "renewal", "renewal"),
    (r"\b(replace|replacement|lost|stolen|damaged|destroyed|misplaced)\b", "replacement", "replacement"),
    (
        r"\b(mov(?:e|ed|ing) to texas|new texas resident|out[- ]of[- ]state license|out of state license|transfer)\b",
        "transfer",
        "out-of-state transfer",
    ),
]


def normalize_text(text: str) -> str:
    """Normalize text enough for predictable regex matching."""

    lowered = text.lower()
    lowered = lowered.replace("driver's", "driver")
    lowered = re.sub(r"[^a-z0-9/\-\s]", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def parse_message(text: str) -> ParseResult:
    """Extract structured facts from one user utterance without using an LLM."""

    normalized = normalize_text(text)
    facts = FactState()
    matches: list[str] = []

    _parse_goal(normalized, facts, matches)
    _parse_age(normalized, facts, matches)
    _parse_residency_and_license(normalized, facts, matches)
    _parse_validity(normalized, facts, matches)
    _parse_renewal_timing(normalized, facts, matches)
    _parse_replacement_changes(normalized, facts, matches)
    _parse_documents(normalized, facts, matches)

    facts.source_notes = matches
    return ParseResult(facts=facts, matched_phrases=matches)


def parse_message_with_context(text: str, next_question: str | None = None) -> ParseResult:
    """Parse a message, using the current s(CASP) question for short answers."""

    result = parse_message(text)
    normalized = normalize_text(text)
    contextual_notes: list[str] = []

    _parse_contextual_age(normalized, next_question, result.facts, contextual_notes)
    _parse_contextual_yes_no(normalized, next_question, result.facts, contextual_notes)
    _parse_contextual_expiration(normalized, next_question, result.facts, contextual_notes)

    for note in contextual_notes:
        if note not in result.matched_phrases:
            result.matched_phrases.append(note)
        if note not in result.facts.source_notes:
            result.facts.source_notes.append(note)

    return result


def _parse_contextual_age(text: str, next_question: str | None, facts: FactState, matches: list[str]) -> None:
    if next_question != "ask_age":
        return
    found = re.fullmatch(r"(?:i am |i m |im |age )?(\d{1,2})(?: years old| year old| yrs old| yo| y/o)?", text)
    if found:
        age = int(found.group(1))
        if 0 < age < 100:
            facts.age = age
            matches.append(f"age {age}")


def _parse_contextual_yes_no(text: str, next_question: str | None, facts: FactState, matches: list[str]) -> None:
    answer = _yes_no_answer(text)
    if answer is None or next_question is None:
        return

    yes_no_mappings = {
        "ask_out_of_state_license_presence": ("has_out_of_state_license", "out-of-state license presence"),
        "ask_out_of_state_validity": ("out_of_state_license_valid", "out-of-state license validity"),
        "ask_if_out_of_state_expired_more_than_two_years": (
            "out_of_state_license_expired_over_two_years",
            "out-of-state license expired over two years",
        ),
        "ask_last_renewal_method": ("last_renewed_in_person", "last renewed in person"),
        "ask_license_status": ("license_valid_status", "license valid status"),
        "ask_ssn_on_record": ("ssn_on_record", "SSN on record"),
        "ask_front_card_changed": ("front_card_changed", "front-of-card change"),
        "ask_card_number_for_online_replacement": ("has_card_number", "card number available"),
        "ask_date_of_birth_for_online_replacement": (
            "has_date_of_birth_for_online",
            "date of birth available",
        ),
        "ask_last4_ssn_for_online_replacement": ("has_last4_ssn", "last four SSN available"),
        "ask_audit_number_for_online_replacement": ("has_audit_number", "audit number available"),
        "ask_residency_documents": ("has_texas_residency_docs", "Texas residency documents"),
        "ask_identity_documents": ("has_identity_doc", "identity document"),
        "ask_social_security": ("has_social_security", "Social Security proof"),
        "ask_lawful_presence_category": ("lawful_presence_category_known", "lawful presence category"),
    }

    if next_question == "ask_health_change":
        facts.health_conditions_unchanged = not answer
        matches.append("health conditions changed" if answer else "health conditions unchanged")
        return

    if next_question == "ask_outstanding_tickets_or_warrants":
        facts.no_outstanding_tickets_or_warrants = not answer
        matches.append("outstanding tickets or warrants" if answer else "no outstanding tickets or warrants")
        return

    if next_question in {"ask_citizenship_for_online_renewal", "ask_lawful_presence_for_online_renewal"}:
        facts.us_citizen = answer
        if answer:
            facts.lawful_presence_category_known = True
        matches.append("U.S. citizen" if answer else "not U.S. citizen")
        return

    if next_question == "ask_if_out_of_state_expired_more_than_two_years" and not answer:
        facts.out_of_state_license_expired_not_over_two_years = True
        matches.append("out-of-state license expired not over two years")
        return

    mapping = yes_no_mappings.get(next_question)
    if mapping:
        field_name, note = mapping
        setattr(facts, field_name, answer)
        matches.append(note)


def _parse_contextual_expiration(text: str, next_question: str | None, facts: FactState, matches: list[str]) -> None:
    if next_question != "ask_out_of_state_expiration":
        return
    if re.search(r"\b(unexpired|not expired|current|valid)\b", text):
        facts.out_of_state_license_unexpired = True
        matches.append("out-of-state license unexpired")
    elif re.search(r"\b(expired|past expiration)\b", text):
        facts.out_of_state_license_unexpired = False
        matches.append("out-of-state license expired")


def _yes_no_answer(text: str) -> bool | None:
    yes_values = {"yes", "y", "yeah", "yep", "correct", "right", "i do", "i have", "i can"}
    no_values = {"no", "n", "nope", "not yet", "i do not", "i don t", "i dont", "i have not", "i haven t"}
    if text in yes_values:
        return True
    if text in no_values:
        return False
    if re.fullmatch(r"yes[,\s].*", text):
        return True
    if re.fullmatch(r"no[,\s].*", text):
        return False
    return None


def _parse_goal(text: str, facts: FactState, matches: list[str]) -> None:
    for pattern, goal, label in GOAL_PATTERNS:
        if re.search(pattern, text):
            facts.goal = goal
            matches.append(label)

    if re.search(r"\b(apply|applying|application|get a texas license|get my texas license)\b", text):
        facts.applying_texas_license = True
        matches.append("applying for a Texas license")


def _parse_age(text: str, facts: FactState, matches: list[str]) -> None:
    age_patterns = [
        r"\b(?:i am|i m|im|age|aged)\s+(\d{1,2})\b",
        r"\b(\d{1,2})\s*(?:years old|year old|yrs old|yo|y/o)\b",
        r"\bage\s*[:=]?\s*(\d{1,2})\b",
    ]
    for pattern in age_patterns:
        found = re.search(pattern, text)
        if found:
            age = int(found.group(1))
            if 0 < age < 100:
                facts.age = age
                matches.append(f"age {age}")
                return


def _parse_residency_and_license(text: str, facts: FactState, matches: list[str]) -> None:
    if re.search(r"\b(mov(?:e|ed|ing) to texas|new texas resident|relocat(?:e|ed|ing) to texas)\b", text):
        facts.new_texas_resident = True
        facts.applying_texas_license = True
        matches.append("new Texas resident")

    if re.search(r"\b(out[- ]of[- ]state|oklahoma|california|florida|new mexico|louisiana|arkansas)\b", text):
        facts.has_out_of_state_license = True
        matches.append("out-of-state license")

    applying_for_texas_license = re.search(
        r"\b(apply|applying|application|get|getting|need|want)\b.{0,40}\b(texas license|tx license|texas driver license|tx driver license)\b",
        text,
    )
    if re.search(r"\b(texas license|tx license|texas driver license|tx driver license)\b", text) and not applying_for_texas_license:
        facts.has_texas_license = True
        matches.append("Texas license")

    if re.search(r"\b(no license|do not have a license|don t have a license|never had (a )?license)\b", text):
        facts.has_out_of_state_license = False
        facts.has_texas_license = False
        matches.append("no current license")


def _parse_validity(text: str, facts: FactState, matches: list[str]) -> None:
    has_out_of_state_context = re.search(
        r"\b(out[- ]of[- ]state|oklahoma|california|florida|new mexico|louisiana|arkansas)\b", text
    )
    is_texas_renewal_context = re.search(r"\b(renew|renewal|texas license|tx license|texas driver license)\b", text)
    if is_texas_renewal_context and not has_out_of_state_context:
        return

    if re.search(r"\b(valid|current|active|good standing)\b", text):
        facts.out_of_state_license_valid = True
        matches.append("license valid")

    if re.search(r"\b(unexpired|not expired|has not expired|isn t expired|is not expired)\b", text):
        facts.out_of_state_license_unexpired = True
        matches.append("license unexpired")

    if re.search(r"\b(invalid|not valid)\b", text):
        facts.out_of_state_license_valid = False
        matches.append("license invalid")

    years_ago = re.search(r"\bexpired (?:about |over |more than |almost )?(\d+)\s+years? ago\b", text)
    if has_out_of_state_context and years_ago:
        years = int(years_ago.group(1))
        facts.out_of_state_license_unexpired = False
        if years <= 2:
            facts.out_of_state_license_expired_not_over_two_years = True
            matches.append("out-of-state license expired not over two years")
        else:
            facts.out_of_state_license_expired_over_two_years = True
            matches.append("out-of-state license expired over two years")
        return

    if re.search(r"\b(expired|past expiration)\b", text) and not re.search(r"\b(not expired|unexpired|has not expired)\b", text):
        facts.out_of_state_license_unexpired = False
        matches.append("license expired")


def _parse_renewal_timing(text: str, facts: FactState, matches: list[str]) -> None:
    if not re.search(r"\b(renew|renewal|expir(?:e|es|ing|ed))\b", text):
        return

    if re.search(r"\b(expiring soon|expires soon|expires next month|expires this month|expires today)\b", text):
        facts.renewal_timing = "within_window"
        matches.append("renewal inside two-year window")
        return

    years_future = re.search(r"\bexpires in (\d+)\s+years?\b", text)
    if years_future:
        years = int(years_future.group(1))
        facts.renewal_timing = "within_window" if years <= 2 else "outside_window"
        matches.append(f"expires in {years} year(s)")
        return

    months_future = re.search(r"\bexpires in (\d+)\s+months?\b", text)
    if months_future:
        facts.renewal_timing = "within_window"
        matches.append(f"expires in {months_future.group(1)} month(s)")
        return

    years_ago = re.search(r"\bexpired (?:about |over |more than |almost )?(\d+)\s+years? ago\b", text)
    if years_ago:
        years = int(years_ago.group(1))
        facts.renewal_timing = "within_window" if years <= 2 else "outside_window"
        matches.append(f"expired {years} year(s) ago")
        return

    if re.search(r"\b(expired last year|expired one year ago|expired 1 year ago|expired recently)\b", text):
        facts.renewal_timing = "within_window"
        matches.append("expired within two years")
        return

    if re.search(r"\b(expired over two years|expired more than two years|expired 3 years|expired three years)\b", text):
        facts.renewal_timing = "outside_window"
        matches.append("expired outside two-year window")
        return

    if re.search(r"\b(expired)\b", text):
        facts.renewal_timing = "unknown_expired"
        matches.append("expired, timing unknown")


def _parse_replacement_changes(text: str, facts: FactState, matches: list[str]) -> None:
    if re.search(r"\b(lost|stolen|damaged|destroyed|misplaced)\b", text):
        facts.license_lost_stolen_damaged = True
        matches.append("license lost/stolen/damaged")

    if re.search(r"\b(stolen).{0,40}\b(fraud|fraudulent|identity theft|used by someone)\b", text):
        facts.license_stolen_and_fraud_used = True
        matches.append("stolen license used fraudulently")

    if re.search(r"\b(changed my name|name changed|new name|change my name|change name)\b", text):
        facts.name_change_requested = True
        facts.front_card_changed = True
        matches.append("name change requested")

    if re.search(r"\b(changed my address|address changed|new address|change my address|change address|moved addresses)\b", text):
        facts.address_change_requested = True
        facts.front_card_changed = True
        matches.append("address change requested")

    if re.search(r"\b(changed my name|name changed|new name|changed my address|address changed|new address)\b", text):
        facts.front_card_changed = True
        matches.append("front-of-card information changed")

    if re.search(r"\b(no changes|nothing changed|same address|same name|no information changes|info has not changed)\b", text):
        facts.front_card_changed = False
        matches.append("no front-of-card changes")


def _parse_documents(text: str, facts: FactState, matches: list[str]) -> None:
    if re.search(r"\b(passport|birth certificate|identity document|id document|proof of identity)\b", text):
        facts.has_identity_doc = True
        matches.append("identity document mentioned")

    if re.search(r"\b(social security|ssn|social security card)\b", text):
        facts.has_social_security = True
        matches.append("Social Security mentioned")

    if re.search(
        r"\b(no|not any|none|do not have|don t have|dont have|have no)\b.{0,45}\b(residency|proofs? of residency|address documents?)\b",
        text,
    ):
        facts.has_texas_residency_docs = False
        facts.texas_residency_doc_count = 0
        matches.append("no Texas residency documents")
    elif re.search(
        r"\b(only|just)?\s*(one|1|single)\b.{0,45}\b(residency|proof of residency|address document|utility bill|lease|mortgage|bank statement)\b",
        text,
    ) or re.search(
        r"\b(utility bill|lease|mortgage|bank statement)\b.{0,45}\b(only|just)?\s*(one|1|single)\b",
        text,
    ):
        facts.has_texas_residency_docs = False
        facts.texas_residency_doc_count = 1
        matches.append("one Texas residency document")
    elif re.search(r"\b(two|2|both)\b.{0,45}\b(proofs? of residency|residency documents?|address documents?)\b", text):
        facts.has_texas_residency_docs = True
        facts.texas_residency_doc_count = 2
        matches.append("two Texas residency documents")
    elif re.search(r"\b(proofs? of residency|residency documents)\b", text):
        facts.has_texas_residency_docs = True
        matches.append("Texas residency documents mentioned")
    else:
        residency_option_hits = sum(
            1
            for pattern in (
                r"\butility bill\b",
                r"\blease\b",
                r"\bmortgage\b",
                r"\bbank statement\b",
                r"\bvoter registration\b",
                r"\bvehicle registration\b",
                r"\binsurance policy\b",
                r"\bgovernment mail\b",
                r"\bschool records?\b",
            )
            if re.search(pattern, text)
        )
        if residency_option_hits:
            facts.texas_residency_doc_count = residency_option_hits
            facts.has_texas_residency_docs = residency_option_hits >= 2
            matches.append(f"{residency_option_hits} Texas residency document(s)")

    if re.search(r"\b(citizen|lawful presence|permanent resident|green card|visa)\b", text):
        facts.lawful_presence_category_known = True
        matches.append("lawful presence category mentioned")

    if re.search(r"\b(adult driver education|driver education|drivers ed|driver ed)\b.{0,45}\b(completed|done|finished)\b", text):
        facts.adult_driver_education_status = "completed"
        matches.append("adult driver education completed")
    elif re.search(
        r"\b(adult driver education|driver education|drivers ed|driver ed)\b.{0,45}\b(in progress|started|working on)\b",
        text,
    ):
        facts.adult_driver_education_status = "in_progress"
        matches.append("adult driver education in progress")
    elif re.search(
        r"\b(no|not completed|haven t completed|have not completed)\b.{0,45}\b(adult driver education|driver education|drivers ed|driver ed)\b",
        text,
    ):
        facts.adult_driver_education_status = "not_completed"
        matches.append("adult driver education not completed")

    if re.search(r"\b(lawful presence).{0,35}\b(on file|on record|already provided|previously provided)\b", text):
        facts.lawful_presence_on_record = True
        matches.append("lawful presence on record")

    if re.search(r"\b(no vehicle|do not own a vehicle|don t own a vehicle|no car)\b", text):
        facts.owns_vehicle = False
        matches.append("no vehicle owned")
    elif re.search(r"\b(own|owns|owned|have|has)\b.{0,25}\b(vehicle|car|truck)\b", text):
        facts.owns_vehicle = True
        matches.append("owns vehicle")

    if re.search(r"\b(proof of insurance|insurance)\b", text):
        facts.has_proof_of_insurance = True
        matches.append("proof of insurance mentioned")

    if re.search(r"\b(texas registration|vehicle registration|registered in texas)\b", text):
        facts.has_texas_vehicle_registration = True
        matches.append("Texas vehicle registration mentioned")

    if re.search(r"\b(card number|driver license number|dl number|license number)\b", text):
        facts.has_card_number = True
        matches.append("card number available")

    if re.search(r"\b(date of birth|dob|birth date)\b", text):
        facts.has_date_of_birth_for_online = True
        matches.append("date of birth available")

    if re.search(r"\b(last ?4|last four).{0,25}\b(ssn|social security)\b", text):
        facts.has_last4_ssn = True
        matches.append("last four SSN available")

    if re.search(r"\b(audit number|audit)\b", text):
        facts.has_audit_number = True
        matches.append("audit number available")

    if re.search(r"\b(not a us citizen|not a u s citizen|not a citizen|noncitizen)\b", text):
        facts.us_citizen = False
        matches.append("not U.S. citizen")
    elif re.search(r"\b(us citizen|u s citizen|united states citizen|i am a citizen)\b", text):
        facts.us_citizen = True
        facts.lawful_presence_category_known = True
        matches.append("U.S. citizen")
    elif re.search(r"\b(green card|permanent resident|lawful permanent resident|i-551|i 551)\b", text):
        facts.us_citizen = False
        facts.lawful_presence_category_known = True
        matches.append("lawful permanent resident")

    if re.search(r"\b(ssn|social security).{0,35}\b(not on file|not on record|not provided)\b", text):
        facts.ssn_on_record = False
        matches.append("SSN not on record")
    elif re.search(r"\b(ssn|social security).{0,35}\b(on file|on record|already provided)\b", text):
        facts.ssn_on_record = True
        matches.append("SSN on record")

    if re.search(r"\b(last renewed|renewed last time|previous renewal).{0,35}\bin person\b", text):
        facts.last_renewed_in_person = True
        matches.append("last renewed in person")

    if re.search(r"\b(last renewed|renewed last time|previous renewal).{0,35}\b(online|mail|by mail)\b", text):
        facts.last_renewed_in_person = False
        matches.append("last renewal not in person")

    if re.search(r"\b(suspended|revoked|invalid)\b.{0,25}\b(texas license|tx license|license)\b", text) or re.search(
        r"\b(texas license|tx license|license)\b.{0,25}\b(suspended|revoked|invalid)\b", text
    ):
        facts.license_valid_status = False
        matches.append("license invalid status")
    elif re.search(r"\b(valid|current|active)\b.{0,25}\b(texas license|tx license|license)\b", text) or re.search(
        r"\b(texas license|tx license|license)\b.{0,25}\b(valid|current|active|good standing)\b", text
    ):
        facts.license_valid_status = True
        matches.append("license valid status")

    if re.search(r"\b(no outstanding|no unpaid|no open)\b.{0,45}\b(tickets|warrants|citations)\b", text):
        facts.no_outstanding_tickets_or_warrants = True
        matches.append("no outstanding tickets or warrants")
    elif re.search(r"\b(outstanding|unpaid|open)\b.{0,45}\b(tickets|warrants|citations)\b", text):
        facts.no_outstanding_tickets_or_warrants = False
        matches.append("outstanding tickets or warrants")

    if re.search(r"\b(health|medical).{0,35}\b(changed|new condition|worse)\b", text):
        facts.health_conditions_unchanged = False
        matches.append("health conditions changed")
    elif re.search(r"\b(health|medical).{0,35}\b(unchanged|no change|same)\b", text):
        facts.health_conditions_unchanged = True
        matches.append("health conditions unchanged")


def non_empty_fact_names(facts: FactState) -> set[str]:
    """Return dataclass field names that contain meaningful extracted values."""

    names: set[str] = set()
    for field_info in fields(facts):
        value = getattr(facts, field_info.name)
        if value not in (None, [], {}):
            names.add(field_info.name)
    return names
