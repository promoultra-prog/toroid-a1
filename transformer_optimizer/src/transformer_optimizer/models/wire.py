from dataclasses import dataclass
from math import pi


@dataclass(frozen=True)
class RoundWire:
    conductor_diameter: float
    insulation_diameter: float
    resistivity_20c: float = 1.724e-8
    temperature_coefficient: float = 0.00393

    def __post_init__(self):
        if self.conductor_diameter <= 0 or self.insulation_diameter < self.conductor_diameter or self.resistivity_20c <= 0:
            raise ValueError("Invalid wire")

    @property
    def area(self): return pi * self.conductor_diameter**2 / 4

    @property
    def resistance_per_meter(self): return self.resistivity_20c / self.area

    def resistance_at_temperature(self, length: float, temperature: float) -> float:
        return self.resistance_per_meter * length * (1 + self.temperature_coefficient * (temperature - 20))


@dataclass(frozen=True)
class WindingWire:
    wire: RoundWire
    parallel_count: int = 1

    def __post_init__(self):
        if self.parallel_count < 1:
            raise ValueError("parallel_count must be positive")

    @property
    def area(self): return self.parallel_count * self.wire.area

    def current_density(self, current: float): return current / self.area

    def resistance_at_temperature(self, length: float, temperature: float):
        return self.wire.resistance_at_temperature(length, temperature) / self.parallel_count
