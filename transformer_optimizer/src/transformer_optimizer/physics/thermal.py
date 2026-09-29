from dataclasses import dataclass


@dataclass(frozen=True)
class ThermalEstimate:
    copper_temperature: float
    core_temperature: float


def thermal_estimate(ambient: float, core_loss: float, copper_loss: float,
                     core_thermal_resistance: float, copper_thermal_resistance: float) -> ThermalEstimate:
    # Both nodes see aggregate heat. Separate measured effective resistances can
    # later replace this shared, lumped approximation.
    total_loss = core_loss + copper_loss
    return ThermalEstimate(ambient + copper_thermal_resistance * total_loss,
                           ambient + core_thermal_resistance * total_loss)
