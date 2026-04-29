from backend.document_catalog import DOCUMENT_CATEGORIES, option_label
from backend.intake import apply_document_selections, facts_from_intake
from backend.models import DocumentSelections


def test_catalog_has_expected_categories_and_options():
    expected = {"identity", "residency", "social_security", "lawful_presence", "driver_education"}
    assert expected.issubset(DOCUMENT_CATEGORIES.keys())
    for category in DOCUMENT_CATEGORIES.values():
        assert category.title
        assert category.summary
        assert category.helper_text
        assert category.options, f"category {category.key} has no options"


def test_option_label_returns_label_or_falls_back():
    assert option_label("identity", "us_passport") == "U.S. passport (book or card)"
    assert option_label("identity", "unknown_key").lower().startswith("unknown")
    assert option_label("nonexistent", "some_value")


def test_apply_selections_marks_category_true_when_picked():
    facts = facts_from_intake("first_time", {"age": 24, "applying_first_texas": "Yes"})
    selections = DocumentSelections(
        selected={
            "identity": ["us_passport"],
            "residency": ["texas_lease_or_mortgage", "texas_utility_bill"],
            "social_security": ["ssn_card"],
        },
        lawful_presence_choice="us_citizen",
    )

    facts = apply_document_selections(facts, selections)

    assert facts.has_identity_doc is True
    assert facts.has_texas_residency_docs is True
    assert facts.has_social_security is True
    assert facts.lawful_presence_category_known is True
    assert facts.us_citizen is True


def test_one_residency_selection_does_not_satisfy_two_document_requirement():
    facts = facts_from_intake("first_time", {"age": 24, "applying_first_texas": "Yes"})
    selections = DocumentSelections(selected={"residency": ["texas_utility_bill"]})

    facts = apply_document_selections(facts, selections)

    assert facts.texas_residency_doc_count == 1
    assert facts.has_texas_residency_docs is False


def test_apply_selections_unsure_keeps_category_unknown():
    facts = facts_from_intake("first_time", {"age": 30, "applying_first_texas": "Yes"})
    selections = DocumentSelections(
        unsure={"identity": True},
    )

    facts = apply_document_selections(facts, selections)

    assert facts.has_identity_doc is None


def test_apply_selections_none_marks_category_false():
    facts = facts_from_intake("first_time", {"age": 30, "applying_first_texas": "Yes"})
    selections = DocumentSelections(
        none={"residency": True},
    )

    facts = apply_document_selections(facts, selections)

    assert facts.has_texas_residency_docs is False


def test_lawful_presence_choice_other_marks_category_known():
    facts = facts_from_intake("transfer", {"age": 28, "new_texas_resident": "Yes"})
    selections = DocumentSelections(lawful_presence_choice="permanent_resident")

    facts = apply_document_selections(facts, selections)

    assert facts.lawful_presence_category_known is True
    assert facts.us_citizen is False
