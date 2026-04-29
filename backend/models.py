"""Typed data structures used across the assistant backend."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class FactState:
    """Structured facts accumulated from the conversation."""

    goal: str | None = None
    age: int | None = None
    applying_texas_license: bool | None = None
    new_texas_resident: bool | None = None
    has_out_of_state_license: bool | None = None
    out_of_state_license_valid: bool | None = None
    out_of_state_license_unexpired: bool | None = None
    out_of_state_license_expired_not_over_two_years: bool | None = None
    out_of_state_license_expired_over_two_years: bool | None = None
    has_texas_license: bool | None = None
    renewal_timing: str | None = None
    front_card_changed: bool | None = None
    name_change_requested: bool | None = None
    address_change_requested: bool | None = None
    license_lost_stolen_damaged: bool | None = None
    license_stolen_and_fraud_used: bool | None = None
    has_identity_doc: bool | None = None
    has_social_security: bool | None = None
    has_texas_residency_docs: bool | None = None
    texas_residency_doc_count: int | None = None
    lawful_presence_category_known: bool | None = None
    lawful_presence_on_record: bool | None = None
    adult_driver_education_status: str | None = None
    owns_vehicle: bool | None = None
    has_proof_of_insurance: bool | None = None
    has_texas_vehicle_registration: bool | None = None
    has_card_number: bool | None = None
    has_date_of_birth_for_online: bool | None = None
    has_last4_ssn: bool | None = None
    has_audit_number: bool | None = None
    us_citizen: bool | None = None
    ssn_on_record: bool | None = None
    last_renewed_in_person: bool | None = None
    license_valid_status: bool | None = None
    no_outstanding_tickets_or_warrants: bool | None = None
    health_conditions_unchanged: bool | None = None
    source_notes: list[str] = field(default_factory=list)

    def to_public_dict(self) -> dict[str, Any]:
        """Return a UI-friendly dictionary without empty values."""

        data = asdict(self)
        return {key: value for key, value in data.items() if value not in (None, [], {})}


@dataclass
class ParseResult:
    """Facts extracted from one user message."""

    facts: FactState = field(default_factory=FactState)
    matched_phrases: list[str] = field(default_factory=list)
    source: str = "deterministic"
    error: str | None = None
    correction: bool = False


@dataclass
class ChatMessage:
    """A message shown in the chat transcript."""

    role: str
    content: str


@dataclass
class PolicyResult:
    """Result returned by the s(CASP) policy program."""

    case_type: str | None = None
    next_question: str | None = None
    missing_info: list[str] = field(default_factory=list)
    service_modes: list[str] = field(default_factory=list)
    required_docs: list[str] = field(default_factory=list)
    likely_exams: list[str] = field(default_factory=list)
    waivers: list[str] = field(default_factory=list)
    explanations: list[str] = field(default_factory=list)
    final_guidance: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass
class DocumentSelections:
    """Per-category document selections made by the user."""

    selected: dict[str, list[str]] = field(default_factory=dict)
    other_text: dict[str, str] = field(default_factory=dict)
    unsure: dict[str, bool] = field(default_factory=dict)
    none: dict[str, bool] = field(default_factory=dict)
    lawful_presence_choice: str | None = None

    def category_options(self, category_key: str) -> list[str]:
        return list(self.selected.get(category_key, []))

    def has_specific_selection(self, category_key: str) -> bool:
        if self.selected.get(category_key):
            return True
        text = self.other_text.get(category_key, "")
        return bool(text and text.strip())


@dataclass
class AssistantSession:
    """Conversation state persisted by Streamlit."""

    facts: FactState = field(default_factory=FactState)
    messages: list[ChatMessage] = field(default_factory=list)
    last_policy_result: PolicyResult | None = None
    last_parse_result: ParseResult | None = None
    documents: DocumentSelections = field(default_factory=DocumentSelections)
    detected_case: str | None = None
    detection_message: str | None = None
    intake_step: int = 0
