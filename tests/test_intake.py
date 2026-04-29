from backend.intake import apply_document_selections, facts_from_intake, scenario_from_facts, steps_for
from backend.models import DocumentSelections, FactState


def test_transfer_intake_maps_grouped_answers_to_facts():
    facts = facts_from_intake(
        "transfer",
        {
            "age": 22,
            "new_texas_resident": "Yes",
            "has_out_of_state_license": "Yes",
            "out_of_state_license_valid": "Yes",
            "out_of_state_license_unexpired": "Yes",
            "has_texas_residency_docs": "Not sure",
            "owns_vehicle": "No",
            "has_proof_of_insurance": "Not sure",
            "has_texas_vehicle_registration": "Not sure",
        },
    )

    assert facts.goal == "transfer"
    assert facts.age == 22
    assert facts.new_texas_resident is True
    assert facts.has_out_of_state_license is True
    assert facts.out_of_state_license_valid is True
    assert facts.out_of_state_license_unexpired is True
    assert facts.has_texas_residency_docs is None
    assert facts.owns_vehicle is False


def test_change_info_intake_uses_replacement_rule_path():
    facts = facts_from_intake(
        "change_info",
        {
            "change_kind": "Address and name",
            "has_texas_license": "Yes",
            "has_card_number": "No",
            "has_date_of_birth_for_online": "Yes",
            "has_last4_ssn": "Yes",
            "has_audit_number": "Not sure",
        },
    )

    assert facts.goal == "replacement"
    assert facts.front_card_changed is True
    assert facts.address_change_requested is True
    assert facts.name_change_requested is True
    assert facts.has_card_number is False


def test_replacement_flow_collects_documents_needed_by_in_person_report():
    document_steps = [step for step in steps_for("replacement") if step.document_categories]

    assert document_steps
    assert document_steps[0].document_categories == ("identity", "social_security", "lawful_presence")


def test_replacement_document_selections_mark_report_docs_confirmed():
    facts = facts_from_intake(
        "replacement",
        {
            "replacement_reason": "Lost",
            "license_stolen_and_fraud_used": "No",
            "front_card_changed": "Yes",
            "has_card_number": "Yes",
            "has_date_of_birth_for_online": "Yes",
            "has_last4_ssn": "Yes",
            "has_audit_number": "Yes",
        },
    )
    docs = DocumentSelections(
        selected={
            "identity": ["us_passport"],
            "social_security": ["ssn_card"],
        },
        lawful_presence_choice="us_citizen",
    )

    facts = apply_document_selections(facts, docs)

    assert facts.has_identity_doc is True
    assert facts.has_social_security is True
    assert facts.lawful_presence_category_known is True


def test_renewal_lawful_presence_status_accepts_green_card_holder():
    facts = facts_from_intake(
        "renewal",
        {
            "has_texas_license": "Yes",
            "renewal_timing": "Expires within two years",
            "age": 35,
            "last_renewed_in_person": "Yes",
            "license_valid_status": "Yes",
            "renewal_lawful_presence_status": "Lawful permanent resident / green card holder",
            "ssn_on_record": "Yes",
            "health_conditions_unchanged": "Yes",
            "no_outstanding_tickets_or_warrants": "Yes",
        },
    )

    assert facts.us_citizen is False
    assert facts.lawful_presence_category_known is True


def test_scenario_detection_from_facts():
    assert scenario_from_facts(FactState(goal="first_time")) == "first_time"
    assert scenario_from_facts(FactState(license_lost_stolen_damaged=True)) == "replacement"
