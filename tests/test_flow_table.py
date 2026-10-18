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
    # Hand-checkable: 100 W in, splits into 60 W useful load / 40 W loss.
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


def test_constructor_rejects_silent_unit_relabeling():
    from energy_flow_atlas import FlowRow
    with pytest.raises(ValueError, match="mixed units"):
        FlowTable("energy", "W", rows=[FlowRow("a", "b", 1.0, "kW")])
    table = FlowTable("energy", "W", rows=[FlowRow("a", "b", 1000.0, "W")])
    assert table.rows[0].value == 1000.0


def test_custom_title_keeps_illustrative_disclosure():
    table = FlowTable("samples", "count", illustrative=True, title="Allocation")
    table.add("a", "b", 1)
    fig, ax = plt.subplots()
    render_sankey(table, ax)
    assert "illustrative" in ax.get_title()
    plt.close(fig)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1, True, "1e-9"])
def test_invalid_tolerance_cannot_silently_pass_balance(bad):
    with pytest.raises(ValueError, match="tolerance"):
        balanced_table().check(bad)


@pytest.mark.parametrize("bad", [12, [], " "])
def test_invalid_node_names_rejected(bad):
    with pytest.raises(ValueError, match="node"):
        FlowTable("energy", "W").add(bad, "sink", 1)


def test_absent_internal_node_is_not_vacuously_balanced():
    table = FlowTable("energy", "W", internal_nodes=("typo",)).add("a", "b", 1)
    with pytest.raises(ValueError, match="absent"):
        table.check()


def test_aggregate_overflow_is_an_explicit_error():
    table = FlowTable("energy", "W").add("a", "b", 1e308).add("a", "c", 1e308)
    with pytest.raises(ValueError, match="aggregate"):
        table.check()


def test_rendering_enforces_conservation_and_rejects_cycles():
    broken = FlowTable("energy", "W", internal_nodes=("b",))
    broken.add("a", "b", 10).add("b", "c", 7)
    with pytest.raises(ValueError, match="imbalanced"):
        render_sankey(broken)
    cyclic = FlowTable("energy", "W").add("a", "b", 10).add("b", "a", 10)
    assert cyclic.check().balanced  # accounting itself supports cycles
    with pytest.raises(ValueError, match="cycle"):
        render_sankey(cyclic)


def test_ribbon_has_positive_area_and_correct_interior_thickness():
    table = FlowTable("energy", "W").add("source", "sink", 100)
    fig, ax = plt.subplots()
    render_sankey(table, ax)
    polygon = next(p for p in ax.patches if p.get_gid().startswith("flow:"))
    points = polygon.get_xy()
    area = abs(np.sum(points[:-1, 0] * points[1:, 1] - points[1:, 0] * points[:-1, 1])) / 2
    left, right = points[:, 0].min(), points[:, 0].max()
    expected_height = 0.78
    assert area == pytest.approx((right - left) * expected_height)
    # Interior vertical cuts independently intersect the actual polygon edges.
    for x in np.linspace(left, right, 13)[1:-1]:
        crossings = []
        for a, b in zip(points[:-1], points[1:]):
            if min(a[0], b[0]) <= x < max(a[0], b[0]):
                crossings.append(a[1] + (x-a[0]) / (b[0]-a[0]) * (b[1]-a[1]))
        assert len(crossings) == 2
        assert abs(crossings[1] - crossings[0]) == pytest.approx(expected_height)
    plt.close(fig)


def test_reordered_edges_keep_true_node_connections_and_bar_throughput():
    original = balanced_table()
    reordered = FlowTable("energy", "W", rows=list(reversed(original.rows)), internal_nodes=original.internal)
    layouts = []
    for table in (original, reordered):
        fig, ax = plt.subplots()
        render_sankey(table, ax)
        nodes = {p.get_gid()[5:]: p for p in ax.patches if p.get_gid().startswith("node:")}
        ribbons = {p.get_gid(): p for p in ax.patches if p.get_gid().startswith("flow:")}
        report = table.check()
        scale = nodes["converter"].get_height() / 100
        for name, bar in nodes.items():
            assert bar.get_height() == pytest.approx(max(report.inflow[name], report.outflow[name]) * scale)
        for row in table.rows:
            vertices = ribbons[f"flow:{row.source}->{row.target}"].get_xy()
            assert vertices[:, 0].min() == pytest.approx(nodes[row.source].get_x() + nodes[row.source].get_width())
            assert vertices[:, 0].max() == pytest.approx(nodes[row.target].get_x())
        layouts.append({name: (bar.get_x(), bar.get_y(), bar.get_height()) for name, bar in nodes.items()})
        plt.close(fig)
    assert layouts[0] == layouts[1]


def test_fixed_scale_changes_width_with_physical_load():
    from examples.run_verification import build_engineering
    heights = []
    for load in (0.05, 1.0):
        table = build_engineering(load)
        report = table.check()
        assert report.inflow["cooling coil"] == pytest.approx(1635 * load)
        assert report.inflow["duct loss"] + report.inflow["cooling coil"] == pytest.approx(1650 * load)
        fig, ax = plt.subplots()
        render_sankey(table, ax, flow_scale=0.0003)
        heights.append(next(p.get_height() for p in ax.patches if p.get_gid() == "node:cooling coil"))
        plt.close(fig)
    assert heights[0] / heights[1] == pytest.approx(0.05)
