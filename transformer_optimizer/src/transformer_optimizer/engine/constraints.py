from ..models.result import CandidateEvaluation
from ..models.specs import TransformerSpec


def violations(spec: TransformerSpec, result: CandidateEvaluation) -> list[str]:
    problems = []
    checks = (
        (result.b_max_mains > spec.max_flux_density, "maximum mains flux density"),
        (result.primary_current_density > spec.max_current_density_primary, "primary current density"),
        (any(j > spec.max_current_density_secondary for j in result.secondary_current_density), "secondary current density"),
        (result.remaining_inner_diameter < spec.minimum_remaining_inner_diameter, "remaining inner diameter"),
        (result.estimated_core_temperature > spec.maximum_core_temperature, "core temperature"),
        (result.estimated_copper_temperature > spec.maximum_copper_temperature, "copper temperature"),
    )
    problems.extend(label for failed, label in checks if failed)
    for index, (secondary, loaded, unloaded) in enumerate(zip(
        spec.expanded_secondaries, result.secondary_voltage_full_load,
        result.secondary_voltage_no_load, strict=True)):
        minimum = (secondary.minimum_full_load_voltage if secondary.minimum_full_load_voltage is not None
                   else secondary.voltage_rms)
        if loaded + 1e-9 < minimum:
            problems.append(f"secondary {index + 1} full-load voltage")
        if secondary.maximum_no_load_voltage is not None and unloaded > secondary.maximum_no_load_voltage:
            problems.append(f"secondary {index + 1} no-load voltage")
    return problems
