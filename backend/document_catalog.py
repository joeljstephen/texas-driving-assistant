"""Curated catalog of common Texas driver license document categories.

This catalog provides UI-friendly content for guided document selectors.
The goal is to give users concrete examples and helper context instead of
asking vague yes/no questions. The category-level boolean still feeds the
s(CASP) reasoning layer (e.g. ``has_identity_doc``); the specific document
selections are used to personalize the report.

Texas DPS publishes the official document lists. Every entry below is a
category-level planning aid, not a substitute for the live DPS rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DocumentOption:
    """One selectable document example inside a category."""

    key: str
    label: str
    group: str = ""


@dataclass(frozen=True)
class DocumentCategory:
    """A curated document group (identity, residency, etc.)."""

    key: str
    title: str
    summary: str
    fact_field: str
    helper_title: str
    helper_text: str
    options: list[DocumentOption] = field(default_factory=list)
    note: str = ""
    allow_other: bool = True
    allow_unsure: bool = True
    multi_select: bool = True


IDENTITY_OPTIONS: list[DocumentOption] = [
    DocumentOption("us_passport", "U.S. passport (book or card)", "Primary"),
    DocumentOption("us_birth_certificate", "Certified U.S. birth certificate", "Primary"),
    DocumentOption("certificate_of_citizenship", "Certificate of U.S. citizenship (N-560 / N-561)", "Primary"),
    DocumentOption("certificate_of_naturalization", "Certificate of naturalization (N-550 / N-570)", "Primary"),
    DocumentOption("permanent_resident_card", "Permanent resident card (Form I-551 / green card)", "Primary"),
    DocumentOption("us_military_id", "U.S. military ID or dependent ID", "Secondary"),
    DocumentOption("out_of_state_license", "Current out-of-state driver license or state ID", "Secondary"),
    DocumentOption("foreign_passport_with_i94", "Unexpired foreign passport with valid I-94", "Secondary"),
    DocumentOption("employment_authorization", "Employment authorization card (Form I-766)", "Secondary"),
    DocumentOption("school_id_with_records", "U.S. school ID with school records", "Supporting"),
    DocumentOption("social_security_card_id", "Social Security card", "Supporting"),
    DocumentOption("medicare_or_medicaid_card", "Medicare or Medicaid card", "Supporting"),
]


RESIDENCY_OPTIONS: list[DocumentOption] = [
    DocumentOption("texas_lease_or_mortgage", "Current Texas lease, deed, or mortgage statement"),
    DocumentOption("texas_utility_bill", "Texas utility bill (electric, gas, water, internet)"),
    DocumentOption("texas_bank_statement", "Recent bank or credit card statement with Texas address"),
    DocumentOption("texas_voter_registration", "Texas voter registration card"),
    DocumentOption("texas_vehicle_registration_doc", "Current Texas vehicle registration or title"),
    DocumentOption("texas_insurance_policy", "Current Texas auto, home, or renters insurance policy"),
    DocumentOption("texas_employer_letter", "Employer or school document on letterhead"),
    DocumentOption("texas_w2_or_paystub", "W-2 or pay stub with Texas address"),
    DocumentOption("texas_government_mail", "Recent government mail addressed to your Texas address"),
    DocumentOption("texas_school_records", "Texas school records or transcripts"),
]


SOCIAL_SECURITY_OPTIONS: list[DocumentOption] = [
    DocumentOption("ssn_card", "Social Security card"),
    DocumentOption("w2_form", "W-2 showing your full SSN"),
    DocumentOption("ssa_1099", "SSA-1099 or non-SSA-1099"),
    DocumentOption("paystub_with_ssn", "Pay stub showing your name and SSN"),
    DocumentOption("knows_ssn_only", "I know my SSN but do not have a document"),
    DocumentOption("not_eligible_for_ssn", "I am not eligible for an SSN"),
]


LAWFUL_PRESENCE_OPTIONS: list[DocumentOption] = [
    DocumentOption("us_citizen", "U.S. citizen"),
    DocumentOption("permanent_resident", "Lawful permanent resident (green card)"),
    DocumentOption("conditional_resident", "Conditional permanent resident"),
    DocumentOption("asylee_or_refugee", "Asylee or refugee"),
    DocumentOption("visa_holder_with_i94", "Nonimmigrant with valid visa and I-94"),
    DocumentOption("employment_authorization_holder", "Employment authorization (Form I-766) holder"),
    DocumentOption("daca_recipient", "DACA recipient (deferred action)"),
    DocumentOption("other_lawful_presence", "Other lawful presence category"),
]


DRIVER_EDUCATION_OPTIONS: list[DocumentOption] = [
    DocumentOption("adult_de_completed", "Six-hour adult driver education completed"),
    DocumentOption("adult_de_in_progress", "Adult driver education in progress"),
    DocumentOption("adult_de_not_started", "Adult driver education not started"),
]


DOCUMENT_CATEGORIES: dict[str, DocumentCategory] = {
    "identity": DocumentCategory(
        key="identity",
        title="Proof of identity",
        summary=(
            "Identity documents prove who you are. Texas DPS uses primary, secondary, "
            "and supporting categories. One primary document is usually enough."
        ),
        fact_field="has_identity_doc",
        helper_title="What counts as proof of identity?",
        helper_text=(
            "Texas DPS recognizes three groups: primary documents (passport, U.S. birth "
            "certificate, citizenship/naturalization certificates, permanent resident "
            "card), secondary documents (military ID, out-of-state license, foreign "
            "passport with valid I-94), and supporting documents (school ID, Social "
            "Security card, Medicare/Medicaid card). Combinations may be required when "
            "no primary document is available. Always confirm the latest list at "
            "Texas DPS."
        ),
        note="Pick everything you can show. One primary document is usually enough on its own.",
        options=IDENTITY_OPTIONS,
    ),
    "residency": DocumentCategory(
        key="residency",
        title="Texas residency documents",
        summary=(
            "Texas DPS generally requires two different documents that show your "
            "Texas residential address. New Texas residents may also need to meet a "
            "30-day duration rule for non-transfer paths."
        ),
        fact_field="has_texas_residency_docs",
        helper_title="What counts as Texas residency?",
        helper_text=(
            "Acceptable documents typically include a Texas lease, mortgage, or deed; "
            "utility bills; bank or credit card statements; voter registration; "
            "vehicle registration or insurance; employer or school letters on "
            "letterhead; W-2 or pay stubs; recent government mail. Two different "
            "documents from different sources are usually required, and many must be "
            "less than 90 days old. The 30-day duration rule may not apply to a valid, "
            "unexpired out-of-state transfer."
        ),
        note="Pick at least two different document types from different sources when possible.",
        options=RESIDENCY_OPTIONS,
    ),
    "social_security": DocumentCategory(
        key="social_security",
        title="Social Security",
        summary=(
            "You usually need to provide proof of your Social Security number. If you "
            "are not eligible for an SSN, Texas DPS has an alternative process."
        ),
        fact_field="has_social_security",
        helper_title="What counts as Social Security proof?",
        helper_text=(
            "Common acceptance includes the Social Security card itself, a W-2, an "
            "SSA-1099, a non-SSA-1099, or a pay stub showing your full or partial SSN. "
            "If you are not eligible for an SSN, Texas DPS may instead accept a signed "
            "statement and additional supporting documentation."
        ),
        note="Selecting 'I know my SSN but do not have a document' still helps the assistant.",
        options=SOCIAL_SECURITY_OPTIONS,
        allow_other=False,
    ),
    "lawful_presence": DocumentCategory(
        key="lawful_presence",
        title="Citizenship or lawful presence",
        summary=(
            "Texas DPS requires proof of U.S. citizenship or lawful presence. The "
            "category you fall into determines which documents are accepted."
        ),
        fact_field="lawful_presence_category_known",
        helper_title="What counts as lawful presence?",
        helper_text=(
            "U.S. citizens can usually rely on a passport, U.S. birth certificate, or "
            "naturalization/citizenship certificate. Lawful permanent residents use a "
            "permanent resident card. Other lawful-presence categories include "
            "asylees, refugees, visa holders with a valid I-94, employment "
            "authorization (I-766) holders, and DACA recipients. The exact category "
            "drives which documents and license expiration rules apply."
        ),
        note="Pick the option that best matches your status. The assistant uses the category, not specific identifiers.",
        options=LAWFUL_PRESENCE_OPTIONS,
        allow_other=False,
        multi_select=False,
    ),
    "driver_education": DocumentCategory(
        key="driver_education",
        title="Adult driver education",
        summary=(
            "First-time applicants 18–24 must complete a six-hour adult driver "
            "education course before applying."
        ),
        fact_field="adult_driver_education_status",
        helper_title="What counts as adult driver education?",
        helper_text=(
            "Adult driver education is a Texas-approved six-hour course for "
            "applicants between 18 and 24 years old. It can be taken online or in "
            "the classroom and must be completed before the first-time application."
        ),
        note="If you are 25 or older, this requirement does not apply.",
        options=DRIVER_EDUCATION_OPTIONS,
        allow_other=False,
        allow_unsure=True,
        multi_select=False,
    ),
}


def category(key: str) -> DocumentCategory:
    """Return a document category descriptor by key."""

    return DOCUMENT_CATEGORIES[key]


def option_label(category_key: str, option_key: str) -> str:
    """Return the human label for a stored option key."""

    cat = DOCUMENT_CATEGORIES.get(category_key)
    if not cat:
        return option_key.replace("_", " ").title()
    for option in cat.options:
        if option.key == option_key:
            return option.label
    return option_key.replace("_", " ").title()
