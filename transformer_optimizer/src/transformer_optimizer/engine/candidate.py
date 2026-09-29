from dataclasses import dataclass
from math import isfinite
from ..models.core import CoreMaterial, ToroidalCore
from ..models.wire import RoundWire, WindingWire


@dataclass(frozen=True)
class TransformerCandidate:
    core: ToroidalCore
    design_flux_density: float
    primary_wire: WindingWire
    secondary_wire: WindingWire


@dataclass(frozen=True)
class TransformerSearchSpace:
    outer_diameter: tuple[float, float]
    inner_diameter: tuple[float, float]
    height: tuple[float, float]
    design_flux_density: tuple[float, float]
    primary_wire_diameter: tuple[float, float]
    secondary_wire_diameter: tuple[float, float]
    primary_parallel_count: tuple[int, int] = (1, 1)
    secondary_parallel_count: tuple[int, int] = (1, 1)
    stacking_factor: float = 0.95
    primary_insulation_ratio: float = 1.08
    secondary_insulation_ratio: float = 1.08
    material: CoreMaterial | None = None

    def __post_init__(self):
        for name in ("outer_diameter", "inner_diameter", "height", "design_flux_density",
                     "primary_wire_diameter", "secondary_wire_diameter", "primary_parallel_count",
                     "secondary_parallel_count"):
            lo, hi = getattr(self, name)
            if lo <= 0 or lo > hi or not all(isfinite(v) for v in (lo, hi)):
                raise ValueError(f"Invalid range: {name}")
        if self.material is None or self.primary_insulation_ratio < 1 or self.secondary_insulation_ratio < 1:
            raise ValueError("Material and insulation ratios are required")

    @property
    def bounds(self):
        return [getattr(self, name) for name in ("outer_diameter", "inner_diameter", "height",
                "design_flux_density", "primary_wire_diameter", "secondary_wire_diameter",
                "primary_parallel_count", "secondary_parallel_count")]


class CandidateGenerator:
    def __init__(self, space: TransformerSearchSpace):
        self.space = space

    def from_vector(self, values) -> TransformerCandidate | None:
        od, id_, h, b, dp, ds, np, ns = map(float, values)
        if od <= id_:
            return None
        s = self.space
        core = ToroidalCore(od, id_, h, s.stacking_factor, s.material.density, s.material)
        return TransformerCandidate(core, b,
            WindingWire(RoundWire(dp, dp * s.primary_insulation_ratio), max(1, round(np))),
            WindingWire(RoundWire(ds, ds * s.secondary_insulation_ratio), max(1, round(ns))))
