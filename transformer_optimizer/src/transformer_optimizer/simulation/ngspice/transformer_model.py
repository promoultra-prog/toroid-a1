from dataclasses import dataclass
from math import pi
from ...models.specs import TransformerSpec
from ...models.result import CandidateEvaluation
from ...engine.candidate import TransformerCandidate
from ...physics.core_loss import CoreLossModel, SteinmetzCoreLoss, TabulatedCoreLoss
from ...physics.copper import resistance
from ...physics.magnetic import flux_density


@dataclass(frozen=True)
class CircuitTransformer:
    primary_inductance_h: float
    secondary_inductances_h: tuple[float, ...]
    primary_resistance_ohm: float
    secondary_resistances_ohm: tuple[float, ...]
    core_loss_resistance_ohm: float
    core_loss_w: float
    core_loss_data_physical: bool


def circuit_transformer(spec: TransformerSpec, candidate: TransformerCandidate,
                        evaluation: CandidateEvaluation, mains_voltage_rms: float,
                        winding_temperature_c: float,
                        core_loss_model: CoreLossModel | None = None) -> CircuitTransformer:
    if not evaluation.valid:
        raise ValueError("Only valid candidates may be simulated")
    # The linear permeability estimate is analytical. Re-evaluate core loss at
    # each line voltage instead of letting a nominal fixed RCORE impose V**2.
    lp = spec.mains_voltage / (2 * pi * spec.mains_frequency * evaluation.magnetizing_current)
    ls = tuple(lp * (n / evaluation.primary_turns)**2 for n in evaluation.secondary_turns)
    b_line = flux_density(mains_voltage_rms, spec.mains_frequency,
                          evaluation.primary_turns, candidate.core.effective_cross_section)
    model = core_loss_model or SteinmetzCoreLoss(candidate.core.material)
    if (isinstance(model, TabulatedCoreLoss) and model.material_name is not None
            and model.material_name != candidate.core.material.name):
        raise ValueError("Core-loss data material does not match candidate steel")
    p_core = model.loss_density(spec.mains_frequency, b_line,
                                spec.ambient_temperature) * candidate.core.core_mass
    if p_core <= 0:
        raise ValueError("Core loss must be positive")
    rcore = mains_voltage_rms**2 / p_core
    rp = resistance(candidate.primary_wire, evaluation.primary_wire_length,
                    winding_temperature_c)
    rs = tuple(resistance(candidate.secondary_wire, length, winding_temperature_c)
               for length in evaluation.secondary_wire_length)
    physical = isinstance(model, TabulatedCoreLoss) and model.physical_data_at(
        spec.mains_frequency, b_line, candidate.core.material.name)
    return CircuitTransformer(lp, ls, rp, rs, rcore, p_core, physical)
