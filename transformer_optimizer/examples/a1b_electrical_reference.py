"""Replay A1-B's selected PSU includes read-only; no transformer optimization."""

import argparse
import csv
from dataclasses import asdict
import json
from pathlib import Path

from transformer_optimizer.simulation.a1b_reference import (
    A1BReferenceCase, A1BReferenceRunner, reference_matrix
)

PUBLISHED_RAIL_MIN_V = {
    "a1b_200_idle_typ": 25.16,
    "a1b_230_idle_typ": 29.29,
    "a1b_240_idle_typ": 30.66,
    "a1b_253_idle_typ": 32.46,
    "a1b_200_unbalanced_cmin": 24.80,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a1b-root", type=Path, required=True,
                        help="Read-only path to the A1-B project root")
    parser.add_argument("--output-dir", type=Path,
                        default=Path(__file__).resolve().parents[1] / "output" / "A1B_REFERENCE")
    parser.add_argument("--matrix", action="store_true",
                        help="Run 200/230/240/253 V × documented DC load cases")
    args = parser.parse_args()
    cases = (reference_matrix() if args.matrix else
             (A1BReferenceCase("a1b_230_idle_typ", 230),))
    runner = A1BReferenceRunner(args.a1b_root, args.output_dir)
    results = []
    for case in cases:
        result = runner.run(case)
        results.append(result)
        published = PUBLISHED_RAIL_MIN_V.get(case.name)
        if published is not None and abs(result.main_rail_min_v["positive"] - published) > .03:
            raise RuntimeError(f"{case.name}: rail minimum differs from A1-B published result")
        if not result.main_rails_settled:
            raise RuntimeError(f"{case.name}: MAIN rails did not settle")
        print(f"{case.name}: +rail min {result.main_rail_min_v['positive']:.3f} V, "
              f"-rail min {result.main_rail_min_v['negative']:.3f} V, "
              f"primary RMS {result.primary_irms_a:.3f} A, "
              f"MAIN rails settled={result.main_rails_settled}")
    summary = [{"case": result.case.name, "mains_v": result.case.mains_v,
                "main_load_pos_a": result.case.main_pos_load_a,
                "main_load_neg_a": result.case.main_neg_load_a,
                "primary_irms_a": result.primary_irms_a,
                "main1_irms_a": result.winding_irms_a["MAIN1"],
                "main2_irms_a": result.winding_irms_a["MAIN2"],
                "aux1_irms_a": result.winding_irms_a["AUX1"],
                "aux2_irms_a": result.winding_irms_a["AUX2"],
                "rail_pos_min_v": result.main_rail_min_v["positive"],
                "rail_neg_min_v": result.main_rail_min_v["negative"],
                "rail_pos_ripple_vpp": result.main_rail_ripple_vpp["positive"],
                "soft_start_energy_j": result.soft_start_energy_j,
                "rail_drift_v_per_cycle": result.rail_drift_v_per_cycle}
               for result in results]
    with (runner.output_dir / "matrix_summary.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=summary[0].keys())
        writer.writeheader()
        writer.writerows(summary)
    (runner.output_dir / "matrix_summary.json").write_text(
        json.dumps({"model_class": "A1-B linear PSU; transformer parasitics assumed",
                    "heavy_program_case": "not specified; not simulated",
                    "physical_validation_complete": False,
                    "cases": [asdict(result) for result in results]}, indent=2), encoding="utf-8")
    print(f"Source files were read only. Decks, results and PNGs: {runner.output_dir}")


if __name__ == "__main__":
    main()
