from math import floor, pi
from ..models.core import ToroidalCore
from ..models.wire import WindingWire
from ..models.winding import WindingGeometry


class GeometryError(ValueError):
    pass


def winding_geometry(core: ToroidalCore, turns: int, wire: WindingWire,
                     starting_build: float, coverage: float, minimum_inner_diameter: float) -> WindingGeometry:
    if turns < 1 or starting_build < 0 or not 0 < coverage <= 1:
        raise GeometryError("Invalid winding inputs")
    pitch = wire.wire.insulation_diameter * wire.parallel_count
    radial_step = wire.wire.insulation_diameter
    remaining = turns
    length = 0.0
    layers = 0
    while remaining:
        offset = starting_build + (layers + 0.5) * radial_step
        inner_diameter = core.inner_diameter - 2 * (starting_build + (layers + 1) * radial_step)
        if inner_diameter <= minimum_inner_diameter:
            raise GeometryError("Winding closes the toroidal window")
        capacity = floor(coverage * pi * inner_diameter / pitch)
        if capacity < 1:
            raise GeometryError("Wire cannot be placed around inner circumference")
        count = min(remaining, capacity)
        # Each turn travels around the insulated rectangular core cross section.
        # Offset perimeter grows by 2*pi*offset for rounded corners.
        turn_length = 2 * (core.radial_thickness + core.height) + 2 * pi * offset
        length += count * turn_length
        remaining -= count
        layers += 1
    build = starting_build + layers * radial_step
    return WindingGeometry(turns, layers, build, build, build, length / turns,
                           length, core.inner_diameter - 2 * build)


def window_fill_ratio(core: ToroidalCore, remaining_inner_diameter: float) -> float:
    return 1 - (remaining_inner_diameter / core.inner_diameter)**2
