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
side-by-side parallel strands and uniform inner-circumference coverage.
