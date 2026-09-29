from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize
from ..engine.transformer import ToroidalTransformerModel
from ..models.specs import TransformerSpec
from ..engine.candidate import TransformerSearchSpace
from .problem import TransformerProblem
from .pareto import OptimizationResult, nondominated


def optimize_transformer(spec: TransformerSpec, search_space: TransformerSearchSpace,
                         population: int = 80, generations: int = 50, seed: int = 1,
                         model: ToroidalTransformerModel | None = None) -> OptimizationResult:
    problem = TransformerProblem(spec, search_space, model)
    algorithm = NSGA2(pop_size=population, eliminate_duplicates=True)
    run = minimize(problem, algorithm, ("n_gen", generations), seed=seed, verbose=False)
    # Keep valid non-dominated designs from the final population. pymoo's res.X
    # can be None when the search has no feasible point.
    population_x = run.pop.get("X")
    pairs = []
    seen = set()
    for row in population_x:
        candidate = problem.generator.from_vector(row)
        if candidate is None:
            continue
        evaluation = problem.model.evaluate(spec, candidate)
        key = (candidate.core.outer_diameter, candidate.core.inner_diameter,
               candidate.core.height, evaluation.primary_turns, evaluation.secondary_turns,
               candidate.primary_wire.wire.conductor_diameter,
               candidate.secondary_wire.wire.conductor_diameter,
               candidate.primary_wire.parallel_count, candidate.secondary_wire.parallel_count)
        if evaluation.valid and key not in seen:
            seen.add(key)
            pairs.append((candidate, evaluation))
    indices = nondominated([r for _, r in pairs])
    candidates = [pairs[i][0] for i in indices]
    evaluations = [pairs[i][1] for i in indices]
    objectives = [(r.total_loss, r.total_mass, r.regulation_percent) for r in evaluations]
    return OptimizationResult(candidates, evaluations, objectives)
