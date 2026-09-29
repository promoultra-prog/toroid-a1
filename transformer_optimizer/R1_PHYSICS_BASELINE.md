# R1 physics baseline for A1-B T1

Status: **input audit, not a validated transformer design**. Read-only audit of
`C:\Users\007\Desktop\A1 Hi End\workspace\A1\A1-B` on 2026-09-30. Nothing in
that project was changed. A1-B's own transformer order specification says
"BUILD AND TEST PROTOTYPE — DO NOT PROMOTE TO SSOT BEFORE MEASUREMENT".

## Inputs already documented in A1-B

| Input | Current A1-B value | Evidence and status |
|---|---|---|
| Mains | 230 VAC nominal, 50/60 Hz; operating 200–240 VAC; 253 VAC at 50 Hz test point | `models/ssot/T1_A1B_TOROID/TRANSFORMER_SPEC_V3.md`: design requirement |
| Main transformer outputs | Two isolated 23.1 VAC no-load windings at 230 VAC, ±1%; 4.5 A RMS continuous each | Same transformer specification: procurement target, not measured hardware |
| AUX transformer outputs | Two isolated 16 VAC no-load windings, 0.5 A RMS continuous each | Same transformer specification: procurement target |
| Main DC rail requirement | ±28 V nominal; UV trip about 23.9 V; low-line manufacturing gate minimum 24.20 V | `docs/USER_SPEC.md`, `docs/PSU_STATUS.md`: design and simulated gate |
| Main bridge | SBR20A200CTB official device card, four diode legs in one bipolar bridge | `lib/psu_main.inc`, `README.md`: vendor model used in A1-B |
| Main reservoirs | One TDK B41456B8339M600 per rail: 33 mF nominal, 6 mΩ typical ESR, about 20 nH ESL; corner 26.4 mF / 12 mΩ | `models/ssot/B41456B8339M600/PROVENANCE.md`: datasheet-derived, not measured cans |
| Screened PSU loads | 1.5 A per main rail nominal; 1.8/1.5 A unbalanced low-line corner; AUX 0.107/0.0044 A in the PSU study | `scripts/chain/psu_2026.py`, `docs/PSU_STATUS.md`: simulated load envelope, not a measured amplifier profile |
| Soft-start and grid model | 47 Ω primary start resistor and bypass; 0.5 Ω grid resistance in selected deck | `lib/psu_main.inc`: modeled values; physical grid range and contact characteristics not established |
| Transformer prototype targets | About 300 VA core/window class if needed, Bmax ≤1.00 T at 230 V and ≤1.10 T at 253 V; DCR limits primary ≤3 Ω, MAIN ≤0.18 Ω/half, AUX ≤0.9 Ω/half at 20 °C; temperature rise ≤45 K | `TRANSFORMER_SPEC_V3.md`: order and acceptance targets, not achieved measurements |

## Inputs still provisional or missing

| Input | Current evidence | Needed before a physical second-stage Pareto |
|---|---|---|
| Steel grade, stacking, W/kg(B), B-H and remanence | Preferred GOES/GOSS; no selected measured grade or complete curves | Supplier material record and prototype I0/P0 at 230/240/253 V; measured B-H/remanence for magnetic inrush |
| Leakage and magnetizing behavior | A1-B linear deck assumes LM 10 H, KMAIN 0.9996, KAUX 0.999, RCORE 150 kΩ | Prototype leakage inductance per winding pair, I0 and no-load power; connection and test frequency |
| Winding build | DCR and insulation targets exist; wire catalogue, enamel diameters, layer/barrier stack and actual turns are not fixed | Supplier construction record or winding trial; screen/shield thickness and fit check |
| Thermal geometry | Temperature-rise acceptance target; no size-dependent thermal resistance or calibration | Equilibrium rise under representative load, installation/orientation and enclosure conditions |
| Main and AUX rectifier/capacitor topology | A1-B includes one centre-referenced bipolar MAIN bridge, separate AUX bridge, bank ESL, soft-start and bypass | A1-B topology must be modeled before porting its values into this optimizer; the current two-independent-bridge demonstrator is different |
| Load envelope | PSU study uses constant DC currents; full amplifier idle, music/program and heavy-duty profiles are not established here as transformer acceptance loads | Defined time/current envelopes and rail limits at 200/230/240/253 V, including channel interaction |
| Mains impedance range and startup state | 0.5 Ω is a model assumption; no verified source impedance range, remanence or hot-restart state | Measured/site bounds and startup tests with the actual 47 Ω bypass circuit |

## Gate for subsequent work

The current `DEMONSTRATOR_ONLY` plots use **2 × 35 VAC, two independent bridges,
10 mF/12 Ω per rail, illustrative steel, fixed coupling 0.995 and a heavy
search-space range**. Their mass and 321 A first-cycle peak are not A1-B T1
results. `ngspice_simulated=True` means a circuit run completed; it does not
mean physical validation.

Once the missing inputs and A1-B circuit topology are reconciled, run the fast
analytical search, simulate every selected shortlist candidate with the same
PSU/load matrix, recalculate winding RMS losses and temperature, apply the
rail/thermal/geometry gates, then form a **separate** post-simulation Pareto
front. Keep the analytical front labeled as a surrogate. No candidate is
called a physical optimum before prototype measurements validate steel,
leakage, DCR, thermal behavior and startup.
