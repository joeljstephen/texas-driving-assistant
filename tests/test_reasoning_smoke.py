import shutil

import pytest

from backend.models import FactState
from backend.scasp_runner import ScaspRunner


pytestmark = pytest.mark.skipif(shutil.which("scasp") is None, reason="scasp executable is not installed")


def test_scasp_runner_smoke_classifies_transfer():
    facts = FactState(
        goal="transfer",
        age=22,
        new_texas_resident=True,
        has_out_of_state_license=True,
        out_of_state_license_valid=True,
        out_of_state_license_unexpired=True,
    )

    result = ScaspRunner().run(facts)

    assert result.error is None
    assert result.case_type == "out_of_state_transfer"
    assert "in_person" in result.service_modes
    assert "residency_30_day_duration_waived" in result.waivers

