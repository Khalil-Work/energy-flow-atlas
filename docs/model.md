# Model and method

## Flow tables

A `FlowTable` records transfers of ONE measurable quantity in ONE
consistent unit:

    FlowRow(source, target, value, unit, label)

Conventions:

- **Non-negative values**: direction lives in source→target ordering; a
  "reverse" transfer is a separate row (rejected negative values, raised
  with the offending row).
- **One unit per table**: the unit is declared at construction and stamped
  on every row; mixing units in a Sankey is the classic apples-oranges
  error and raises immediately.
- **Finite values only** (NaN/Inf rejected).
- **No self-flows** (source == target is not a transfer).

## Node balance

For each node: inflow − outflow.

- **Internal nodes** (declared via `internal_nodes`) must close within
  `tol × total flow` — `check()` raises naming the worst offender; this is
  the conservation gate before any diagram is drawn.
- **External nodes** may carry a declared net imbalance (sources/sinks);
  it is reported, never forced to zero.

## Rendering

A staged left-to-right Sankey drawn with plain Matplotlib primitives:
each ribbon is a filled polygon whose **constant-x cross-section height is
exactly value × (one global scale factor)** — a single consistent
measurable quantity, stated in the title of every figure. Node bars
summarize throughput with in/out annotations in the table's unit.
Illustrative tables (`illustrative=True`) carry that label into every
output title; they are demonstration data, never measured energy or mass.

## The engineering example

An air-handling energy balance at a documented operating point: fan power
300 W (5% duct loss), equipment 1200 W, envelope gain 150 W, closed
air-loop with the coil removing the net — every internal node closes to
0.0 W and the commissioning animation re-balances the whole table at each
load fraction.

## Limits

- Accounting-level tool: balances flows, does not model the physics
  producing them.
- One quantity per diagram (draw two diagrams for coupled energy+mass).
- The staged layout is heuristic (first-appearance stages); very cyclic
  tables may render with crossing ribbons — the numbers remain correct.
