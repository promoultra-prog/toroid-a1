import pandas as pd
from ..optimize.pareto import OptimizationResult


def to_dataframe(result: OptimizationResult) -> pd.DataFrame:
    rows = []
    for c, r in zip(result.candidates, result.evaluations, strict=True):
        rows.append({
            "OD_mm": c.core.outer_diameter * 1e3,
            "ID_mm": c.core.inner_diameter * 1e3,
            "H_mm": c.core.height * 1e3,
            "VA": sum(v * j * c.secondary_wire.area for v, j in zip(
                r.secondary_voltage_full_load, r.secondary_current_density, strict=True)),
            "Bmax_T": r.b_max_mains,
            "Np": r.primary_turns, "Ns": r.secondary_turns,
            "primary_wire_mm": c.primary_wire.wire.conductor_diameter * 1e3,
            "secondary_wire_mm": c.secondary_wire.wire.conductor_diameter * 1e3,
            "primary_parallel": c.primary_wire.parallel_count,
            "secondary_parallel": c.secondary_wire.parallel_count,
            "Jp_A_mm2": r.primary_current_density / 1e6,
            "Js_A_mm2": tuple(j / 1e6 for j in r.secondary_current_density),
            "Pcu_W": r.primary_copper_loss + r.secondary_copper_loss,
            "Pcore_W": r.core_loss, "Ptotal_W": r.total_loss,
            "efficiency_pct": r.efficiency * 100,
            "regulation_pct": r.regulation_percent,
            "core_mass_kg": r.core_mass, "copper_mass_kg": r.copper_mass,
            "total_mass_kg": r.total_mass,
            "Tcore_C": r.estimated_core_temperature,
            "Tcopper_C": r.estimated_copper_temperature,
            "remaining_ID_mm": r.remaining_inner_diameter * 1e3,
            "fill_ratio": r.fill_ratio,
            "magnetizing_current_A": r.magnetizing_current,
            "valid": r.valid,
        })
    return pd.DataFrame(rows)
