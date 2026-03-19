"""
GWP Parity Plot — Process-based vs. EIO-LCA
============================================
Generates a publication-quality parity plot exportable as SVG (editable
in Illustrator / Inkscape) or PNG. Designed to scale to multiple case studies.

Dependencies:
    pip install matplotlib numpy

Usage:
    python gwp_parity_plot.py
    → outputs gwp_parity_plot.svg and gwp_parity_plot.png
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.lines import Line2D

# ── 1. DATA ──────────────────────────────────────────────────────────────────
# Each case study is a dict with:
#   "label"   : legend label string
#   "process" : list of process-based GWP values (kg CO2 eq.)
#   "eio"     : list of EIO-LCA GWP values (kg CO2 eq.)
#   "color"   : matplotlib color for scatter points
#   "marker"  : matplotlib marker style (keep distinct per case study)

CASE_STUDIES = [
    {
        "label": "Dutta et al. (2015)",
        "color": "#1D9E75",
        "edge":  "#0F6E56",
        "marker": "o",
        "process": [
            247000, 1710000, 688000, 247000, 120000, 112000, 39400, 17600,
            54100, 3240, 3850, 3450, 23600, 4020, 4330, 2190, 3450, 23600,
            373, 5060, 5060, 5060, 4460, 7070, 5900, 5900, 4540,
        ],
        "eio": [
            201000, 2700000, 464000, 238000, 412000, 426000, 177000, 110000,
            124000, 18900, 22100, 18400, 282000, 14600, 50000, 12600, 53300,
            46500, 3260, 18800, 26300, 9690, 7650, 9150, 9520, 8950, 7220,
        ],
    },
    {
        "label": "Humbird et al. (2011)",
        "color": "#185FA5",
        "edge":  "#0C447C",
        "marker": "s",
        "process": [
            402000, 4910, 38700, 7770, 115000, 50700, 120000, 359000,
            2540000, 93900, 24100, 39100, 215000, 6000000, 395, 395,
            10000, 77400, 342000, 93900, 493, 2270, 14700,
        ],
        "eio": [
            8640000, 3650, 7760, 6980, 239000, 95000, 106000, 199000,
            1730000, 128000, 47000, 79800, 1450000, 4420000, 32900, 50900,
            68700, 154000, 515000, 1570000, 80300, 100000, 166000,
        ],
    },
    # ── Add further case studies here, following the same structure ──────────
    # {
    #     "label"  : "Case study 3",
    #     "color"  : "#D85A30",
    #     "edge"   : "#993C1D",
    #     "marker" : "^",
    #     "process": [...],
    #     "eio"    : [...],
    # },
]

# ── 2. OUTPUT SETTINGS ───────────────────────────────────────────────────────
OUTPUT_SVG = "gwp_parity_plot.svg"
OUTPUT_PNG = "gwp_parity_plot.png"
PNG_DPI    = 300          # use 600 for some journal requirements
FIG_SIZE   = (5.5, 5.0)  # inches — typical single-column journal width

# ── 3. STYLE SETTINGS ────────────────────────────────────────────────────────
FONT_FAMILY    = "Arial"    # swap to "Helvetica" or "Times New Roman" per journal
AXIS_LABEL_FS  = 10
TICK_FS        = 8.5
LEGEND_FS      = 8.5
POINT_SIZE     = 28         # scatter marker area (s= parameter)
POINT_ALPHA    = 0.75
PARITY_COLOR   = "#888780"  # 1:1 line
GRID_COLOR     = "#dedede"

# ── 4. DERIVED VALUES ─────────────────────────────────────────────────────────
all_process = [v for cs in CASE_STUDIES for v in cs["process"]]
all_eio     = [v for cs in CASE_STUDIES for v in cs["eio"]]

for cs in CASE_STUDIES:
    cs["total_p"] = sum(cs["process"])
    cs["total_e"] = sum(cs["eio"])
    cs["agg_r"]   = cs["total_e"] / cs["total_p"]

# ── 5. PLOT ───────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.family":       FONT_FAMILY,
    "axes.linewidth":    0.6,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "xtick.major.size":  3,
    "ytick.major.size":  3,
    "xtick.direction":   "out",
    "ytick.direction":   "out",
})

fig, ax = plt.subplots(figsize=FIG_SIZE)

# ── axis limits: pad ~0.4 log-decades beyond data range
combined   = all_process + all_eio
ax_min     = 10 ** (np.floor(np.log10(min(combined))) - 0.2)
ax_max     = 10 ** (np.ceil(np.log10(max(combined)))  + 0.2)
axis_range = [ax_min, ax_max]

ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlim(axis_range)
ax.set_ylim(axis_range)

# ── grid
ax.grid(True, which="major", color=GRID_COLOR, linewidth=0.5, zorder=0)
ax.grid(True, which="minor", color=GRID_COLOR, linewidth=0.25, linestyle=":", zorder=0)
ax.set_axisbelow(True)

# ── 1:1 parity line
ax.plot(axis_range, axis_range,
        color=PARITY_COLOR, linewidth=1.2, linestyle=(0,(5,4)),
        zorder=1, label="1:1 parity")

# ── per-case-study aggregate ratio lines
for cs in CASE_STUDIES:
    ratio_y = [v * cs["agg_r"] for v in axis_range]
    ax.plot(axis_range, ratio_y,
            color=cs["color"], linewidth=1.2, linestyle=(0,(7,4)),
            alpha=0.65, zorder=1,
            label=f"{cs['label']} ratio ({cs['agg_r']:.2f}\u00d7)")

# ── scatter points (ratio lines drawn first so points sit on top)
for cs in CASE_STUDIES:
    edge = cs.get("edge", cs["color"])
    ax.scatter(
        cs["process"], cs["eio"],
        s=POINT_SIZE, color=cs["color"], marker=cs["marker"],
        alpha=POINT_ALPHA, edgecolors=edge, linewidths=0.6,
        zorder=3, label=cs["label"],
    )

# ── axis labels
ax.set_xlabel("Process-based GWP (kg CO\u2082 eq.)", fontsize=AXIS_LABEL_FS, labelpad=8)
ax.set_ylabel("EIO-LCA GWP (kg CO\u2082 eq.)",       fontsize=AXIS_LABEL_FS, labelpad=8)

# ── tick formatting: e.g. 10³, 10⁶
ax.xaxis.set_major_formatter(ticker.LogFormatterMathtext())
ax.yaxis.set_major_formatter(ticker.LogFormatterMathtext())
ax.tick_params(labelsize=TICK_FS)

# ── legend
legend = ax.legend(
    fontsize=LEGEND_FS,
    frameon=True,
    framealpha=0.9,
    edgecolor="#cccccc",
    loc="upper left",
)
legend.get_frame().set_linewidth(0.5)

# ── per-case-study summary annotation (bottom-right)
annot_lines = []
for cs in CASE_STUDIES:
    annot_lines.append(
        f"{cs['label']}: {cs['total_p']/1e6:.2f} \u00d710\u2076 (process) "
        f"/ {cs['total_e']/1e6:.2f} \u00d710\u2076 (EIO) kg CO\u2082 eq."
    )
ax.annotate(
    "\n".join(annot_lines),
    xy=(0.97, 0.04), xycoords="axes fraction",
    ha="right", va="bottom",
    fontsize=7.0, color="#555555",
    bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#cccccc", lw=0.5),
)

plt.tight_layout(pad=1.2)

# ── 6. EXPORT ─────────────────────────────────────────────────────────────────
fig.savefig(OUTPUT_SVG, format="svg", bbox_inches="tight")
print(f"Saved: {OUTPUT_SVG}")

fig.savefig(OUTPUT_PNG, format="png", dpi=PNG_DPI, bbox_inches="tight")
print(f"Saved: {OUTPUT_PNG}  ({PNG_DPI} DPI)")

plt.show()
