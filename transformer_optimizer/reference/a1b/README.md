# A1-B electrical reference snapshot

**Model-limited electrical replay, not transformer hardware validation.**

The checked-in `.cir` is a reviewable 230 VAC / 1.5 A per MAIN rail case.
It includes four relative files selected from the A1-B project:
`lib/psu_main.inc`, `lib/aux_supply.inc`,
`models/derived/SBR20A200CTB_element.inc`, and
`models/derived/TDK_B41456B8339M600.inc`. Their pinned SHA-256 values are in
`simulation/a1b_reference.py` and the case JSON. The files themselves are
copied **only into local `output/A1B_REFERENCE/` when the runner executes**;
they are not included in this repository. A1-B remains the source of truth for
the selected PSU circuit. This snapshot was generated read-only from A1-B on
2026-09-30.

Run with ngspice 47 and access to the A1-B workspace:

```powershell
python examples/a1b_electrical_reference.py --a1b-root "C:\path\to\A1-B" --matrix
```

The matrix CSV covers 200/230/240/253 VAC at 1.5/1.5 A and 1.8/1.5 A MAIN
loads with A1-B's documented AUX DC loads, cold capacitors, 47 Ω soft-start
and bypass at 189°. It records **assumed** LM, coupling, DCR and RCORE through
the A1-B include. MAIN rail minima reproduce A1-B's published PSU table to
within 0.005 V for the four typical cases, and the 200 V unbalanced corner
reproduces 24.80 V. All eight runs had <1 mV per cycle MAIN rail drift.

The separate heavy/program load envelope, measured leakage, steel curves,
remanence and thermal calibration are missing. The reference outputs must not
be used as a physical Pareto front or toroid acceptance evidence.
