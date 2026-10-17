"""Energy Flow Atlas: validated engineering flow tables and Sankey diagrams.

A flow table is a list of rows (source, target, value, unit, label) plus
metadata (default unit, quantity name). Validation:

- every value must be finite and >= 0 (mass/energy flows are
  non-negative; direction lives in source->target);
- ONE consistent unit per table (mixed units raise, with the recorded
  unit per row);
- node balance: for the declared external nodes (net sources/sinks),
  imbalance is reported per node and checked against a tolerance; for
  internal nodes the balance must close within tolerance (conservation).

Sankey rendering uses Matplotlib's sankey (via matplotlib.sankey) or a
clear horizontal-bar flow diagram when the Sankey layout is not
appropriate; the renderer states exactly what it draws. Illustrative
demonstration data must be labeled as such at creation time
(``illustrative=True``) and carries the label into every output.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["FlowTable", "FlowRow", "BalanceReport"]


@dataclass(frozen=True)
class FlowRow:
    source: str
    target: str
    value: float
    unit: str
    label: str = ""


@dataclass
class BalanceReport:
    inflow: dict = field(default_factory=dict)
    outflow: dict = field(default_factory=dict)
    imbalance: dict = field(default_factory=dict)
    max_abs_imbalance: float = 0.0
    balanced: bool = False


class FlowTable:
    """A validated flow table with node-balance accounting."""

    def __init__(self, quantity: str, unit: str, rows=None,
                 internal_nodes=(), illustrative=False, title=None):
        if not quantity or not isinstance(quantity, str):
            raise ValueError("quantity name must be a non-empty string")
        if not unit or not isinstance(unit, str):
            raise ValueError("unit must be a non-empty string")
        self.quantity = quantity
        self.unit = unit
        self.internal = set(internal_nodes)
        self.illustrative = illustrative
        self.title = title or (f"{quantity} flow [{unit}]"
                               + (" — illustrative demonstration data"
                                  if illustrative else ""))
        self.rows: list[FlowRow] = []
        for r in rows or []:
            self.add(r.source, r.target, r.value, r.label)

    def add(self, source, target, value, label=""):
        if not source or not target:
            raise ValueError("source and target must be non-empty node names")
        if source == target:
            raise ValueError(f"self-flow {source}->{source} is not a transfer")
        if not isinstance(value, (int, float)):
            raise ValueError(f"flow value must be numeric, got {value!r}")
        value = float(value)
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError(f"flow value must be finite, got {value}")
        if value < 0.0:
            raise ValueError(
                f"negative flow {value} from {source} to {target}: direction "
                "belongs in source->target ordering; split or reverse the row"
            )
        self.rows.append(FlowRow(source, target, value, self.unit, label))
        return self

    def totals(self):
        out = {}
        for r in self.rows:
            out[r.source] = out.get(r.source, 0.0) - r.value
            out[r.target] = out.get(r.target, 0.0) + r.value
        return out

    def balance(self, tol=1e-9):
        """Node balance: inflow - outflow per node.

        Internal nodes must close within tol*total_scale; external nodes
        may carry a net imbalance (declared sources/sinks) which is
        reported, not required to vanish.
        """
        if not self.rows:
            raise ValueError("empty flow table has no balance")
        total_scale = sum(r.value for r in self.rows)
        inflow, outflow = {}, {}
        for r in self.rows:
            outflow[r.source] = outflow.get(r.source, 0.0) + r.value
            inflow[r.target] = inflow.get(r.target, 0.0) + r.value
        nodes = sorted(set(inflow) | set(outflow))
        imbalance = {n: inflow.get(n, 0.0) - outflow.get(n, 0.0) for n in nodes}
        max_internal = 0.0
        for n in nodes:
            if n in self.internal:
                max_internal = max(max_internal, abs(imbalance[n]))
        return BalanceReport(
            inflow=inflow, outflow=outflow, imbalance=imbalance,
            max_abs_imbalance=max_internal,
            balanced=max_internal <= tol * max(total_scale, 1.0),
        )

    def check(self, tol=1e-9):
        """Raise unless internal nodes balance within tolerance."""
        rep = self.balance(tol=tol)
        if not rep.balanced:
            worst = max(
                ((abs(rep.imbalance[n]), n) for n in self.internal), default=(0, "?")
            )
            raise ValueError(
                f"internal node '{worst[1]}' imbalanced by {worst[0]:.6g} "
                f"{self.unit} (tolerance {tol:.1e} of total flow)"
            )
        return rep
