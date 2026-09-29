from pathlib import Path
import numpy as np
from scipy.integrate import trapezoid
from .deck import NgSpiceTransformerDeck
from .result import NgSpiceResult
from ...physics.thermal import thermal_estimate


def read_samples(path: Path, secondaries: int) -> np.ndarray:
    data = np.loadtxt(path, ndmin=2)
    expected = 1 + 3 + 4 * secondaries
    if data.shape[1] != expected or len(data) < 100:
        raise ValueError(f"Expected at least 100 rows and {expected} ngspice columns, got {data.shape}")
    if not np.isfinite(data).all() or np.any(np.diff(data[:, 0]) <= 0):
        raise ValueError("ngspice output has nonfinite or nonmonotonic samples")
    return data


def _window(data: np.ndarray, start: float, end: float) -> np.ndarray:
    if start < data[0, 0] or end > data[-1, 0] + 1e-9 or end <= start:
        raise ValueError("ngspice output does not cover the requested full-cycle window")
    interior = data[(data[:, 0] > start) & (data[:, 0] < end)]
    boundaries = [np.array([time, *(np.interp(time, data[:, 0], data[:, col])
                                  for col in range(1, data.shape[1]))])
                  for time in (start, end)]
    result = np.vstack((boundaries[0], interior, boundaries[1]))
    if len(result) < 10:
        raise ValueError("ngspice did not produce enough samples in the requested window")
    return result


def _average(data: np.ndarray, column: int) -> float:
    return float(trapezoid(data[:, column], data[:, 0]) / (data[-1, 0] - data[0, 0]))


def _rms(data: np.ndarray, column: int) -> float:
    return float(np.sqrt(trapezoid(data[:, column]**2, data[:, 0]) /
                         (data[-1, 0] - data[0, 0])))


def parse_results(deck: NgSpiceTransformerDeck, loaded: np.ndarray,
                  unloaded: np.ndarray) -> NgSpiceResult:
    spec, config = deck.spec, deck.config
    circuit = deck.circuit()
    stop = config.cycles / spec.mains_frequency
    start = (config.cycles - config.measurement_cycles) / spec.mains_frequency
    on = _window(loaded, start, stop)
    off = _window(unloaded, start, stop)
    rms_primary = _rms(on, 2)
    no_load_current = _rms(off, 2)
    vac, sec_i, sec_peak, sec_steady_peak, crest, vdc, sag, ripple, rail_min, rail_max, angles, regulation = ([] for _ in range(12))
    for index, resistance in enumerate(circuit.secondary_resistances_ohm):
        base = 4 + 4 * index
        loaded_vac, unloaded_vac = _rms(on, base), _rms(off, base)
        current = _rms(on, base + 1) / config.sense_resistance_ohm
        peak = float(np.max(np.abs(loaded[:, base + 1]))) / config.sense_resistance_ohm
        steady_peak = float(np.max(np.abs(on[:, base + 1]))) / config.sense_resistance_ohm
        loaded_dc, unloaded_dc = _average(on, base + 2), _average(off, base + 2)
        conducting = (np.abs(on[:, base + 3]) / config.sense_resistance_ohm >=
                      config.conduction_threshold_a)
        angle = 360 * trapezoid(conducting.astype(float), on[:, 0]) / (on[-1, 0] - on[0, 0])
        vac.append(loaded_vac)
        sec_i.append(current)
        sec_peak.append(peak)
        sec_steady_peak.append(steady_peak)
        crest.append(steady_peak / current if current else 0.0)
        vdc.append(loaded_dc)
        sag.append(unloaded_dc - loaded_dc)
        ripple.append(float(np.ptp(on[:, base + 2])))
        rail_min.append(float(np.min(on[:, base + 2])))
        rail_max.append(float(np.max(on[:, base + 2])))
        angles.append(float(angle))
        regulation.append(100 * (unloaded_vac - loaded_vac) / loaded_vac if loaded_vac else 0.0)
    # Integrate terminal voltage over the steady window. Removing linear
    # numerical drift gives AC peak B; remanence is not inferred from this.
    dt = np.diff(on[:, 0])
    integrated = np.r_[0.0, np.cumsum((on[:-1, 3] + on[1:, 3]) * dt / 2)]
    trend = np.linspace(integrated[0], integrated[-1], len(integrated))
    flux = (integrated - trend) / (deck.evaluation.primary_turns *
                                  deck.candidate.core.effective_cross_section)
    b_peak = float(np.ptp(flux) / 2)
    startup = _window(loaded, 0, 1 / spec.mains_frequency)
    copper_loss = rms_primary**2 * circuit.primary_resistance_ohm + sum(
        current**2 * resistance for current, resistance in zip(
            sec_i, circuit.secondary_resistances_ohm, strict=True))
    core_loss = _rms(on, 3)**2 / circuit.core_loss_resistance_ohm
    thermal = thermal_estimate(spec.ambient_temperature, core_loss,
        copper_loss, spec.core_thermal_resistance, spec.copper_thermal_resistance)
    bh_physical = config.mode == "nonlinear" and config.bh_curve.measured
    remanence_modeled = False  # The present core deck has no initial magnetic state.
    return NgSpiceResult(
        model=config.mode,
        physical_material_data=(bh_physical and circuit.core_loss_data_physical
                                and remanence_modeled),
        bh_data_physical=bh_physical,
        core_loss_data_physical=circuit.core_loss_data_physical,
        remanence_modeled=remanence_modeled,
        magnetic_inrush_valid=False,
        magnetic_inrush_peak_a=None,
        mains_voltage_rms=config.mains_voltage_rms or spec.mains_voltage,
        switch_phase_deg=config.switch_phase_deg, primary_rms_current_a=rms_primary,
        secondary_rms_voltage_v=tuple(vac), secondary_rms_current_a=tuple(sec_i),
        secondary_peak_current_a=tuple(sec_peak),
        secondary_steady_peak_current_a=tuple(sec_steady_peak),
        secondary_crest_factor=tuple(crest),
        no_load_current_a=no_load_current,
        copper_loss_w=copper_loss,
        core_loss_w=core_loss,
        estimated_copper_temperature_c=thermal.copper_temperature,
        winding_resistance_temperature_c=(deck.winding_temperature_c
            if deck.winding_temperature_c is not None else
            deck.evaluation.estimated_copper_temperature),
        thermal_iterations=1,
        primary_resistance_ohm=circuit.primary_resistance_ohm,
        secondary_resistances_ohm=circuit.secondary_resistances_ohm,
        peak_flux_density_t=b_peak,
        peak_primary_current_a=float(np.max(np.abs(loaded[:, 2]))),
        steady_primary_peak_current_a=float(np.max(np.abs(on[:, 2]))),
        regulation_percent=tuple(regulation),
        startup_primary_peak_a=float(np.max(np.abs(startup[:, 2]))),
        rectified_dc_voltage_v=tuple(vdc), dc_rail_sag_v=tuple(sag),
        dc_ripple_pp_v=tuple(ripple), dc_rail_min_v=tuple(rail_min),
        dc_rail_max_v=tuple(rail_max), diode_conduction_angle_deg=tuple(angles))
