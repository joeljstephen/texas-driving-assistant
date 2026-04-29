from backend.parser import parse_message, parse_message_with_context
from backend.state_manager import merge_facts
from backend.models import FactState


def test_parser_transfer_valid_unexpired_age():
    result = parse_message("I am 22 and moved to Texas from Oklahoma with a valid unexpired license.")

    assert result.facts.goal == "transfer"
    assert result.facts.age == 22
    assert result.facts.new_texas_resident is True
    assert result.facts.has_out_of_state_license is True
    assert result.facts.out_of_state_license_valid is True
    assert result.facts.out_of_state_license_unexpired is True


def test_parser_first_time_no_license():
    result = parse_message("I am 20 and applying for my first time license. I have no license now.")

    assert result.facts.goal == "first_time"
    assert result.facts.age == 20
    assert result.facts.applying_texas_license is True
    assert result.facts.has_out_of_state_license is False


def test_parser_first_texas_driver_license_does_not_mean_current_texas_license():
    result = parse_message("I am applying for my first texas driver license")

    assert result.facts.goal == "first_time"
    assert result.facts.applying_texas_license is True
    assert result.facts.has_texas_license is None


def test_parser_replacement_front_card_changes():
    result = parse_message("I lost my Texas license and changed my address.")

    assert result.facts.goal == "replacement"
    assert result.facts.has_texas_license is True
    assert result.facts.front_card_changed is True


def test_parser_renewal_outside_window():
    result = parse_message("I need to renew my Texas license but it expired 3 years ago.")

    assert result.facts.goal == "renewal"
    assert result.facts.renewal_timing == "outside_window"
    assert result.facts.out_of_state_license_unexpired is None


def test_parser_online_renewal_supporting_facts():
    result = parse_message(
        "I want to renew my Texas license. It expires soon. I am 35. I last renewed in person. "
        "My health is unchanged. My Texas license is valid. No outstanding tickets or warrants. "
        "I am a US citizen. My SSN is on record."
    )

    assert result.facts.renewal_timing == "within_window"
    assert result.facts.last_renewed_in_person is True
    assert result.facts.health_conditions_unchanged is True
    assert result.facts.license_valid_status is True
    assert result.facts.no_outstanding_tickets_or_warrants is True
    assert result.facts.us_citizen is True
    assert result.facts.ssn_on_record is True


def test_contextual_bare_number_answers_age_question():
    result = parse_message_with_context("24", next_question="ask_age")

    assert result.facts.age == 24


def test_contextual_yes_answers_residency_documents_question():
    result = parse_message_with_context("Yes", next_question="ask_residency_documents")

    assert result.facts.has_texas_residency_docs is True


def test_one_residency_document_is_partial_not_complete():
    result = parse_message("I only have one Texas residency document, a utility bill.")

    assert result.facts.texas_residency_doc_count == 1
    assert result.facts.has_texas_residency_docs is False


def test_merge_facts_latest_explicit_values_win():
    current = FactState(goal="replacement", front_card_changed=True)
    incoming = parse_message("No changes, same name and same address.").facts

    merged = merge_facts(current, incoming)

    assert merged.front_card_changed is False
