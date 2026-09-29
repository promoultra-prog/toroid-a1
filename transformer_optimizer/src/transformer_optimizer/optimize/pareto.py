from dataclasses import dataclass
from typing import Sequence
from ..engine.candidate import TransformerCandidate
from ..models.result import CandidateEvaluation


@dataclass
class OptimizationResult:
    candidates: list[TransformerCandidate]
    evaluations: list[CandidateEvaluation]
    objectives: list[tuple[float, float, float]]

    @property
    def dataframe(self):
        from ..reports.dataframe import to_dataframe
        return to_dataframe(self)


def nondominated(evaluations: Sequence[CandidateEvaluation]) -> list[int]:
    values = [(r.total_loss, r.total_mass, r.regulation_percent) for r in evaluations]
    return [i for i, a in enumerate(values) if not any(
        j != i and all(bk <= ak for bk, ak in zip(b, a, strict=True)) and
        any(bk < ak for bk, ak in zip(b, a, strict=True))
        for j, b in enumerate(values))]


def rank_shortlist(result: OptimizationResult, weights: tuple[float, float, float]):
    if len(weights) != 3 or any(w < 0 for w in weights) or sum(weights) <= 0:
        raise ValueError("Provide three nonnegative weights with positive sum")
    if not result.objectives:
        return []
    mins = [min(row[i] for row in result.objectives) for i in range(3)]
    spans = [max(row[i] for row in result.objectives) - mins[i] for i in range(3)]
    return sorted(range(len(result.objectives)), key=lambda j: sum(
        weights[i] * (result.objectives[j][i] - mins[i]) / (spans[i] or 1.0) for i in range(3)))
