# Toroidal transformer optimizer

Analytical design search for 50/60 Hz toroidal power transformers. Internal units
are SI; report dimensions use millimetres. The example steel loss coefficients,
thermal resistances, winding coverage, and linear permeability are illustrative
inputs and require measurement or datasheet calibration for a build decision.

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -e ".[test]"
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe examples\audio_amp_500va.py
.venv\Scripts\python.exe -m transformer_optimizer.cli --help
```

`optimize_transformer(spec, search_space)` runs NSGA-II and returns feasible
non-dominated designs in `result.candidates`, complete physics results in
`result.evaluations`, and `result.dataframe`. `rank_shortlist(result, weights)`
adds a transparent post-search score. Set the secondary minimum loaded and
maximum unloaded voltage where required.

The lumped thermal paths use aggregate heat and ignore airflow and local hot spots. The magnetizing current
uses constant relative permeability and is explicitly marked estimated.
Voltage regulation includes winding resistance but not leakage reactance,
rectifier charging pulses, stray losses, mains DC offset, or inrush. Core loss
uses the supplied Steinmetz coefficients in W/kg. Winding capacity assumes
side-by-side parallel strands. Each layer records inner and outer coverage and
its own turn length. A continuous toroidal turn surrounds the whole core cross
section, so a full layer adds the same radial clearance to the inner and outer
faces and the same normal clearance to the axial faces. The inner circumference
limits turn count. This remains a packing estimate until a winding trial or a
more detailed placement model is available.

## Optional OpenMagnetics check

`integrations.openmagnetics.build_mas(...)` exports a selected, valid design as
a MAS exchange document with a custom toroid shape and round-wire descriptions.
`OpenMagneticsValidator` can compare core loss, winding loss, inductance, and
magnetizing current after optimisation. It is never called by `pymoo`.

The included [Nippon Steel 23Z110 product data](https://www.nipponsteel.com/product/electrolytic-tinplate/list/grain-oriented/01.html)
contains a **maximum** 1.10 W/kg at 1.7 T / 50 Hz, minimum B at 800 A/m,
density, thickness, and minimum stacking factor. It does not contain a loss
curve or B-H curve. The validator therefore returns `available=False` for this
dataset rather than constructing imaginary material data. Supply measured
curves covering the operating point and a matching steel registered in MKF to
enable the check. `PyOpenMagnetics` is optional and imported only at validation
time. Its upstream [compatibility note](https://github.com/OpenMagnetics/PyOpenMagnetics/blob/main/docs/compatibility.md)
lists native Windows as unsupported; run the binding in a supported environment.
The adapter uses the documented `mas_autocomplete`, `process_inputs`,
`calculate_core_losses`, `calculate_winding_losses`, and inductance calls; an
end-to-end MKF run needs a complete material and compatible runtime.

## ngspice rectifier check

Install ngspice 47 or another compatible build and put `ngspice` on `PATH`.
Run `python examples/ngspice_rectifier.py` after the Python dependencies are
installed. The example optimizes a small Pareto set, then simulates one
selected candidate with two independent 35 V windings, one bridge and 10 mF
reservoir capacitor per winding, and a 12 Ω load per DC output. Those circuit
values illustrate the workflow; they are not A1 supply specifications.
The example saves five PNG files in `output/ngspice_rectifier/`: Pareto,
startup winding currents, steady winding currents, DC rails, and first-cycle
primary peak versus switch-on phase. Use `--output-dir PATH` to choose another
directory. Output files are kept locally and excluded from Git.

`NgSpiceTransformerDeck.from_candidate(spec, candidate, evaluation, config)`
builds the netlist. `NgSpiceRunner().run(deck)` runs loaded and no-load
transients and returns RMS and peak winding currents, crest factor, conduction
angle, rail voltage/sag/ripple, copper loss, AC flux amplitude, and first-cycle
primary peak. `with_ngspice_results(pareto, {row_index: result})` adds selected
simulations to the Pareto DataFrame. `NgSpiceRunner.sweep(deck, (207, 230, 253),
(0,))` runs steady electrical cases. `sweep_startup(deck, (230,),
(0, 15, 30, 45, 60, 75, 90))` measures first-cycle primary peaks without
assuming that later linear-model currents have settled.
Pass `plots_dir=PATH` to `run` or `plot_path=PATH` to `sweep_startup` to save
those graphs from another script. Plotting uses a noninteractive backend.
On Windows the runner launches ngspice with a hidden console, including when
the command on `PATH` is a `.cmd` wrapper.

The RMS metrics use the final complete 50 Hz periods, with interpolated period
boundaries. `peak_primary_current_a` and `secondary_peak_current_a` cover the
whole transient; separate steady peak fields and `startup_primary_peak_a`
preserve the distinction. Rails include steady minimum and maximum voltages.
Each secondary retains its own values. `magnetic_inrush_peak_a=None` and
`magnetic_inrush_valid=False` explicitly forbid treating capacitor charging as
magnetic inrush. `bh_data_physical` and `core_loss_data_physical` separately
identify measured inputs; `remanence_modeled=False` keeps the aggregate
`physical_material_data=False` even when both measured inputs are supplied.
`core_loss_data_quality` is one of `illustrative`, `manufacturer_typical`,
`manufacturer_guaranteed`, or `measured`. Manufacturer typical curves remain
usable for interpolation without being labeled measured. Guarantee-only
maximum points are upper bounds and are rejected as a nominal loss curve.

The linear model uses the analytical magnetizing inductance, winding hot
resistances, a configurable coupling coefficient, and a parallel resistance
initially calibrated from the selected core-loss model at each line voltage. By default
that is the candidate steel's illustrative Steinmetz model. For measured loss
points, pass `TabulatedCoreLoss(points, source=..., material_name=...)` as
`NgSpiceConfig.core_loss_model`; the range must cover the operating flux.
The resistor remains an equivalent sinusoidal-loss approximation, not a
hysteresis model. After each run the model integrates the measured magnetic
branch voltage `V(p)` to estimate peak AC flux, recomputes target core loss,
and updates `RCORE` from the measured branch RMS voltage. The runner also
updates winding resistance. It stops only when copper temperature changes by
at most 0.05 °C and actual versus target core loss differs by at most 0.1 %;
otherwise it raises an error. Its startup
current includes capacitor charging but cannot predict saturation or remanence.
The measured period must be late enough for the capacitor/load to settle.

The optional XSPICE `lcouple + core` mode requires a supplied signed B-H curve.
Its piecewise-linear core model has no hysteresis or remanence. A synthetic
curve is used only in the single-secondary syntax smoke test. Multi-secondary
XSPICE convergence is not verified, so the API rejects that combination;
the two-secondary rectifier example uses the tested linear model. See the
[ngspice manual](https://ngspice.sourceforge.io/docs/ngspice-manual.pdf)
for the model definitions and their limits.
