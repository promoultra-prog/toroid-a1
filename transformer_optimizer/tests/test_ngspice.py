import shutil
from dataclasses import replace
import pytest
import numpy as np
from transformer_optimizer import (
    ToroidalCore, RoundWire, WindingWire, TransformerCandidate, ToroidalTransformerModel, SecondarySpec
)
from transformer_optimizer.simulation.ngspice import (
    BHCurve, NgSpiceConfig, NgSpiceRunner, NgSpiceTransformerDeck, RectifierLoad
)
from transformer_optimizer.optimize.pareto import OptimizationResult
from transformer_optimizer.reports.ngspice import with_ngspice_results
from transformer_optimizer.simulation.ngspice.parser import _window
from transformer_optimizer.physics.core_loss import CoreLossDataQuality, TabulatedCoreLoss
from transformer_optimizer.integrations.openmagnetics.material_adapter import LossPoint


def _deck(spec, material, mode="linear"):
    if mode == "nonlinear":
        spec = replace(spec, secondaries=(SecondarySpec(35, 7),))
    core = ToroidalCore(.16, .08, .06, .95, material.density, material)
    candidate = TransformerCandidate(core, 1.2,
        WindingWire(RoundWire(.0015, .00162)),
        WindingWire(RoundWire(.0025, .0027), 2))
    evaluation = ToroidalTransformerModel().evaluate(spec, candidate)
    assert evaluation.valid, evaluation.violations
    # Synthetic, reversible B-H samples used only to test XSPICE syntax.
    curve = BHCurve((-5000, -3000, -1500, -600, 0, 600, 1500, 3000, 5000),
                    (-1.8, -1.7, -1.55, -1.3, 0, 1.3, 1.55, 1.7, 1.8))
    config = NgSpiceConfig(loads=tuple(RectifierLoad(.01, 12) for _ in spec.expanded_secondaries),
                           mode=mode, bh_curve=curve if mode == "nonlinear" else None,
                           cycles=40, measurement_cycles=3, samples_per_cycle=150)
    return NgSpiceTransformerDeck.from_candidate(spec, candidate, evaluation, config)


def test_deck_contract(spec, material):
    deck = _deck(spec, material)
    text = deck.render()
    assert "KALL LPRI LSEC1 LSEC2" in text
    assert "D1A" in text and "D2D" in text
    assert "RLOAD1" in text and "CRES2" in text
    assert f"RLOAD1 rail1 0 {deck.config.no_load_resistance_ohm:.12g}" in deck.render(no_load=True)
    high_line = NgSpiceTransformerDeck.from_candidate(
        spec, deck.candidate, deck.evaluation, replace(deck.config, mains_voltage_rms=253))
    assert f"{253 * 2**0.5:.12g}" in high_line.render()
    with pytest.raises(ValueError):
        NgSpiceConfig(loads=(RectifierLoad(.01, 12),), mode="nonlinear")
    with pytest.raises(ValueError, match="one secondary"):
        NgSpiceTransformerDeck.from_candidate(spec, deck.candidate, deck.evaluation,
            replace(deck.config, mode="nonlinear", bh_curve=BHCurve(
                (-2, -1, 0, 1, 2), (-2, -1, 0, 1, 2))))
    with pytest.raises(ValueError, match="source"):
        BHCurve((-2, -1, 0, 1, 2), (-2, -1, 0, 1, 2), measured=True)


def test_full_cycle_window_interpolates_endpoints():
    data = np.column_stack((np.arange(0, 0.061, .003),
                            np.arange(0, 0.061, .003)))
    selected = _window(data, .02, .06)
    assert selected[0, 0] == pytest.approx(.02)
    assert selected[-1, 0] == pytest.approx(.06)
    assert selected[0, 1] == pytest.approx(.02)


def test_core_loss_recomputed_for_line_voltage(spec, material):
    deck = _deck(spec, material)
    measured = TabulatedCoreLoss((LossPoint(50, 1.0, .4, "measured"),
                                  LossPoint(50, 1.5, 1.2, "measured"),
                                  LossPoint(50, 2.0, 3.0, "measured")),
                                 source="measurement record", material_name=material.name)
    nominal = replace(deck, config=replace(deck.config, core_loss_model=measured))
    high = replace(nominal, config=replace(nominal.config, mains_voltage_rms=253))
    assert nominal.circuit().core_loss_data_physical
    assert nominal.circuit().core_loss_data_quality == CoreLossDataQuality.MEASURED
    assert high.circuit().core_loss_data_physical
    assert high.circuit().core_loss_w > nominal.circuit().core_loss_w
    assert high.circuit().core_loss_resistance_ohm != pytest.approx(
        nominal.circuit().core_loss_resistance_ohm)
    wrong_grade = replace(nominal, config=replace(nominal.config,
        core_loss_model=TabulatedCoreLoss(measured.points, source=measured.source,
                                          material_name="other steel")))
    with pytest.raises(ValueError, match="does not match"):
        wrong_grade.circuit()
    typical = TabulatedCoreLoss(tuple(replace(point, kind="typical") for point in measured.points),
                                source="manufacturer curve", material_name=material.name)
    assert typical.quality_at(50, 1.2, material.name) == CoreLossDataQuality.MANUFACTURER_TYPICAL
    guaranteed = TabulatedCoreLoss(tuple(replace(point, kind="maximum") for point in measured.points),
                                   source="manufacturer limit", material_name=material.name)
    assert guaranteed.quality_at(50, 1.2, material.name) == CoreLossDataQuality.MANUFACTURER_GUARANTEED
    with pytest.raises(ValueError):
        guaranteed.loss_density(50, 1.2, 25)


@pytest.mark.skipif(shutil.which("ngspice") is None, reason="ngspice executable unavailable")
def test_core_loss_feedback_uses_magnetic_branch_voltage(spec, material):
    deck = _deck(spec, material)
    curve = TabulatedCoreLoss((LossPoint(50, .8, .2, "typical"),
                               LossPoint(50, 1.2, .7, "typical"),
                               LossPoint(50, 1.6, 2.5, "typical")),
                              source="manufacturer curve", material_name=material.name)
    deck = replace(deck, config=replace(deck.config, core_loss_model=curve,
                                         mains_resistance_ohm=5.0))
    result = NgSpiceRunner().run(deck)
    assert result.primary_magnetic_voltage_rms_v < spec.mains_voltage
    assert result.peak_flux_density_t < deck.evaluation.b_nominal
    assert result.core_loss_target_w < deck.circuit().core_loss_w
    assert result.core_loss_relative_error <= deck.config.core_loss_relative_tolerance
    assert result.core_loss_data_quality == CoreLossDataQuality.MANUFACTURER_TYPICAL
    assert not result.core_loss_data_physical
    final_rcore = result.primary_magnetic_voltage_rms_v**2 / result.core_loss_w
    assert final_rcore != pytest.approx(deck.circuit().core_loss_resistance_ohm)


@pytest.mark.skipif(shutil.which("ngspice") is None, reason="ngspice executable unavailable")
def test_linear_rectifier_smoke(spec, material, tmp_path):
    deck = _deck(spec, material)
    result = NgSpiceRunner().run(
        deck, plots_dir=tmp_path, plot_banner="DEMONSTRATOR ONLY",
        plot_filename_prefix="DEMONSTRATOR_ONLY_")
    for name in ("startup_currents.png", "steady_currents.png", "dc_rails.png"):
        image = tmp_path / f"DEMONSTRATOR_ONLY_{name}"
        assert image.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert result.primary_rms_current_a > result.no_load_current_a > 0
    assert len(result.secondary_rms_current_a) == 2
    assert all(0 < i < 20 for i in result.secondary_rms_current_a)
    assert all(0 < angle < 180 for angle in result.diode_conduction_angle_deg)
    assert all(v > 0 for v in result.rectified_dc_voltage_v)
    assert result.copper_loss_w > 0
    assert result.primary_magnetic_voltage_rms_v < spec.mains_voltage
    assert result.core_loss_relative_error <= deck.config.core_loss_relative_tolerance
    assert result.core_loss_w == pytest.approx(result.core_loss_target_w, rel=.001)
    assert result.core_loss_data_quality == CoreLossDataQuality.ILLUSTRATIVE
    assert not result.physical_material_data
    assert not result.bh_data_physical
    assert not result.core_loss_data_physical
    assert not result.remanence_modeled
    assert not result.magnetic_inrush_valid
    assert result.magnetic_inrush_peak_a is None
    assert result.startup_primary_peak_a > 0
    assert result.thermal_iterations >= 1
    assert abs(result.winding_resistance_temperature_c -
               result.estimated_copper_temperature_c) <= deck.config.thermal_tolerance_c
    assert result.peak_primary_current_a >= result.steady_primary_peak_current_a
    assert all(a >= b for a, b in zip(result.secondary_peak_current_a,
                                      result.secondary_steady_peak_current_a, strict=True))
    assert all(hi - lo == pytest.approx(pp) for hi, lo, pp in zip(
        result.dc_rail_max_v, result.dc_rail_min_v, result.dc_ripple_pp_v, strict=True))
    assert all(current > voltage / 12 for current, voltage in zip(
        result.secondary_rms_current_a, result.rectified_dc_voltage_v, strict=True))
    high_line = NgSpiceRunner().sweep(_deck(spec, material), (253.0,), (0.0,))[(253.0, 0.0)]
    assert high_line.mains_voltage_rms == 253.0
    assert high_line.switch_phase_deg == 0.0
    assert high_line.rectified_dc_voltage_v[0] > result.rectified_dc_voltage_v[0]
    startup = NgSpiceRunner().sweep_startup(
        deck, (230.0,), (0.0, 90.0),
        plot_path=tmp_path / "startup_phase_sweep.png")
    assert (tmp_path / "startup_phase_sweep.png").read_bytes().startswith(
        b"\x89PNG\r\n\x1a\n")
    assert startup[(230.0, 0.0)] > 0
    assert startup[(230.0, 90.0)] > 0
    report = with_ngspice_results(OptimizationResult(
        [deck.candidate], [deck.evaluation], [
            (deck.evaluation.total_loss, deck.evaluation.total_mass,
             deck.evaluation.regulation_percent)]), {0: result})
    assert bool(report.at[0, "ngspice_simulated"])
    assert not bool(report.at[0, "physical_validation_complete"])
    assert report.at[0, "ngspice_copper_loss_w"] == result.copper_loss_w


@pytest.mark.skipif(shutil.which("ngspice") is None, reason="ngspice executable unavailable")
def test_nonlinear_deck_smoke(spec, material):
    deck = _deck(spec, material, mode="nonlinear")
    assert "H_array" in deck.render() and "lcouple" in deck.render()
    result = NgSpiceRunner().run(deck)
    assert result.primary_rms_current_a > 0
    assert result.peak_flux_density_t > 0
    assert not result.physical_material_data
    measured = TabulatedCoreLoss((LossPoint(50, 1.0, .5, "measured"),
                                  LossPoint(50, 1.5, 1.0, "measured")),
                                 source="measurement record", material_name=material.name)
    tagged = replace(deck, config=replace(deck.config,
        bh_curve=replace(deck.config.bh_curve, measured=True,
                         source="measurement record", material_name=material.name),
        core_loss_model=measured))
    tagged_result = NgSpiceRunner().run(tagged)
    assert tagged_result.bh_data_physical
    assert tagged_result.core_loss_data_physical
    assert tagged_result.core_loss_data_quality == CoreLossDataQuality.MEASURED
    assert not tagged_result.remanence_modeled
    assert not tagged_result.magnetic_inrush_valid
    assert not tagged_result.physical_material_data
    wrong_bh = replace(tagged, config=replace(tagged.config,
        bh_curve=replace(tagged.config.bh_curve, material_name="other steel")))
    with pytest.raises(ValueError, match="does not match"):
        wrong_bh.render()
