from dataclasses import dataclass


@dataclass(frozen=True)
class WindingGeometry:
    turns: int
    layers: int
    inner_build: float
    outer_build: float
    axial_build: float
    mean_turn_length: float
    total_wire_length: float
    remaining_inner_diameter: float
