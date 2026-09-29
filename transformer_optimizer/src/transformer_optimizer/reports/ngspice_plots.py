"""Save electrical demonstration plots without opening GUI windows."""

from pathlib import Path
import numpy as np


def _pyplot():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def _save(fig, path: Path, plt):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def save_waveform_plots(deck, loaded: np.ndarray, output_dir: Path) -> tuple[Path, ...]:
    """Save startup and steady waveforms from the final thermal iteration."""
    plt = _pyplot()
    output_dir = Path(output_dir)
    frequency = deck.spec.mains_frequency
    startup = loaded[loaded[:, 0] <= 3 / frequency]
    steady = loaded[loaded[:, 0] >= (
        deck.config.cycles - deck.config.measurement_cycles) / frequency]
    count = len(deck.config.loads)
    saved = []

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(startup[:, 0] * 1000, -startup[:, 2], label="Primary current")
    for index in range(count):
        ax.plot(startup[:, 0] * 1000,
                startup[:, 5 + 4 * index] / deck.config.sense_resistance_ohm,
                label=f"Secondary {index + 1} current", alpha=.75)
    ax.set(xlabel="Time (ms)", ylabel="Current (A)",
           title="Startup electrical currents (magnetic inrush unverified)")
    ax.grid(alpha=.25)
    ax.legend()
    saved.append(_save(fig, output_dir / "startup_currents.png", plt))

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(steady[:, 0] * 1000, -steady[:, 2], label="Primary current")
    for index in range(count):
        ax.plot(steady[:, 0] * 1000,
                steady[:, 5 + 4 * index] / deck.config.sense_resistance_ohm,
                label=f"Secondary {index + 1} current", alpha=.75)
    ax.set(xlabel="Time (ms)", ylabel="Current (A)",
           title="Winding currents: final measurement periods")
    ax.grid(alpha=.25)
    ax.legend()
    saved.append(_save(fig, output_dir / "steady_currents.png", plt))

    fig, ax = plt.subplots(figsize=(10, 4.5))
    for index in range(count):
        ax.plot(steady[:, 0] * 1000, steady[:, 6 + 4 * index],
                label=f"DC rail {index + 1}")
    ax.set(xlabel="Time (ms)", ylabel="Rail voltage (V)",
           title="Rectified DC rails: final measurement periods")
    ax.grid(alpha=.25)
    ax.legend()
    saved.append(_save(fig, output_dir / "dc_rails.png", plt))
    return tuple(saved)


def save_startup_sweep_plot(peaks: dict[tuple[float, float], float], path: Path) -> Path:
    """Save first-cycle primary peaks versus switch-on phase for each line voltage."""
    if not peaks:
        raise ValueError("Startup sweep has no cases")
    plt = _pyplot()
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for voltage in sorted({case[0] for case in peaks}):
        phases = sorted(phase for line, phase in peaks if line == voltage)
        ax.plot(phases, [peaks[(voltage, phase)] for phase in phases], "o-",
                label=f"{voltage:g} V")
    ax.set(xlabel="Switch-on phase (degrees)", ylabel="First-cycle primary peak (A)",
           title="Electrical startup stress (magnetic inrush unverified)")
    ax.grid(alpha=.25)
    ax.legend(title="Mains RMS")
    return _save(fig, Path(path), plt)
