"""Verification tests for energy_flow_atlas.

Each test pins a distinct property:
- flow values: finite, non-negative, no self-flows, numeric-only;
- node balance closes exactly on a hand-checkable table;
- imbalance detection: a broken table raises with the offending node in
  the message;
- external nodes may carry declared net imbalance (reported, not forced);
- illustrative labeling propagates into the title;
- totals/inflow/outflow accounting matches hand values;
- rendering: an axis is produced and ribbon heights are proportional to
  the flow values (geometric check on the drawn artists).
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest

from energy_flow_atlas import FlowTable, render_sankey


def balanced_table():
    # Hand-checkable: 100 W in, splits 60/40, recombines to 90 out with
    # 10 W loss declared at the internal node.
    t = FlowTable("energy", "W",
                 internal_nodes=("converter", "stage"),
                 title="demo")
    t.add("source", "converter", 100.0)
    t.add("converter", "stage", 60.0)
    t.add("converter", "loss", 40.0)          # loss is external (net sink)
    t.add("stage", "load", 60.0)
    return t


def test_value_validation():
    t = FlowTable("energy", "W")
    t.add("a", "b", 1.0)
    with pytest.raises(ValueError, match="negative"):
        t.add("b", "c", -5.0)
    with pytest.raises(ValueError, match="finite"):
        t.add("b", "c", float("nan"))
    with pytest.raises(ValueError, match="self-flow"):
        t.add("c", "c", 1.0)
    with pytest.raises(ValueError, match="numeric"):
        t.add("b", "c", "lots")


def test_balance_closes_and_reports():
    t = balanced_table()
    rep = t.check()
    assert rep.balanced
    assert rep.imbalance["converter"] == pytest.approx(0.0)
    assert rep.inflow["converter"] == pytest.approx(100.0)
    assert rep.outflow["converter"] == pytest.approx(100.0)
    # External nodes: net source and net sink reported.
    assert rep.imbalance["source"] == pytest.approx(-100.0)
    assert rep.imbalance["loss"] == pytest.approx(40.0)
    assert rep.imbalance["load"] == pytest.approx(60.0)


def test_imbalance_detection_names_the_node():
    t = FlowTable("energy", "W", internal_nodes=("mid",))
    t.add("a", "mid", 10.0)
    t.add("mid", "b", 7.0)   # 3 units missing
    with pytest.raises(ValueError, match="mid"):
        t.check()


def test_illustrative_label_propagates():
    t = FlowTable("energy", "W", illustrative=True)
    assert "illustrative" in t.title.lower()
    t2 = FlowTable("energy", "W", illustrative=False)
    assert "illustrative" not in t2.title.lower()


def test_totals_match_hand_values():
    t = balanced_table()
    totals = t.totals()
    # converter: receives 100, sends 60 + 40 = 100 -> net zero (balanced).
    assert totals["converter"] == pytest.approx(0.0)
    assert totals["source"] == pytest.approx(-100.0)
    assert totals["load"] == pytest.approx(60.0)
    assert totals["loss"] == pytest.approx(40.0)


def test_empty_table_rejected():
    t = FlowTable("energy", "W")
    with pytest.raises(ValueError, match="empty"):
        t.balance()


def test_rendering_produces_proportional_ribbons():
    t = balanced_table()
    fig, ax = plt.subplots()
    out = render_sankey(t, ax=ax)
    assert out is ax
    # ax.fill adds polygon patches (one per ribbon); node bars use a
    # different facecolor and are excluded. Measure each ribbon's height
    # as a constant-x cross section (global y-extent would include the
    # vertical shift of slanted ribbons).
    widths = []
    for patch in ax.patches:
        rgba = matplotlib.colors.to_rgba(patch.get_facecolor())
        if rgba[:3] == matplotlib.colors.to_rgb("#37474f"):
            continue  # node bar
        v = patch.get_path().vertices
        x_left = v[:, 0].min()
        at_left = v[np.isclose(v[:, 0], x_left), 1]
        widths.append(at_left.max() - at_left.min())
    assert len(widths) == len(t.rows)
    # Proportionality: height == value * scale for a single scale factor.
    values = sorted((row.value for row in t.rows), reverse=True)
    scales = [h / v for h, v in zip(sorted(widths, reverse=True), values)]
    np.testing.assert_allclose(scales, scales[0], rtol=1e-10)
    plt.close(fig)
