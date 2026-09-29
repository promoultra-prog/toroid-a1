from typing import Protocol
from ..models.core import CoreMaterial


class CoreLossModel(Protocol):
    def loss_density(self, frequency: float, flux_density: float, temperature: float) -> float:
        """Return W/kg."""
        ...


class SteinmetzCoreLoss:
    def __init__(self, material: CoreMaterial):
        self.material = material

    def loss_density(self, frequency: float, flux_density: float, temperature: float) -> float:
        # Temperature is reserved for a calibrated material model; no guessed correction.
        m = self.material
        return m.steinmetz_k * frequency**m.steinmetz_alpha * flux_density**m.steinmetz_beta


class TabulatedCoreLoss:
    """Interpolate measured W/kg points; refuse extrapolation and guarantee-only data."""

    def __init__(self, points, source: str | None = None,
                 material_name: str | None = None):
        self.points = tuple(points)
        self.source = source
        self.material_name = material_name

    def physical_data_at(self, frequency: float, flux_density: float,
                         material_name: str) -> bool:
        samples = [p for p in self.points if p.frequency_hz == frequency
                   and p.kind == "measured"]
        return bool(self.source and self.material_name == material_name and
                    len(samples) >= 2 and
                    min(p.flux_density_t for p in samples) <= flux_density <=
                    max(p.flux_density_t for p in samples))

    def loss_density(self, frequency: float, flux_density: float, temperature: float) -> float:
        from scipy.interpolate import PchipInterpolator
        samples = sorted((p.flux_density_t, p.watts_per_kg) for p in self.points
                         if p.frequency_hz == frequency and p.kind in ("typical", "measured"))
        if len(samples) < 2 or len({b for b, _ in samples}) != len(samples):
            raise ValueError("At least two distinct measured loss points at this frequency are required")
        if not samples[0][0] <= flux_density <= samples[-1][0]:
            raise ValueError("Core-loss interpolation outside measured flux range is not allowed")
        return float(PchipInterpolator(*zip(*samples, strict=True))(flux_density))
