from dataclasses import dataclass
from ...models.specs import TransformerSpec
from ...models.result import CandidateEvaluation
from ...engine.candidate import TransformerCandidate
from .result import NgSpiceConfig
from .transformer_model import circuit_transformer


def _number(value: float) -> str:
    return f"{value:.12g}"


def _array_lines(prefix: str, values: tuple[float, ...]) -> list[str]:
    chunks = [values[index:index + 8] for index in range(0, len(values), 8)]
    lines = [prefix + " ".join(_number(value) for value in chunks[0])]
    lines.extend("+ " + " ".join(_number(value) for value in chunk) for chunk in chunks[1:])
    lines[-1] += "]"
    return lines


@dataclass(frozen=True)
class NgSpiceTransformerDeck:
    spec: TransformerSpec
    candidate: TransformerCandidate
    evaluation: CandidateEvaluation
    config: NgSpiceConfig
    winding_temperature_c: float | None = None

    def circuit(self):
        if (self.config.bh_curve is not None and self.config.bh_curve.measured and
                self.config.bh_curve.material_name != self.candidate.core.material.name):
            raise ValueError("B-H data material does not match candidate steel")
        return circuit_transformer(
            self.spec, self.candidate, self.evaluation,
            self.config.mains_voltage_rms or self.spec.mains_voltage,
            self.winding_temperature_c if self.winding_temperature_c is not None
            else self.evaluation.estimated_copper_temperature,
            self.config.core_loss_model)

    @classmethod
    def from_candidate(cls, spec: TransformerSpec, candidate: TransformerCandidate,
                       evaluation: CandidateEvaluation, config: NgSpiceConfig):
        if len(config.loads) != len(spec.expanded_secondaries):
            raise ValueError("One rectifier load per independent secondary is required")
        if len(evaluation.secondary_turns) != len(config.loads):
            raise ValueError("Evaluation and load counts differ")
        if config.mode == "nonlinear" and len(config.loads) != 1:
            raise ValueError("Nonlinear XSPICE mode currently supports one secondary; multiwinding convergence is unverified")
        deck = cls(spec, candidate, evaluation, config)
        deck.circuit()
        return deck

    def render(self, no_load: bool = False) -> str:
        spec, config = self.spec, self.config
        circuit = self.circuit()
        step = 1 / (spec.mains_frequency * config.samples_per_cycle)
        stop = config.cycles / spec.mains_frequency
        mains_voltage = config.mains_voltage_rms or spec.mains_voltage
        lines = ["Toroidal transformer and rectifier validation",
                 f"* mode={config.mode} no_load={int(no_load)}",
                 ".options method=gear reltol=1e-4 gmin=1e-10 rshunt=1e12",
                 f"VMAINS source 0 SIN(0 {_number(mains_voltage * 2**0.5)} "
                 f"{_number(spec.mains_frequency)} 0 0 {_number(config.switch_phase_deg)})",
                 f"RMAINS source vin {_number(config.mains_resistance_ohm)}",
                 f"RCORE p 0 {_number(circuit.core_loss_resistance_ohm)}",
                 f".model DRECT D(Is={_number(config.diode_saturation_current_a)} "
                 f"Rs={_number(config.diode_series_resistance_ohm)} "
                 f"N={_number(config.diode_emission_coefficient)} "
                 f"Cjo={_number(config.diode_junction_capacitance_f)} "
                 f"Tt={_number(config.diode_transit_time_s)})"]
        if config.mode == "linear":
            lines.append(f"RPRI vin p {_number(circuit.primary_resistance_ohm)}")
            lines.append(f"LPRI p 0 {_number(circuit.primary_inductance_h)}")
            for index, ls in enumerate(circuit.secondary_inductances_h, 1):
                lines.append(f"LSEC{index} s{index}p s{index}n {_number(ls)}")
            names = " ".join(["LPRI", *(f"LSEC{i}" for i in range(1, len(config.loads) + 1))])
            lines.append(f"KALL {names} {_number(config.coupling)}")
        else:
            curve = config.bh_curve
            lines.append(f"RPRI vin p {_number(circuit.primary_resistance_ohm)}")
            lines.extend([
                "APRI (p 0) (mmf 0) LCPRI",
                f".model LCPRI lcouple(num_turns={self.evaluation.primary_turns})",
                "ACORE (mmf fluxnode) COREMODEL",
            ])
            lines.extend(_array_lines(".model COREMODEL core(H_array=[", curve.h_a_per_m))
            lines.extend(_array_lines("+ B_array=[", curve.b_t))
            lines.append(f"+ area={_number(self.candidate.core.effective_cross_section)} "
                         f"length={_number(self.candidate.core.mean_magnetic_path)})")
            for index, turns in enumerate(self.evaluation.secondary_turns, 1):
                mmf_in = "fluxnode" if index == 1 else f"mmf{index}"
                mmf_out = "0" if index == len(self.evaluation.secondary_turns) else f"mmf{index + 1}"
                lines.extend([f"ASEC{index} (s{index}p s{index}n) ({mmf_in} {mmf_out}) LCSEC{index}",
                              f".model LCSEC{index} lcouple(num_turns={turns})"])
        for index, (load, resistance) in enumerate(zip(config.loads,
                 circuit.secondary_resistances_ohm, strict=True), 1):
            rload = config.no_load_resistance_ohm if no_load else load.resistance_ohm
            lines.extend([
                f"RSEC{index} s{index}p ac{index}a {_number(resistance)}",
                f"RSHUNTSEC{index} s{index}p s{index}n "
                f"{_number(config.secondary_shunt_resistance_ohm)}",
                f"RSECSENSE{index} ac{index}b s{index}n {_number(config.sense_resistance_ohm)}",
                f"RDIODESENSE{index} ac{index}a d{index}a {_number(config.sense_resistance_ohm)}",
                f"D{index}A d{index}a rail{index} DRECT",
                f"D{index}B ac{index}b rail{index} DRECT",
                f"D{index}C 0 ac{index}a DRECT",
                f"D{index}D 0 ac{index}b DRECT",
                f"RCESR{index} rail{index} cap{index} {_number(load.capacitor_esr_ohm)}",
                f"CRES{index} cap{index} 0 {_number(load.capacitance_f)} IC=0",
                f"RLOAD{index} rail{index} 0 {_number(rload)}",
            ])
        vectors = ["v(vin)", "i(vmains)", "v(p)"]
        for index in range(1, len(config.loads) + 1):
            vectors.extend([f"v(ac{index}a,ac{index}b)", f"v(ac{index}b,s{index}n)",
                            f"v(rail{index})", f"v(ac{index}a,d{index}a)"])
        lines.extend([f".tran {_number(step)} {_number(stop)} 0 {_number(step)}",
                      ".control", "set wr_singlescale", "set numdgt=15", "run",
                      "wrdata samples.dat " + " ".join(vectors), "quit", ".endc", ".end"])
        return "\n".join(lines) + "\n"
