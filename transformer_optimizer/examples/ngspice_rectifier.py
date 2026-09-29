import argparse
from pathlib import Path

from transformer_optimizer import (
    CoreMaterial, SecondarySpec, TransformerSearchSpace, TransformerSpec, optimize_transformer
)
from transformer_optimizer.simulation.ngspice import (
    NgSpiceConfig, NgSpiceRunner, NgSpiceTransformerDeck, RectifierLoad
)
from transformer_optimizer.reports.ngspice import with_ngspice_results
from transformer_optimizer.reports.plots import plot_pareto


def main():
    parser = argparse.ArgumentParser(description="Run the ngspice rectifier example")
    parser.add_argument("--output-dir", type=Path,
                        default=Path(__file__).resolve().parents[1] / "output" / "ngspice_rectifier")
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    # Demonstrator circuit values only. Replace load and capacitor bank with A1 data.
    steel = CoreMaterial("example grain-oriented steel", 7650.0, 0.003, 1.5, 2.0)
    spec = TransformerSpec(230.0, 50.0, 253.0,
        (SecondarySpec(35.0, 7.0, quantity=2, maximum_no_load_voltage=39.0),),
        1.4, 2.5e6, 2.8e6, core_thermal_resistance=1.5,
        copper_thermal_resistance=1.5)
    space = TransformerSearchSpace(
        outer_diameter=(.15, .19), inner_diameter=(.08, .10), height=(.06, .08),
        design_flux_density=(1.1, 1.25), primary_wire_diameter=(.0013, .0016),
        secondary_wire_diameter=(.0023, .0029),
        secondary_parallel_count=(2, 2), material=steel)
    pareto = optimize_transformer(spec, space, population=20, generations=3, seed=3)
    if not pareto.candidates:
        raise RuntimeError("No feasible transformer candidate")
    config = NgSpiceConfig(loads=(RectifierLoad(.01, 12.0), RectifierLoad(.01, 12.0)))
    deck = NgSpiceTransformerDeck.from_candidate(spec, pareto.candidates[0],
                                                  pareto.evaluations[0], config)
    result = NgSpiceRunner().run(deck, plots_dir=output_dir)
    print(f"Model: {result.model}")
    print(f"Primary RMS: {result.primary_rms_current_a:.2f} A")
    print(f"Secondary RMS: {[round(x, 2) for x in result.secondary_rms_current_a]} A")
    print(f"Rectified DC: {[round(x, 2) for x in result.rectified_dc_voltage_v]} V")
    print(f"Copper loss with charging pulses: {result.copper_loss_w:.2f} W")
    print(f"Core loss at {result.mains_voltage_rms:.0f} V: {result.core_loss_w:.2f} W")
    print(f"Thermal feedback iterations: {result.thermal_iterations}")
    phases = (0, 15, 30, 45, 60, 75, 90)
    startup = NgSpiceRunner().sweep_startup(
        deck, (spec.mains_voltage,), phases,
        plot_path=output_dir / "startup_phase_sweep.png")
    worst_startup_primary_peak_a = max(startup.values())
    print(f"Largest first-cycle primary peak across {len(phases)} phases: "
          f"{worst_startup_primary_peak_a:.2f} A")
    print(f"Physical material data: {result.physical_material_data}")
    report = with_ngspice_results(pareto, {0: result})
    print(f"Pareto report: {len(report)} rows; ngspice validated: {int(report.ngspice_validated.sum())}")
    import matplotlib.pyplot as plt
    figure = plot_pareto(pareto)
    figure.savefig(output_dir / "pareto.png", dpi=160, bbox_inches="tight")
    plt.close(figure)
    print(f"Saved 5 PNG plots in {output_dir}")


if __name__ == "__main__":
    main()
