import json

from backend.gemini_parser import GeminiParserConfig, parse_with_gemini_or_fallback, validate_gemini_payload
from backend.models import AssistantSession, FactState, ParseResult
from backend.state_manager import apply_user_turn


BASE_PAYLOAD = {
    "goal": None,
    "age": None,
    "new_resident": None,
    "has_out_of_state_license": None,
    "out_of_state_license_valid": None,
    "out_of_state_license_unexpired": None,
    "out_of_state_license_expired_not_over_two_years": None,
    "out_of_state_license_expired_over_two_years": None,
    "current_texas_license": None,
    "renewal_requested": None,
    "replacement_requested": None,
    "first_time_applicant": None,
    "license_expired": None,
    "expiration_timing": None,
    "front_of_card_changed": None,
    "name_change_requested": None,
    "address_change_requested": None,
    "license_lost_stolen_damaged": None,
    "license_stolen_and_fraud_used": None,
    "has_identity_doc": None,
    "has_social_security": None,
    "has_texas_residency_docs": None,
    "texas_residency_doc_count": None,
    "lawful_presence_category_known": None,
    "lawful_presence_on_record": None,
    "adult_driver_education_status": None,
    "owns_vehicle": None,
    "has_proof_of_insurance": None,
    "has_texas_vehicle_registration": None,
    "has_card_number": None,
    "has_date_of_birth_for_online": None,
    "has_last4_ssn": None,
    "has_audit_number": None,
    "us_citizen": None,
    "ssn_on_record": None,
    "last_renewed_in_person": None,
    "license_valid_status": None,
    "no_outstanding_tickets_or_warrants": None,
    "health_conditions_unchanged": None,
    "correction": False,
}


def payload(**updates):
    data = BASE_PAYLOAD.copy()
    data.update(updates)
    return data


def test_validate_gemini_payload_maps_transfer_facts():
    result = validate_gemini_payload(
        payload(
            goal="transfer",
            age=22,
            new_resident=True,
            has_out_of_state_license=True,
            out_of_state_license_valid=True,
            out_of_state_license_unexpired=True,
        )
    )

    assert result.source == "gemini"
    assert result.facts.goal == "transfer"
    assert result.facts.age == 22
    assert result.facts.new_texas_resident is True
    assert result.facts.has_out_of_state_license is True
    assert result.facts.out_of_state_license_valid is True
    assert result.facts.out_of_state_license_unexpired is True


def test_validate_gemini_payload_rejects_unexpected_fields():
    invalid = payload(goal="renewal")
    invalid["service_mode"] = "online"

    try:
        validate_gemini_payload(invalid)
    except ValueError as exc:
        assert "Unexpected Gemini fields" in str(exc)
    else:
        raise AssertionError("Expected validation failure")


def test_gemini_unavailable_falls_back_to_deterministic_parser():
    result = parse_with_gemini_or_fallback(
        "I am 20 and applying for my first time Texas license. I have no license.",
        GeminiParserConfig(enabled=True, api_key=None, model="gemini-test"),
    )

    assert result.source == "fallback"
    assert "GEMINI_API_KEY" in result.error
    assert result.facts.goal == "first_time"
    assert result.facts.age == 20


def test_gemini_client_can_be_mocked_for_successful_parse():
    class FakeResponse:
        text = json.dumps(payload(goal="replacement", current_texas_license=True, front_of_card_changed=False))

    class FakeModels:
        def generate_content(self, **kwargs):
            assert kwargs["config"]["response_mime_type"] == "application/json"
            assert "response_json_schema" in kwargs["config"]
            return FakeResponse()

    class FakeClient:
        models = FakeModels()

    result = parse_with_gemini_or_fallback(
        "I lost my Texas license. No changes.",
        GeminiParserConfig(enabled=True, api_key="test-key", model="gemini-test"),
        client=FakeClient(),
    )

    assert result.source == "gemini"
    assert result.facts.goal == "replacement"
    assert result.facts.has_texas_license is True
    assert result.facts.front_card_changed is False


def test_gemini_merge_preserves_existing_fact_without_correction():
    session = AssistantSession(facts=FactState(goal="renewal", has_texas_license=True))
    incoming = ParseResult(facts=FactState(goal="replacement", front_card_changed=False), source="gemini")

    apply_user_turn(session, "I lost it", incoming)

    assert session.facts.goal == "renewal"
    assert session.facts.front_card_changed is False


def test_gemini_merge_allows_clear_correction():
    session = AssistantSession(facts=FactState(front_card_changed=True))
    incoming = ParseResult(
        facts=FactState(front_card_changed=False),
        source="gemini",
        correction=True,
    )

    apply_user_turn(session, "Correction: no information changed.", incoming)

    assert session.facts.front_card_changed is False
