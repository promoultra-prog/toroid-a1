import numpy as np
from pymoo.core.problem import ElementwiseProblem
from ..engine.candidate import CandidateGenerator, TransformerSearchSpace
from ..engine.transformer import ToroidalTransformerModel
from ..models.specs import TransformerSpec


class TransformerProblem(ElementwiseProblem):
    def __init__(self, spec: TransformerSpec, space: TransformerSearchSpace,
                 model: ToroidalTransformerModel | None = None):
        self.spec = spec
        self.generator = CandidateGenerator(space)
        self.model = model or ToroidalTransformerModel()
        bounds = np.asarray(space.bounds, dtype=float)
        super().__init__(n_var=8, n_obj=3, n_ieq_constr=1,
                         xl=bounds[:, 0], xu=bounds[:, 1])

    def _evaluate(self, x, out, *args, **kwargs):
        candidate = self.generator.from_vector(x)
        if candidate is None:
            out["F"] = [1e9, 1e9, 1e9]
            out["G"] = [1e3]
            return
        result = self.model.evaluate(self.spec, candidate)
        if not result.valid:
            # Continuous penalty guides NSGA-II across integer-turn discontinuities.
            # Invalid states stay explicit in CandidateEvaluation.
            severity = len(result.violations)
            if result.total_loss > 0:
                severity += max(0, result.b_max_mains / self.spec.max_flux_density - 1)
                severity += max(0, result.primary_current_density / self.spec.max_current_density_primary - 1)
                severity += max(0, result.estimated_copper_temperature / self.spec.maximum_copper_temperature - 1)
            out["F"] = [result.total_loss or 1e6, result.total_mass or 1e6,
                        result.regulation_percent or 1e6]
            out["G"] = [severity]
            return
        out["F"] = [result.total_loss, result.total_mass, result.regulation_percent]
        out["G"] = [-1.0]
