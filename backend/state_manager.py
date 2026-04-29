"""Session-state helpers for merging newly extracted facts."""

from __future__ import annotations

from dataclasses import fields

from .models import AssistantSession, ChatMessage, FactState, ParseResult


CASE_SPECIFIC_FIELDS = {
    "transfer": {
        "renewal_timing",
        "front_card_changed",
        "name_change_requested",
        "address_change_requested",
        "license_lost_stolen_damaged",
        "license_stolen_and_fraud_used",
        "has_texas_license",
        "last_renewed_in_person",
        "license_valid_status",
        "no_outstanding_tickets_or_warrants",
        "health_conditions_unchanged",
        "ssn_on_record",
        "has_card_number",
        "has_date_of_birth_for_online",
        "has_last4_ssn",
        "has_audit_number",
        "adult_driver_education_status",
    },
    "first_time": {
        "renewal_timing",
        "front_card_changed",
        "name_change_requested",
        "address_change_requested",
        "license_lost_stolen_damaged",
        "license_stolen_and_fraud_used",
        "has_texas_license",
        "last_renewed_in_person",
        "license_valid_status",
        "no_outstanding_tickets_or_warrants",
        "health_conditions_unchanged",
        "ssn_on_record",
        "has_card_number",
        "has_date_of_birth_for_online",
        "has_last4_ssn",
        "has_audit_number",
        "adult_driver_education_status",
    },
    "renewal": {
        "new_texas_resident",
        "has_out_of_state_license",
        "out_of_state_license_valid",
        "out_of_state_license_unexpired",
        "out_of_state_license_expired_not_over_two_years",
        "out_of_state_license_expired_over_two_years",
        "front_card_changed",
        "name_change_requested",
        "address_change_requested",
        "license_lost_stolen_damaged",
        "license_stolen_and_fraud_used",
        "has_card_number",
        "has_date_of_birth_for_online",
        "has_last4_ssn",
        "has_audit_number",
        "adult_driver_education_status",
    },
    "replacement": {
        "new_texas_resident",
        "has_out_of_state_license",
        "out_of_state_license_valid",
        "out_of_state_license_unexpired",
        "out_of_state_license_expired_not_over_two_years",
        "out_of_state_license_expired_over_two_years",
        "renewal_timing",
        "last_renewed_in_person",
        "license_valid_status",
        "no_outstanding_tickets_or_warrants",
        "health_conditions_unchanged",
        "adult_driver_education_status",
    },
}


def merge_facts(current: FactState, incoming: FactState, allow_overwrite: bool = True) -> FactState:
    """Merge new facts into accumulated state, with latest explicit facts winning."""

    if incoming.goal and incoming.goal != current.goal and allow_overwrite:
        _clear_case_specific_fields(current, incoming.goal)

    for field_info in fields(FactState):
        name = field_info.name
        if name == "source_notes":
            continue
        value = getattr(incoming, name)
        current_value = getattr(current, name)
        if value is not None and (allow_overwrite or current_value is None or current_value == value):
            setattr(current, name, value)

    for note in incoming.source_notes:
        if note not in current.source_notes:
            current.source_notes.append(note)

    return current


def apply_user_turn(session: AssistantSession, user_text: str, parse_result: ParseResult) -> AssistantSession:
    """Append a user turn and merge extracted facts."""

    session.messages.append(ChatMessage(role="user", content=user_text))
    allow_overwrite = parse_result.source != "gemini" or parse_result.correction
    session.facts = merge_facts(session.facts, parse_result.facts, allow_overwrite=allow_overwrite)
    session.last_parse_result = parse_result
    return session


def append_assistant_turn(session: AssistantSession, assistant_text: str) -> AssistantSession:
    """Append an assistant response."""

    session.messages.append(ChatMessage(role="assistant", content=assistant_text))
    return session


def reset_session() -> AssistantSession:
    """Create a fresh assistant session."""

    return AssistantSession()


def _clear_case_specific_fields(facts: FactState, new_goal: str) -> None:
    for field_name in CASE_SPECIFIC_FIELDS.get(new_goal, set()):
        setattr(facts, field_name, None)
