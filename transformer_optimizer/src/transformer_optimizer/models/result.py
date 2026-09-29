from dataclasses import dataclass, field
from .winding import WindingGeometry


@dataclass
class CandidateEvaluation:
    valid: bool = False
    violations: list[str] = field(default_factory=list)
    primary_turns: int = 0
    secondary_turns: tuple[int, ...] = ()
    b_nominal: float = 0.0
    b_max_mains: float = 0.0
    primary_current_density: float = 0.0
    secondary_current_density: tuple[float, ...] = ()
    primary_wire_length: float = 0.0
    secondary_wire_length: tuple[float, ...] = ()
    primary_resistance: float = 0.0
    secondary_resistance: tuple[float, ...] = ()
    primary_copper_loss: float = 0.0
    secondary_copper_loss: float = 0.0
    core_loss: float = 0.0
    total_loss: float = 0.0
    efficiency: float = 0.0
    secondary_voltage_no_load: tuple[float, ...] = ()
    secondary_voltage_full_load: tuple[float, ...] = ()
    regulation_percent: float = 0.0
    core_mass: float = 0.0
    copper_mass: float = 0.0
    total_mass: float = 0.0
    remaining_inner_diameter: float = 0.0
    fill_ratio: float = 0.0
    estimated_core_temperature: float = 0.0
    estimated_copper_temperature: float = 0.0
    magnetizing_current: float = 0.0
    magnetizing_current_estimated: bool = True
    winding_geometries: tuple[WindingGeometry, ...] = ()
