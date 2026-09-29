from typing import Protocol
from enum import Enum
from ..models.core import CoreMaterial


class CoreLossModel(Protocol):
    def loss_density(self, frequency: float, flux_density: float, temperature: float) -> float:
        """Return W/kg."""
        ...


class CoreLossDataQuality(str, Enum):
    ILLUSTRATIVE = "illustrative"
    MANUFACTURER_TYPICAL = "manufacturer_typical"
    MANUFACTURER_GUARANTEED = "manufacturer_guaranteed"
    MEASURED = "measured"


class SteinmetzCoreLoss:
    def __init__(self, material: CoreMaterial):
        self.material = material

    def loss_density(self, frequency: float, flux_density: float, temperature: float) -> float:
        # Temperature is reserved for a calibrated material model; no guessed correction.
        m = self.material
        return m.steinmetz_k * frequency**m.steinmetz_alpha * flux_density**m.steinmetz_beta


class TabulatedCoreLoss:
    """Interpolate typical/measured W/kg; guarantees are bounds, not nominal loss."""

    def __init__(self, points, source: str | None = None,
                 material_name: str | None = None):
        self.points = tuple(points)
        self.source = source
        self.material_name = material_name

    def physical_data_at(self, frequency: float, flux_density: float,
                         material_name: str) -> bool:
        return self.quality_at(frequency, flux_density, material_name) == CoreLossDataQuality.MEASURED

    def quality_at(self, frequency: float, flux_density: float,
                   material_name: str) -> CoreLossDataQuality:
        if not self.source or self.material_name != material_name:
            return CoreLossDataQuality.ILLUSTRATIVE
        usable = [p for p in self.points if p.frequency_hz == frequency and
                  p.kind in ("typical", "measured")]
        if (len(usable) >= 2 and min(p.flux_density_t for p in usable) <= flux_density <=
                max(p.flux_density_t for p in usable)):
            if all(p.kind == "measured" for p in usable):
                return CoreLossDataQuality.MEASURED
            return CoreLossDataQuality.MANUFACTURER_TYPICAL
        guaranteed = [p for p in self.points if p.frequency_hz == frequency and
                      p.kind == "maximum"]
        if (len(guaranteed) >= 2 and
                min(p.flux_density_t for p in guaranteed) <= flux_density <=
                max(p.flux_density_t for p in guaranteed)):
            return CoreLossDataQuality.MANUFACTURER_GUARANTEED
        return CoreLossDataQuality.ILLUSTRATIVE

    def loss_density(self, frequency: float, flux_density: float, temperature: float) -> float:
        from scipy.interpolate import PchipInterpolator
        samples = sorted((p.flux_density_t, p.watts_per_kg) for p in self.points
                         if p.frequency_hz == frequency and p.kind in ("typical", "measured"))
        if len(samples) < 2 or len({b for b, _ in samples}) != len(samples):
            raise ValueError("At least two distinct measured loss points at this frequency are required")
        if not samples[0][0] <= flux_density <= samples[-1][0]:
            raise ValueError("Core-loss interpolation outside measured flux range is not allowed")
        return float(PchipInterpolator(*zip(*samples, strict=True))(flux_density))
