from dataclasses import replace
import pytest
from transformer_optimizer import ToroidalCore, RoundWire, WindingWire, TransformerCandidate, ToroidalTransformerModel
from transformer_optimizer.integrations.openmagnetics import (
    OpenMagneticsValidator, build_mas, load_reference_steel
)
from transformer_optimizer.integrations.openmagnetics.material_adapter import LossPoint
from transformer_optimizer.physics.core_loss import TabulatedCoreLoss


def _case(spec, material):
    core = ToroidalCore(.16, .08, .06, .95, material.density, material)
    candidate = TransformerCandidate(core, 1.2,
        WindingWire(RoundWire(.0015, .00162)),
        WindingWire(RoundWire(.0025, .0027), 2))
    return candidate, ToroidalTransformerModel().evaluate(spec, candidate)


def test_published_steel_is_not_invented():
    steel = load_reference_steel()
    assert steel.grade == "ORIENTCORE 23Z110"
    assert steel.loss_points[0].watts_per_kg == 1.10
    assert steel.loss_points[0].kind == "maximum"
    assert not steel.has_loss_curve and not steel.has_bh_curve
    with pytest.raises(ValueError):
        TabulatedCoreLoss(steel.loss_points).loss_density(50, 1.2, 25)
    measured = (LossPoint(50, 1.0, .5, "measured"), LossPoint(50, 1.5, 1.0, "measured"))
    assert TabulatedCoreLoss(measured).loss_density(50, 1.25, 25) == pytest.approx(.75)
    with pytest.raises(ValueError):
        TabulatedCoreLoss(measured).loss_density(50, 1.7, 25)


def test_mas_export_and_fail_closed_validation(spec, material):
    candidate, evaluation = _case(spec, material)
    mas = build_mas(spec, candidate, evaluation, material.name)
    shape = mas["magnetic"]["core"]["functionalDescription"]["shape"]
    assert shape["dimensions"]["A"]["nominal"] == .16
    assert len(mas["magnetic"]["coil"]["functionalDescription"]) == 3
    assert mas["magnetic"]["coil"]["functionalDescription"][1]["numberTurns"] == evaluation.secondary_turns[0]
    assert len(mas["inputs"]["operatingPoints"][0]["excitationsPerWinding"]) == 3
    check = OpenMagneticsValidator(load_reference_steel(), "23Z110").validate(spec, candidate, evaluation)
    assert not check.available and check.core_loss_w is None and check.warnings
    assert not OpenMagneticsValidator().validate(spec, candidate, evaluation).available


def test_validation_compares_external_results(spec, material):
    class FakeAdapter:
        def calculate(self, mas, temperature):
            assert mas["magnetic"]["core"]["functionalDescription"]["material"] == "registered steel"
            return {"core_loss_w": 2.0, "winding_loss_w": 4.0,
                    "inductance_h": 1.0, "core_temperature_c": 42.0}

    candidate, evaluation = _case(spec, material)
    dataset = replace(load_reference_steel(), grade=material.name,
        loss_points=(LossPoint(50, 1.0, 1.0, "measured"), LossPoint(50, 1.7, 2.0, "measured")),
        bh_curve=((100.0, 1.0), (800.0, 1.7)))
    check = OpenMagneticsValidator(dataset, "registered steel", FakeAdapter()).validate(
        spec, candidate, evaluation)
    assert check.available
    assert check.core_loss_error_pct == pytest.approx(100 * (2 / evaluation.core_loss - 1))
    assert check.winding_loss_error_pct == pytest.approx(100 * (4 /
        (evaluation.primary_copper_loss + evaluation.secondary_copper_loss) - 1))
