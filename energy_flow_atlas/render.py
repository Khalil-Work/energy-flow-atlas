"""Sankey-style rendering for validated flow tables.

Renders a left-to-right staged Sankey using plain Matplotlib primitives
(ribbons as filled polygons whose widths are proportional to the flow
value in the table's single unit). The drawing states its convention in
the axis label; every ribbon width uses the same measurable quantity.
"""

from __future__ import annotations

import numpy as np

__all__ = ["render_sankey"]


def _node_order(table):
    """Order nodes by first appearance and push them into coarse stages."""
    order, stage = [], {}
    for r in table.rows:
        for n in (r.source, r.target):
            if n not in stage:
                stage[n] = len(order)
                order.append(n)
    return order, stage


def render_sankey(table, ax=None, node_gap=0.6, ribbon_alpha=0.55,
                  label_fontsize=8, value_fontsize=7):
    """Draw a staged Sankey of the validated table on a Matplotlib axis.

    Returns the axis. The y-extent of every ribbon equals the flow value
    in the table's unit scaled by the same factor (one consistent
    measurable quantity; widths balance at nodes by construction when the
    table balances).
    """
    import matplotlib.pyplot as plt

    if not table.rows:
        raise ValueError("cannot render an empty flow table")
    order, stage = _node_order(table)
    n_nodes = len(order)
    # Map each node to a stage (x) by its first appearance, capped to keep
    # the drawing readable; nodes reused across many stages sit at their
    # first appearance.
    xs = {node: 0.15 + 0.7 * stage[node] / max(n_nodes - 1, 1) for node in order}

    totals = table.totals()
    throughput = {n: max(totals.get(n, 0.0) + 2 * _inflow_of(table, n),
                         _inflow_of(table, n) + _outflow_of(table, n))
                  for n in order}
    ymax = max(throughput.values())
    scale = 1.0 / ymax if ymax > 0 else 1.0

    if ax is None:
        _, ax = plt.subplots(figsize=(10.0, 5.6))

    offsets_out = {n: 0.0 for n in order}
    offsets_in = {n: 0.0 for n in order}
    for r in table.rows:
        x0, x1 = xs[r.source], xs[r.target]
        if x1 <= x0:
            x1 = min(x0 + 0.12, 0.92)
        y0 = 0.5 - throughput[r.source] * scale / 2 + offsets_out[r.source]
        y1 = 0.5 - throughput[r.target] * scale / 2 + offsets_in[r.target]
        h = r.value * scale
        offsets_out[r.source] += h
        offsets_in[r.target] += h

        # Ribbon: a filled quadrilateral with cubic-looking flanks.
        n_mid = 12
        t = np.linspace(0.0, 1.0, n_mid)
        top0 = y0 + h
        top1 = y1 + h
        bot0, bot1 = y0, y1
        s_curve = 3 * t**2 - 2 * t**3
        ax.fill(
            np.concatenate([x0 + (x1 - x0) * t, (x1 + (x0 - x1) * t)[::-1]]),
            np.concatenate([bot0 + (bot1 - bot0) * s_curve,
                            (top1 + (top0 - top1) * s_curve)[::-1]]),
            color="#1f4e79", alpha=ribbon_alpha, lw=0,
        )

    # Node bars + labels.
    for n in order:
        h = throughput[n] * scale
        y = 0.5 - h / 2
        ax.barh(y + h / 2, 0.012, height=h, left=xs[n] - 0.006,
                color="#37474f", zorder=3)
        side = "right" if xs[n] < 0.5 else "left"
        ax.annotate(n, (xs[n], y + h + 0.02), ha="center", fontsize=label_fontsize)
        if value_fontsize:
            ax.annotate(f"{_inflow_of(table, n):.3g} in / "
                        f"{_outflow_of(table, n):.3g} out {table.unit}",
                        (xs[n], y - 0.05), ha="center", fontsize=value_fontsize,
                        color="#555555")

    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(-0.12, 1.12)
    ax.axis("off")
    ax.set_title(table.title +
                 f"\nribbon height = flow value [{table.unit}], one consistent "
                 "quantity", fontsize=10)
    return ax


def _inflow_of(table, node):
    return sum(r.value for r in table.rows if r.target == node)


def _outflow_of(table, node):
    return sum(r.value for r in table.rows if r.source == node)
