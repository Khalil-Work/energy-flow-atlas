# Build a quantitative engineering flow diagram

## 1. Choose the boundary and quantity

For a converter, take electrical power in W as the only quantity. A 100 W
input may become 70 W useful output plus 30 W loss. Do not put efficiency
percentages or mass flow in the same flow table; they need different units.

## 2. Declare conservation explicitly

```python
from energy_flow_atlas import FlowTable, render_sankey

table = FlowTable("power", "W", internal_nodes=("converter",),
                  title="100 W converter accounting")
table.add("electrical input", "converter", 100)
table.add("converter", "useful output", 70)
table.add("converter", "heat loss", 30)
report = table.check()
print(report.imbalance)
# converter: 0; electrical input: -100; heat loss: 30; useful output: 70
```

Only `converter` must balance. The other nodes are boundary sources/sinks.
Omitting the 30 W loss produces a named conservation error. A balanced
diagram is still only as physically sound as its supplied data.

## 3. Save a clean figure

```python
axis = render_sankey(table)
axis.figure.savefig("converter.png", dpi=150, bbox_inches="tight")
```

The 70 W ribbon is 70/30 times the vertical thickness of the loss ribbon
at every x cross-section. Input rows can be reordered without relocating
endpoints. Cycles are rejected; collapse a recirculating system into a
boundary energy ledger or use a renderer designed for feedback paths.

## 4. Compare operating points honestly

Automatic scaling fills each individual diagram. To compare widths across
figures or frames, pass the **same** `flow_scale` to every call, chosen to
fit the largest operating point. For this small converter, `0.005` gives
100 W a height of 0.5 normalized axis units. Then 50 W has height 0.25 in
every diagram. Node gap is independent of flow; the commissioning example
uses this convention and saves each frame's underlying numbers.

## 5. Reproduce the supplied examples

`python examples/run_verification.py` builds the documented fan/equipment/
envelope ledger, checks each frame, and exports figures plus CSV/JSON.
The second figure demonstrates conservation of sample count; it is
explicitly illustrative. Read `run_summary.json` and the CSVs before
interpreting a visually thick ribbon as system input: edge sums count
the same energy again after intermediate transfers.
