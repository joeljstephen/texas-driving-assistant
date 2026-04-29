from backend.case_detection import case_label, detect_case
from backend.intake import SCENARIOS


def test_detect_case_first_time_from_natural_language():
    detection = detect_case("I am applying for my first Texas driver license", use_gemini=False)
    assert detection.scenario_key == "first_time"
    assert detection.facts.applying_texas_license is True
    assert detection.detected
    assert "first" in detection.message.lower()


def test_detect_case_transfer_from_oklahoma():
    detection = detect_case("I moved to Texas with an Oklahoma license", use_gemini=False)
    assert detection.scenario_key == "transfer"
    assert detection.facts.has_out_of_state_license is True


def test_detect_case_renewal():
    detection = detect_case("I want to renew my Texas license. It expires soon.", use_gemini=False)
    assert detection.scenario_key == "renewal"
    assert detection.facts.renewal_timing == "within_window"


def test_detect_case_replacement():
    detection = detect_case("I lost my Texas license and need a replacement", use_gemini=False)
    assert detection.scenario_key == "replacement"


def test_case_label_returns_human_text():
    for key in SCENARIOS:
        label = case_label(key)
        assert label
        assert label != key
    assert "not yet" in case_label(None).lower()
