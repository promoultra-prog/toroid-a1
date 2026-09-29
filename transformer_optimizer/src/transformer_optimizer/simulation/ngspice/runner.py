from pathlib import Path
from dataclasses import replace
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

    def run(self, deck: NgSpiceTransformerDeck) -> NgSpiceResult:
        with tempfile.TemporaryDirectory(prefix="toroid-ngspice-") as temporary:
            root = Path(temporary)
            loaded = self._run_deck(deck, root / "loaded", no_load=False)
            unloaded = self._run_deck(deck, root / "unloaded", no_load=True)
            return parse_results(deck, loaded, unloaded)

    def sweep(self, deck: NgSpiceTransformerDeck, mains_voltages: tuple[float, ...],
              phases_deg: tuple[float, ...]) -> dict[tuple[float, float], NgSpiceResult]:
        """Run selected line-voltage and switch-on phase combinations after optimization."""
        return {(voltage, phase): self.run(replace(deck, config=replace(
            deck.config, mains_voltage_rms=voltage, switch_phase_deg=phase)))
            for voltage in mains_voltages for phase in phases_deg}
