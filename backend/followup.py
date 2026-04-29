"""Follow-up chat support after the report is generated.

The follow-up chat is intentionally narrow: it answers questions using
only the facts the user already provided and the s(CASP) reasoning result.
Optional Gemini polishing rephrases the deterministic answer for a more
natural feel without inventing new requirements.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from .gemini_parser import env_bool
from .models import DocumentSelections, FactState, PolicyResult
from .report_composer import Report
from .response_generator import (
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
class FollowUpConfig:
    """Configuration for optional Gemini follow-up rewriting."""

    enabled: bool = False
    api_key: str | None = None
    model: str | None = None

    @classmethod
    def from_env(cls, enabled: bool | None = None) -> "FollowUpConfig":
        return cls(
            enabled=env_bool("ENABLE_GEMINI_FOLLOWUP", False) if enabled is None else enabled,
            api_key=os.getenv("GEMINI_API_KEY"),
            model=os.getenv("GEMINI_MODEL"),
        )


TOPICS = {
    "identity": [
        "identity",
        "id ",
        "passport",
        "birth certificate",
        "green card",
        "citizenship doc",
    ],
    "residency": [
        "residency",
        "address",
        "30 day",
        "30-day",
        "lease",
        "utility",
        "two proofs",
    ],
    "social_security": [
        "social security",
        "ssn",
        "ss number",
        "ss card",
    ],
    "lawful_presence": [
        "lawful",
        "permanent resident",
        "visa",
        "i-94",
        "i94",
        "asylee",
        "refugee",
        "noncitizen",
        "non-citizen",
    ],
    "vehicle": [
        "car",
        "vehicle",
        "insurance",
        "registration",
        "no vehicle",
        "do not own",
        "don't own",
    ],
    "driver_education": [
        "driver education",
        "driver ed",
        "drivers ed",
        "adult driver",
        "impact texas",
    ],
    "out_of_state": [
        "out of state",
        "out-of-state",
        "expired license",
        "transfer",
        "another state",
    ],
    "renewal": [
        "renew",
        "renewal",
        "expir",
        "online renewal",
    ],
    "replacement": [
        "replace",
        "replacement",
        "lost",
        "stolen",
        "damaged",
        "front of card",
    ],
    "missing": [
        "missing",
        "what else",
        "what next",
        "what now",
        "still need",
    ],
    "service": [
        "online",
        "in person",
        "in-person",
        "by mail",
        "appointment",
    ],
    "report": [
        "report",
        "summary",
        "generated",
        "current",
        "currently",
        "explain",
        "why",
        "what does it say",
    ],
}


def answer_follow_up(
    user_text: str,
    facts: FactState,
    result: PolicyResult | None,
    documents: DocumentSelections,
    report: Report | None,
    config: FollowUpConfig | None = None,
    client: Any | None = None,
) -> str:
    """Build a grounded answer to a user follow-up question."""

    deterministic = build_deterministic_answer(user_text, facts, result, documents, report)
    active_config = config or FollowUpConfig.from_env()
    if not active_config.enabled or not result or result.error:
        return deterministic
    try:
        return call_gemini_followup(user_text, facts, result, documents, report, deterministic, active_config, client=client) or deterministic
    except Exception:
        return deterministic


def build_deterministic_answer(
    user_text: str,
    facts: FactState,
    result: PolicyResult | None,
    documents: DocumentSelections,
    report: Report | None,
) -> str:
    """Resolve the user question against structured state."""

    if not result:
        return (
            "Run the guided intake first so I can ground my answer in the rule "
            "engine result. Pick a scenario above and click 'Check my requirements'."
        )
    if result.error:
        return (
            "The rule engine result is not available right now. Once s(CASP) is "
            "installed and runs, I can answer follow-ups grounded in your case."
        )

    text = user_text.lower()
    topics = _topics_in(text)

    pieces: list[str] = []

    if "identity" in topics:
        pieces.append(_identity_answer(facts, documents))
    if "residency" in topics:
        pieces.append(_residency_answer(facts, documents))
    if "social_security" in topics:
        pieces.append(_ssn_answer(facts, documents))
    if "lawful_presence" in topics:
        pieces.append(_lawful_presence_answer(facts, documents))
    if "vehicle" in topics:
        pieces.append(_vehicle_answer(facts))
    if "driver_education" in topics:
        pieces.append(_driver_education_answer(facts, result))
    if "out_of_state" in topics:
        pieces.append(_out_of_state_answer(facts, result))
    if "renewal" in topics:
        pieces.append(_renewal_answer(facts, result))
    if "replacement" in topics:
        pieces.append(_replacement_answer(facts, result))
    if "missing" in topics:
        pieces.append(_missing_answer(result))
    if "service" in topics:
        pieces.append(_service_answer(result))
    if "report" in topics:
        pieces.append(_report_answer(result, report))

    pieces = [piece for piece in pieces if piece]

    if not pieces:
        pieces.append(_general_answer(result, report))

    if result.missing_info and "missing" not in topics:
        pieces.append(_missing_answer(result))

    pieces.append(
        "Educational project only. Verify documents, deadlines, and fees with "
        "official Texas DPS or Texas.gov before acting."
    )
    return "\n\n".join(pieces)


def _topics_in(text: str) -> set[str]:
    matched: set[str] = set()
    for topic, keywords in TOPICS.items():
        if any(keyword in text for keyword in keywords):
            matched.add(topic)
    return matched


def _identity_answer(facts: FactState, documents: DocumentSelections) -> str:
    selected = documents.selected.get("identity", [])
    intro = (
        "Texas DPS uses category-based identity rules: a primary document on its own (passport, "
        "U.S. birth certificate, citizenship/naturalization certificate, permanent resident card) "
        "or a combination from the secondary and supporting groups."
    )
    if selected:
        return f"{intro} You selected {len(selected)} identity document(s)."
    if facts.has_identity_doc is True:
        return f"{intro} You confirmed identity documents are available."
    return f"{intro} I don't see specific identity documents recorded yet — pick from the catalog under Documents."


def _residency_answer(facts: FactState, documents: DocumentSelections) -> str:
    selected = documents.selected.get("residency", [])
    intro = (
        "Texas DPS generally requires two different documents that show your Texas residential "
        "address (lease, utility, bank, voter registration, vehicle registration, insurance, "
        "school or government mail). The 30-day duration rule is waived only for valid, unexpired "
        "out-of-state transfers."
    )
    if facts.has_out_of_state_license is True and facts.out_of_state_license_unexpired is True:
        intro += " Because your out-of-state license is valid and unexpired, the 30-day duration rule does not apply to you."
    if selected:
        if len(selected) == 1:
            return f"{intro} You picked 1 residency document so far, so the two-document requirement is still incomplete."
        return f"{intro} You picked {len(selected)} residency document(s) so far."
    if facts.texas_residency_doc_count == 1:
        return f"{intro} You have 1 residency document recorded, so the two-document requirement is still incomplete."
    if facts.has_texas_residency_docs is True:
        return f"{intro} You confirmed two Texas residency documents are available."
    return f"{intro} You haven't recorded specific residency documents yet."


def _ssn_answer(facts: FactState, documents: DocumentSelections) -> str:
    intro = (
        "Acceptable Social Security proof commonly includes the SS card, a W-2, an SSA-1099, a "
        "non-SSA-1099, or a pay stub showing your name and SSN. If you are not eligible for an "
        "SSN, Texas DPS has a separate process."
    )
    selected = documents.selected.get("social_security", [])
    if selected:
        if "not_eligible_for_ssn" in selected:
            return f"{intro} You indicated you are not eligible for an SSN; expect Texas DPS to use the alternate process."
        if "knows_ssn_only" in selected and len(selected) == 1:
            return f"{intro} You said you know your SSN but don't have a document; bring an alternative proof to your visit."
        return f"{intro} You have at least one accepted SS proof recorded."
    if facts.has_social_security is True:
        return f"{intro} You confirmed Social Security proof is available."
    return f"{intro} You haven't picked a specific SS proof yet."


def _lawful_presence_answer(facts: FactState, documents: DocumentSelections) -> str:
    choice = documents.lawful_presence_choice
    intro = (
        "Lawful presence is recorded by category — U.S. citizen, lawful permanent resident, "
        "asylee/refugee, valid visa with I-94, employment authorization (I-766), DACA, or other. "
        "The category drives which documents and license expirations apply."
    )
    if choice == "us_citizen" or facts.us_citizen is True:
        return f"{intro} You're recorded as a U.S. citizen."
    if choice:
        return f"{intro} You picked: {choice.replace('_', ' ')}."
    if facts.lawful_presence_category_known is True:
        return f"{intro} You confirmed your category is known."
    return f"{intro} You haven't picked a category yet — open the Documents step to set it."


def _vehicle_answer(facts: FactState) -> str:
    if facts.owns_vehicle is True:
        return (
            "You own a vehicle, so plan for proof of insurance for each vehicle and (for an "
            "out-of-state transfer) Texas vehicle registration."
        )
    if facts.owns_vehicle is False:
        return (
            "You don't own a vehicle, so the rules use a no-vehicle statement instead of insurance "
            "or registration documents."
        )
    return (
        "Vehicle ownership wasn't recorded yet. If you own a vehicle, expect proof of insurance "
        "to be required; if not, a no-vehicle statement is used."
    )


def _driver_education_answer(facts: FactState, result: PolicyResult) -> str:
    if result.case_type != "first_time_application":
        return ""
    if facts.age is None:
        return "Adult driver education is required for first-time applicants 18–24."
    if 18 <= facts.age <= 24:
        status = facts.adult_driver_education_status
        if status == "completed":
            return f"You're {facts.age}, and you confirmed adult driver education is completed."
        if status == "in_progress":
            return f"You're {facts.age} and adult driver education is in progress; finish it before applying."
        if status == "not_completed":
            return f"You're {facts.age}; you must complete adult driver education before applying."
        return f"You're {facts.age}, so adult driver education applies; record your status under Documents."
    return f"You're {facts.age}, so adult driver education does not apply to you."


def _out_of_state_answer(facts: FactState, result: PolicyResult) -> str:
    if facts.has_out_of_state_license is False:
        return "You said you don't currently have an out-of-state license, so transfer waivers do not apply."
    if facts.out_of_state_license_unexpired is True and facts.out_of_state_license_valid is True:
        return (
            "Your valid, unexpired out-of-state license usually qualifies for the knowledge and "
            "skills exam waivers and the 30-day Texas residency duration waiver."
        )
    if facts.out_of_state_license_unexpired is False:
        return (
            "Your out-of-state license is expired. If it expired within two years, some waivers may "
            "still apply; over two years, expect to be treated more like a first-time application."
        )
    return "Confirm whether your out-of-state license is valid and unexpired in the intake to lock in the right path."


def _renewal_answer(facts: FactState, result: PolicyResult) -> str:
    if result.case_type != "renewal":
        return ""
    if facts.renewal_timing == "outside_window":
        return (
            "Because the license expired more than two years ago, this falls outside the renewal "
            "window. Plan to follow original-application guidance, not ordinary renewal."
        )
    if "may_be_online" in result.service_modes:
        return "Online renewal may be possible based on the eligibility checks you confirmed."
    if "likely_in_person" in result.service_modes:
        return (
            "Online renewal eligibility was not fully met from your answers. Plan for an in-person "
            "renewal at a Texas DPS office."
        )
    return "Renewal timing and eligibility checks decide whether you can renew online or in person."


def _replacement_answer(facts: FactState, result: PolicyResult) -> str:
    if result.case_type != "replacement":
        return ""
    if facts.front_card_changed is True:
        return (
            "Information on the front of the card needs to change, so expect a non-online or "
            "in-person path."
        )
    if facts.front_card_changed is False:
        if all(value is True for value in (facts.has_card_number, facts.has_date_of_birth_for_online, facts.has_last4_ssn, facts.has_audit_number)):
            return "No front-of-card changes and all required identifiers are recorded — online replacement may be possible."
        return (
            "No front-of-card changes are needed, but you're still missing one or more identifiers "
            "(card number, DOB, last-four SSN, audit number). Online replacement requires all four."
        )
    return "Confirm whether front-of-card information needs to change to lock the path."


def _missing_answer(result: PolicyResult) -> str:
    if not result.missing_info:
        return "There are no missing items flagged by the rule engine."
    pieces = ", ".join(label_atom(MISSING_LABELS, item) for item in result.missing_info)
    return f"Items still flagged as missing or unclear: {pieces}. Update them in the intake and re-run."


def _service_answer(result: PolicyResult) -> str:
    if not result.service_modes:
        return "No service mode has been determined yet."
    pieces = ", ".join(label_atom(SERVICE_LABELS, item) for item in result.service_modes)
    return f"The rule engine selected: {pieces}."


def _general_answer(result: PolicyResult, report: Report | None) -> str:
    if report:
        return _report_answer(result, report)
    if result.case_type:
        return f"Your inferred case is {result.case_type.replace('_', ' ')}."
    return "I don't have enough information yet — try the guided intake or ask about a specific topic like identity, residency, vehicle, online eligibility, or missing items."


def _report_answer(result: PolicyResult, report: Report | None) -> str:
    if not report:
        return _general_answer(result, None)

    lines = [report.case_outcome, f"Service method: {report.service_method}."]
    if report.fact_summary:
        facts = "; ".join(f"{key}: {value}" for key, value in report.fact_summary.items())
        lines.append(f"Recorded facts: {facts}.")
    if report.missing_items:
        lines.append("Missing or unclear: " + ", ".join(report.missing_items) + ".")
    else:
        lines.append("The rule engine is not flagging missing items.")
    if report.next_steps:
        lines.append("Next step: " + report.next_steps[0])
    return " ".join(line for line in lines if line)


def call_gemini_followup(
    user_text: str,
    facts: FactState,
    result: PolicyResult,
    documents: DocumentSelections,
    report: Report | None,
    deterministic_answer: str,
    config: FollowUpConfig,
    client: Any | None = None,
) -> str:
    """Optionally rephrase the deterministic answer with Gemini."""

    if not config.api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    if not config.model:
        raise RuntimeError("GEMINI_MODEL is not set")

    active_client = client or _create_client(config.api_key)
    response = active_client.models.generate_content(
        model=config.model,
        contents=_build_prompt(user_text, facts, result, documents, report, deterministic_answer),
        config={"temperature": 0.2},
    )
    return (getattr(response, "text", "") or "").strip()


def _create_client(api_key: str) -> Any:
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError("google-genai is not installed") from exc
    return genai.Client(api_key=api_key)


def _build_prompt(
    user_text: str,
    facts: FactState,
    result: PolicyResult,
    documents: DocumentSelections,
    report: Report | None,
    deterministic_answer: str,
) -> str:
    payload = {
        "facts": facts.to_public_dict(),
        "documents": {
            "selected": documents.selected,
            "other_text": documents.other_text,
            "lawful_presence_choice": documents.lawful_presence_choice,
        },
        "result": {
            "case_type": result.case_type,
            "service_modes": result.service_modes,
            "required_docs": [label_atom(DOC_LABELS, atom) for atom in result.required_docs],
            "likely_exams": [label_atom(EXAM_LABELS, atom) for atom in result.likely_exams],
            "waivers": [label_atom(WAIVER_LABELS, atom) for atom in result.waivers],
            "missing_info": [label_atom(MISSING_LABELS, atom) for atom in result.missing_info],
            "explanations": [label_atom(EXPLANATION_LABELS, atom) for atom in result.explanations],
            "final_guidance": [label_atom(GUIDANCE_LABELS, atom) for atom in result.final_guidance],
        },
    }
    if report:
        payload["report"] = {
            "case_outcome": report.case_outcome,
            "service_method": report.service_method,
            "why_lines": report.why_lines,
            "missing_items": report.missing_items,
            "next_steps": report.next_steps,
        }
    return (
        "You are a Texas driver license guidance assistant. Use ONLY the structured payload "
        "below to answer the user's follow-up question. Do not invent documents, exams, fees, "
        "deadlines, or eligibility rules. Do not contradict the deterministic answer. Keep the "
        "tone friendly and concise (3 to 6 short sentences). If the payload doesn't cover the "
        "question, say so and suggest revisiting the intake.\n\n"
        f"User question: {user_text}\n\n"
        f"Deterministic answer (must remain factually consistent with this):\n{deterministic_answer}\n\n"
        f"Structured payload:\n{json.dumps(payload, default=str, indent=2)}"
    )
