from math import pi, sin, sqrt
from ...models.specs import TransformerSpec
from ...models.result import CandidateEvaluation
from ...engine.candidate import TransformerCandidate


def _waveform(rms: float, frequency: float) -> dict:
    period = 1 / frequency
    return {"waveform": {
        "time": [period * i / 32 for i in range(33)],
        "data": [sqrt(2) * rms * sin(2 * pi * i / 32) for i in range(33)],
    }}


def _wire_description(winding_wire) -> dict:
    wire = winding_wire.wire
    return {"type": "round", "material": "copper",
            "conductingDiameter": {"nominal": wire.conductor_diameter},
            "outerDiameter": {"nominal": wire.insulation_diameter}}


def build_mas(spec: TransformerSpec, candidate: TransformerCandidate,
              evaluation: CandidateEvaluation, material_name: str) -> dict:
    """Create an SI MAS exchange document; MKF still needs the named steel registered."""
    if not evaluation.valid:
        raise ValueError("Only valid evaluated candidates can be exported")
    if not material_name:
        raise ValueError("MAS material name is required")
    core = candidate.core
    shape = {"type": "custom", "family": "t", "magneticCircuit": "closed",
             "name": f"T {core.outer_diameter:.6g}/{core.inner_diameter:.6g}/{core.height:.6g}",
             "dimensions": {"A": {"nominal": core.outer_diameter},
                            "B": {"nominal": core.inner_diameter},
                            "C": {"nominal": core.height}}}
    windings = [{"name": "Primary", "numberTurns": evaluation.primary_turns,
                 "numberParallels": candidate.primary_wire.parallel_count,
                 "wire": _wire_description(candidate.primary_wire), "isolationSide": "primary"}]
    for index, turns in enumerate(evaluation.secondary_turns, 1):
        windings.append({"name": f"Secondary {index}", "numberTurns": turns,
                         "numberParallels": candidate.secondary_wire.parallel_count,
                         "wire": _wire_description(candidate.secondary_wire), "isolationSide": "secondary"})
    primary_rms = evaluation.primary_current_density * candidate.primary_wire.area
    excitation = [{"name": "Primary", "frequency": spec.mains_frequency,
                   "voltage": _waveform(spec.mains_voltage, spec.mains_frequency),
                   "current": _waveform(primary_rms, spec.mains_frequency)}]
    for index, (voltage, current) in enumerate(zip(
        evaluation.secondary_voltage_full_load, evaluation.secondary_currents, strict=True), 1):
        excitation.append({"name": f"Secondary {index}", "frequency": spec.mains_frequency,
                           "voltage": _waveform(voltage, spec.mains_frequency),
                           "current": _waveform(current, spec.mains_frequency)})
    l_estimate = spec.mains_voltage / (2 * pi * spec.mains_frequency * evaluation.magnetizing_current)
    return {
        "inputs": {"designRequirements": {
            "magnetizingInductance": {"nominal": l_estimate},
            "turnsRatios": [{"nominal": evaluation.primary_turns / n} for n in evaluation.secondary_turns]},
            "operatingPoints": [{"name": "Nominal", "conditions": {
                "ambientTemperature": spec.ambient_temperature}, "excitationsPerWinding": excitation}]},
        "magnetic": {"core": {"functionalDescription": {
            "type": "toroidal", "shape": shape, "material": material_name,
            "gapping": [], "numberStacks": 1}},
            "coil": {"functionalDescription": windings}},
    }
