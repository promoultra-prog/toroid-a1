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
