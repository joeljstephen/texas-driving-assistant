"""Scenario-specific guided intake configuration.

Each supported case is broken into a small number of grouped steps:
``About your case`` → ``Your documents`` → ``Extra requirements`` →
``Review and check``. The Streamlit layer renders one step at a time
so the experience feels guided instead of dumping a long form.

Backwards compatible helpers ``facts_from_intake`` and ``intake_defaults``
still accept a flat dict of values so existing tests and callers keep
working. Document-related selections are translated through the
``DocumentSelections`` model when the new UI is used.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .document_catalog import DOCUMENT_CATEGORIES
from .models import DocumentSelections, FactState


YES_NO_UNKNOWN = ["Not sure", "Yes", "No"]
YES_NO = ["Yes", "No"]


@dataclass(frozen=True)
class IntakeField:
    """A single field rendered inside an intake step."""

    key: str
    label: str
    kind: str
    options: list[str] | None = None
    helper_title: str | None = None
    helper_text: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class IntakeStep:
    """A grouped portion of the intake flow."""

    key: str
    title: str
    description: str
    fields: tuple[IntakeField, ...] = ()
    document_categories: tuple[str, ...] = ()
    summary_kind: str = ""


@dataclass(frozen=True)
class IntakeScenario:
    """Top-level guided intake configuration for one case."""

    key: str
    label: str
    description: str
    steps: tuple[IntakeStep, ...]

    @property
    def fields(self) -> list[IntakeField]:
        flat: list[IntakeField] = []
        for step in self.steps:
            flat.extend(step.fields)
        return flat


def _step(
    key: str,
    title: str,
    description: str,
    *,
    fields: Iterable[IntakeField] = (),
    document_categories: Iterable[str] = (),
    summary_kind: str = "",
) -> IntakeStep:
    return IntakeStep(
        key=key,
        title=title,
        description=description,
        fields=tuple(fields),
        document_categories=tuple(document_categories),
        summary_kind=summary_kind,
    )


SCENARIOS: dict[str, IntakeScenario] = {
    "first_time": IntakeScenario(
        key="first_time",
        label="First-time application",
        description="Adult applying for a first Texas driver license.",
        steps=(
            _step(
                "about",
                "About your case",
                "Tell me a few quick things about you and your situation.",
                fields=(
                    IntakeField(
                        "age",
                        "Your age",
                        "number",
                        description="Age determines whether adult driver education applies.",
                    ),
                    IntakeField(
                        "applying_first_texas",
                        "Is this your first Texas driver license?",
                        "choice",
                        YES_NO,
                    ),
                    IntakeField(
                        "has_out_of_state_license",
                        "Do you currently hold an out-of-state license?",
                        "choice",
                        YES_NO,
                        helper_title="Why this matters",
                        helper_text=(
                            "If you have a valid, unexpired license from another U.S. state, "
                            "your case may switch to an out-of-state transfer with exam waivers."
                        ),
                    ),
                    IntakeField(
                        "owns_vehicle",
                        "Do you own a vehicle?",
                        "choice",
                        YES_NO,
                        description="If yes, expect proof of insurance to be required.",
                    ),
                ),
            ),
            _step(
                "documents",
                "Your documents",
                "Pick the documents you actually have. You will see what counts in each panel.",
                document_categories=("identity", "social_security", "residency", "lawful_presence"),
            ),
            _step(
                "extras",
                "Extra requirements",
                "A couple of last details specific to first-time adult applications.",
                fields=(
                    IntakeField(
                        "adult_driver_education_status",
                        "Adult driver education status",
                        "choice",
                        ["Not sure", "Completed", "In progress", "Not started"],
                        helper_title="Who needs this?",
                        helper_text=(
                            "Adult driver education is required for first-time applicants between 18 and 24. "
                            "Applicants 25 or older are not required to take it."
                        ),
                    ),
                ),
            ),
            _step(
                "review",
                "Review and check",
                "Review what you provided. When you continue, the rules engine runs once.",
                summary_kind="review",
            ),
        ),
    ),
    "transfer": IntakeScenario(
        key="transfer",
        label="Out-of-state transfer",
        description="New Texas resident transferring an out-of-state license.",
        steps=(
            _step(
                "about",
                "About your case",
                "A few facts about you and your out-of-state license.",
                fields=(
                    IntakeField("age", "Your age", "number"),
                    IntakeField(
                        "new_texas_resident",
                        "Are you a new Texas resident?",
                        "choice",
                        YES_NO,
                    ),
                    IntakeField(
                        "has_out_of_state_license",
                        "Do you have an out-of-state license?",
                        "choice",
                        YES_NO,
                    ),
                    IntakeField(
                        "out_of_state_license_valid",
                        "Is the out-of-state license valid (not suspended or revoked)?",
                        "choice",
                        YES_NO_UNKNOWN,
                    ),
                    IntakeField(
                        "out_of_state_license_unexpired",
                        "Is the out-of-state license unexpired?",
                        "choice",
                        YES_NO_UNKNOWN,
                        helper_title="Why this matters",
                        helper_text=(
                            "A valid, unexpired out-of-state license usually qualifies for "
                            "knowledge and skills exam waivers and the 30-day Texas residency "
                            "duration waiver."
                        ),
                    ),
                ),
            ),
            _step(
                "documents",
                "Your documents",
                "Identity, residency, Social Security, and lawful-presence documents for the transfer.",
                document_categories=("identity", "social_security", "residency", "lawful_presence"),
            ),
            _step(
                "extras",
                "Vehicle and insurance",
                "Details about any vehicle you brought to Texas.",
                fields=(
                    IntakeField("owns_vehicle", "Do you own a vehicle in Texas?", "choice", YES_NO),
                    IntakeField(
                        "has_proof_of_insurance",
                        "Do you have proof of Texas auto insurance for each owned vehicle?",
                        "choice",
                        YES_NO_UNKNOWN,
                        helper_title="Why this matters",
                        helper_text=(
                            "Texas requires proof of insurance for every vehicle you own. If you don't "
                            "own a vehicle, the rules use a no-vehicle statement instead."
                        ),
                    ),
                    IntakeField(
                        "has_texas_vehicle_registration",
                        "Is each vehicle registered in Texas?",
                        "choice",
                        YES_NO_UNKNOWN,
                    ),
                ),
            ),
            _step(
                "review",
                "Review and check",
                "Review what you provided. Continue to run the rules engine once.",
                summary_kind="review",
            ),
        ),
    ),
    "renewal": IntakeScenario(
        key="renewal",
        label="Renewal",
        description="Renewing an existing Texas driver license.",
        steps=(
            _step(
                "about",
                "About your renewal",
                "Quick facts about your current Texas license and timing.",
                fields=(
                    IntakeField(
                        "has_texas_license",
                        "Do you currently hold a Texas driver license?",
                        "choice",
                        YES_NO,
                    ),
                    IntakeField(
                        "renewal_timing",
                        "Renewal timing or expiration status",
                        "choice",
                        [
                            "Not sure",
                            "Expires within two years",
                            "Expired less than two years ago",
                            "Expired more than two years ago",
                            "Outside the renewal window",
                        ],
                        helper_title="Why this matters",
                        helper_text=(
                            "Texas DPS allows renewal up to two years before or after expiration. "
                            "If your license expired more than two years ago you cannot renew normally."
                        ),
                    ),
                    IntakeField("age", "Your age", "number"),
                ),
            ),
            _step(
                "extras",
                "Online renewal eligibility",
                "These help determine whether online renewal may be available.",
                fields=(
                    IntakeField(
                        "last_renewed_in_person",
                        "Was your last renewal done in person at a Texas DPS office?",
                        "choice",
                        YES_NO_UNKNOWN,
                    ),
                    IntakeField(
                        "license_valid_status",
                        "Is your current Texas license valid (not suspended or revoked)?",
                        "choice",
                        YES_NO_UNKNOWN,
                    ),
                    IntakeField(
                        "renewal_lawful_presence_status",
                        "What is your citizenship or lawful-presence status?",
                        "choice",
                        [
                            "Not sure",
                            "U.S. citizen",
                            "Lawful permanent resident / green card holder",
                            "Other lawful-presence category",
                            "No lawful-presence category",
                        ],
                        helper_title="Why this matters",
                        helper_text=(
                            "Online renewal eligibility should account for a known U.S. citizenship "
                            "or lawful-presence category, not only U.S. citizenship."
                        ),
                    ),
                    IntakeField(
                        "ssn_on_record",
                        "Is your Social Security number already on record with Texas DPS?",
                        "choice",
                        YES_NO_UNKNOWN,
                    ),
                    IntakeField(
                        "health_conditions_unchanged",
                        "Have your medical or health conditions stayed the same?",
                        "choice",
                        YES_NO_UNKNOWN,
                    ),
                    IntakeField(
                        "no_outstanding_tickets_or_warrants",
                        "Are you free of outstanding tickets, warrants, or license issues?",
                        "choice",
                        YES_NO_UNKNOWN,
                    ),
                ),
            ),
            _step(
                "review",
                "Review and check",
                "Review what you provided. Continue to run the rules engine once.",
                summary_kind="review",
            ),
        ),
    ),
    "replacement": IntakeScenario(
        key="replacement",
        label="Replacement",
        description="Replacing a lost, stolen, or damaged Texas license.",
        steps=(
            _step(
                "about",
                "About your replacement",
                "Tell me what happened and whether anything on the card needs to change.",
                fields=(
                    IntakeField(
                        "replacement_reason",
                        "Reason for replacement",
                        "choice",
                        ["Lost", "Stolen", "Damaged"],
                    ),
                    IntakeField(
                        "license_stolen_and_fraud_used",
                        "If stolen, has it been used fraudulently?",
                        "choice",
                        YES_NO_UNKNOWN,
                        helper_title="Why this matters",
                        helper_text=(
                            "If a stolen license is being used fraudulently, file a police report. "
                            "Some replacement paths may require an in-person visit."
                        ),
                    ),
                    IntakeField(
                        "front_card_changed",
                        "Does any printed information on the front need to change (name, address)?",
                        "choice",
                        YES_NO_UNKNOWN,
                    ),
                ),
            ),
            _step(
                "extras",
                "Online replacement eligibility",
                "Online replacement requires you to know specific details from your card.",
                fields=(
                    IntakeField(
                        "has_card_number",
                        "Do you have your card number?",
                        "choice",
                        YES_NO_UNKNOWN,
                    ),
                    IntakeField(
                        "has_date_of_birth_for_online",
                        "Do you have your date of birth available?",
                        "choice",
                        YES_NO_UNKNOWN,
                    ),
                    IntakeField(
                        "has_last4_ssn",
                        "Do you have the last 4 digits of your SSN?",
                        "choice",
                        YES_NO_UNKNOWN,
                    ),
                    IntakeField(
                        "has_audit_number",
                        "Do you have the audit number from your most recent card?",
                        "choice",
                        YES_NO_UNKNOWN,
                    ),
                ),
            ),
            _step(
                "documents",
                "Documents for in-person replacement",
                (
                    "If online replacement is not available, Texas DPS may ask for identity, "
                    "Social Security, and citizenship or lawful-presence proof."
                ),
                document_categories=("identity", "social_security", "lawful_presence"),
            ),
            _step(
                "review",
                "Review and check",
                "Review what you provided. Continue to run the rules engine once.",
                summary_kind="review",
            ),
        ),
    ),
    "change_info": IntakeScenario(
        key="change_info",
        label="Change address or name",
        description="Changing address or name on an existing Texas license.",
        steps=(
            _step(
                "about",
                "About your change",
                "Pick what's changing and confirm your current license.",
                fields=(
                    IntakeField(
                        "change_kind",
                        "What needs to change?",
                        "choice",
                        ["Address", "Name", "Address and name"],
                    ),
                    IntakeField(
                        "has_texas_license",
                        "Do you currently hold a Texas driver license?",
                        "choice",
                        YES_NO,
                    ),
                ),
            ),
            _step(
                "extras",
                "Online eligibility",
                "Online changes require specific identifiers.",
                fields=(
                    IntakeField("has_card_number", "Do you have your card number?", "choice", YES_NO_UNKNOWN),
                    IntakeField("has_date_of_birth_for_online", "Date of birth available?", "choice", YES_NO_UNKNOWN),
                    IntakeField("has_last4_ssn", "Last 4 digits of SSN available?", "choice", YES_NO_UNKNOWN),
                    IntakeField("has_audit_number", "Audit number available?", "choice", YES_NO_UNKNOWN),
                ),
            ),
            _step(
                "documents",
                "Documents for non-online changes",
                (
                    "If the change cannot be handled online, Texas DPS may ask for identity, "
                    "Social Security, and citizenship or lawful-presence proof."
                ),
                document_categories=("identity", "social_security", "lawful_presence"),
            ),
            _step(
                "review",
                "Review and check",
                "Review what you provided. Continue to run the rules engine once.",
                summary_kind="review",
            ),
        ),
    ),
}


GOAL_TO_SCENARIO = {
    "first_time": "first_time",
    "first_time_application": "first_time",
    "transfer": "transfer",
    "out_of_state_transfer": "transfer",
    "renewal": "renewal",
    "replacement": "replacement",
    "change_info": "change_info",
}


def scenario_from_facts(facts: FactState) -> str | None:
    """Return the best intake scenario key from known facts."""

    if facts.goal in GOAL_TO_SCENARIO:
        return GOAL_TO_SCENARIO[facts.goal or ""]
    if facts.new_texas_resident or facts.has_out_of_state_license:
        return "transfer"
    if facts.license_lost_stolen_damaged:
        return "replacement"
    if facts.address_change_requested or facts.name_change_requested:
        return "change_info"
    if facts.renewal_timing or facts.has_texas_license:
        return "renewal"
    return None


def steps_for(scenario_key: str) -> tuple[IntakeStep, ...]:
    """Return the configured steps for a scenario."""

    return SCENARIOS[scenario_key].steps


def step_count(scenario_key: str) -> int:
    return len(SCENARIOS[scenario_key].steps)


def facts_from_intake(scenario_key: str, values: dict[str, Any]) -> FactState:
    """Map submitted form values into canonical facts for s(CASP).

    ``values`` is a flat mapping that may include both classic IntakeField keys
    and document-category overrides shaped as ``{"<category_key>__has": True}``
    or ``{"<category_key>__details": "selected items"}``.
    """

    facts = FactState(goal=_goal_for_scenario(scenario_key))

    if scenario_key in {"first_time", "transfer"}:
        facts.applying_texas_license = True
    if scenario_key == "transfer":
        facts.new_texas_resident = True
    if scenario_key in {"renewal", "replacement", "change_info"}:
        facts.has_texas_license = True
    if scenario_key in {"replacement", "change_info"}:
        facts.license_lost_stolen_damaged = scenario_key == "replacement"

    for key, value in values.items():
        if key == "age":
            facts.age = int(value) if value not in (None, "") else None
        elif key == "renewal_timing":
            facts.renewal_timing = _renewal_timing(value)
        elif key == "adult_driver_education_status":
            facts.adult_driver_education_status = _education_status(value)
        elif key == "replacement_reason":
            facts.license_lost_stolen_damaged = True
            if not isinstance(values.get("license_stolen_and_fraud_used"), str):
                facts.license_stolen_and_fraud_used = None
        elif key == "change_kind":
            facts.front_card_changed = True
            facts.address_change_requested = value in {"Address", "Address and name"}
            facts.name_change_requested = value in {"Name", "Address and name"}
        elif key == "applying_first_texas":
            if value == "Yes":
                facts.applying_texas_license = True
                facts.has_texas_license = False
            elif value == "No":
                facts.has_texas_license = True
        elif key == "renewal_lawful_presence_status":
            _apply_renewal_lawful_presence_status(facts, value)
        elif key.endswith("__has"):
            category_key = key[: -len("__has")]
            cat = DOCUMENT_CATEGORIES.get(category_key)
            if cat:
                _apply_category_status(facts, cat.fact_field, value)
        elif key == "lawful_presence_choice":
            _apply_lawful_presence_choice(facts, value)
        elif hasattr(facts, key):
            setattr(facts, key, _choice_to_bool(value))

    if scenario_key == "first_time":
        if facts.has_out_of_state_license is None:
            facts.has_out_of_state_license = False
        if facts.has_texas_license is None:
            facts.has_texas_license = False
    if scenario_key == "change_info":
        facts.front_card_changed = True

    facts.source_notes = [f"guided intake: {SCENARIOS[scenario_key].label}"]
    return facts


SCENARIO_FIELD_DEFAULTS: dict[str, dict[str, str]] = {
    "first_time": {
        "has_out_of_state_license": "No",
        "owns_vehicle": "No",
        "applying_first_texas": "Yes",
    },
    "transfer": {
        "new_texas_resident": "Yes",
        "has_out_of_state_license": "Yes",
        "owns_vehicle": "Yes",
    },
    "renewal": {
        "has_texas_license": "Yes",
    },
    "replacement": {
        "replacement_reason": "Lost",
    },
    "change_info": {
        "has_texas_license": "Yes",
    },
}


def intake_defaults(scenario_key: str, facts: FactState) -> dict[str, Any]:
    """Return form defaults based on already extracted facts."""

    defaults: dict[str, Any] = {}
    scenario_overrides = SCENARIO_FIELD_DEFAULTS.get(scenario_key, {})
    for field_def in SCENARIOS[scenario_key].fields:
        if field_def.key == "age":
            defaults[field_def.key] = facts.age or 18
        elif field_def.key == "renewal_timing":
            defaults[field_def.key] = _renewal_timing_label(facts.renewal_timing)
        elif field_def.key == "adult_driver_education_status":
            defaults[field_def.key] = _education_status_label(facts.adult_driver_education_status)
        elif field_def.key == "replacement_reason":
            defaults[field_def.key] = scenario_overrides.get(field_def.key, "Lost")
        elif field_def.key == "applying_first_texas":
            if facts.has_texas_license is True:
                defaults[field_def.key] = "No"
            elif facts.has_texas_license is False or facts.applying_texas_license:
                defaults[field_def.key] = "Yes"
            else:
                defaults[field_def.key] = scenario_overrides.get(field_def.key, "Yes")
        elif field_def.key == "change_kind":
            if facts.address_change_requested and facts.name_change_requested:
                defaults[field_def.key] = "Address and name"
            elif facts.name_change_requested:
                defaults[field_def.key] = "Name"
            else:
                defaults[field_def.key] = "Address"
        elif field_def.key == "renewal_lawful_presence_status":
            defaults[field_def.key] = _renewal_lawful_presence_status_label(facts)
        elif hasattr(facts, field_def.key):
            value = getattr(facts, field_def.key)
            options = field_def.options or YES_NO_UNKNOWN
            if value is None and field_def.key in scenario_overrides:
                fallback = scenario_overrides[field_def.key]
                if fallback in options:
                    defaults[field_def.key] = fallback
                    continue
            defaults[field_def.key] = _bool_to_choice(value, options)
    return defaults


def apply_document_selections(facts: FactState, selections: DocumentSelections) -> FactState:
    """Mirror DocumentSelections into the FactState booleans s(CASP) reads."""

    for category_key, category in DOCUMENT_CATEGORIES.items():
        if category_key == "lawful_presence":
            _apply_lawful_presence_choice(facts, selections.lawful_presence_choice)
            continue
        if category_key == "driver_education":
            picks = selections.selected.get(category_key, [])
            if picks:
                facts.adult_driver_education_status = _education_from_option(picks[0])
            continue
        unsure = selections.unsure.get(category_key, False)
        none = selections.none.get(category_key, False)
        if unsure and none:
            unsure = False
        has_specific = selections.has_specific_selection(category_key)
        specific_count = len(selections.selected.get(category_key, []))
        if selections.other_text.get(category_key, "").strip():
            specific_count += 1

        target_field = category.fact_field
        if not hasattr(facts, target_field):
            continue
        if unsure:
            if category_key == "residency":
                facts.texas_residency_doc_count = None
            setattr(facts, target_field, None)
        elif none:
            if category_key == "residency":
                facts.texas_residency_doc_count = 0
            setattr(facts, target_field, False)
        elif category_key == "residency" and specific_count:
            facts.texas_residency_doc_count = specific_count
            facts.has_texas_residency_docs = specific_count >= 2
        elif has_specific:
            setattr(facts, target_field, True)

    return facts


def _apply_lawful_presence_choice(facts: FactState, value: str | None) -> None:
    if not value:
        return
    if value == "us_citizen":
        facts.us_citizen = True
        facts.lawful_presence_category_known = True
    elif value == "not_sure":
        facts.lawful_presence_category_known = None
    else:
        facts.us_citizen = False if facts.us_citizen is None else facts.us_citizen
        facts.lawful_presence_category_known = True


def _apply_renewal_lawful_presence_status(facts: FactState, value: str | None) -> None:
    if value == "U.S. citizen":
        facts.us_citizen = True
        facts.lawful_presence_category_known = True
    elif value in {"Lawful permanent resident / green card holder", "Other lawful-presence category"}:
        facts.us_citizen = False
        facts.lawful_presence_category_known = True
    elif value == "No lawful-presence category":
        facts.us_citizen = False
        facts.lawful_presence_category_known = False
    else:
        facts.us_citizen = None
        facts.lawful_presence_category_known = None


def _renewal_lawful_presence_status_label(facts: FactState) -> str:
    if facts.us_citizen is True:
        return "U.S. citizen"
    if facts.lawful_presence_category_known is True:
        return "Other lawful-presence category"
    if facts.lawful_presence_category_known is False:
        return "No lawful-presence category"
    return "Not sure"


def _apply_category_status(facts: FactState, fact_field: str, value: Any) -> None:
    if not hasattr(facts, fact_field):
        return
    if value == "Yes" or value is True:
        setattr(facts, fact_field, True)
    elif value == "No" or value is False:
        setattr(facts, fact_field, False)
    else:
        setattr(facts, fact_field, None)


def _goal_for_scenario(scenario_key: str) -> str:
    return "replacement" if scenario_key == "change_info" else scenario_key


def _choice_to_bool(value: Any) -> bool | None:
    if value == "Yes":
        return True
    if value == "No":
        return False
    return None


def _bool_to_choice(value: bool | None, options: list[str]) -> str:
    if value is True and "Yes" in options:
        return "Yes"
    if value is False and "No" in options:
        return "No"
    return options[0]


def _renewal_timing(value: str | None) -> str | None:
    return {
        "Expires within two years": "within_window",
        "Expired less than two years ago": "within_window",
        "Expired more than two years ago": "outside_window",
        "Outside the renewal window": "outside_window",
        "Outside renewal window": "outside_window",
    }.get(value or "")


def _renewal_timing_label(value: str | None) -> str:
    if value in {"within_window", "within_two_years_before", "expires_within_two_years", "expired_less_than_two_years"}:
        return "Expires within two years"
    if value in {"outside_window", "expired_more_than_two_years"}:
        return "Expired more than two years ago"
    return "Not sure"


def _education_status(value: str | None) -> str | None:
    if value in {"Yes", "Completed"}:
        return "completed"
    if value in {"No", "Not started"}:
        return "not_completed"
    if value == "In progress":
        return "in_progress"
    return None


def _education_status_label(value: str | None) -> str:
    return {
        "completed": "Completed",
        "not_completed": "Not started",
        "in_progress": "In progress",
    }.get(value or "", "Not sure")


def _education_from_option(option_key: str) -> str | None:
    return {
        "adult_de_completed": "completed",
        "adult_de_in_progress": "in_progress",
        "adult_de_not_started": "not_completed",
    }.get(option_key)
