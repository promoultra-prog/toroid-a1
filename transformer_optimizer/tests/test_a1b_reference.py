import os
from pathlib import Path
import shutil

import pytest

from transformer_optimizer.simulation.a1b_reference import (
    A1BReferenceCase, A1BReferenceRunner, SOURCE_SHA256,
    reference_matrix, render_reference_deck
)


def test_a1b_reference_deck_contract(tmp_path):
    case = A1BReferenceCase("a1b_230_idle_typ", 230)
    text = render_reference_deck(case)
    assert ".include lib/psu_main.inc" in text
    assert ".include lib/aux_supply.inc" in text
    assert "VMAIN=23.1 VAUX=16 CRES=0.033 CAP_ESR=0.006" in text
    assert "BLP VCC 0 I={1.5*tanh" in text
    assert "tran 5u .6 0 5u uic" in text
    assert "@d.xpsu.d1[id]" in text and "i(l.xpsu.lbpesl)" in text
    assert case.bypass_time_s == pytest.approx((7 + 189 / 360) / 50)
    matrix = reference_matrix()
    assert len(matrix) == 8
    assert {case.mains_v for case in matrix} == {200, 230, 240, 253}
    with pytest.raises(ValueError, match="inside A1-B"):
        A1BReferenceRunner(tmp_path, tmp_path / "outputs", executable="ngspice")
    with pytest.raises(ValueError, match="changed"):
        root = tmp_path / "a1b"
        for relative in SOURCE_SHA256:
            source = root / relative
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text("not the pinned source")
        A1BReferenceRunner(root, tmp_path / "output", executable="ngspice").stage_sources()


@pytest.mark.skipif(not os.environ.get("A1B_ROOT") or shutil.which("ngspice") is None,
                    reason="Set A1B_ROOT and install ngspice for local reference integration")
def test_a1b_reference_matches_published_psu(tmp_path):
    root = Path(os.environ["A1B_ROOT"])
    result = A1BReferenceRunner(root, tmp_path).run(
        A1BReferenceCase("a1b_230_idle_typ", 230))
    assert result.main_rail_min_v["positive"] == pytest.approx(29.29, abs=.03)
    assert result.main_rail_ripple_vpp["positive"] == pytest.approx(.345, abs=.01)
    assert result.primary_irms_a == pytest.approx(153.1 / 230, rel=.02)
    assert result.winding_irms_a["MAIN1"] > 1.5
    assert result.bridge_steady_peak_a["D1"] < result.bridge_peak_a["D1"]
    assert result.main_rails_settled and not result.physical_validation_complete
    assert (tmp_path / "a1b_230_idle_typ.cir").is_file()
    assert (tmp_path / "a1b_230_idle_typ_startup.png").is_file()
