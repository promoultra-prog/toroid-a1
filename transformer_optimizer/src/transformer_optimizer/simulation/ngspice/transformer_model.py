from dataclasses import dataclass
from math import pi
from ...models.specs import TransformerSpec
from ...models.result import CandidateEvaluation
from ...engine.candidate import TransformerCandidate


@dataclass(frozen=True)
class CircuitTransformer:
    primary_inductance_h: float
    secondary_inductances_h: tuple[float, ...]
    primary_resistance_ohm: float
    secondary_resistances_ohm: tuple[float, ...]
    core_loss_resistance_ohm: float


def circuit_transformer(spec: TransformerSpec, candidate: TransformerCandidate,
                        evaluation: CandidateEvaluation) -> CircuitTransformer:
    if not evaluation.valid:
        raise ValueError("Only valid candidates may be simulated")
    # Uses the analytical linear-permeability magnetizing estimate. Rcore is
    # calibrated from our analytical core loss, not an independent SPICE model.
    lp = spec.mains_voltage / (2 * pi * spec.mains_frequency * evaluation.magnetizing_current)
    ls = tuple(lp * (n / evaluation.primary_turns)**2 for n in evaluation.secondary_turns)
    rcore = spec.mains_voltage**2 / evaluation.core_loss
    return CircuitTransformer(lp, ls, evaluation.primary_resistance,
                              evaluation.secondary_resistance, rcore)
