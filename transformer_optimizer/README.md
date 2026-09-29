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
