"""Convert structured policy results into concise user-facing responses."""

from __future__ import annotations

from .models import FactState, PolicyResult


CASE_LABELS = {
    "out_of_state_transfer": "out-of-state transfer",
    "first_time_application": "first-time adult application",
    "renewal": "Texas license renewal",
    "replacement": "Texas license replacement",
    "out_of_scope_under_18": "outside this assistant's adult-license scope",
}

QUESTION_TEXT = {
    "ask_goal": "What are you trying to do: apply for your first Texas license, transfer an out-of-state license, renew a Texas license, or replace a lost/stolen/damaged Texas license?",
    "ask_out_of_state_license_presence": "Do you currently have an out-of-state driver license?",
    "ask_out_of_state_license": "Do you currently have an out-of-state driver license?",
    "ask_out_of_state_validity": "Is your out-of-state driver license valid and unexpired?",
    "ask_out_of_state_expiration": "Is your out-of-state driver license unexpired, or has it expired?",
    "ask_if_out_of_state_expired_more_than_two_years": "If your out-of-state license expired, did it expire more than two years ago?",
    "ask_age": "How old are you?",
    "ask_renewal_timing": "When does your Texas license expire, or how long ago did it expire?",
    "ask_last_renewal_method": "Was your last Texas license renewal completed in person?",
    "ask_health_change": "Have your health or medical conditions changed since your last renewal?",
    "ask_license_status": "Is your current Texas license valid and in good standing?",
    "ask_outstanding_tickets_or_warrants": "Do you have any outstanding tickets, citations, or warrants?",
    "ask_citizenship_for_online_renewal": "Are you a U.S. citizen?",
    "ask_lawful_presence_for_online_renewal": "Are you a U.S. citizen?",
    "ask_ssn_on_record": "Is your Social Security number already on record?",
    "ask_front_card_changed": "Does any information printed on the front of your license need to change, such as your name or address?",
    "ask_card_number_for_online_replacement": "Do you have your Texas driver license or card number?",
    "ask_date_of_birth_for_online_replacement": "Can you provide your date of birth for online replacement eligibility?",
    "ask_last4_ssn_for_online_replacement": "Do you have the last four digits of your Social Security number?",
    "ask_audit_number_for_online_replacement": "Do you have the audit number from your most recent Texas card?",
    "ask_residency_documents": "Do you have documents that can show Texas residency, such as two acceptable proofs of residency?",
    "ask_identity_documents": "Do you have proof of identity?",
    "ask_social_security": "Do you have Social Security proof or a Social Security number available?",
    "ask_lawful_presence_category": "Do you know your citizenship or lawful-presence document category?",
}

MISSING_LABELS = {
    "goal": "case type",
    "out_of_state_license_presence": "out-of-state license presence",
    "out_of_state_license_validity": "out-of-state license validity",
    "out_of_state_license_expiration": "out-of-state license expiration",
    "out_of_state_two_year_expiration_detail": "whether the out-of-state license expired more than two years ago",
    "age": "age",
    "renewal_timing": "renewal timing",
    "last_renewal_method": "last renewal method",
    "health_change": "health or medical condition changes",
    "license_status": "license status",
    "outstanding_tickets_or_warrants": "outstanding tickets, warrants, or license issues",
    "citizenship_for_online_renewal": "U.S. citizenship for online renewal",
    "lawful_presence_for_online_renewal": "U.S. citizenship for online renewal",
    "ssn_on_record": "SSN on record",
    "front_card_changed": "front-of-card information change",
    "card_number_for_online_replacement": "card number",
    "date_of_birth_for_online_replacement": "date of birth",
    "last4_ssn_for_online_replacement": "last four SSN digits",
    "audit_number_for_online_replacement": "audit number",
    "residency_documents": "two Texas residency documents",
    "identity_documents": "proof of identity",
    "social_security": "Social Security proof",
    "lawful_presence_category": "citizenship or lawful-presence category",
}

SERVICE_LABELS = {
    "in_person": "likely in-person office path",
    "may_be_online": "online service may be possible for eligible users",
    "non_online_or_in_person": "likely non-online or in-person path",
    "likely_in_person_or_new_application": "likely in-person review or a new application-style path",
    "likely_in_person": "likely in-person path",
    "cannot_renew_use_original_application_path": "cannot renew through the ordinary renewal path; use an original-application-style path",
    "online_mail_or_in_person": "online, mail, or in-person service may be available depending on eligibility",
    "not_available_adult_flow": "not available through this adult driver-license flow",
}

DOC_LABELS = {
    "identity": "identity",
    "application_form": "application form",
    "lawful_presence_category": "lawful presence category, if applicable",
    "citizenship_or_lawful_presence": "citizenship or lawful presence",
    "social_security": "Social Security",
    "social_security_number": "Social Security number",
    "texas_residency_two_documents": "two Texas residency documents",
    "proof_of_insurance_for_each_owned_vehicle": "proof of insurance for each vehicle owned",
    "texas_vehicle_registration_for_each_owned_vehicle": "Texas vehicle registration for each vehicle owned",
    "statement_no_vehicle_owned": "statement that no vehicle is owned",
    "out_of_state_license_to_surrender": "the out-of-state license, which is typically surrendered",
    "adult_driver_education_certificate": "adult driver education completion proof",
    "impact_texas_drivers_certificate_within_90_days": "Impact Texas Drivers certificate within 90 days of a skills test",
    "identity_verification": "identity verification",
    "current_texas_license": "current Texas license information",
    "most_recent_texas_license_and_audit_number": "most recent Texas license and audit number",
    "renewal_application_form": "renewal application form",
    "citizenship_or_lawful_presence_if_not_on_record": "citizenship or lawful-presence proof if not already on record",
    "replacement_application_form": "replacement application form",
    "identity_one_primary_secondary_or_supporting_doc": "one acceptable identity document",
    "citizenship_or_lawful_presence_if_not_previously_provided": "citizenship or lawful-presence proof if not previously provided",
    "social_security_if_not_previously_provided": "Social Security proof if not previously provided",
    "card_number_date_of_birth_last4_ssn_audit_number": "card number, date of birth, last four SSN digits, and audit number",
}

EXAM_LABELS = {
    "vision_exam": "vision exam or screening",
    "knowledge_exam": "knowledge exam",
    "skills_exam": "skills/drive test",
    "impact_texas_drivers_before_skills": "Impact Texas Drivers before the drive test, if a skills test is needed",
    "impact_texas_drivers_before_skills_test": "Impact Texas Drivers before the skills test, if a skills test is needed",
    "no_knowledge_or_skills_exam_expected": "knowledge and skills exams are generally not expected for a valid, unexpired out-of-state transfer",
}

WAIVER_LABELS = {
    "residency_30_day_duration_waived": "30-day Texas residency duration rule is waived for the valid, unexpired out-of-state transfer path",
    "knowledge_exam_waived": "knowledge exam is generally waived",
    "skills_exam_waived": "skills exam is generally waived",
    "adult_driver_education_waived": "adult driver education is generally waived for this transfer credential path",
    "impact_texas_drivers_waived": "Impact Texas Drivers is generally waived for this transfer credential path",
}

EXPLANATION_LABELS = {
    "new_resident_valid_out_of_state": "you said you moved to Texas and have a valid, unexpired out-of-state license",
    "new_resident_with_out_of_state_license": "you described a new Texas resident with an out-of-state license",
    "valid_or_recent_out_of_state_license_exam_waiver": "a valid or recently expired out-of-state license can support exam waivers",
    "transfer_requires_in_person": "first-time Texas applications and out-of-state transfers are handled as in-person application flows",
    "transfer_requires_in_person_processing": "out-of-state transfers require in-person processing",
    "valid_unexpired_out_of_state_residency_30_day_waiver": "a valid unexpired out-of-state license supports the 30-day residency-duration waiver",
    "first_time_without_transfer": "you are applying without a qualifying valid out-of-state transfer case",
    "first_time_application_requires_in_person_processing": "first-time applications require in-person processing",
    "first_time_application_requires_tests": "first-time applications usually involve testing requirements",
    "age_18_24_adult_driver_education": "Texas adult first-time applicants age 18 through 24 need adult driver education",
    "age_18_to_24_requires_adult_driver_education": "Texas adult first-time applicants age 18 through 24 need adult driver education",
    "renewal_window_two_years": "Texas licenses can generally be renewed up to two years before or after expiration",
    "renewal_window_is_two_years_before_or_after_expiration": "Texas licenses can generally be renewed up to two years before or after expiration",
    "renewal_expired_more_than_two_years_cannot_be_renewed": "a license expired more than two years is not handled as an ordinary renewal",
    "online_renewal_requires_extra_eligibility_checks": "online renewal depends on additional eligibility checks",
    "replacement_no_front_change": "you described a replacement where front-of-card information does not need to change",
    "replacement_without_front_card_changes_may_be_done_online": "replacement without front-of-card changes may be possible online if all required card data is available",
    "replacement_front_change": "you said information printed on the front of the card needs to change",
    "replacement_front_of_card_changes_require_non_online_path": "front-of-card changes generally require a non-online path",
    "address_change_is_handled_as_replacement": "address changes are handled through the replacement/change process",
    "stolen_fraudulent_card_should_be_reported_to_police": "a stolen license used fraudulently should be reported to police",
    "under_18_out_of_scope": "this project intentionally excludes under-18 licensing paths",
}

GUIDANCE_LABELS = {
    "drive_out_of_state_up_to_90_days": "A new Texas resident may generally drive with a valid out-of-state license for up to 90 days after moving.",
    "drive_on_valid_out_of_state_license_for_up_to_90_days_after_moving": "A new Texas resident may generally drive with a valid out-of-state license for up to 90 days after moving.",
    "transfer_in_person_and_surrender": "Plan for an in-person transfer flow and expect the out-of-state license to be surrendered.",
    "apply_in_person_and_surrender_out_of_state_license": "Plan for an in-person transfer flow and expect the out-of-state license to be surrendered.",
    "out_of_state_transfer_exam_waivers_likely_apply": "Knowledge and skills exam waivers likely apply for the recognized transfer credential path.",
    "out_of_state_transfer_but_exam_waivers_not_certain": "Exam waivers are not certain from the facts provided, so plan for official DPS review.",
    "first_time_in_person_application": "Plan for an in-person first-time adult application flow.",
    "first_time_application_in_person_with_docs_and_tests": "Plan for an in-person first-time adult application with documents and expected testing steps.",
    "complete_adult_driver_education_before_applying": "Complete adult driver education before relying on the first-time adult application path.",
    "renewal_confirm_online_eligibility": "Online renewal may be possible, but final eligibility must be confirmed through official Texas online services.",
    "renewal_may_be_done_online_if_all_eligibility_rules_are_met": "Online renewal may be possible if all eligibility rules are met.",
    "renewal_likely_requires_in_person_if_online_rules_not_met": "If online renewal rules are not met, plan for an in-person or non-online renewal path.",
    "renewal_outside_window_conservative": "Because the timing appears outside the two-year renewal window, treat this as requiring official review before assuming renewal is available.",
    "license_expired_more_than_two_years_follow_original_application_guidance": "If the license expired more than two years ago, follow original-application-style guidance rather than ordinary renewal.",
    "replacement_online_if_no_changes": "Online replacement may be possible if eligible and no front-of-card information needs to change.",
    "replacement_may_be_done_online_if_no_front_changes_and_you_have_required_card_data": "Online replacement may be possible if no front-of-card information changed and you have the required card data.",
    "replacement_in_person_if_changes": "If front-of-card information changed, expect a non-online or in-person-style path.",
    "replacement_likely_requires_in_person_if_front_of_card_information_changed": "If front-of-card information changed, expect an in-person or non-online path.",
    "address_must_be_changed_within_30_days_of_moving": "Texas address changes should be handled within 30 days of moving.",
    "address_change_can_be_online_mail_or_in_person_when_eligible": "Address changes may be handled online, by mail, or in person when eligible.",
    "file_police_report_if_stolen_card_was_used_fraudulently": "If a stolen card was used fraudulently, file a police report.",
    "verify_with_official_texas_dps_and_texas_gov_sources": "Verify all guidance with Texas DPS or Texas.gov before acting.",
    "verify_official_sources": "Verify all guidance with Texas DPS or Texas.gov before acting.",
    "under_15_no_ordinary_driver_license_path": "At this age, do not use an ordinary Texas driver-license application path; Texas minor licensing starts with separate learner/provisional rules.",
    "under_18_adult_license_not_available": "Do not use the adult application, renewal, replacement, or transfer guidance here. Use Texas DPS minor/learner/provisional-license information with a parent or guardian instead.",
}


def generate_response(facts: FactState, result: PolicyResult) -> str:
    """Build a natural-language answer from s(CASP) output."""

    if result.error:
        return (
            "I could not run the local s(CASP) reasoning engine. "
            f"{result.error}\n\n"
            "Install s(CASP), make sure `scasp` is in PATH, then restart the app. "
            "The README includes verification steps."
        )

    if result.next_question:
        return _generate_followup_response(result)

    parts: list[str] = []
    if result.case_type:
        parts.append(f"This looks like a **{CASE_LABELS.get(result.case_type, result.case_type)}** case.")
        if result.case_type == "out_of_scope_under_18":
            parts.append(
                "This assistant covers adult, non-commercial driver-license paths only. "
                "Do not use the adult application, renewal, replacement, or transfer guidance for this applicant."
            )
    else:
        parts.append("I still need one more detail before I can classify the case.")

    if result.service_modes:
        service = ", ".join(_label(SERVICE_LABELS, item) for item in result.service_modes)
        parts.append(f"Likely path: {service}.")

    if result.final_guidance:
        guidance = " ".join(_label(GUIDANCE_LABELS, item) for item in result.final_guidance)
        parts.append(guidance)
    elif result.required_docs:
        docs = _short_list([_label(DOC_LABELS, item) for item in result.required_docs], limit=4)
        parts.append(f"Plan around these document categories: {docs}.")

    if facts.age is not None and facts.age < 18:
        parts.append("This assistant only covers adult, non-commercial driver license scenarios.")

    return "\n\n".join(parts)


def _generate_followup_response(result: PolicyResult) -> str:
    case_label = CASE_LABELS.get(result.case_type, result.case_type) if result.case_type else None
    question = QUESTION_TEXT.get(result.next_question or "", result.next_question or "")
    parts: list[str] = []

    if case_label:
        parts.append(f"Got it. This still looks like a **{case_label}** case.")
    else:
        parts.append("Got it. I need one more detail to classify this correctly.")

    reason = _primary_reason(result)
    if reason:
        parts.append(reason)

    if result.missing_info:
        missing_count = len(result.missing_info)
        parts.append(f"I still need {missing_count} detail{'s' if missing_count != 1 else ''} to narrow the guidance.")

    if question:
        parts.append(f"**{question}**")

    return "\n\n".join(parts)


def _primary_reason(result: PolicyResult) -> str | None:
    if result.service_modes:
        return f"Likely path: {_label(SERVICE_LABELS, result.service_modes[0])}."
    if result.explanations:
        return _label(EXPLANATION_LABELS, result.explanations[0]).capitalize() + "."
    return None


def _short_list(items: list[str], limit: int) -> str:
    if len(items) <= limit:
        return ", ".join(items)
    visible = ", ".join(items[:limit])
    return f"{visible}, and {len(items) - limit} more"


def summarize_reasoning(result: PolicyResult) -> str:
    """Return a compact reasoning summary for debug or developer views."""

    if result.error:
        return result.error
    summary = []
    if result.case_type:
        summary.append(f"Case: {CASE_LABELS.get(result.case_type, result.case_type)}")
    if result.missing_info:
        summary.append("Missing: " + ", ".join(result.missing_info))
    if result.explanations:
        summary.append("Why: " + "; ".join(_label(EXPLANATION_LABELS, item) for item in result.explanations))
    return "\n".join(summary) or "No reasoning result yet."


def _label(mapping: dict[str, str], atom: str) -> str:
    return mapping.get(atom, atom.replace("_", " "))


def label_atom(mapping: dict[str, str], atom: str) -> str:
    """Public wrapper for UI modules that need consistent atom labels."""

    return _label(mapping, atom).capitalize()
