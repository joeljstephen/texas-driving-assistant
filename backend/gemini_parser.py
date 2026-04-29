"""Optional Gemini-backed structured parser with deterministic fallback."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import FactState, ParseResult
from .parser import parse_message_with_context


GOALS = {"first_time", "transfer", "renewal", "replacement", "change_info"}
EXPIRATION_TIMINGS = {
    "within_window",
    "outside_window",
    "unknown_expired",
    "within_two_years_before",
    "expires_within_two_years",
    "expired_less_than_two_years",
    "expired_more_than_two_years",
}

GEMINI_FACT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "goal": {
            "type": ["string", "null"],
            "enum": ["first_time", "transfer", "renewal", "replacement", "change_info", None],
        },
        "age": {"type": ["integer", "null"], "minimum": 0, "maximum": 120},
        "new_resident": {"type": ["boolean", "null"]},
        "has_out_of_state_license": {"type": ["boolean", "null"]},
        "out_of_state_license_valid": {"type": ["boolean", "null"]},
        "out_of_state_license_unexpired": {"type": ["boolean", "null"]},
        "out_of_state_license_expired_not_over_two_years": {"type": ["boolean", "null"]},
        "out_of_state_license_expired_over_two_years": {"type": ["boolean", "null"]},
        "current_texas_license": {"type": ["boolean", "null"]},
        "renewal_requested": {"type": ["boolean", "null"]},
        "replacement_requested": {"type": ["boolean", "null"]},
        "first_time_applicant": {"type": ["boolean", "null"]},
        "license_expired": {"type": ["boolean", "null"]},
        "expiration_timing": {
            "type": ["string", "null"],
            "enum": [
                "within_window",
                "outside_window",
                "unknown_expired",
                "within_two_years_before",
                "expires_within_two_years",
                "expired_less_than_two_years",
                "expired_more_than_two_years",
                None,
            ],
        },
        "front_of_card_changed": {"type": ["boolean", "null"]},
        "name_change_requested": {"type": ["boolean", "null"]},
        "address_change_requested": {"type": ["boolean", "null"]},
        "license_lost_stolen_damaged": {"type": ["boolean", "null"]},
        "license_stolen_and_fraud_used": {"type": ["boolean", "null"]},
        "has_identity_doc": {"type": ["boolean", "null"]},
        "has_social_security": {"type": ["boolean", "null"]},
        "has_texas_residency_docs": {"type": ["boolean", "null"]},
        "texas_residency_doc_count": {"type": ["integer", "null"], "minimum": 0, "maximum": 20},
        "lawful_presence_category_known": {"type": ["boolean", "null"]},
        "lawful_presence_on_record": {"type": ["boolean", "null"]},
        "adult_driver_education_status": {
            "type": ["string", "null"],
            "enum": ["completed", "not_completed", "in_progress", None],
        },
        "owns_vehicle": {"type": ["boolean", "null"]},
        "has_proof_of_insurance": {"type": ["boolean", "null"]},
        "has_texas_vehicle_registration": {"type": ["boolean", "null"]},
        "has_card_number": {"type": ["boolean", "null"]},
        "has_date_of_birth_for_online": {"type": ["boolean", "null"]},
        "has_last4_ssn": {"type": ["boolean", "null"]},
        "has_audit_number": {"type": ["boolean", "null"]},
        "us_citizen": {"type": ["boolean", "null"]},
        "ssn_on_record": {"type": ["boolean", "null"]},
        "last_renewed_in_person": {"type": ["boolean", "null"]},
        "license_valid_status": {"type": ["boolean", "null"]},
        "no_outstanding_tickets_or_warrants": {"type": ["boolean", "null"]},
        "health_conditions_unchanged": {"type": ["boolean", "null"]},
        "correction": {"type": "boolean"},
    },
    "required": [
        "goal",
        "age",
        "new_resident",
        "has_out_of_state_license",
        "out_of_state_license_valid",
        "out_of_state_license_unexpired",
        "out_of_state_license_expired_not_over_two_years",
        "out_of_state_license_expired_over_two_years",
        "current_texas_license",
        "renewal_requested",
        "replacement_requested",
        "first_time_applicant",
        "license_expired",
        "expiration_timing",
        "front_of_card_changed",
        "name_change_requested",
        "address_change_requested",
        "license_lost_stolen_damaged",
        "license_stolen_and_fraud_used",
        "has_identity_doc",
        "has_social_security",
        "has_texas_residency_docs",
        "texas_residency_doc_count",
        "lawful_presence_category_known",
        "lawful_presence_on_record",
        "adult_driver_education_status",
        "owns_vehicle",
        "has_proof_of_insurance",
        "has_texas_vehicle_registration",
        "has_card_number",
        "has_date_of_birth_for_online",
        "has_last4_ssn",
        "has_audit_number",
        "us_citizen",
        "ssn_on_record",
        "last_renewed_in_person",
        "license_valid_status",
        "no_outstanding_tickets_or_warrants",
        "health_conditions_unchanged",
        "correction",
    ],
}


@dataclass
class GeminiParserConfig:
    """Runtime configuration for Gemini parsing."""

    enabled: bool = True
    api_key: str | None = None
    model: str | None = None

    @classmethod
    def from_env(cls, enabled: bool | None = None) -> "GeminiParserConfig":
        return cls(
            enabled=env_bool("ENABLE_GEMINI_PARSER", True) if enabled is None else enabled,
            api_key=os.getenv("GEMINI_API_KEY"),
            model=os.getenv("GEMINI_MODEL"),
        )


def parse_with_gemini_or_fallback(
    text: str,
    config: GeminiParserConfig | None = None,
    client: Any | None = None,
    current_facts: FactState | None = None,
    next_question: str | None = None,
) -> ParseResult:
    """Use Gemini for structured parsing when configured, otherwise fall back."""

    active_config = config or GeminiParserConfig.from_env()
    if not active_config.enabled:
        return parse_message_with_context(text, next_question=next_question)

    try:
        return parse_with_gemini(text, active_config, client=client, current_facts=current_facts, next_question=next_question)
    except Exception as exc:
        fallback = parse_message_with_context(text, next_question=next_question)
        fallback.source = "fallback"
        fallback.error = f"Gemini parsing unavailable: {exc}"
        fallback.matched_phrases.append("Gemini fallback parser used")
        if "Gemini fallback parser used" not in fallback.facts.source_notes:
            fallback.facts.source_notes.append("Gemini fallback parser used")
        return fallback


def parse_with_gemini(
    text: str,
    config: GeminiParserConfig,
    client: Any | None = None,
    current_facts: FactState | None = None,
    next_question: str | None = None,
) -> ParseResult:
    """Parse a user utterance through Gemini structured output."""

    if not config.api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    if not config.model:
        raise RuntimeError("GEMINI_MODEL is not set")

    active_client = client or _create_client(config.api_key)
    response = active_client.models.generate_content(
        model=config.model,
        contents=_build_prompt(text, current_facts=current_facts, next_question=next_question),
        config={
            "response_mime_type": "application/json",
            "response_json_schema": GEMINI_FACT_SCHEMA,
            "temperature": 0,
        },
    )
    payload = _response_to_payload(response)
    return validate_gemini_payload(payload)


def validate_gemini_payload(payload: dict[str, Any]) -> ParseResult:
    """Validate Gemini JSON and map it into the app's canonical FactState."""

    if not isinstance(payload, dict):
        raise ValueError("Gemini output must be a JSON object")

    unexpected = set(payload) - set(GEMINI_FACT_SCHEMA["properties"])
    if unexpected:
        raise ValueError(f"Unexpected Gemini fields: {', '.join(sorted(unexpected))}")

    for field_name in GEMINI_FACT_SCHEMA["required"]:
        if field_name not in payload:
            raise ValueError(f"Missing Gemini field: {field_name}")

    goal = _optional_enum(payload["goal"], GOALS, "goal")
    age = _optional_int(payload["age"], "age", minimum=0, maximum=120)
    expiration_timing = _optional_enum(payload["expiration_timing"], EXPIRATION_TIMINGS, "expiration_timing")
    texas_residency_doc_count = _optional_int(
        payload["texas_residency_doc_count"],
        "texas_residency_doc_count",
        minimum=0,
        maximum=20,
    )

    facts = FactState(
        goal=_derive_goal(payload, goal),
        age=age,
        applying_texas_license=True if goal in {"first_time", "transfer"} or payload["first_time_applicant"] else None,
        new_texas_resident=_optional_bool(payload["new_resident"], "new_resident"),
        has_out_of_state_license=_optional_bool(payload["has_out_of_state_license"], "has_out_of_state_license"),
        out_of_state_license_valid=_optional_bool(payload["out_of_state_license_valid"], "out_of_state_license_valid"),
        out_of_state_license_unexpired=_derive_unexpired(payload),
        out_of_state_license_expired_not_over_two_years=_optional_bool(
            payload["out_of_state_license_expired_not_over_two_years"],
            "out_of_state_license_expired_not_over_two_years",
        ),
        out_of_state_license_expired_over_two_years=_optional_bool(
            payload["out_of_state_license_expired_over_two_years"],
            "out_of_state_license_expired_over_two_years",
        ),
        has_texas_license=_optional_bool(payload["current_texas_license"], "current_texas_license"),
        renewal_timing=expiration_timing,
        front_card_changed=_optional_bool(payload["front_of_card_changed"], "front_of_card_changed"),
        name_change_requested=_optional_bool(payload["name_change_requested"], "name_change_requested"),
        address_change_requested=_optional_bool(payload["address_change_requested"], "address_change_requested"),
        license_lost_stolen_damaged=_optional_bool(
            payload["license_lost_stolen_damaged"], "license_lost_stolen_damaged"
        ),
        license_stolen_and_fraud_used=_optional_bool(
            payload["license_stolen_and_fraud_used"], "license_stolen_and_fraud_used"
        ),
        has_identity_doc=_optional_bool(payload["has_identity_doc"], "has_identity_doc"),
        has_social_security=_optional_bool(payload["has_social_security"], "has_social_security"),
        has_texas_residency_docs=_derive_residency_docs_available(payload, texas_residency_doc_count),
        texas_residency_doc_count=texas_residency_doc_count,
        lawful_presence_category_known=_optional_bool(
            payload["lawful_presence_category_known"], "lawful_presence_category_known"
        ),
        lawful_presence_on_record=_optional_bool(payload["lawful_presence_on_record"], "lawful_presence_on_record"),
        adult_driver_education_status=_optional_enum(
            payload["adult_driver_education_status"],
            {"completed", "not_completed", "in_progress"},
            "adult_driver_education_status",
        ),
        owns_vehicle=_optional_bool(payload["owns_vehicle"], "owns_vehicle"),
        has_proof_of_insurance=_optional_bool(payload["has_proof_of_insurance"], "has_proof_of_insurance"),
        has_texas_vehicle_registration=_optional_bool(
            payload["has_texas_vehicle_registration"], "has_texas_vehicle_registration"
        ),
        has_card_number=_optional_bool(payload["has_card_number"], "has_card_number"),
        has_date_of_birth_for_online=_optional_bool(
            payload["has_date_of_birth_for_online"], "has_date_of_birth_for_online"
        ),
        has_last4_ssn=_optional_bool(payload["has_last4_ssn"], "has_last4_ssn"),
        has_audit_number=_optional_bool(payload["has_audit_number"], "has_audit_number"),
        us_citizen=_optional_bool(payload["us_citizen"], "us_citizen"),
        ssn_on_record=_optional_bool(payload["ssn_on_record"], "ssn_on_record"),
        last_renewed_in_person=_optional_bool(payload["last_renewed_in_person"], "last_renewed_in_person"),
        license_valid_status=_optional_bool(payload["license_valid_status"], "license_valid_status"),
        no_outstanding_tickets_or_warrants=_optional_bool(
            payload["no_outstanding_tickets_or_warrants"], "no_outstanding_tickets_or_warrants"
        ),
        health_conditions_unchanged=_optional_bool(
            payload["health_conditions_unchanged"], "health_conditions_unchanged"
        ),
        source_notes=["Gemini structured parser"],
    )

    matched = [note for note in facts.source_notes]
    return ParseResult(
        facts=facts,
        matched_phrases=matched,
        source="gemini",
        correction=_optional_bool(payload["correction"], "correction") is True,
    )


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_dotenv_file(path: str | Path = ".env") -> None:
    """Load simple KEY=VALUE pairs from a local .env file if present."""

    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _create_client(api_key: str) -> Any:
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError("google-genai is not installed") from exc
    return genai.Client(api_key=api_key)


def _build_prompt(text: str, current_facts: FactState | None = None, next_question: str | None = None) -> str:
    current_fact_text = current_facts.to_public_dict() if current_facts else {}
    return (
        "Extract only facts explicitly stated or directly corrected by the user for this Texas driver license "
        "assistant. Do not infer eligibility, requirements, legal conclusions, or process decisions. "
        "Use null for unknown fields. Mark correction true only when the user clearly corrects a prior fact. "
        "If the user gives a short answer like yes, no, or a number, interpret it only in relation to the "
        "current_next_question. For example, if current_next_question is ask_age and the user says 24, set age=24; "
        "if current_next_question is ask_residency_documents and the user says yes, set has_texas_residency_docs=true. "
        "Texas residency requires two documents: if the user says they have one/only one residency document, "
        "set texas_residency_doc_count=1 and has_texas_residency_docs=false; if they say two or more, set "
        "texas_residency_doc_count accordingly and has_texas_residency_docs=true. "
        f"Current known facts: {current_fact_text}\n"
        f"Current next question: {next_question}\n"
        "User utterance:\n"
        f"{text}"
    )


def _response_to_payload(response: Any) -> dict[str, Any]:
    if hasattr(response, "parsed") and response.parsed is not None:
        parsed = response.parsed
        if isinstance(parsed, dict):
            return parsed
    text = getattr(response, "text", None)
    if not text:
        raise ValueError("Gemini returned no JSON text")
    return json.loads(text)


def _derive_goal(payload: dict[str, Any], goal: str | None) -> str | None:
    if goal:
        return goal
    if _optional_bool(payload["renewal_requested"], "renewal_requested"):
        return "renewal"
    if _optional_bool(payload["replacement_requested"], "replacement_requested"):
        return "replacement"
    if _optional_bool(payload["first_time_applicant"], "first_time_applicant"):
        return "first_time"
    return None


def _derive_unexpired(payload: dict[str, Any]) -> bool | None:
    explicit_unexpired = _optional_bool(payload["out_of_state_license_unexpired"], "out_of_state_license_unexpired")
    license_expired = _optional_bool(payload["license_expired"], "license_expired")
    has_out_of_state_license = _optional_bool(payload["has_out_of_state_license"], "has_out_of_state_license")
    current_texas_license = _optional_bool(payload["current_texas_license"], "current_texas_license")

    if explicit_unexpired is not None:
        return explicit_unexpired
    if license_expired is not None and has_out_of_state_license and not current_texas_license:
        return not license_expired
    return None


def _derive_residency_docs_available(payload: dict[str, Any], count: int | None) -> bool | None:
    if count is not None:
        return count >= 2
    return _optional_bool(payload["has_texas_residency_docs"], "has_texas_residency_docs")


def _optional_bool(value: Any, field_name: str) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    raise ValueError(f"{field_name} must be a boolean or null")


def _optional_int(value: Any, field_name: str, minimum: int, maximum: int) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer or null")
    if value < minimum or value > maximum:
        raise ValueError(f"{field_name} out of range")
    return value


def _optional_enum(value: Any, allowed: set[str], field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{field_name} must be one of {sorted(allowed)} or null")
    return value
