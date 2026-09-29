from dataclasses import dataclass


@dataclass(frozen=True)
class SecondarySpec:
    voltage_rms: float
    current_rms: float
    quantity: int = 1
    minimum_full_load_voltage: float | None = None
    maximum_no_load_voltage: float | None = None

    def __post_init__(self):
        if self.voltage_rms <= 0 or self.current_rms <= 0 or self.quantity < 1:
            raise ValueError("Secondary voltage, current and quantity must be positive")


@dataclass(frozen=True)
class TransformerSpec:
    mains_voltage: float
    mains_frequency: float
    mains_max_voltage: float
    secondaries: tuple[SecondarySpec, ...]
    max_flux_density: float
    max_current_density_primary: float
    max_current_density_secondary: float
    ambient_temperature: float = 25.0
    maximum_core_temperature: float = 110.0
    maximum_copper_temperature: float = 110.0
    minimum_remaining_inner_diameter: float = 0.015
    core_insulation: float = 0.0005
    interwinding_insulation: float = 0.0003
    winding_coverage: float = 0.85
    core_thermal_resistance: float = 2.0
    copper_thermal_resistance: float = 2.5
    relative_permeability_estimate: float = 2000.0

    def __post_init__(self):
        if not self.secondaries or self.mains_voltage <= 0 or self.mains_frequency <= 0 or self.mains_max_voltage < self.mains_voltage:
            raise ValueError("Invalid mains or secondary specification")
        if min(self.max_flux_density, self.max_current_density_primary, self.max_current_density_secondary,
               self.minimum_remaining_inner_diameter, self.core_thermal_resistance,
               self.copper_thermal_resistance, self.relative_permeability_estimate) <= 0:
            raise ValueError("Limits and model parameters must be positive")
        if not 0 < self.winding_coverage <= 1 or min(self.core_insulation, self.interwinding_insulation) < 0:
            raise ValueError("Invalid winding insulation or coverage")

    @property
    def expanded_secondaries(self) -> tuple[SecondarySpec, ...]:
        return tuple(s for s in self.secondaries for _ in range(s.quantity))

    @property
    def output_va(self) -> float:
        return sum(s.voltage_rms * s.current_rms * s.quantity for s in self.secondaries)
