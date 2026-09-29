from math import isfinite, pi
from ...models.specs import TransformerSpec
from ...models.result import CandidateEvaluation
from ...engine.candidate import TransformerCandidate
from .adapter import PyOpenMagneticsAdapter
from .mas_builder import build_mas
from .material_adapter import SteelDataset, load_reference_steel, require_mkf_material
from .result import OpenMagneticsValidation


def _difference_pct(external: float, ours: float) -> float:
    return 100 * (external - ours) / ours


class OpenMagneticsValidator:
    def __init__(self, material: SteelDataset | None = None, registered_material_name: str | None = None,
                 adapter=None):
        self.material = material or load_reference_steel()
        self.registered_material_name = registered_material_name
        self.adapter = adapter or PyOpenMagneticsAdapter()

    def validate(self, spec: TransformerSpec, candidate: TransformerCandidate,
                 evaluation: CandidateEvaluation) -> OpenMagneticsValidation:
        result = OpenMagneticsValidation(
            our_core_loss_w=evaluation.core_loss,
            our_winding_loss_w=evaluation.primary_copper_loss + evaluation.secondary_copper_loss)
        if not evaluation.valid:
            result.warnings.append("Candidate is invalid in the analytical model")
            return result
        try:
            material_name = require_mkf_material(self.material, self.registered_material_name,
                                                  spec.mains_frequency, evaluation.b_nominal)
            if candidate.core.material.name != self.material.grade:
                raise ValueError("Candidate steel grade differs from the registered dataset")
            if candidate.core.density != self.material.density_kg_m3:
                raise ValueError("Candidate steel density differs from the dataset")
            if candidate.core.stacking_factor < self.material.minimum_stacking_factor:
                raise ValueError("Candidate stacking factor is below the published minimum")
            mas = build_mas(spec, candidate, evaluation, material_name)
            external = self.adapter.calculate(mas, evaluation.estimated_copper_temperature)
            for key in ("core_loss_w", "winding_loss_w", "inductance_h"):
                value = float(external[key])
                if not isfinite(value) or value <= 0:
                    raise ValueError(f"OpenMagnetics returned invalid {key}")
                setattr(result, key, value)
            result.core_temperature_c = external.get("core_temperature_c")
            result.magnetizing_current_a = spec.mains_voltage / (
                2 * pi * spec.mains_frequency * result.inductance_h)
            result.core_loss_error_pct = _difference_pct(result.core_loss_w, result.our_core_loss_w)
            result.winding_loss_error_pct = _difference_pct(result.winding_loss_w, result.our_winding_loss_w)
            result.available = True
        except Exception as exc:  # External bindings raise their own EngineError type.
            result.available = False
            result.core_loss_w = result.winding_loss_w = result.inductance_h = None
            result.magnetizing_current_a = result.core_loss_error_pct = result.winding_loss_error_pct = None
            result.warnings.append(f"OpenMagnetics cross-check unavailable: {exc}")
        return result
