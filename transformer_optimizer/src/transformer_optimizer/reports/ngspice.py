from dataclasses import asdict
from ..optimize.pareto import OptimizationResult
from ..simulation.ngspice.result import NgSpiceResult


def with_ngspice_results(pareto: OptimizationResult,
                        simulations: dict[int, NgSpiceResult]):
    """Attach post-search runs; do not imply physical candidate validation."""
    report = pareto.dataframe.copy()
    for index in simulations:
        if index < 0 or index >= len(report):
            raise IndexError(f"Pareto row {index} is out of range")
    report["ngspice_simulated"] = False
    report["physical_validation_complete"] = False
    for index, result in simulations.items():
        report.at[index, "ngspice_simulated"] = True
        for name, value in asdict(result).items():
            column = f"ngspice_{name}"
            if column not in report.columns:
                report[column] = None
            report.at[index, column] = value
    return report
