"""Conservative staged Sankey diagrams with a single ribbon-height scale."""
from __future__ import annotations

import heapq
import math
import textwrap
import numpy as np

__all__ = ["render_sankey"]


def _node_order(table):
    """Deterministic topological order and longest-path stage, independent of rows."""
    nodes = {r.source for r in table.rows} | {r.target for r in table.rows}
    children = {n: set() for n in nodes}
    parents = {n: set() for n in nodes}
    for row in table.rows:
        children[row.source].add(row.target)
        parents[row.target].add(row.source)
    degree = {n: len(parents[n]) for n in nodes}
    ready = [n for n in nodes if degree[n] == 0]
    heapq.heapify(ready)
    order, stage = [], {n: 0 for n in nodes}
    while ready:
        node = heapq.heappop(ready)
        order.append(node)
        for target in sorted(children[node]):
            stage[target] = max(stage[target], stage[node] + 1)
            degree[target] -= 1
            if degree[target] == 0:
                heapq.heappush(ready, target)
    if len(order) != len(nodes):
        raise ValueError("left-to-right Sankey requires an acyclic graph; cycle detected")
    return order, stage


def render_sankey(table, ax=None, node_gap=0.10, ribbon_alpha=0.55,
                  label_fontsize=8, value_fontsize=7, flow_scale=None):
    """Draw a balanced directed acyclic table and return the Matplotlib axis.

    Ribbon vertical height is value * scale at EVERY cross-section. Bars use
    max(inflow, outflow); inlet and outlet ribbons stack independently from the
    bar bottom. ``node_gap`` is a vertical gap in normalized axis coordinates.
    ``flow_scale`` optionally fixes axis-height per table unit across frames;
    it must be positive, finite, and small enough for every stage to fit.
    Cyclic/all-zero tables and imbalanced declared internal nodes raise.
    Different ribbons may cross; the layout does not minimize crossings.
    """
    import matplotlib.pyplot as plt

    report = table.check()
    for name, value, low, high in (("node_gap", node_gap, 0.0, 0.78),
                                   ("ribbon_alpha", ribbon_alpha, 0.0, 1.0)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"{name} must be finite and in [{low}, {high}]")
    order, stages = _node_order(table)
    levels = [[n for n in order if stages[n] == stage]
              for stage in range(max(stages.values()) + 1)]
    throughput = {n: max(report.inflow[n], report.outflow[n]) for n in order}
    if not max(throughput.values()):
        raise ValueError("cannot render an all-zero flow table")
    available = [0.78 - node_gap * (len(level) - 1) for level in levels]
    if min(available) <= 0:
        raise ValueError("too many nodes in a stage; reduce node_gap")
    maximum_scale = min(space / math.fsum(throughput[n] for n in level)
                        for level, space in zip(levels, available)
                        if any(throughput[n] > 0 for n in level))
    scale = maximum_scale if flow_scale is None else flow_scale
    if isinstance(scale, bool) or not isinstance(scale, (int, float)) or not math.isfinite(scale) or scale <= 0 or scale > maximum_scale * (1 + 1e-12):
        raise ValueError("flow_scale must be positive, finite and fit the stage heights")
    xs = {n: 0.08 + 0.84 * stages[n] / max(len(levels) - 1, 1) for n in order}
    bottoms = {}
    for level in levels:
        height = math.fsum(throughput[n] for n in level) * scale + node_gap * (len(level) - 1)
        y = 0.46 - height / 2
        for node in level:
            bottoms[node] = y
            y += throughput[node] * scale + node_gap

    if ax is None:
        _, ax = plt.subplots(figsize=(11.0, 6.0))
    ax.set_facecolor("white")
    ax.figure.set_facecolor("white")
    offsets_in = dict.fromkeys(order, 0.0)
    offsets_out = dict.fromkeys(order, 0.0)
    colors = ("#277DA8", "#43AA8B", "#CF8B35", "#7768AE", "#C56372")
    t = np.linspace(0, 1, 61)
    smooth = 3 * t**2 - 2 * t**3
    for row in sorted(table.rows, key=lambda r: (stages[r.source], r.source, r.target, r.label, r.value)):
        x0, x1 = xs[row.source] + 0.006, xs[row.target] - 0.006
        y0 = bottoms[row.source] + offsets_out[row.source]
        y1 = bottoms[row.target] + offsets_in[row.target]
        h = row.value * scale
        offsets_out[row.source] += h
        offsets_in[row.target] += h
        x = x0 + (x1 - x0) * t
        bottom = y0 + (y1 - y0) * smooth
        # Follow the lower edge left->right, then upper edge right->left ONCE.
        ribbon = ax.fill(np.r_[x, x[::-1]], np.r_[bottom, (bottom + h)[::-1]],
                         color=colors[stages[row.source] % len(colors)],
                         alpha=ribbon_alpha, lw=0)[0]
        ribbon.set_gid(f"flow:{row.source}->{row.target}")
    for node in order:
        h = throughput[node] * scale
        bar = ax.barh(bottoms[node] + h / 2, 0.012, height=h,
                      left=xs[node] - 0.006, color="#37474f", zorder=3)[0]
        bar.set_gid(f"node:{node}")
        label = textwrap.fill(node, width=17)
        ax.annotate(label, (xs[node], bottoms[node] + h + 0.012),
                    ha="center", va="bottom", fontsize=label_fontsize, color="#22313F")
        if value_fontsize:
            ax.annotate(f"{report.inflow[node]:.4g} in / {report.outflow[node]:.4g} out",
                        (xs[node], bottoms[node] - 0.012), ha="center", va="top",
                        fontsize=value_fontsize, color="#555555")
    ax.set(xlim=(-0.02, 1.02), ylim=(-0.08, 1.04))
    ax.axis("off")
    ax.set_title(table.title + f"\nRibbon height = flow [{table.unit}] × {scale:.3g}; one common scale",
                 fontsize=10, pad=14)
    return ax
