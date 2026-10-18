"""Produce the Sankey figures, animation, and raw data for Energy Flow Atlas.

Two tables:
1. Engineering example: a computed air-handling energy balance (values
   derived from the documented operating point - all in W, internal nodes
   must balance).
2. Sample-allocation demo table explicitly labeled illustrative.

Outputs: sankey figures (engineering + illustrative), balance CSVs,
41-frame GIF (steady operating-point sweep: load fraction 0.05..1, each frame a
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
    """Steady energy ledger; recirculating air is not recirculating power."""
    if not np.isfinite(load_fraction) or not 0 <= load_fraction <= 1:
        raise ValueError("load_fraction must be finite and in [0, 1]")
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
    # Fan work becomes heat; equipment/envelope add heat in the room.
    # The coil removes ALL room heat. No energy is credited back to the
    # electrical fan source merely because the air itself recirculates.
    t.add("fan power", "supply", fan)
    t.add("supply", "duct loss", duct_loss)
    t.add("supply", "room", delivered)
    t.add("equipment", "room", equip)
    t.add("envelope gain", "room", envelope)
    room_out = delivered + equip + envelope
    t.add("room", "return", room_out)
    t.add("return", "cooling coil", room_out)
    return t


def illustrative_table():
    t = FlowTable(
        "samples", "count",
        internal_nodes=("cleaning", "screening", "training split"),
        illustrative=True,
        title="Sample allocation across processing stages",
    )
    t.add("raw batch", "cleaning", 1000)
    t.add("cleaning", "rejected", 40)
    t.add("cleaning", "screening", 960)
    t.add("screening", "screened out", 110)
    t.add("screening", "training split", 850)
    t.add("training split", "held-out eval", 150)
    t.add("training split", "training set", 700)
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
    rows = ["node,inflow,outflow,imbalance,is_internal,quantity,unit,illustrative"]
    for node in sorted(set(rep.inflow) | set(rep.outflow)):
        rows.append(
            f"{node},{rep.inflow.get(node, 0.0):.6f},"
            f"{rep.outflow.get(node, 0.0):.6f},"
            f"{rep.imbalance[node]:.6f},{int(node in table.internal)},"
            f"{table.quantity},{table.unit},{int(table.illustrative)}"
        )
    (RESULTS / filename).write_text("\n".join(rows), encoding="utf-8")
    return rep


def make_gif(frames=41):
    fracs = np.linspace(0.05, 1.0, frames)
    fig, ax = plt.subplots(figsize=(11.0, 6.0), dpi=100)
    fig.subplots_adjust(left=0.02, right=0.98, bottom=0.05, top=0.82)
    # Fixed physical scale: widths grow with actual W rather than normalizing
    # every operating point back to the same full-size diagram.
    scale = (0.78 - 2 * 0.10) / 1650.0
    frame_rows = []
    writer = mpl_animation.PillowWriter(fps=8)

    with writer.saving(fig, RESULTS / "commissioning.gif", dpi=100):
        for f in fracs:
            ax.clear()
            t = build_engineering(f)
            report = t.check()
            render_sankey(t, ax=ax, flow_scale=scale)
            ax.set_title(f"Air-handling load sweep · {f:.1%} of rated input\n"
                         f"Fan {300*f:.1f} W + equipment {1200*f:.1f} W + envelope {150*f:.1f} W",
                         fontsize=11, pad=12)
            fig.texts.clear()
            fig.text(0.5, 0.025, "Steady operating points · fixed W-to-height scale · not a startup transient",
                     ha="center", fontsize=9, color=GRAY)
            for row in t.rows:
                frame_rows.append(f"{f:.8f},{row.source},{row.target},{row.value:.8f},W,{report.max_abs_imbalance:.12g}")
            writer.grab_frame()
    plt.close(fig)
    (RESULTS / "commissioning_flows.csv").write_text(
        "load_fraction,source,target,power,unit,max_internal_imbalance\n" + "\n".join(frame_rows), encoding="utf-8")
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
            "engineering_edge_sum_W": sum(r.value for r in eng.rows),
            "external_power_input_W": 1650.0,
            "cooling_coil_W": rep.inflow["cooling coil"],
            "duct_loss_W": rep.inflow["duct loss"],
            "illustrative_max_internal_imbalance": rep_ill.max_abs_imbalance,
            "proportionality": "single scale factor verified geometrically "
                               "in the test suite",
        },
        "animation": {"file": "commissioning.gif", "frames": frames,
                      "load_fraction_range": [0.05, 1.0],
                      "fixed_height_per_W": (0.78 - 2 * 0.10) / 1650.0,
                      "content": "steady operating-point sweep; fixed physical scale; "
                                 "each table is balanced; not a startup transient"},
    }
    (RESULTS / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary["results"], indent=2))
    print("frames", frames)


if __name__ == "__main__":
    main()
