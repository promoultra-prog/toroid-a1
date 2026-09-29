from dataclasses import dataclass


@dataclass(frozen=True)
class WindingLayer:
    turns: int
    inner_center_diameter: float
    outer_center_diameter: float
    axial_center_height: float
    turn_length: float
    inner_coverage: float
    outer_coverage: float


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
    layer_details: tuple[WindingLayer, ...] = ()
