from ..models.wire import WindingWire

COPPER_DENSITY = 8960.0  # kg/m^3, exposed here so the mass estimate is traceable.


def resistance(wire: WindingWire, length: float, temperature: float) -> float:
    return wire.resistance_at_temperature(length, temperature)


def copper_loss(current: float, resistance_ohm: float) -> float:
    return current**2 * resistance_ohm


def copper_mass(wire: WindingWire, length: float) -> float:
    return wire.area * length * COPPER_DENSITY
