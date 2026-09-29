from dataclasses import dataclass, field


@dataclass
class OpenMagneticsValidation:
    available: bool = False
    core_loss_w: float | None = None
    winding_loss_w: float | None = None
    inductance_h: float | None = None
    magnetizing_current_a: float | None = None
    core_temperature_c: float | None = None
    our_core_loss_w: float = 0.0
    our_winding_loss_w: float = 0.0
    core_loss_error_pct: float | None = None
    winding_loss_error_pct: float | None = None
    warnings: list[str] = field(default_factory=list)
