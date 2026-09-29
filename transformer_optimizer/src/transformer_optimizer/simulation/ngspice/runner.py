from pathlib import Path
from dataclasses import replace
from math import isfinite
import numpy as np
import shutil
import subprocess
import sys
import tempfile
from .deck import NgSpiceTransformerDeck
from .parser import read_samples, parse_results
from .result import NgSpiceResult


class NgSpiceExecutionError(RuntimeError):
    pass


class NgSpiceRunner:
    def __init__(self, executable: str | None = None, timeout_s: float = 120.0):
        self.executable = executable or shutil.which("ngspice")
        if self.executable is None:
            raise NgSpiceExecutionError("ngspice executable was not found")
        self.timeout_s = timeout_s

    def _run_deck(self, deck: NgSpiceTransformerDeck, directory: Path, no_load: bool):
        directory.mkdir()
        netlist = directory / "transformer.cir"
        netlist.write_text(deck.render(no_load=no_load), encoding="ascii")
        launch_options = {}
        if sys.platform == "win32":
            # The Windows ngspice CLI may be a .cmd wrapper. Hide both its
            # console and the ngspice process it launches.
            startup = subprocess.STARTUPINFO()
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = subprocess.SW_HIDE
            launch_options = {"creationflags": subprocess.CREATE_NO_WINDOW,
                              "startupinfo": startup}
        try:
            process = subprocess.run([self.executable, "-b", str(netlist)], cwd=directory,
                                     stdin=subprocess.DEVNULL, capture_output=True,
                                     text=True, timeout=self.timeout_s, **launch_options)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise NgSpiceExecutionError(f"ngspice invocation failed: {exc}") from exc
        samples = directory / "samples.dat"
        if process.returncode != 0 or not samples.is_file():
            raise NgSpiceExecutionError(
                f"ngspice failed ({process.returncode}):\n{process.stdout[-3000:]}\n{process.stderr[-3000:]}")
        try:
            data = read_samples(samples, len(deck.config.loads))
            expected_stop = deck.config.cycles / deck.spec.mains_frequency
            if data[-1, 0] < expected_stop * 0.99:
                raise ValueError(f"Transient stopped at {data[-1, 0]:.6g} s before {expected_stop:.6g} s")
            return data
        except ValueError as exc:
            raise NgSpiceExecutionError(
                f"Invalid ngspice output: {exc}\n{process.stdout[-3000:]}\n{process.stderr[-3000:]}") from exc

    def run(self, deck: NgSpiceTransformerDeck,
            plots_dir: Path | None = None,
            plot_banner: str | None = None,
            plot_filename_prefix: str = "") -> NgSpiceResult:
        with tempfile.TemporaryDirectory(prefix="toroid-ngspice-") as temporary:
            root = Path(temporary)
            temperature = (deck.winding_temperature_c if deck.winding_temperature_c is not None
                           else deck.evaluation.estimated_copper_temperature)
            core_resistance = deck.core_loss_resistance_ohm
            for iteration in range(1, deck.config.thermal_max_iterations + 1):
                current = replace(deck, winding_temperature_c=temperature,
                                  core_loss_resistance_ohm=core_resistance)
                loaded = self._run_deck(current, root / f"loaded-{iteration}", no_load=False)
                unloaded = self._run_deck(current, root / f"unloaded-{iteration}", no_load=True)
                result = parse_results(current, loaded, unloaded)
                next_temperature = result.estimated_copper_temperature_c
                if not isfinite(next_temperature) or next_temperature > 1e4:
                    raise NgSpiceExecutionError("ngspice thermal feedback diverged")
                if (abs(next_temperature - temperature) <= deck.config.thermal_tolerance_c and
                        result.core_loss_relative_error <=
                        deck.config.core_loss_relative_tolerance):
                    if plots_dir is not None:
                        from ...reports.ngspice_plots import save_waveform_plots
                        save_waveform_plots(current, loaded, Path(plots_dir),
                                            banner=plot_banner,
                                            filename_prefix=plot_filename_prefix)
                    return replace(result, thermal_iterations=iteration)
                temperature = next_temperature
                core_resistance = (result.primary_magnetic_voltage_rms_v**2 /
                                   result.core_loss_target_w)
                if not isfinite(core_resistance) or core_resistance <= 0:
                    raise NgSpiceExecutionError("ngspice core-loss feedback diverged")
            raise NgSpiceExecutionError("ngspice thermal/core-loss feedback did not converge")

    def sweep(self, deck: NgSpiceTransformerDeck, mains_voltages: tuple[float, ...],
              phases_deg: tuple[float, ...]) -> dict[tuple[float, float], NgSpiceResult]:
        """Run selected line-voltage and switch-on phase combinations after optimization."""
        return {(voltage, phase): self.run(replace(deck, config=replace(
            deck.config, mains_voltage_rms=voltage, switch_phase_deg=phase)))
            for voltage in mains_voltages for phase in phases_deg}

    def sweep_startup(self, deck: NgSpiceTransformerDeck,
                      mains_voltages: tuple[float, ...],
                      phases_deg: tuple[float, ...],
                      plot_path: Path | None = None,
                      plot_banner: str | None = None) -> dict[tuple[float, float], float]:
        """First-cycle primary peaks; no magnetic-inrush validity is implied."""
        peaks = {}
        with tempfile.TemporaryDirectory(prefix="toroid-ngspice-startup-") as temporary:
            root = Path(temporary)
            for voltage_index, voltage in enumerate(mains_voltages):
                for phase_index, phase in enumerate(phases_deg):
                    case = replace(deck, config=replace(
                        deck.config, mains_voltage_rms=voltage, switch_phase_deg=phase,
                        cycles=3, measurement_cycles=1))
                    samples = self._run_deck(case, root / f"v{voltage_index}-p{phase_index}",
                                             no_load=False)
                    startup = samples[samples[:, 0] <= 1 / deck.spec.mains_frequency]
                    peaks[(voltage, phase)] = float(np.max(np.abs(startup[:, 2])))
        if plot_path is not None:
            from ...reports.ngspice_plots import save_startup_sweep_plot
            save_startup_sweep_plot(peaks, Path(plot_path), banner=plot_banner)
        return peaks
