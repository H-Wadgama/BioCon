"""
GHG Emissions Scenario Bar Chart
Construction-phase + operational emissions across three biorefinery case studies.
Produces SVG + PNG (300 DPI) suitable for manuscript submission.
"""

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D

# ── Font setup ──────────────────────────────────────────────────────────────
FONT_PREF = ["Gill Sans MT", "Gill Sans", "Arial", "Liberation Sans"]
matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["font.sans-serif"] = FONT_PREF + ["DejaVu Sans"]
matplotlib.rcParams["pdf.fonttype"] = 42   # embed fonts properly
matplotlib.rcParams["svg.fonttype"] = "none"
matplotlib.rcParams["axes.linewidth"] = 0.6
matplotlib.rcParams["xtick.major.width"] = 0.6
matplotlib.rcParams["ytick.major.width"] = 0.6

# ── Data ────────────────────────────────────────────────────────────────────
case_studies = ["In-situ\npyrolysis", "Ex-situ\npyrolysis", "Humbird et al."]

# (operational, construction)  g CO2 eq / MJ
without_elec = [(13.10, 0.58), (12.56, 0.58), (23.00, 0.73)]
with_elec    = [( 9.20, 0.58), (10.20, 0.58), ( 6.00, 0.73)]
petroleum    = 93.07

# ── Colours ─────────────────────────────────────────────────────────────────
# Without electricity credits: blue family
C_WO_OP    = "#185FA5"   # operational  – dark blue
C_WO_CON   = "#85B7EB"   # construction – light blue
# With electricity credits: teal / green family
C_WI_OP    = "#0F6E56"   # operational  – dark teal
C_WI_CON   = "#5DCAA5"   # construction – light teal
# Petroleum
C_PETRO    = "#A32D2D"

# ── Layout ──────────────────────────────────────────────────────────────────
fig_w_in  = 3.54       # ~90 mm — standard single-column width
fig_h_in  = 3.40
bar_w     = 0.30
gap       = 0.06       # gap between paired bars
x         = np.arange(len(case_studies))
x_wo      = x - (bar_w / 2 + gap / 2)   # left bar (w/o elec)
x_wi      = x + (bar_w / 2 + gap / 2)   # right bar (w/ elec)

fig, ax = plt.subplots(figsize=(fig_w_in, fig_h_in))

# ── Stacked bars ─────────────────────────────────────────────────────────────
ops_wo  = [v[0] for v in without_elec]
cons_wo = [v[1] for v in without_elec]
ops_wi  = [v[0] for v in with_elec]
cons_wi = [v[1] for v in with_elec]

# Without electricity credits
ax.bar(x_wo, ops_wo,  bar_w, color=C_WO_OP,  zorder=3, linewidth=0)
ax.bar(x_wo, cons_wo, bar_w, color=C_WO_CON, zorder=3, linewidth=0,
       bottom=ops_wo)

# With electricity credits
ax.bar(x_wi, ops_wi,  bar_w, color=C_WI_OP,  zorder=3, linewidth=0)
ax.bar(x_wi, cons_wi, bar_w, color=C_WI_CON, zorder=3, linewidth=0,
       bottom=ops_wi)

# ── Petroleum baseline ───────────────────────────────────────────────────────
petro_line = ax.axhline(petroleum, color=C_PETRO, linewidth=1.0,
                        linestyle=(0, (6, 3)), zorder=4)
ax.text(x[-1] + bar_w / 2 + gap / 2 + 0.08, petroleum + 1.2,
        "Petroleum baseline\n(93.07 g CO₂ eq/MJ)",
        fontsize=5.5, color=C_PETRO, va="bottom", ha="left", linespacing=1.4)

# ── Axes styling ─────────────────────────────────────────────────────────────
ax.set_xticks(x)
ax.set_xticklabels(case_studies, fontsize=7)
ax.set_ylabel("g CO₂ eq / MJ", fontsize=7)
ax.set_ylim(0, 110)
ax.set_xlim(x[0] - 0.55, x[-1] + 0.90)
ax.yaxis.set_tick_params(labelsize=6.5, direction="in", length=3)
ax.xaxis.set_tick_params(labelsize=7,   direction="in", length=3)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.yaxis.grid(True, linewidth=0.3, color="#cccccc", zorder=0)
ax.set_axisbelow(True)

# ── Legend ───────────────────────────────────────────────────────────────────
legend_elements = [
    mpatches.Patch(facecolor=C_WO_OP,  label="Operational — w/o elec. credits"),
    mpatches.Patch(facecolor=C_WO_CON, label="Construction — w/o elec. credits"),
    mpatches.Patch(facecolor=C_WI_OP,  label="Operational — w/ elec. credits"),
    mpatches.Patch(facecolor=C_WI_CON, label="Construction — w/ elec. credits"),
]
ax.legend(
    handles=legend_elements,
    fontsize=5.5,
    frameon=False,
    loc="upper right",
    handlelength=1.0,
    handletextpad=0.4,
    labelspacing=0.35,
)

# ── Group labels below x-axis ─────────────────────────────────────────────────
label_y = -0.175   # axes-fraction units
for xi, label_pair in zip(x, [("w/o", "w/"), ("w/o", "w/"), ("w/o", "w/")]):
    ax.text(xi - (bar_w / 2 + gap / 2), label_y, "w/o",
            ha="center", va="top", fontsize=5.5,
            color="#555555", transform=ax.get_xaxis_transform())
    ax.text(xi + (bar_w / 2 + gap / 2), label_y, "w/",
            ha="center", va="top", fontsize=5.5,
            color="#555555", transform=ax.get_xaxis_transform())

# Sub-label: "elec. credits" centred under each group
for xi in x:
    ax.text(xi, label_y - 0.055, "elec. credits",
            ha="center", va="top", fontsize=5.0,
            color="#777777", transform=ax.get_xaxis_transform())

# ── Export ───────────────────────────────────────────────────────────────────
fig.tight_layout(rect=[0, 0.02, 1, 1])
fig.savefig("/mnt/user-data/outputs/ghg_scenarios_barchart.svg",
            format="svg", dpi=300, bbox_inches="tight")
fig.savefig("/mnt/user-data/outputs/ghg_scenarios_barchart.png",
            format="png", dpi=300, bbox_inches="tight")
print("Saved SVG and PNG.")
plt.show()
