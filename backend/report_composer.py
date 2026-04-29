"""Compose a rich, structured report from FactState + PolicyResult.

The Streamlit layer renders the returned ``Report`` as cards, badges, and
checklists. All decisions still come from s(CASP); this module only
formats those decisions into a clearer, more personalized presentation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .document_catalog import DOCUMENT_CATEGORIES, option_label
from .models import DocumentSelections, FactState, PolicyResult
from .response_generator import (
    CASE_LABELS,
    DOC_LABELS,
    EXAM_LABELS,
    EXPLANATION_LABELS,
    GUIDANCE_LABELS,
    MISSING_LABELS,
    SERVICE_LABELS,
    WAIVER_LABELS,
    label_atom,
)


@dataclass
class ChecklistItem:
    """One row in a checklist (documents, exams, waivers, etc.)."""

    label: str
    status: str = "todo"
    detail: str | None = None


@dataclass
class ReportSection:
    """One titled section in the report."""

    key: str
    title: str
    icon: str = ""
    summary: str = ""
    items: list[ChecklistItem] = field(default_factory=list)
    bullets: list[str] = field(default_factory=list)
    empty_text: str = ""


@dataclass
class Report:
    """Top-level report structure for the result panel."""

    case_title: str
    case_label: str
    case_outcome: str
    service_method: str
    confidence_note: str
    summary_lines: list[str] = field(default_factory=list)
    sections: list[ReportSection] = field(default_factory=list)
    why_lines: list[str] = field(default_factory=list)
    missing_items: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    fact_summary: dict[str, str] = field(default_factory=dict)
    error: str | None = None
    disclaimer: str = (
        "Educational project only. Always verify documents, deadlines, and fees with "
        "official Texas DPS or Texas.gov sources before acting."
    )


SERVICE_HEADLINE = {
    "in_person": "In person at a Texas DPS office",
    "may_be_online": "Online may be possible",
    "non_online_or_in_person": "Non-online or in person",
    "likely_in_person_or_new_application": "Likely in person or original application",
    "likely_in_person": "Likely in person",
    "cannot_renew_use_original_application_path": "Original application path",
    "online_mail_or_in_person": "Online, by mail, or in person",
    "not_available_adult_flow": "Not available in this adult flow",
}


SCENARIO_HEADLINES = {
    "first_time_application": "First-time adult Texas driver license application",
    "out_of_state_transfer": "Out-of-state license transfer to Texas",
    "renewal": "Texas driver license renewal",
    "replacement": "Texas driver license replacement",
    "out_of_scope_under_18": "Outside this assistant's adult-license scope",
}


def compose_report(
    facts: FactState,
    result: PolicyResult,
    documents: DocumentSelections,
) -> Report:
    """Build a complete Report from facts, s(CASP) result, and selections."""

    case_label = SCENARIO_HEADLINES.get(result.case_type or "", CASE_LABELS.get(result.case_type or "", "Case not classified"))
    service_method = _service_summary(result.service_modes)
    case_outcome = _build_case_outcome(result)
    summary_lines = _build_summary_lines(facts, result, documents)

    report = Report(
        case_title=case_label,
        case_label=case_label,
        case_outcome=case_outcome,
        service_method=service_method,
        confidence_note=_confidence_note(result),
        summary_lines=summary_lines,
        error=result.error,
    )

    if result.error:
        return report

    if result.case_type == "out_of_scope_under_18":
        report.sections.append(_underage_section(facts))
        report.why_lines = _build_why_lines(facts, result, documents)
        report.missing_items = []
        report.next_steps = _build_next_steps(facts, result)
        report.fact_summary = _fact_summary(facts, documents)
        return report

    report.sections.append(_documents_section(facts, result, documents))
    report.sections.append(_tests_section(result))
    report.sections.append(_waivers_section(result))
    report.sections.append(_service_section(result))

    report.why_lines = _build_why_lines(facts, result, documents)
    report.missing_items = [label_atom(MISSING_LABELS, item) for item in result.missing_info]
    report.next_steps = _build_next_steps(facts, result)
    report.fact_summary = _fact_summary(facts, documents)
    return report


def _service_summary(service_modes: list[str]) -> str:
    if not service_modes:
        return "Not yet determined"
    headlines = [SERVICE_HEADLINE.get(item, label_atom(SERVICE_LABELS, item)) for item in service_modes]
    return " · ".join(_dedupe(headlines))


def _build_case_outcome(result: PolicyResult) -> str:
    if not result.case_type:
        return "Case not yet classified"
    case = SCENARIO_HEADLINES.get(result.case_type, CASE_LABELS.get(result.case_type, ""))
    if result.case_type == "out_of_scope_under_18":
        return (
            "This applicant is under 18. Do not use this adult driver-license "
            "application, renewal, replacement, or transfer path."
        )
    return f"Your case is: {case}."


def _confidence_note(result: PolicyResult) -> str:
    if result.error:
        return "The rule engine could not run."
    missing = len(result.missing_info)
    if missing == 0:
        return "All inputs needed by the rules were provided."
    return f"{missing} input{'s' if missing != 1 else ''} are still unclear; see the missing-items section."


def _build_summary_lines(facts: FactState, result: PolicyResult, documents: DocumentSelections) -> list[str]:
    lines: list[str] = []
    if result.case_type:
        lines.append(_build_case_outcome(result))
    if result.service_modes:
        lines.append(f"Service method: {_service_summary(result.service_modes)}.")
    if facts.age is not None and facts.age < 18:
        if facts.age < 15:
            lines.append(
                f"Age provided: {facts.age}. This is too young for an ordinary Texas driver-license path, "
                "and this assistant does not cover minor learner, provisional, or hardship licenses."
            )
        else:
            lines.append(
                f"Age provided: {facts.age}. This assistant only covers adult driver-license paths; use "
                "Texas DPS minor learner/provisional-license guidance instead."
            )
        return lines
    if facts.age is not None:
        lines.append(f"Age provided: {facts.age}.")
    if facts.has_out_of_state_license is True and facts.out_of_state_license_unexpired is True:
        lines.append("You confirmed a valid, unexpired out-of-state license.")
    if facts.has_identity_doc is True:
        lines.append("Identity documents are confirmed.")
    if facts.has_social_security is True:
        lines.append("Social Security proof is confirmed.")
    if facts.has_texas_residency_docs is True:
        lines.append("Texas residency documents are confirmed.")
    elif facts.texas_residency_doc_count == 1:
        lines.append("One Texas residency document is recorded; Texas DPS generally requires two.")
    if facts.us_citizen is True:
        lines.append("You confirmed U.S. citizenship.")
    return lines


def _documents_section(
    facts: FactState,
    result: PolicyResult,
    documents: DocumentSelections,
) -> ReportSection:
    items: list[ChecklistItem] = []
    seen: set[str] = set()
    for atom in result.required_docs:
        label = label_atom(DOC_LABELS, atom)
        if label in seen:
            continue
        seen.add(label)
        status = _doc_status(atom, facts, documents)
        detail = _doc_detail(atom, facts, documents)
        items.append(ChecklistItem(label=label, status=status, detail=detail))

    return ReportSection(
        key="documents",
        title="Documents you need",
        icon="📄",
        summary="The category-level requirements the rule engine produced for your case.",
        items=items,
        empty_text="No documents are required for this case based on the rules.",
    )


def _doc_status(atom: str, facts: FactState, documents: DocumentSelections) -> str:
    confirmed = {
        "identity": facts.has_identity_doc is True,
        "identity_one_primary_secondary_or_supporting_doc": facts.has_identity_doc is True,
        "identity_verification": facts.has_identity_doc is True,
        "texas_residency_two_documents": facts.has_texas_residency_docs is True,
        "social_security": facts.has_social_security is True,
        "social_security_number": facts.has_social_security is True,
        "social_security_if_not_previously_provided": facts.has_social_security is True,
        "citizenship_or_lawful_presence": facts.lawful_presence_category_known is True,
        "citizenship_or_lawful_presence_if_not_on_record": facts.lawful_presence_category_known is True,
        "citizenship_or_lawful_presence_if_not_previously_provided": facts.lawful_presence_category_known is True,
        "lawful_presence_category": facts.lawful_presence_category_known is True,
        "proof_of_insurance_for_each_owned_vehicle": facts.has_proof_of_insurance is True,
        "texas_vehicle_registration_for_each_owned_vehicle": facts.has_texas_vehicle_registration is True,
        "statement_no_vehicle_owned": facts.owns_vehicle is False,
        "out_of_state_license_to_surrender": facts.has_out_of_state_license is True,
        "adult_driver_education_certificate": facts.adult_driver_education_status == "completed",
        "card_number_date_of_birth_last4_ssn_audit_number": all(
            value is True
            for value in (
                facts.has_card_number,
                facts.has_date_of_birth_for_online,
                facts.has_last4_ssn,
                facts.has_audit_number,
            )
        ),
    }
    if confirmed.get(atom):
        return "confirmed"
    return "todo"


def _doc_detail(atom: str, facts: FactState, documents: DocumentSelections) -> str | None:
    mapping = {
        "identity": "identity",
        "identity_one_primary_secondary_or_supporting_doc": "identity",
        "identity_verification": "identity",
        "texas_residency_two_documents": "residency",
        "social_security": "social_security",
        "social_security_number": "social_security",
        "social_security_if_not_previously_provided": "social_security",
        "citizenship_or_lawful_presence": "lawful_presence",
        "citizenship_or_lawful_presence_if_not_on_record": "lawful_presence",
        "citizenship_or_lawful_presence_if_not_previously_provided": "lawful_presence",
        "lawful_presence_category": "lawful_presence",
    }
    category_key = mapping.get(atom)
    if not category_key:
        return None
    if category_key == "residency":
        selected_count = len(documents.selected.get(category_key, []))
        if documents.other_text.get(category_key, "").strip():
            selected_count += 1
        count = selected_count or facts.texas_residency_doc_count
        if documents.none.get(category_key):
            return "You marked that you do not have Texas residency documents yet."
        if documents.unsure.get(category_key):
            return "You marked this as unsure. Texas DPS generally needs two acceptable residency documents."
        if count == 1:
            return "You have 1 Texas residency document recorded. Texas DPS generally requires two, so this is still incomplete."
    selected_keys = documents.selected.get(category_key, [])
    other_text = documents.other_text.get(category_key, "").strip()
    pieces: list[str] = []
    if selected_keys:
        pieces.extend(option_label(category_key, key) for key in selected_keys)
    if other_text:
        pieces.append(f"Other: {other_text}")
    if category_key == "lawful_presence" and documents.lawful_presence_choice:
        pieces.append(option_label("lawful_presence", documents.lawful_presence_choice))
    if not pieces:
        return None
    return "You picked: " + ", ".join(pieces)


def _tests_section(result: PolicyResult) -> ReportSection:
    items: list[ChecklistItem] = []
    for atom in result.likely_exams:
        items.append(ChecklistItem(label=label_atom(EXAM_LABELS, atom), status="todo"))
    return ReportSection(
        key="tests",
        title="Tests and courses",
        icon="📝",
        summary="Knowledge, skills, vision, and Impact Texas Drivers expectations.",
        items=items,
        empty_text="No tests or courses are expected for this case from the current rules.",
    )


def _underage_section(facts: FactState) -> ReportSection:
    age = facts.age if facts.age is not None else "under 18"
    if isinstance(age, int) and age < 15:
        label = (
            f"Age {age} is not eligible for the adult Texas driver-license flows in this assistant. "
            "Do not continue with the adult application, renewal, transfer, or replacement guidance."
        )
        detail = "Texas minor licensing is a separate learner/provisional or hardship process, not this adult workflow."
    else:
        label = f"Age {age} is under 18, so this adult workflow is not the right path."
        detail = "Use official Texas DPS minor learner/provisional-license guidance with a parent or guardian."
    return ReportSection(
        key="underage_scope",
        title="Adult-license eligibility",
        icon="⚠️",
        summary="This assistant intentionally stops ordinary adult guidance when the applicant is under 18.",
        items=[ChecklistItem(label=label, status="todo", detail=detail)],
        empty_text="",
    )


def _waivers_section(result: PolicyResult) -> ReportSection:
    items: list[ChecklistItem] = []
    for atom in result.waivers:
        items.append(ChecklistItem(label=label_atom(WAIVER_LABELS, atom), status="confirmed"))
    return ReportSection(
        key="waivers",
        title="Waivers and exceptions that apply",
        icon="🎯",
        summary="Rule-driven waivers that reduce required documents, exams, or steps.",
        items=items,
        empty_text="No waivers were triggered by the current facts.",
    )


def _service_section(result: PolicyResult) -> ReportSection:
    items = []
    for atom in result.service_modes:
        items.append(ChecklistItem(label=label_atom(SERVICE_LABELS, atom), status="info"))
    return ReportSection(
        key="service",
        title="Application or service method",
        icon="🏢",
        summary="The path the rule engine selected for handling this case.",
        items=items,
        empty_text="The rule engine has not selected a service method yet.",
    )


def _build_why_lines(
    facts: FactState,
    result: PolicyResult,
    documents: DocumentSelections,
) -> list[str]:
    lines: list[str] = []
    case_label = SCENARIO_HEADLINES.get(result.case_type or "", "your case")

    if facts.goal == "first_time" or result.case_type == "first_time_application":
        lines.append("You said you are applying for your first Texas driver license.")
    if facts.goal == "transfer" or result.case_type == "out_of_state_transfer":
        lines.append("You said you are moving to Texas with an existing out-of-state license.")
    if facts.goal == "renewal" or result.case_type == "renewal":
        lines.append("You said you are renewing an existing Texas driver license.")
    if facts.goal == "replacement" or result.case_type == "replacement":
        lines.append("You said you are replacing or updating a Texas driver license.")

    if facts.age is not None:
        if 18 <= facts.age <= 24 and result.case_type == "first_time_application":
            lines.append(f"You are {facts.age}, so adult driver education applies in this rule set.")
        elif facts.age >= 25 and result.case_type == "first_time_application":
            lines.append(f"You are {facts.age}, so adult driver education does not apply.")
        elif facts.age < 18:
            lines.append(f"You are {facts.age}, which is under 18 and outside this assistant's adult scope.")
        else:
            lines.append(f"You are {facts.age}.")

    if facts.has_out_of_state_license is True and facts.out_of_state_license_unexpired is True and facts.out_of_state_license_valid is True:
        lines.append("Your out-of-state license is valid and unexpired, so transfer waivers apply.")
    elif facts.has_out_of_state_license is True and facts.out_of_state_license_unexpired is False:
        lines.append("Your out-of-state license has expired, which limits the waivers available.")

    confirmed_docs: list[str] = []
    if facts.has_identity_doc is True:
        confirmed_docs.append("identity")
    if facts.has_social_security is True:
        confirmed_docs.append("Social Security")
    if facts.has_texas_residency_docs is True:
        confirmed_docs.append("Texas residency")
    if facts.lawful_presence_category_known is True:
        confirmed_docs.append("citizenship or lawful presence")
    if confirmed_docs:
        lines.append("You confirmed " + _join_with_and(confirmed_docs) + " documents.")

    missing_docs: list[str] = []
    if facts.has_identity_doc is None or facts.has_identity_doc is False:
        if any(atom.startswith("identity") for atom in result.required_docs):
            missing_docs.append("identity")
    if facts.has_social_security is None or facts.has_social_security is False:
        if any("social_security" in atom for atom in result.required_docs):
            missing_docs.append("Social Security")
    if facts.has_texas_residency_docs is None or facts.has_texas_residency_docs is False:
        if "texas_residency_two_documents" in result.required_docs:
            missing_docs.append("Texas residency")
    if missing_docs:
        lines.append("You still need to confirm " + _join_with_and(missing_docs) + " documents.")

    if result.case_type == "renewal" and facts.renewal_timing:
        if facts.renewal_timing == "within_window":
            lines.append("Your timing is inside the two-year renewal window.")
        elif facts.renewal_timing == "outside_window":
            lines.append("Your timing is outside the two-year renewal window, so this is treated as an original application.")

    if result.case_type == "replacement":
        if facts.front_card_changed is True:
            lines.append("Information on the front of the card needs to change.")
        elif facts.front_card_changed is False:
            lines.append("No front-of-card information is changing.")

    for atom in result.explanations:
        lines.append(label_atom(EXPLANATION_LABELS, atom))

    if not lines:
        lines.append(f"The rule engine selected {case_label} based on the facts you provided.")
    return _dedupe(lines)


def _build_next_steps(facts: FactState, result: PolicyResult) -> list[str]:
    steps: list[str] = []
    for atom in result.final_guidance:
        steps.append(label_atom(GUIDANCE_LABELS, atom))
    if result.case_type == "out_of_scope_under_18":
        return _dedupe(steps)
    if result.missing_info:
        steps.append(
            "Update your answers above to fill in: "
            + ", ".join(label_atom(MISSING_LABELS, atom) for atom in result.missing_info)
            + "."
        )
    if result.case_type == "first_time_application":
        steps.append("Plan an in-person visit to a Texas DPS office to complete the application.")
    if result.case_type == "out_of_state_transfer":
        steps.append("Bring your out-of-state license to surrender during the in-person transfer.")
    return _dedupe(steps)


def _fact_summary(facts: FactState, documents: DocumentSelections) -> dict[str, str]:
    summary: dict[str, str] = {}
    if facts.age is not None:
        summary["Age"] = str(facts.age)
    if facts.has_out_of_state_license is not None:
        summary["Out-of-state license"] = "Yes" if facts.has_out_of_state_license else "No"
    if facts.out_of_state_license_unexpired is not None:
        summary["Out-of-state license unexpired"] = "Yes" if facts.out_of_state_license_unexpired else "No"
    if facts.has_texas_license is not None:
        summary["Current Texas license"] = "Yes" if facts.has_texas_license else "No"
    if facts.us_citizen is not None:
        summary["U.S. citizen"] = "Yes" if facts.us_citizen else "No"
    if facts.adult_driver_education_status:
        summary["Adult driver education"] = facts.adult_driver_education_status.replace("_", " ").title()
    for category_key, category in DOCUMENT_CATEGORIES.items():
        choices = documents.selected.get(category_key, [])
        if choices:
            summary[category.title] = ", ".join(option_label(category_key, key) for key in choices)
    if documents.lawful_presence_choice:
        summary["Citizenship or lawful presence"] = option_label("lawful_presence", documents.lawful_presence_choice)
    return summary


def _join_with_and(values: Iterable[str]) -> str:
    items = list(values)
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered
