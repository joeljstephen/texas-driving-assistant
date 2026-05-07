import shutil

import pytest

from backend.parser import parse_message
from backend.scasp_runner import ScaspRunner


pytestmark = pytest.mark.skipif(shutil.which("scasp") is None, reason="scasp executable is not installed")


def reason(text):
    return ScaspRunner().run(parse_message(text).facts)


def test_age_22_moved_from_oklahoma_valid_unexpired_license():
    result = reason("I am 22, moved to Texas from Oklahoma, and have a valid unexpired out of state license.")

    assert result.case_type == "out_of_state_transfer"
    assert "in_person" in result.service_modes
    assert "texas_residency_two_documents" in result.required_docs
    assert "no_knowledge_or_skills_exam_expected" in result.likely_exams
    assert "residency_30_day_duration_waived" in result.waivers


def test_age_20_first_time_applicant():
    result = reason("I am 20 and applying for my first time Texas license. I have no license.")

    assert result.case_type == "first_time_application"
    assert "in_person" in result.service_modes
    assert "adult_driver_education_certificate" in result.required_docs
    assert "skills_exam" in result.likely_exams
    assert "impact_texas_drivers_before_skills_test" in result.likely_exams


def test_texas_license_expiring_soon_renewal():
    result = reason("I want to renew my Texas license. It expires soon.")

    assert result.case_type == "renewal"
    assert "likely_in_person" in result.service_modes
    assert "ask_age" == result.next_question
    assert "renewal_likely_requires_in_person_if_online_rules_not_met" in result.final_guidance


def test_lost_texas_license_no_information_changes():
    result = reason("I lost my Texas license and need a replacement. No information changes.")

    assert result.case_type == "replacement"
    assert "likely_in_person" in result.service_modes
    assert "ask_card_number_for_online_replacement" == result.next_question


def test_lost_texas_license_name_or_address_change():
    result = reason("I lost my Texas license and changed my address.")

    assert result.case_type == "replacement"
    assert "address_change_is_handled_as_replacement" in result.explanations
    assert "address_must_be_changed_within_30_days_of_moving" in result.final_guidance


def test_renewal_outside_likely_window():
    result = reason("I need to renew my Texas license. It expired 3 years ago.")

    assert result.case_type == "renewal"
    assert "cannot_renew_use_original_application_path" in result.service_modes
    assert "license_expired_more_than_two_years_follow_original_application_guidance" in result.final_guidance


def test_green_card_holder_does_not_satisfy_online_renewal_citizenship_check():
    facts = parse_message(
        "I want to renew my Texas license. It expires soon. I am 35. I last renewed in person. "
        "My health is unchanged. My Texas license is valid. No outstanding tickets or warrants. "
        "I am a green card holder. My SSN is on record."
    ).facts

    result = ScaspRunner().run(facts)

    assert result.case_type == "renewal"
    assert "likely_in_person" in result.service_modes
    assert "may_be_online" not in result.service_modes
    assert "citizenship_for_online_renewal" not in result.missing_info


def test_us_citizen_can_satisfy_online_renewal_citizenship_check():
    facts = parse_message(
        "I want to renew my Texas license. It expires soon. I am 35. I last renewed in person. "
        "My health is unchanged. My Texas license is valid. No outstanding tickets or warrants. "
        "I am a US citizen. My SSN is on record."
    ).facts

    result = ScaspRunner().run(facts)

    assert result.case_type == "renewal"
    assert "may_be_online" in result.service_modes
    assert "citizenship_for_online_renewal" not in result.missing_info


def test_underage_applicant_gets_strong_adult_scope_stop():
    result = reason("I am 9 and applying for my first Texas license.")

    assert result.case_type == "out_of_scope_under_18"
    assert "not_available_adult_flow" in result.service_modes
    assert "under_18_adult_license_not_available" in result.final_guidance
