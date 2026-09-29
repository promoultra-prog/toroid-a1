from dataclasses import dataclass
from importlib.resources import files
import json


@dataclass(frozen=True)
class LossPoint:
    frequency_hz: float
    flux_density_t: float
    watts_per_kg: float
    kind: str  # "typical", "measured", or "maximum"


@dataclass(frozen=True)
class SteelDataset:
    manufacturer: str
    grade: str
    strip_thickness_m: float
    density_kg_m3: float
    minimum_stacking_factor: float
    source_url: str
    loss_points: tuple[LossPoint, ...]
    bh_curve: tuple[tuple[float, float], ...] = ()  # (H in A/m, B in T)
    minimum_b_at_800_a_per_m: float | None = None

    @property
    def has_loss_curve(self) -> bool:
        return len([p for p in self.loss_points if p.kind in ("typical", "measured")
                    and p.frequency_hz == 50.0]) >= 2

    @property
    def has_bh_curve(self) -> bool:
        return len(self.bh_curve) >= 2


def load_reference_steel() -> SteelDataset:
    """Load published guarantees, without inventing a B-H or loss curve."""
    resource = files("transformer_optimizer.integrations.openmagnetics").joinpath("data/23z110.json")
    raw = json.loads(resource.read_text(encoding="utf-8"))
    return SteelDataset(
        manufacturer=raw["manufacturer"], grade=raw["grade"],
        strip_thickness_m=raw["strip_thickness_m"],
        density_kg_m3=raw["density_kg_m3"],
        minimum_stacking_factor=raw["minimum_stacking_factor"],
        source_url=raw["source_url"],
        loss_points=tuple(LossPoint(**p) for p in raw["loss_points"]),
        bh_curve=tuple(tuple(point) for point in raw["bh_curve"]),
        minimum_b_at_800_a_per_m=raw["minimum_b_at_800_a_per_m"],
    )


def require_mkf_material(dataset: SteelDataset, registered_name: str | None,
                         frequency: float, flux_density: float) -> str:
    if not registered_name:
        raise ValueError("Register a complete steel material in OpenMagnetics and pass its name")
    losses = [p for p in dataset.loss_points if p.kind in ("typical", "measured")
              and p.frequency_hz == frequency]
    if len(losses) < 2 or not dataset.has_bh_curve:
        raise ValueError("Steel dataset needs at least two measured loss points at this frequency and two B-H points")
    if not min(p.flux_density_t for p in losses) <= flux_density <= max(p.flux_density_t for p in losses):
        raise ValueError("Operating flux is outside the measured loss range")
    if not min(b for _, b in dataset.bh_curve) <= flux_density <= max(b for _, b in dataset.bh_curve):
        raise ValueError("Operating flux is outside the measured B-H range")
    return registered_name
