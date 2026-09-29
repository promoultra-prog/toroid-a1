from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class BHCurve:
    h_a_per_m: tuple[float, ...]
    b_t: tuple[float, ...]
    measured: bool = False
    source: str | None = None

    def __post_init__(self):
        if len(self.h_a_per_m) < 5 or len(self.h_a_per_m) != len(self.b_t):
            raise ValueError("B-H curve needs at least five paired samples")
        if not all(isfinite(x) for x in (*self.h_a_per_m, *self.b_t)):
            raise ValueError("B-H curve must be finite")
        if any(a >= b for a, b in zip(self.h_a_per_m, self.h_a_per_m[1:])):
            raise ValueError("H must increase strictly")
        if any(a > b for a, b in zip(self.b_t, self.b_t[1:])):
            raise ValueError("B must be monotonic")
        if not (self.h_a_per_m[0] < 0 < self.h_a_per_m[-1] and
                self.b_t[0] < 0 < self.b_t[-1]):
            raise ValueError("B-H curve must include positive and negative branches")
        if self.measured and not self.source:
            raise ValueError("Measured B-H data requires a source")


@dataclass(frozen=True)
class RectifierLoad:
    capacitance_f: float
    resistance_ohm: float
    capacitor_esr_ohm: float = 0.05

    def __post_init__(self):
        if min(self.capacitance_f, self.resistance_ohm, self.capacitor_esr_ohm) <= 0:
            raise ValueError("Rectifier load parameters must be positive")


@dataclass(frozen=True)
class NgSpiceConfig:
    loads: tuple[RectifierLoad, ...]
    mode: str = "linear"
    coupling: float = 0.995
    mains_resistance_ohm: float = 0.1
    diode_saturation_current_a: float = 1e-9
    diode_series_resistance_ohm: float = 0.02
    diode_emission_coefficient: float = 1.0
    diode_junction_capacitance_f: float = 1e-9
    diode_transit_time_s: float = 1e-6
    secondary_shunt_resistance_ohm: float = 1e9
    cycles: int = 40
    measurement_cycles: int = 3
    samples_per_cycle: int = 500
    switch_phase_deg: float = 0.0
    mains_voltage_rms: float | None = None
    conduction_threshold_a: float = 0.1
    no_load_resistance_ohm: float = 1e9
    sense_resistance_ohm: float = 0.001
    bh_curve: BHCurve | None = None

    def __post_init__(self):
        if not self.loads or self.mode not in ("linear", "nonlinear"):
            raise ValueError("Loads and supported transformer mode are required")
        if not 0 < self.coupling <= 1 or self.mains_resistance_ohm <= 0:
            raise ValueError("Invalid magnetic coupling or mains resistance")
        if min(self.diode_saturation_current_a, self.diode_series_resistance_ohm,
               self.diode_emission_coefficient, self.conduction_threshold_a,
               self.no_load_resistance_ohm, self.sense_resistance_ohm,
               self.diode_junction_capacitance_f, self.diode_transit_time_s,
               self.secondary_shunt_resistance_ohm) <= 0:
            raise ValueError("Invalid circuit parameter")
        if self.cycles < 3 or self.measurement_cycles < 1 or self.measurement_cycles >= self.cycles:
            raise ValueError("Invalid simulation window")
        if self.samples_per_cycle < 50:
            raise ValueError("At least 50 samples per mains cycle are required")
        if self.mode == "nonlinear" and self.bh_curve is None:
            raise ValueError("A signed B-H curve is required for nonlinear mode")
        if self.mains_voltage_rms is not None and self.mains_voltage_rms <= 0:
            raise ValueError("Mains voltage override must be positive")


@dataclass(frozen=True)
class NgSpiceResult:
    model: str
    physical_material_data: bool
    mains_voltage_rms: float
    switch_phase_deg: float
    primary_rms_current_a: float
    secondary_rms_voltage_v: tuple[float, ...]
    secondary_rms_current_a: tuple[float, ...]
    secondary_peak_current_a: tuple[float, ...]
    secondary_steady_peak_current_a: tuple[float, ...]
    secondary_crest_factor: tuple[float, ...]
    no_load_current_a: float
    copper_loss_w: float
    estimated_copper_temperature_c: float
    peak_flux_density_t: float
    peak_primary_current_a: float
    steady_primary_peak_current_a: float
    regulation_percent: tuple[float, ...]
    inrush_peak_a: float
    rectified_dc_voltage_v: tuple[float, ...]
    dc_rail_sag_v: tuple[float, ...]
    dc_ripple_pp_v: tuple[float, ...]
    dc_rail_min_v: tuple[float, ...]
    dc_rail_max_v: tuple[float, ...]
    diode_conduction_angle_deg: tuple[float, ...]
