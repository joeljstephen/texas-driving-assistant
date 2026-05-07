"""Detect the guided intake case from the user's entry message."""

from __future__ import annotations

from dataclasses import dataclass

from .gemini_parser import GeminiParserConfig, parse_with_gemini_or_fallback
from .intake import scenario_from_facts
from .models import FactState, ParseResult


CASE_LABELS: dict[str, str] = {
    "first_time": "First-time Texas driver license application",
    "transfer": "Out-of-state license transfer to Texas",
    "renewal": "Texas driver license renewal",
    "replacement": "Texas driver license replacement",
    "change_info": "Texas driver license address or name change",
}

CASE_INTROS: dict[str, str] = {
    "first_time": (
        "Got it — this looks like a first-time Texas driver license application. "
        "I'll guide you through the documents and extra steps that matter for adult applicants."
    ),
    "transfer": (
        "Got it — you're transferring an out-of-state license to Texas. "
        "I'll walk you through the validity, residency, and vehicle details that change your path."
    ),
    "renewal": (
        "Got it — you want to renew your Texas driver license. "
        "I'll ask about timing and a few eligibility checks that decide whether online renewal is possible."
    ),
    "replacement": (
        "Got it — you're replacing a lost, stolen, or damaged Texas license. "
        "I'll check whether you can do it online or whether you need an in-person visit."
    ),
    "change_info": (
        "Got it — you're updating address or name on your Texas license. "
        "I'll check whether the change can be done online or by mail."
    ),
}

UNKNOWN_INTRO = (
    "Thanks for the message. I couldn't tell which case applies yet. "
    "Pick the closest scenario below and I'll start the guided intake."
)


@dataclass
class CaseDetection:
    """Result of running a free-text entry through the parser."""

    facts: FactState
    parse_result: ParseResult
    scenario_key: str | None
    message: str

    @property
    def detected(self) -> bool:
        return self.scenario_key is not None


def detect_case(
    user_text: str,
    *,
    use_gemini: bool,
    current_facts: FactState | None = None,
) -> CaseDetection:
    """Run the parser and pick the best scenario for the user message."""

    parsed = parse_with_gemini_or_fallback(
        user_text,
        GeminiParserConfig.from_env(enabled=use_gemini),
        current_facts=current_facts,
        next_question=None,
    )
    scenario_key = scenario_from_facts(parsed.facts)
    message = build_intro_message(scenario_key, parsed)
    return CaseDetection(
        facts=parsed.facts,
        parse_result=parsed,
        scenario_key=scenario_key,
        message=message,
    )


def build_intro_message(scenario_key: str | None, parsed: ParseResult) -> str:
    """Compose the assistant's first acknowledgement message."""

    base = CASE_INTROS.get(scenario_key or "", UNKNOWN_INTRO)
    facts = parsed.facts
    if facts.age is not None and facts.age < 18:
        base = (
            "I can record the details, but this assistant covers adult Texas driver-license paths. "
            "Because the applicant is under 18, the final report will stop the adult workflow and point you "
            "to Texas DPS minor learner/provisional-license guidance instead."
        )
    extras: list[str] = []
    if facts.age is not None:
        extras.append(f"You're {facts.age}.")
    if facts.has_out_of_state_license is True:
        extras.append("You mentioned an out-of-state license.")
    if facts.new_texas_resident is True:
        extras.append("You moved to Texas.")
    if facts.renewal_timing in {"within_window"}:
        extras.append("Renewal timing looks like it's within the two-year window.")
    if facts.renewal_timing == "outside_window":
        extras.append("It sounds like the license expired more than two years ago.")
    if facts.license_lost_stolen_damaged is True:
        extras.append("Your card is lost, stolen, or damaged.")
    if extras:
        return base + "\n\n" + " ".join(extras)
    return base


def case_label(scenario_key: str | None) -> str:
    if not scenario_key:
        return "Case not yet classified"
    return CASE_LABELS.get(scenario_key, scenario_key.replace("_", " ").title())
