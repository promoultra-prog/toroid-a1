from math import ceil, pi, sqrt


def primary_turns(voltage: float, frequency: float, design_flux_density: float, area: float) -> int:
    return max(1, ceil(voltage / (4.44 * frequency * design_flux_density * area)))


def secondary_turns(voltage: float, volts_per_turn_value: float) -> int:
    return max(1, ceil(voltage / volts_per_turn_value))


def flux_density(voltage: float, frequency: float, turns: int, area: float) -> float:
    return voltage / (4.44 * frequency * turns * area)


def volts_per_turn(voltage: float, turns: int) -> float:
    return voltage / turns


def estimate_magnetizing_current(frequency: float, turns: int, area: float, path: float,
                                  flux: float, relative_permeability: float) -> float:
    # Linear permeability only; real toroidal steel needs a B-H curve near saturation.
    mu0 = 4 * pi * 1e-7
    inductance = mu0 * relative_permeability * turns**2 * area / path
    voltage = 4.44 * frequency * turns * flux * area
    return voltage / (2 * pi * frequency * inductance)
