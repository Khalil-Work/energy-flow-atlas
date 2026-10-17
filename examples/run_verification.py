"""Produce the Sankey figures, animation, and raw data for Energy Flow Atlas.

Two tables:
1. Engineering example: a computed air-handling energy balance (values
   derived from the documented operating point - all in W, internal nodes
   must balance).
2. Sample-allocation demo table explicitly labeled illustrative.

Outputs: sankey figures (engineering + illustrative), balance CSVs,
41-frame GIF (progressive commissioning: load fraction 0..1, each frame a
fully re-balanced table), run_summary.json.
"""

from __future__ import annotations

import json
import pathlib
import platform
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.animation as mpl_animation
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from energy_flow_atlas import FlowTable, render_sankey

RESULTS = pathlib.Path(__file__).resolve().parents[1] / "docs" / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

BLUE, GRAY = "#1f4e79", "#555555"
plt.rcParams.update(
    {
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "axes.grid": False,
        "font.size": 10,
    }
)


def build_engineering(load_fraction=1.0):
    """Balanced engineering table (supply node balances via a return path)."""
    fan = 300.0 * load_fraction
    equip = 1200.0 * load_fraction
    envelope = 150.0 * load_fraction
    duct_loss = 0.05 * fan
    delivered = fan - duct_loss
    t = FlowTable(
        "energy", "W",
        internal_nodes=("room", "supply", "return"),
        title="Air-handling energy balance (computed operating point)",
    )
    # Supply air path: fan power enters supply; duct loss leaves; the rest
    # is delivered to the room; room exhaust returns through the return
    # node back to the fan (closed air loop, energy accounted).
    t.add("fan power", "supply", fan)
    t.add("supply", "duct loss", duct_loss)
    t.add("supply", "room", delivered)
    t.add("equipment", "room", equip)
    t.add("envelope gain", "room", envelope)
    room_out = delivered + equip + envelope
    t.add("room", "return", room_out)
    t.add("return", "coil", room_out - fan)  # coil removes the net
    t.add("return", "fan power", fan)        # recovered air-side energy
    return t


def illustrative_table():
    t = FlowTable(
        "samples", "count",
        illustrative=True,
        title="Sample allocation across processing stages",
    )
    t.add("raw batch", "cleaning", 1000)
    t.add("cleaning", "rejected", 40)
    t.add("cleaning", "feature extraction", 960)
    t.add("feature extraction", "discarded features", 110)
    t.add("feature extraction", "training split", 850)
    t.add("training split", "held-out eval", 150)
    return t


def render_and_save(table, filename):
    fig, ax = plt.subplots(figsize=(11.0, 5.8))
    render_sankey(table, ax=ax)
    fig.tight_layout()
    fig.savefig(RESULTS / filename, dpi=150, bbox_inches="tight")
    fig.savefig(RESULTS / (filename.replace(".png", ".svg")), dpi=180,
                bbox_inches="tight")
    plt.close(fig)


def write_balance_csv(table, filename):
    rep = table.check()
    rows = ["node,inflow,outflow,imbalance,is_internal"]
    for node in sorted(set(rep.inflow) | set(rep.outflow)):
        rows.append(
            f"{node},{rep.inflow.get(node, 0.0):.6f},"
            f"{rep.outflow.get(node, 0.0):.6f},"
            f"{rep.imbalance[node]:.6f},{int(node in table.internal)}"
        )
    (RESULTS / filename).write_text("\n".join(rows), encoding="utf-8")
    return rep


def make_gif(frames=41):
    fracs = np.linspace(0.05, 1.0, frames)
    fig, ax = plt.subplots(figsize=(11.0, 5.8), dpi=120)
    writer = mpl_animation.PillowWriter(fps=8)

    with writer.saving(fig, RESULTS / "commissioning.gif", dpi=120):
        for f in fracs:
            ax.clear()
            t = build_engineering(f)
            render_sankey(t, ax=ax)
            writer.grab_frame()
    plt.close(fig)
    return frames


def main():
    eng = build_engineering(1.0)
    rep = eng.check()  # raises unless balanced
    render_and_save(eng, "engineering_balance.png")
    write_balance_csv(eng, "engineering_balance.csv")

    ill = illustrative_table()
    rep_ill = ill.check()  # internal nodes: none declared -> balanced
    render_and_save(ill, "illustrative_allocation.png")
    write_balance_csv(ill, "illustrative_allocation.csv")

    frames = make_gif()

    summary = {
        "runtime": {
            "python": platform.python_version(),
            "matplotlib": matplotlib.__version__,
            "system": platform.platform(),
        },
        "results": {
            "engineering_max_internal_imbalance_W": rep.max_abs_imbalance,
            "engineering_total_flow_W": sum(r.value for r in eng.rows),
            "illustrative_max_internal_imbalance": rep_ill.max_abs_imbalance,
            "proportionality": "single scale factor verified geometrically "
                               "in the test suite",
        },
        "animation": {"file": "commissioning.gif", "frames": frames,
                      "content": "each frame is a fully re-balanced "
                                 "engineering table at that load fraction"},
    }
    (RESULTS / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary["results"], indent=2))
    print("frames", frames)


if __name__ == "__main__":
    main()
