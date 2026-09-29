"""Read-only A1-B PSU reference: exact source includes, no core optimization."""

from dataclasses import asdict, dataclass
from hashlib import sha256
from math import sqrt
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile

import numpy as np
from scipy.integrate import trapezoid

from .ngspice.parser import _window


# Pinned A1-B source snapshot from 2026-09-30. Updating it requires reviewing
# the A1-B PSU changes and refreshing the reference results together.
SOURCE_SHA256 = {
    "lib/psu_main.inc": "7f8599f100b96c18f8a3c58d0e3f34286a6775965e5fae7cb0b1540472de1a4b",
    "lib/aux_supply.inc": "1f65baa3584dfb72bb3039f7c57798e53a6bed0dec96952ca0f91d90e9b0734c",
    "models/derived/SBR20A200CTB_element.inc": "dd7fdb3047d45bf87aa77fefbe9df8cb32e7f87157ebc7bbaacd866622196728",
    "models/derived/TDK_B41456B8339M600.inc": "a8a5827470d7278e475547aca734d8e61afc3b9fef2817a0121080f088133e08",
}

PROBES = (
    ("vcc", "v(vcc)"), ("vee", "v(vee)"),
    ("main1_v", "v(xpsu.ep)"), ("main2_v", "v(xpsu.en)"),
    ("aux1_v", "v(xpsu.eap)"), ("aux2_v", "v(xpsu.ean)"),
    ("main1_i", "i(v.xpsu.vsp)"), ("main2_i", "i(v.xpsu.vsn)"),
    ("aux1_i", "i(v.xpsu.vsap)"), ("aux2_i", "i(v.xpsu.vsan)"),
    ("primary_i", "i(vm)"),
    ("bridge1_i", "@d.xpsu.d1[id]"), ("bridge2_i", "@d.xpsu.d2[id]"),
    ("bridge3_i", "@d.xpsu.d3[id]"), ("bridge4_i", "@d.xpsu.d4[id]"),
    ("cap_pos_i", "i(l.xpsu.lbpesl)"), ("cap_neg_i", "i(l.xpsu.lbnesl)"),
    ("soft_start_i", "@r.xpsu.rss[i]"),
    ("aux_raw_pos_v", "v(auxrawp)"), ("aux_raw_neg_v", "v(auxrawn)"),
    ("aux_pos_v", "v(auxp)"), ("aux_neg_v", "v(auxn)"),
)
COL = {name: index + 1 for index, (name, _) in enumerate(PROBES)}


@dataclass(frozen=True)
class A1BReferenceCase:
    name: str
    mains_v: float
    main_pos_load_a: float = 1.5
    main_neg_load_a: float = 1.5
    aux_pos_load_a: float = 0.107
    aux_neg_load_a: float = 0.0044
    main_no_load_v: float = 23.1
    aux_no_load_v: float = 16.0
    capacitor_corner: str = "typ"
    bypass_phase_deg: float = 189.0

    def __post_init__(self):
        if not self.name.replace("_", "").isalnum():
            raise ValueError("Case name must be alphanumeric with underscores")
        if min(self.mains_v, self.main_no_load_v, self.aux_no_load_v) <= 0:
            raise ValueError("Supply voltages must be positive")
        if min(self.main_pos_load_a, self.main_neg_load_a,
               self.aux_pos_load_a, self.aux_neg_load_a) < 0:
            raise ValueError("Load currents must be nonnegative")
        if self.capacitor_corner not in ("typ", "cmin_esrmax"):
            raise ValueError("Unknown capacitor corner")
        if not 0 <= self.bypass_phase_deg < 360:
            raise ValueError("Bypass phase must be in [0, 360) degrees")

    @property
    def bypass_time_s(self) -> float:
        return (7 + self.bypass_phase_deg / 360) / 50


@dataclass(frozen=True)
class A1BReferenceResult:
    case: A1BReferenceCase
    source_sha256: dict[str, str]
    model_class: str
    physical_validation_complete: bool
    winding_irms_a: dict[str, float]
    winding_peak_a: dict[str, float]
    winding_steady_peak_a: dict[str, float]
    primary_irms_a: float
    primary_peak_a: float
    primary_steady_peak_a: float
    main_rail_average_v: dict[str, float]
    main_rail_min_v: dict[str, float]
    main_rail_max_v: dict[str, float]
    main_rail_ripple_vpp: dict[str, float]
    bridge_irms_a: dict[str, float]
    bridge_peak_a: dict[str, float]
    bridge_steady_peak_a: dict[str, float]
    capacitor_irms_a: dict[str, float]
    capacitor_peak_a: dict[str, float]
    capacitor_steady_peak_a: dict[str, float]
    soft_start_energy_j: float
    soft_start_peak_w: float
    primary_peak_before_bypass_a: float
    primary_peak_after_bypass_a: float
    rail_drift_v_per_cycle: float
    main_rails_settled: bool


def _average(data: np.ndarray, column: int) -> float:
    return float(trapezoid(data[:, column], data[:, 0]) / (data[-1, 0] - data[0, 0]))


def _rms(data: np.ndarray, column: int) -> float:
    return float(sqrt(_average(np.column_stack((data[:, 0], data[:, column] ** 2)), 1)))


def render_reference_deck(case: A1BReferenceCase) -> str:
    """Match scripts/chain/psu_2026.py and its selected A1-B PSU topology."""
    c, esr = ((.033, .006) if case.capacitor_corner == "typ" else (.0264, .012))
    tc = case.bypass_time_s
    vectors = " ".join(vector for _, vector in PROBES)
    return f"""A1-B PSU reference, {case.name}; transformer parasitics ASSUMED / NOT MEASURED
.include lib/psu_main.inc
.include lib/aux_supply.inc
VM L 0 SIN(0 {case.mains_v * sqrt(2):.6g} 50)
XPSU L 0 VCC VEE AUXRAWP AUXRAWN 0 SSBYP A1B_PSU_MAIN VMAIN={case.main_no_load_v:g} VAUX={case.aux_no_load_v:g} CRES={c:g} CAP_ESR={esr:g}
XAUX AUXRAWP AUXRAWN AUXP AUXN 0 A1B_AUX_SUPPLY
VB SSBYP 0 PWL(0 0 {tc - 50e-6:.6g} 0 {tc + 50e-6:.6g} 1)
BLP VCC 0 I={{{case.main_pos_load_a:g}*tanh(max(v(VCC),0)/2)}}
BLN 0 VEE I={{{case.main_neg_load_a:g}*tanh(max(-v(VEE),0)/2)}}
BLAP AUXP 0 I={{{case.aux_pos_load_a:g}*tanh(max(v(AUXP),0)/.5)}}
BLAN 0 AUXN I={{{case.aux_neg_load_a:g}*tanh(max(-v(AUXN),0)/.5)}}
.options reltol=1e-3 abstol=1e-8 vntol=1e-5 chgtol=1e-10 trtol=10 method=gear maxord=2
.control
set klu
set numdgt=15
set wr_vecnames
set wr_singlescale
save {vectors}
tran 5u .6 0 5u uic
wrdata {case.name}.dat {vectors}
quit
.endc
.end
"""


def _parse(case: A1BReferenceCase, path: Path,
           source_sha256: dict[str, str]) -> A1BReferenceResult:
    data = np.loadtxt(path, skiprows=1, ndmin=2)
    if (data.shape[1] != len(PROBES) + 1 or len(data) < 100 or
            not np.isfinite(data).all() or np.any(np.diff(data[:, 0]) <= 0) or
            data[-1, 0] < .599):
        raise ValueError("A1-B reference transient is missing, truncated or malformed")
    steady = _window(data, .5, .6)
    windings = {name: COL[f"{name.lower()}_i"] for name in ("MAIN1", "MAIN2", "AUX1", "AUX2")}
    bridges = {f"D{index}": COL[f"bridge{index}_i"] for index in range(1, 5)}
    capacitors = {"positive": COL["cap_pos_i"], "negative": COL["cap_neg_i"]}
    pos = steady[:, COL["vcc"]]
    neg = -steady[:, COL["vee"]]
    current = np.abs(data[:, COL["primary_i"]])
    before = data[:, 0] < case.bypass_time_s
    after = (data[:, 0] >= case.bypass_time_s) & (data[:, 0] < case.bypass_time_s + .1)
    if not before.any() or not after.any():
        raise ValueError("Bypass event is outside transient data")
    resistor_power = data[:, COL["soft_start_i"]] ** 2 * 47
    early = _window(data, .5, .52)
    late = _window(data, .58, .6)
    drift = max(abs(_average(late, COL["vcc"]) - _average(early, COL["vcc"])),
                abs(_average(late, COL["vee"]) - _average(early, COL["vee"]))) / 4
    return A1BReferenceResult(
        case=case, source_sha256=source_sha256,
        model_class="A1-B selected linear PSU; transformer parasitics assumed",
        physical_validation_complete=False,
        winding_irms_a={name: _rms(steady, col) for name, col in windings.items()},
        winding_peak_a={name: float(np.max(np.abs(data[:, col]))) for name, col in windings.items()},
        winding_steady_peak_a={name: float(np.max(np.abs(steady[:, col])))
                               for name, col in windings.items()},
        primary_irms_a=_rms(steady, COL["primary_i"]),
        primary_peak_a=float(np.max(current)),
        primary_steady_peak_a=float(np.max(np.abs(steady[:, COL["primary_i"]]))),
        main_rail_average_v={"positive": float(_average(steady, COL["vcc"])),
                             "negative": float(-_average(steady, COL["vee"]))},
        main_rail_min_v={"positive": float(np.min(pos)), "negative": float(np.min(neg))},
        main_rail_max_v={"positive": float(np.max(pos)), "negative": float(np.max(neg))},
        main_rail_ripple_vpp={"positive": float(np.ptp(pos)), "negative": float(np.ptp(neg))},
        bridge_irms_a={name: _rms(steady, col) for name, col in bridges.items()},
        bridge_peak_a={name: float(np.max(np.abs(data[:, col]))) for name, col in bridges.items()},
        bridge_steady_peak_a={name: float(np.max(np.abs(steady[:, col])))
                              for name, col in bridges.items()},
        capacitor_irms_a={name: _rms(steady, col) for name, col in capacitors.items()},
        capacitor_peak_a={name: float(np.max(np.abs(data[:, col]))) for name, col in capacitors.items()},
        capacitor_steady_peak_a={name: float(np.max(np.abs(steady[:, col])))
                                 for name, col in capacitors.items()},
        soft_start_energy_j=float(trapezoid(resistor_power[before], data[before, 0])),
        soft_start_peak_w=float(np.max(resistor_power)),
        primary_peak_before_bypass_a=float(np.max(current[before])),
        primary_peak_after_bypass_a=float(np.max(current[after])),
        rail_drift_v_per_cycle=drift, main_rails_settled=drift < .001)


def _save_plots(case: A1BReferenceCase, data: np.ndarray, output_dir: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    banner = "A1-B ELECTRICAL REFERENCE - TRANSFORMER PARAMETERS UNMEASURED"
    startup = data[data[:, 0] <= .25]
    steady = _window(data, .5, .6)
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(startup[:, 0] * 1000, -startup[:, COL["primary_i"]], label="Primary")
    for name in ("main1", "main2", "aux1", "aux2"):
        ax.plot(startup[:, 0] * 1000, startup[:, COL[f"{name}_i"]], label=name.upper(),
                alpha=.7)
    ax.axvline(case.bypass_time_s * 1000, color="black", linestyle="--",
               label="Bypass")
    ax.set(xlabel="Time (ms)", ylabel="Current (A)", title=banner)
    ax.grid(alpha=.25)
    ax.legend(ncol=3)
    fig.savefig(output_dir / f"{case.name}_startup.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(steady[:, 0] * 1000, steady[:, COL["vcc"]], label="+MAIN rail")
    ax.plot(steady[:, 0] * 1000, -steady[:, COL["vee"]], label="-MAIN magnitude")
    ax.set(xlabel="Time (ms)", ylabel="Rail magnitude (V)", title=banner)
    ax.grid(alpha=.25)
    ax.legend()
    fig.savefig(output_dir / f"{case.name}_rails.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


class A1BReferenceRunner:
    def __init__(self, source_root: Path, output_dir: Path,
                 executable: str | None = None, timeout_s: float = 180):
        self.source_root = Path(source_root).resolve()
        self.output_dir = Path(output_dir).resolve()
        if self.output_dir == self.source_root or self.output_dir.is_relative_to(self.source_root):
            raise ValueError("Reference outputs must not be written inside A1-B")
        self.executable = executable or shutil.which("ngspice")
        self.timeout_s = timeout_s
        if self.executable is None:
            raise FileNotFoundError("ngspice was not found")

    def stage_sources(self) -> dict[str, str]:
        hashes = {}
        for relative, expected in SOURCE_SHA256.items():
            source = (self.source_root / relative).resolve()
            if not source.is_relative_to(self.source_root):
                raise ValueError(f"Source path escapes A1-B root: {relative}")
            contents = source.read_bytes()
            digest = sha256(contents).hexdigest()
            if digest != expected:
                raise ValueError(f"A1-B source changed: {relative}; review and update pinned hash")
            destination = self.output_dir / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.parent.resolve().is_relative_to(self.source_root):
                raise ValueError("Reference output resolves inside A1-B")
            with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as stream:
                stream.write(contents)
                temporary = Path(stream.name)
            temporary.replace(destination)
            hashes[relative] = digest
        return hashes

    def run(self, case: A1BReferenceCase, save_plots: bool = True) -> A1BReferenceResult:
        hashes = self.stage_sources()
        deck = self.output_dir / f"{case.name}.cir"
        for suffix in ("cir", "dat", "log", "json"):
            path = self.output_dir / f"{case.name}.{suffix}"
            if path.is_symlink() or (path.exists() and path.stat().st_nlink > 1):
                raise ValueError(f"Unsafe reference output path: {path}")
        if save_plots:
            for suffix in ("startup.png", "rails.png"):
                path = self.output_dir / f"{case.name}_{suffix}"
                if path.is_symlink() or (path.exists() and path.stat().st_nlink > 1):
                    raise ValueError(f"Unsafe reference output path: {path}")
        deck.write_text(render_reference_deck(case), encoding="ascii")
        launch = {}
        if sys.platform == "win32":
            startup = subprocess.STARTUPINFO()
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = subprocess.SW_HIDE
            launch = {"creationflags": subprocess.CREATE_NO_WINDOW, "startupinfo": startup}
        process = subprocess.run([self.executable, "-b", str(deck)], cwd=self.output_dir,
                                 stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                 timeout=self.timeout_s, **launch)
        (self.output_dir / f"{case.name}.log").write_text(
            process.stdout + "\n" + process.stderr, encoding="utf-8")
        if process.returncode != 0:
            raise RuntimeError(f"A1-B ngspice failed: {process.stderr[-1500:]}")
        result = _parse(case, self.output_dir / f"{case.name}.dat", hashes)
        if save_plots:
            samples = np.loadtxt(self.output_dir / f"{case.name}.dat", skiprows=1, ndmin=2)
            _save_plots(case, samples, self.output_dir)
        (self.output_dir / f"{case.name}.json").write_text(
            json.dumps(asdict(result), indent=2), encoding="utf-8")
        return result


def reference_matrix() -> tuple[A1BReferenceCase, ...]:
    """Documented DC-load cases; heavy/program load awaits an A1-B envelope."""
    return tuple(
        A1BReferenceCase(f"a1b_{mains}_{label}", mains, pos, neg,
                         capacitor_corner=corner)
        for mains in (200, 230, 240, 253)
        for label, pos, neg, corner in (
            ("idle_typ", 1.5, 1.5, "typ"),
            ("unbalanced_cmin", 1.8, 1.5, "cmin_esrmax")))
