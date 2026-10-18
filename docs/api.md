# API and failure behavior

Imports are re-exported by `energy_flow_atlas`.

## `FlowRow(source, target, value, unit, label="")`

Frozen record for a directed transfer. Use it in the `rows` constructor.
The receiving table validates the record, including exact unit equality.
There is no automatic conversion. A label is stored as metadata; the
renderer annotates node names and totals rather than individual edge labels.

## `FlowTable(quantity, unit, rows=None, internal_nodes=(), illustrative=False, title=None)`

- `quantity`, `unit`, node names and optional title: nonblank strings.
- `rows`: iterable of `FlowRow` records; optional.
- `internal_nodes`: collection of names expected to have zero net transfer.
  They must appear in the completed table when `balance`/`check` runs.
- `illustrative`: boolean; appends a demonstration-data marker even to a
  custom title. The example exporter also records it in CSV metadata.
- `title`: optional figure title, otherwise generated from quantity/unit.

`add(source, target, value, label="") -> self` adds a row in the table unit.
`value` must be a finite real number >=0 (booleans excluded). Blank/nonstring
nodes, self-flows, nonstring labels and mixed-unit constructor rows raise
`ValueError`. Multiple rows between the same nodes are allowed. Modify
tables with `add`, not by manually altering `rows`, `internal` or metadata.

`balance(tol=1e-9) -> BalanceReport` computes dictionaries `inflow`,
`outflow`, `imbalance` for every node, `max_abs_imbalance` over internal
nodes and `balanced`. Empty tables, missing internal nodes, invalid
tolerance and aggregate numeric overflow raise `ValueError`.

`check(tol=1e-9) -> BalanceReport` additionally raises when internal balance
fails, naming the worst residual. `totals()` returns the node-imbalance
dictionary. Neither method requires a graph to be acyclic.

## `render_sankey(table, ax=None, node_gap=0.10, ribbon_alpha=0.55, label_fontsize=8, value_fontsize=7, flow_scale=None) -> ax`

Calls `table.check()` with its default tolerance before drawing. Requires
an acyclic graph with at least one positive transfer. If no axis is supplied,
creates a white 11×6 inch figure. The caller owns closing or saving it.

- `node_gap`: normalized vertical separation between nodes in one stage;
  finite, 0–0.78. If too many nodes fit poorly, reduce the gap or use a larger
  figure. A stage leaving no positive flow space raises `ValueError`.
- `ribbon_alpha`: finite opacity in [0,1].
- `label_fontsize`, `value_fontsize`: Matplotlib point sizes; set the latter
  to 0 to suppress node totals. Names wrap at spaces near 17 characters.
- `flow_scale`: optional positive finite axis-height per table unit. Must
  fit all stages; otherwise raises. Default scales automatically per table.
  Use a common explicit value for quantitative comparisons between frames.

Bars have artist GIDs `node:<name>`; ribbons `flow:<source>-><target>`.
Parallel edges share a GID. GIDs support diagnostics; layout optimization
and interaction callbacks are outside this package's scope.

## Examples that should fail

```python
from energy_flow_atlas import FlowTable, FlowRow, render_sankey

# ValueError: mixed units; convert 1 kW to 1,000 W explicitly first.
FlowTable("power", "W", rows=[FlowRow("a", "b", 1, "kW")])

# ValueError naming b: 10 W enters, only 7 W leaves.
t = FlowTable("power", "W", internal_nodes=("b",))
t.add("a", "b", 10).add("b", "c", 7)
render_sankey(t)

# Ledger can be checked, but left-to-right drawing rejects cycles.
c = FlowTable("power", "W").add("a", "b", 10).add("b", "a", 10)
c.check()
render_sankey(c)
```
