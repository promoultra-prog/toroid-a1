from math import isfinite
from ..models.result import CandidateEvaluation
from ..models.specs import TransformerSpec
from ..physics.magnetic import primary_turns, secondary_turns, flux_density, volts_per_turn, estimate_magnetizing_current
from ..physics.geometry import winding_geometry, window_fill_ratio, GeometryError
from ..physics.copper import resistance, copper_loss, copper_mass
from ..physics.core_loss import CoreLossModel, SteinmetzCoreLoss
from ..physics.electrical import full_load_voltage, regulation_percent
from ..physics.thermal import thermal_estimate
from .candidate import TransformerCandidate
from .constraints import violations


class ToroidalTransformerModel:
    def __init__(self, core_loss_model: CoreLossModel | None = None):
        self.core_loss_model = core_loss_model

    def evaluate(self, spec: TransformerSpec, candidate: TransformerCandidate) -> CandidateEvaluation:
        result = CandidateEvaluation()
        core = candidate.core
        if candidate.design_flux_density <= 0:
            result.violations = ["design flux density"]
            return result
        secondaries = spec.expanded_secondaries
        area = core.effective_cross_section
        n_primary = primary_turns(spec.mains_voltage, spec.mains_frequency,
                                  candidate.design_flux_density, area)
        b_nominal = flux_density(spec.mains_voltage, spec.mains_frequency, n_primary, area)
        b_max = flux_density(spec.mains_max_voltage, spec.mains_frequency, n_primary, area)
        loss_model = self.core_loss_model or SteinmetzCoreLoss(core.material)
        p_core = loss_model.loss_density(spec.mains_frequency, b_nominal, spec.ambient_temperature) * core.core_mass
        vpt = volts_per_turn(spec.mains_voltage, n_primary)
        ns = tuple(secondary_turns(s.voltage_rms, vpt) for s in secondaries)
        pgeom = None
        sgeom = ()
        for _ in range(10):
            try:
                pgeom = winding_geometry(core, n_primary, candidate.primary_wire,
                    spec.core_insulation, spec.winding_coverage, spec.minimum_remaining_inner_diameter)
                build = pgeom.inner_build + spec.interwinding_insulation
                geometries = []
                for turns in ns:
                    geom = winding_geometry(core, turns, candidate.secondary_wire, build,
                        spec.winding_coverage, spec.minimum_remaining_inner_diameter)
                    geometries.append(geom)
                    build = geom.inner_build + spec.interwinding_insulation
                sgeom = tuple(geometries)
            except GeometryError as exc:
                result.violations = [str(exc)]
                return result
            rp = resistance(candidate.primary_wire, pgeom.total_wire_length, spec.ambient_temperature)
            rs = tuple(resistance(candidate.secondary_wire, g.total_wire_length,
                                  spec.ambient_temperature) for g in sgeom)
            ip = (spec.output_va + p_core + sum(s.current_rms**2 * r for s, r in zip(secondaries, rs, strict=True))) / spec.mains_voltage
            corrected = tuple(max(n, secondary_turns(
                s.voltage_rms + s.current_rms * r + ip * rp * n / n_primary, vpt))
                for s, r, n in zip(secondaries, rs, ns, strict=True))
            if corrected == ns:
                break
            ns = corrected
        else:
            result.violations = ["secondary turns did not converge"]
            return result

        temperature = spec.ambient_temperature
        for _ in range(100):
            rp = resistance(candidate.primary_wire, pgeom.total_wire_length, temperature)
            rs = tuple(resistance(candidate.secondary_wire, g.total_wire_length, temperature) for g in sgeom)
            # Apparent-load estimate; phase angle and iron-loss current are not resolved.
            ip = (spec.output_va + p_core + sum(s.current_rms**2 * r for s, r in zip(secondaries, rs, strict=True))) / spec.mains_voltage
            pcu_p = copper_loss(ip, rp)
            pcu_s = sum(copper_loss(s.current_rms, r) for s, r in zip(secondaries, rs, strict=True))
            thermal = thermal_estimate(spec.ambient_temperature, p_core, pcu_p + pcu_s,
                spec.core_thermal_resistance, spec.copper_thermal_resistance)
            if not isfinite(thermal.copper_temperature) or thermal.copper_temperature > 1e4:
                result.violations = ["thermal calculation diverged"]
                return result
            if abs(thermal.copper_temperature - temperature) < 0.01:
                break
            temperature = thermal.copper_temperature
        else:
            result.violations = ["thermal calculation did not converge"]
            return result
        no_load = tuple(vpt * n for n in ns)
        loaded = tuple(full_load_voltage(v, s.current_rms, r, ip, rp, n / n_primary)
            for v, s, r, n in zip(no_load, secondaries, rs, ns, strict=True))
        if any(v <= 0 for v in loaded):
            result.violations = ["nonpositive loaded secondary voltage"]
            return result
        p_copper = pcu_p + pcu_s
        m_copper = copper_mass(candidate.primary_wire, pgeom.total_wire_length) + sum(
            copper_mass(candidate.secondary_wire, g.total_wire_length) for g in sgeom)
        remaining = sgeom[-1].remaining_inner_diameter
        result = CandidateEvaluation(
            primary_turns=n_primary, secondary_turns=ns,
            b_nominal=b_nominal, b_max_mains=b_max,
            primary_current_density=candidate.primary_wire.current_density(ip),
            secondary_current_density=tuple(candidate.secondary_wire.current_density(s.current_rms) for s in secondaries),
            primary_wire_length=pgeom.total_wire_length,
            secondary_wire_length=tuple(g.total_wire_length for g in sgeom),
            primary_resistance=rp, secondary_resistance=rs,
            primary_copper_loss=pcu_p, secondary_copper_loss=pcu_s,
            core_loss=p_core, total_loss=p_core + p_copper,
            efficiency=sum(v * s.current_rms for v, s in zip(loaded, secondaries, strict=True)) /
                (sum(v * s.current_rms for v, s in zip(loaded, secondaries, strict=True)) + p_core + p_copper),
            secondary_voltage_no_load=no_load, secondary_voltage_full_load=loaded,
            regulation_percent=max(regulation_percent(u, v) for u, v in zip(no_load, loaded, strict=True)),
            core_mass=core.core_mass, copper_mass=m_copper, total_mass=core.core_mass + m_copper,
            remaining_inner_diameter=remaining, fill_ratio=window_fill_ratio(core, remaining),
            estimated_core_temperature=thermal.core_temperature,
            estimated_copper_temperature=thermal.copper_temperature,
            magnetizing_current=estimate_magnetizing_current(spec.mains_frequency, n_primary, area,
                core.mean_magnetic_path, b_nominal, spec.relative_permeability_estimate),
            winding_geometries=(pgeom, *sgeom),
        )
        result.violations = violations(spec, result)
        result.valid = not result.violations
        return result
