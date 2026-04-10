import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

# ── Font / style ──────────────────────────────────────────────────────
FONTS = ["Gill Sans MT", "Gill Sans", "Arial", "Liberation Sans"]
plt.rcParams["font.family"]      = "sans-serif"
plt.rcParams["font.sans-serif"]  = FONTS
plt.rcParams["axes.linewidth"]   = 0.6
plt.rcParams["xtick.direction"]  = "in"
plt.rcParams["ytick.direction"]  = "in"
plt.rcParams["mathtext.fontset"] = "custom"
plt.rcParams["mathtext.sf"]      = "Arial"   # fallback math font for sub/superscripts

# ── Data ──────────────────────────────────────────────────────────────
case_studies = ["In-situ\npyrolysis", "Ex-situ\npyrolysis", "Humbird\net al."]

op_without  = np.array([13.10, 12.56, 23.00])
con_without = np.array([ 0.58,  0.58,  0.73])

op_with     = np.array([ 9.20, 10.20,  6.00])
con_with    = np.array([ 0.58,  0.58,  0.73])

petroleum   = 93.07

# ── Figure ────────────────────────────────────────────────────────────
fig_w_in = 3.5          # single-column (~89 mm); set to 5.0 for double-column
fig_h_in = 3.0
fig, ax = plt.subplots(figsize=(fig_w_in, fig_h_in))

n     = len(case_studies)
x     = np.arange(n)
bar_w = 0.32
gap   = 0.04

x_left  = x - bar_w / 2 - gap / 2
x_right = x + bar_w / 2 + gap / 2

# ── Colours ───────────────────────────────────────────────────────────
c_op_wo  = "#185FA5"    # deep blue  — operational w/o
c_con_wo = "#85B7EB"    # light blue — construction w/o
c_op_wi  = "#0F6E56"    # deep teal  — operational w/
c_con_wi = "#5DCAA5"    # light teal — construction w/
c_petro  = "#A32D2D"    # dark red   — petroleum baseline

# ── Bars ──────────────────────────────────────────────────────────────
ax.bar(x_left,  op_without,  bar_w, color=c_op_wo,  zorder=3)
ax.bar(x_left,  con_without, bar_w, bottom=op_without,
       color=c_con_wo, zorder=3)

ax.bar(x_right, op_with,  bar_w, color=c_op_wi,  zorder=3)
ax.bar(x_right, con_with, bar_w, bottom=op_with,
       color=c_con_wi, zorder=3)

# ── Petroleum baseline line ───────────────────────────────────────────
x_line = [x[0] - bar_w - gap / 2 - 0.05,
          x[-1] + bar_w + gap / 2 + 0.05]
ax.plot(x_line, [petroleum, petroleum],
        color=c_petro, linewidth=1.2,
        linestyle=(0, (5, 3)), zorder=4)
ax.text(x_line[1] + 0.03, petroleum,
        f"{petroleum:.0f}",
        va="center", ha="left",
        fontsize=6.5, color=c_petro)

# ── Axes ──────────────────────────────────────────────────────────────
ax.set_xticks(x)
ax.set_xticklabels(case_studies, fontsize=7.5)
ax.set_xlim(x[0] - bar_w - gap / 2 - 0.15,
            x[-1] + bar_w + gap / 2 + 0.25)

ax.set_ylim(0, 105)
ax.set_yticks([0, 20, 40, 60, 80, 100])

# Use mathtext for sub/superscripts — avoids Unicode glyph issues
ax.set_ylabel(r"GHG intensity (g $\mathregular{CO_2}$ eq $\mathregular{MJ^{-1}}$)",
              fontsize=8)

ax.tick_params(axis="both", which="both", direction="in",
               labelsize=7.5, length=3, width=0.6)
ax.tick_params(axis="x", which="both", bottom=True, top=False)
ax.tick_params(axis="y", which="both", left=True, right=False)

ax.yaxis.grid(True, linewidth=0.35, color="#cccccc", zorder=0)
ax.set_axisbelow(True)

# ── Sub-labels (w/o / w/) below x-axis ───────────────────────────────
y_sub = -10.5
for xi in x:
    ax.text(xi - bar_w / 2 - gap / 2, y_sub, "w/o",
            ha="center", va="top", fontsize=5.5,
            color="#555555", clip_on=False)
    ax.text(xi + bar_w / 2 + gap / 2, y_sub, "w/",
            ha="center", va="top", fontsize=5.5,
            color="#555555", clip_on=False)

# ── Legend ────────────────────────────────────────────────────────────
legend_items = [
    mpatches.Patch(facecolor=c_op_wo,  label="Operational — w/o elec. credits"),
    mpatches.Patch(facecolor=c_con_wo, label="Construction — w/o elec. credits"),
    mpatches.Patch(facecolor=c_op_wi,  label="Operational — w/ elec. credits"),
    mpatches.Patch(facecolor=c_con_wi, label="Construction — w/ elec. credits"),
    plt.Line2D([0], [0], color=c_petro, linewidth=1.2,
               linestyle=(0, (5, 3)), label="Petroleum baseline"),
]
ax.legend(
    handles=legend_items,
    fontsize=5.8,
    loc="upper right",
    frameon=True,
    framealpha=0.92,
    edgecolor="#cccccc",
    fancybox=False,
    handlelength=1.6,
    handletextpad=0.5,
    borderpad=0.6,
    labelspacing=0.35,
)

fig.tight_layout(rect=[0, 0.02, 1, 1])

# ── Output — saved next to the script ────────────────────────────────
out_dir = Path(__file__).parent
fig.savefig(out_dir / "ghg_scenarios_barchart.png", dpi=300, bbox_inches="tight")
fig.savefig(out_dir / "ghg_scenarios_barchart.pdf",           bbox_inches="tight")
print("Saved PNG and PDF to:", out_dir)
plt.close()
