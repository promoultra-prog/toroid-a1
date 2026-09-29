from dataclasses import dataclass
from math import pi


@dataclass(frozen=True)
class CoreMaterial:
    name: str
    density: float
    steinmetz_k: float  # W/kg / (Hz**alpha * T**beta)
    steinmetz_alpha: float
    steinmetz_beta: float

    def __post_init__(self):
        if min(self.density, self.steinmetz_k, self.steinmetz_alpha, self.steinmetz_beta) <= 0:
            raise ValueError("Invalid core material")


@dataclass(frozen=True)
class ToroidalCore:
    outer_diameter: float
    inner_diameter: float
    height: float
    stacking_factor: float
    density: float
    material: CoreMaterial

    def __post_init__(self):
        if not (self.outer_diameter > self.inner_diameter > 0 and self.height > 0 and 0 < self.stacking_factor <= 1 and self.density > 0):
            raise ValueError("Invalid core geometry")

    @property
    def radial_thickness(self): return (self.outer_diameter - self.inner_diameter) / 2

    @property
    def effective_cross_section(self): return self.radial_thickness * self.height * self.stacking_factor

    @property
    def mean_magnetic_path(self): return pi * (self.outer_diameter + self.inner_diameter) / 2

    @property
    def core_volume(self): return self.effective_cross_section * self.mean_magnetic_path

    @property
    def core_mass(self): return self.core_volume * self.density

    @property
    def window_area(self): return pi * self.inner_diameter**2 / 4
