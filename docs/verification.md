# Verification evidence and reproduction

Run `python -m pytest tests -q` followed by
`python examples/run_verification.py` from the repository root. The suite
has **23 collected test cases**, including parametrized invalid-input cases.
Recorded Python/Matplotlib/OS versions accompany the result JSON. CI runs
the same tests on Ubuntu/Python 3.12; the local reproduction used Windows.

## Independent invariants exercised

| Check | Evidence / failure caught |
| --- | --- |
| Hand ledger | 100 W source splits into 60 W useful / 40 W loss; internal residuals exactly zero |
| Invalid transfers | Negative/nonfinite/nonnumeric values and self-flows raise |
| Unit preservation | Constructor rejects 1 kW in a W table instead of silently treating it as 1 W |
| Internal-node errors | Imbalance names its node; missing declared names cannot pass vacuously |
| Tolerance and sums | NaN/Inf/negative/boolean/string tolerances and aggregate overflow raise |
| Illustrative title | Custom figure title still says illustrative |
| Conservation gate | Rendering an internally unbalanced table raises before drawing |
| Graph connectivity | Reversed edge order gives the same layout; ribbon endpoints match actual bar faces |
| Node throughput | Every bar has height max(inflow,outflow) × common scale |
| Ribbon proportionality | Endpoint heights across several flow values share a common scale |
| Interior geometry | Single-ribbon area equals span × thickness; eleven interior cuts have two crossings and correct thickness |
| Cycles | Numerically account-able but explicitly rejected by staged rendering |
| Load comparison | Coil width at 5% is exactly 0.05 of its rated width under a fixed scale |

The old endpoint-only geometry test passed bow-tie polygons. The new area
and interior-intersection regression would fail that implementation. The
connectivity test also catches moving a destination to an arbitrary x
position when rows are supplied in a different order.

## Recorded numerical results

At rated load the supply, room and return residuals are exactly **0 W**.
External input is **1,650 W**, coil heat removal **1,635 W**, duct loss
**15 W**. The seven edge values sum to **5,220 W**; that is a transfer-edge
sum, not power entering the complete system.

The illustrative 1,000-sample example conserves count through cleaning,
screening and splitting: 40 rejected + 110 screened out + 700 training +
150 held out = 1,000. Its maximum internal residual is **0 count**.

## Saved evidence

- `engineering_balance.png/.svg`: rated ledger, equal units per ribbon
  height, node totals and explicitly named heat-removal sink.
- `engineering_balance.csv`: node accounting, quantity/unit and data flag.
- `illustrative_allocation.png/.svg/.csv`: labeled demonstration counts.
- `commissioning.gif`: 41 distinct steady-load frames from 0.05 to 1.0,
  1,100×600 px, fixed physical height scale and white/no-grid interiors.
- `commissioning_flows.csv`: all 287 edge transfers, load fraction and
  maximum internal residual for every frame, including unit W.
- `run_summary.json`: operating-point metrics and runtime provenance.

These tests verify accounting and geometric contracts. They do not validate
an HVAC plant, experimental measurements, thermodynamic efficiency, optimal
graph layout or uncertainty. The GIF is a parameter sweep, not elapsed time.
