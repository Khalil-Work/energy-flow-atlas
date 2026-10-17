# API reference

Module `energy_flow_atlas.flow_table` + `render` (re-exported at package
level).

- `FlowTable(quantity, unit, rows=None, internal_nodes=(), illustrative=False, title=None)`
- `table.add(source, target, value, label="") -> table` (chainable;
  validates each row: non-empty distinct nodes, finite numeric value ≥ 0).
- `table.totals() -> {node: net}` (in − out).
- `table.balance(tol=1e-9) -> BalanceReport` — per-node inflow/outflow/
  imbalance, max internal-node imbalance, `balanced` flag.
- `table.check(tol=1e-9) -> BalanceReport` — same, but raises ValueError
  naming the worst imbalanced internal node.
- `render_sankey(table, ax=None, ...) -> ax` — staged ribbon diagram; one
  global scale factor maps every value to its ribbon height; node bars
  with in/out annotations; the title states the unit and (when set) the
  illustrative-data label.

## Example (executed in CI)

```python
from energy_flow_atlas import FlowTable, render_sankey

t = FlowTable("energy", "W", internal_nodes=("mid",))
t.add("heater", "mid", 100.0)
t.add("mid", "useful load", 70.0)
t.add("mid", "loss", 30.0)
report = t.check()          # internal node 'mid' closes: 100 - 70 - 30 = 0
render_sankey(t)            # one consistent quantity [W]
```
