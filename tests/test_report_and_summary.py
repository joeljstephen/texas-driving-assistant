from backend.followup import build_deterministic_answer
from backend.followup_state import reconcile_followup_documents, should_apply_followup_facts
from backend.gemini_summary import GeminiSummaryConfig, build_deterministic_summary, generate_summary
from backend.intake import apply_document_selections
from backend.models import DocumentSelections, FactState, PolicyResult
from backend.parser import parse_message
from backend.report_composer import compose_report


def make_first_time_facts():
    return FactState(
        goal="first_time",
        age=24,
        applying_texas_license=True,
        has_out_of_state_license=False,
        has_texas_license=False,
        has_identity_doc=True,
        has_social_security=True,
        has_texas_residency_docs=True,
        lawful_presence_category_known=True,
        us_citizen=True,
        owns_vehicle=False,
        adult_driver_education_status="completed",
    )


def make_first_time_result():
    return PolicyResult(
        case_type="first_time_application",
        service_modes=["in_person"],
        required_docs=[
            "application_form",
            "identity",
            "citizenship_or_lawful_presence",
            "social_security_number",
            "texas_residency_two_documents",
            "statement_no_vehicle_owned",
            "adult_driver_education_certificate",
            "impact_texas_drivers_certificate_within_90_days",
        ],
        likely_exams=["vision_exam", "knowledge_exam", "skills_exam"],
        explanations=[
            "first_time_application_requires_in_person_processing",
            "first_time_application_requires_tests",
        ],
        final_guidance=[
            "first_time_application_in_person_with_docs_and_tests",
            "verify_with_official_texas_dps_and_texas_gov_sources",
        ],
        missing_info=[],
    )


def test_compose_report_marks_documents_confirmed_when_facts_match():
    facts = make_first_time_facts()
    result = make_first_time_result()
    docs = DocumentSelections(
        selected={
            "identity": ["us_passport"],
            "social_security": ["ssn_card"],
            "residency": ["texas_lease_or_mortgage", "texas_utility_bill"],
        },
        lawful_presence_choice="us_citizen",
    )

    report = compose_report(facts, result, docs)

    documents = next(section for section in report.sections if section.key == "documents")
    statuses = {item.label: item.status for item in documents.items}
    assert any("identity" in label.lower() for label in statuses)
    assert all(status in {"confirmed", "todo"} for status in statuses.values())
    assert any(status == "confirmed" for status in statuses.values())
    assert "First-time adult Texas driver license application" in report.case_title
    assert any("you said you are applying" in line.lower() for line in report.why_lines)
    assert report.next_steps  # final guidance is rendered


def test_compose_report_lists_missing_when_documents_absent():
    facts = make_first_time_facts()
    facts.has_identity_doc = None
    facts.has_social_security = None
    result = make_first_time_result()
    result = PolicyResult(**{**result.__dict__, "missing_info": ["identity_documents", "social_security"]})
    docs = DocumentSelections()

    report = compose_report(facts, result, docs)

    assert "proof of identity" in " ".join(report.missing_items).lower()
    assert any("identity" in line.lower() for line in report.why_lines)


def test_underage_report_stops_adult_guidance_strongly():
    facts = FactState(goal="first_time", age=9, applying_texas_license=True)
    result = PolicyResult(
        case_type="out_of_scope_under_18",
        service_modes=["not_available_adult_flow"],
        explanations=["under_18_out_of_scope"],
        final_guidance=["under_15_no_ordinary_driver_license_path", "under_18_adult_license_not_available"],
    )

    report = compose_report(facts, result, DocumentSelections())

    assert "Do not use this adult driver-license" in report.case_outcome
    assert report.sections[0].key == "underage_scope"
    assert not any(section.key == "documents" for section in report.sections)
    assert any("Do not use the adult" in step for step in report.next_steps)


def test_deterministic_summary_grounded_in_report_data():
    facts = make_first_time_facts()
    result = make_first_time_result()
    docs = DocumentSelections(lawful_presence_choice="us_citizen")
    report = compose_report(facts, result, docs)

    summary = build_deterministic_summary(facts, result, report)

    assert "First-time adult Texas driver license application" in summary
    assert "in person" in summary.lower() or "In person" in summary


def test_generate_summary_falls_back_when_gemini_disabled():
    facts = make_first_time_facts()
    result = make_first_time_result()
    docs = DocumentSelections()
    report = compose_report(facts, result, docs)

    summary = generate_summary(
        facts,
        result,
        docs,
        report,
        GeminiSummaryConfig(enabled=False),
    )

    assert summary  # never empty
    assert "First-time adult Texas driver license application" in summary


def test_generate_summary_uses_gemini_when_client_succeeds():
    facts = make_first_time_facts()
    result = make_first_time_result()
    docs = DocumentSelections()
    report = compose_report(facts, result, docs)

    class FakeResponse:
        text = "You're starting your first Texas driver license application."

    class FakeModels:
        def generate_content(self, **kwargs):
            assert "model" in kwargs
            return FakeResponse()

    class FakeClient:
        models = FakeModels()

    summary = generate_summary(
        facts,
        result,
        docs,
        report,
        GeminiSummaryConfig(enabled=True, api_key="x", model="gemini-test"),
        client=FakeClient(),
    )

    assert "first Texas driver license" in summary


def test_followup_topic_routing_returns_grounded_text():
    facts = make_first_time_facts()
    result = make_first_time_result()
    docs = DocumentSelections(selected={"identity": ["us_passport"]})
    report = compose_report(facts, result, docs)

    answer = build_deterministic_answer("What counts as proof of identity?", facts, result, docs, report)
    assert "primary" in answer.lower() or "passport" in answer.lower()

    vehicle = build_deterministic_answer("What if I don't own a car?", facts, result, docs, report)
    assert "no-vehicle" in vehicle.lower() or "vehicle" in vehicle.lower()


def test_followup_without_result_asks_user_to_run_intake():
    facts = FactState()
    docs = DocumentSelections()
    answer = build_deterministic_answer("What counts as proof of identity?", facts, None, docs, None)
    assert "guided intake" in answer.lower() or "rule engine" in answer.lower()


def test_followup_document_update_clears_unsure_before_reapplying_documents():
    facts = FactState(goal="first_time", has_identity_doc=None)
    docs = DocumentSelections(unsure={"identity": True})
    parsed = parse_message("I have a passport now.")

    docs = reconcile_followup_documents("I have a passport now.", parsed.facts, docs)
    facts.has_identity_doc = parsed.facts.has_identity_doc
    facts = apply_document_selections(facts, docs)

    assert facts.has_identity_doc is True
    assert docs.unsure["identity"] is False
    assert "us_passport" in docs.selected["identity"]


def test_followup_one_residency_document_remains_incomplete():
    facts = FactState(goal="first_time", has_texas_residency_docs=False)
    docs = DocumentSelections(none={"residency": True})
    parsed = parse_message("Actually, I have only one Texas residency document, a utility bill.")

    docs = reconcile_followup_documents("Actually, I have only one Texas residency document, a utility bill.", parsed.facts, docs)
    facts.texas_residency_doc_count = parsed.facts.texas_residency_doc_count
    facts.has_texas_residency_docs = parsed.facts.has_texas_residency_docs
    facts = apply_document_selections(facts, docs)

    assert docs.none["residency"] is False
    assert "texas_utility_bill" in docs.selected["residency"]
    assert facts.texas_residency_doc_count == 1
    assert facts.has_texas_residency_docs is False


def test_followup_lawful_presence_update_replaces_not_sure_choice():
    facts = FactState(goal="first_time", lawful_presence_category_known=None, us_citizen=None)
    docs = DocumentSelections(lawful_presence_choice="not_sure")
    parsed = parse_message("I am a U.S. citizen.")

    docs = reconcile_followup_documents("I am a U.S. citizen.", parsed.facts, docs)
    facts.lawful_presence_category_known = parsed.facts.lawful_presence_category_known
    facts.us_citizen = parsed.facts.us_citizen
    facts = apply_document_selections(facts, docs)

    assert facts.us_citizen is True
    assert facts.lawful_presence_category_known is True
    assert docs.lawful_presence_choice == "us_citizen"


def test_followup_question_about_documents_does_not_mutate_state():
    parsed = parse_message("What counts as proof of identity?")

    assert parsed.facts.has_identity_doc is True
    assert should_apply_followup_facts("What counts as proof of identity?", parsed) is False


def test_followup_statement_about_documents_mutates_state():
    parsed = parse_message("I have a passport now.")

    assert should_apply_followup_facts("I have a passport now.", parsed) is True
