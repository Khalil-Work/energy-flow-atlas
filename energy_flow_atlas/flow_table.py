"""Single-quantity, single-unit transfer tables and node conservation."""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from numbers import Real

__all__ = ["FlowTable", "FlowRow", "BalanceReport"]


def _name(value, kind):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{kind} must be a non-empty string")
    return value


def _nonnegative(value, kind):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{kind} must be numeric")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{kind} must be finite")
    if value < 0:
        raise ValueError(f"{kind} must be non-negative")
    return value


def _sum(values):
    try:
        result = math.fsum(values)
    except OverflowError as exc:
        raise ValueError("aggregate flow exceeds the finite numeric range") from exc
    if not math.isfinite(result):
        raise ValueError("aggregate flow must be finite")
    return result


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
    """Transfers in one unit; declared internal nodes must conserve flow.

    No unit conversion is implicit. Non-internal nodes may be net sources or
    sinks. Cycles can be accounted for, but the left-to-right renderer requires
    a directed acyclic graph. ``check`` must be rerun after adding rows.
    """

    def __init__(self, quantity: str, unit: str, rows=None,
                 internal_nodes=(), illustrative=False, title=None):
        self.quantity = _name(quantity, "quantity name")
        self.unit = _name(unit, "unit")
        if isinstance(internal_nodes, str):
            raise ValueError("internal_nodes must be a collection of node names")
        self.internal = {_name(n, "internal node") for n in internal_nodes}
        if not isinstance(illustrative, bool):
            raise ValueError("illustrative must be a boolean")
        self.illustrative = illustrative
        base_title = f"{quantity} flow [{unit}]" if title is None else _name(title, "title")
        self.title = base_title + (" — illustrative demonstration data" if illustrative else "")
        self.rows: list[FlowRow] = []
        for row in (() if rows is None else rows):
            if not isinstance(row, FlowRow):
                raise ValueError("rows must contain FlowRow instances")
            if row.unit != self.unit:
                raise ValueError(f"mixed units: row {row.unit!r}, table {self.unit!r}")
            self.add(row.source, row.target, row.value, row.label)

    def add(self, source, target, value, label=""):
        source = _name(source, "source node")
        target = _name(target, "target node")
        if source == target:
            raise ValueError(f"self-flow {source}->{source} is not a transfer")
        value = _nonnegative(value, "flow value")
        if not isinstance(label, str):
            raise ValueError("row label must be a string")
        self.rows.append(FlowRow(source, target, value, self.unit, label))
        return self

    def totals(self):
        """Return each node's inflow minus outflow, in the table unit."""
        return self.balance().imbalance

    def balance(self, tol=1e-9):
        """Report balances; internal error <= tol * max(sum(row values), 1).

        ``tol`` is finite and nonnegative. The floor of one is expressed in
        the table unit. Missing declared internal nodes are input errors.
        Aggregate transfers count edges, not unique energy entering a system.
        """
        tol = _nonnegative(tol, "tolerance")
        if not self.rows:
            raise ValueError("empty flow table has no balance")
        nodes = sorted({r.source for r in self.rows} | {r.target for r in self.rows})
        missing = self.internal.difference(nodes)
        if missing:
            raise ValueError(f"declared internal nodes absent from table: {sorted(missing)}")
        total_scale = max(_sum(r.value for r in self.rows), 1.0)
        inflow = {n: _sum(r.value for r in self.rows if r.target == n) for n in nodes}
        outflow = {n: _sum(r.value for r in self.rows if r.source == n) for n in nodes}
        imbalance = {n: inflow[n] - outflow[n] for n in nodes}
        max_internal = max((abs(imbalance[n]) for n in self.internal), default=0.0)
        return BalanceReport(inflow, outflow, imbalance, max_internal,
                             max_internal / total_scale <= tol)

    def check(self, tol=1e-9):
        """Raise with the worst internal node unless the balance closes."""
        report = self.balance(tol)
        if not report.balanced:
            worst = max(self.internal, key=lambda n: abs(report.imbalance[n]))
            raise ValueError(f"internal node {worst!r} imbalanced by "
                             f"{abs(report.imbalance[worst]):.6g} {self.unit} "
                             f"(tolerance {tol:.1e} of total flow)")
        return report
