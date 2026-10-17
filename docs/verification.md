# Verification evidence

Reproduced by `python -m pytest tests -q` (7 tests) and
`python examples/run_verification.py` (figures + GIF + CSV/JSON). Verified
on Windows 11, Python 3.13.5, Matplotlib 3.10.0; CI on Ubuntu.

## What each test establishes

| Test | Property established |
| --- | --- |
| `test_value_validation` | Negative/NaN/non-numeric values and self-flows are rejected with specific errors. |
| `test_balance_closes_and_reports` | A hand-checkable table closes exactly at internal nodes; external net sources/sinks are reported, not forced. |
| `test_imbalance_detection_names_the_node` | A broken table raises, naming the offending internal node. |
| `test_illustrative_label_propagates` | The illustrative flag carries into every output title. |
| `test_totals_match_hand_values` | Per-node net accounting matches hand values (converter exactly 0). |
| `test_empty_table_rejected` | Balance on an empty table raises. |
| `test_rendering_produces_proportional_ribbons` | Geometric check: every ribbon's constant-x cross-section height equals value × (one common scale factor) — the single-consistent-quantity guarantee. |

## Recorded run (`docs/results/`)

- `engineering_balance.png/.svg` + `engineering_balance.csv`: the
  air-handling example — all internal nodes close to **0.0 W** exactly
  (total recorded flow 5,220 W across 8 rows).
- `illustrative_allocation.png` + `illustrative_allocation.csv`: the
  sample-allocation demo table, explicitly labeled illustrative.
- `commissioning.gif`: 41 frames; each frame is a fully re-balanced
  engineering table at that load fraction.
- `run_summary.json`: metrics + runtime context.

## Limits of this evidence

- Accounting correctness, not physical modeling: values in the
  engineering example derive from the documented operating point, not
  from a solved thermodynamic model.
- The illustrative table is demonstration data by design.
- Staged layout is heuristic; cyclic tables may cross ribbons (numbers
  unaffected).
