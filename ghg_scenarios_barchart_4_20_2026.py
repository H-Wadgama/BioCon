import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import numpy as np
from pathlib import Path

TARGET_DPI = 300
FIG_W      = 6.0
FIG_H      = 4.0

FONTS = ["Gill Sans MT", "Gill Sans", "Arial", "Liberation Sans"]
plt.rcParams["font.family"]      = "sans-serif"
plt.rcParams["font.sans-serif"]  = FONTS
plt.rcParams["axes.linewidth"]   = 2.0
plt.rcParams["xtick.direction"]  = "in"
plt.rcParams["ytick.direction"]  = "in"
plt.rcParams["mathtext.fontset"] = "custom"
plt.rcParams["mathtext.sf"]      = "Arial"
plt.rcParams["svg.fonttype"]     = "none"

FS_TITLE  = 11.0
FS_YLABEL = 11.0
FS_YTICK  =  9.5
FS_LEGEND =  8.0

# ── Data ──────────────────────────────────────────────────────────────
cases   = ["In-situ pyrolysis", "Ex-situ pyrolysis", "Cellulosic ethanol"]
op_disp = np.array([ 9.18, 10.15,  5.84])
op_eng  = np.array([12.11, 12.22, 19.12])
con_lo  = np.array([ 0.56,  0.58,  0.73])
con_hi  = np.array([ 3.03,  3.15,  4.21])

# ── Layout ────────────────────────────────────────────────────────────
n           = len(cases)
bar_w       = 0.36
pair_gap    = 0.10
group_gap   = 0.72
group_pitch = bar_w * 2 + pair_gap + group_gap

gc  = np.arange(n) * group_pitch
x_d = gc - bar_w / 2 - pair_gap / 2
x_e = gc + bar_w / 2 + pair_gap / 2

# ── Colours ───────────────────────────────────────────────────────────
c_op_d   = "#007093"
c_op_e   = "#C17B1E"
c_con_lo = "#3B6D11"   # green  — baseline circle
c_con_hi = "#A32D2D"   # red    — high diamond

MS  = 7.5
MEW = 1.2

# ── Figure ────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))

for i in range(n):
    # Operational bars
    ax.bar(x_d[i], op_disp[i], bar_w, color=c_op_d, zorder=3, linewidth=0)
    ax.bar(x_e[i], op_eng[i],  bar_w, color=c_op_e, zorder=3, linewidth=0)

    # Construction markers — both centred on bar x
    ax.plot(x_d[i], op_disp[i] + con_lo[i],
            marker="o", markersize=MS, color=c_con_lo,
            markeredgecolor="white", markeredgewidth=MEW, zorder=5)
    ax.plot(x_e[i], op_eng[i] + con_lo[i],
            marker="o", markersize=MS, color=c_con_lo,
            markeredgecolor="white", markeredgewidth=MEW, zorder=5)

    ax.plot(x_d[i], op_disp[i] + con_hi[i],
            marker="D", markersize=MS, color=c_con_hi,
            markeredgecolor="white", markeredgewidth=MEW, zorder=5)
    ax.plot(x_e[i], op_eng[i] + con_hi[i],
            marker="D", markersize=MS, color=c_con_hi,
            markeredgecolor="white", markeredgewidth=MEW, zorder=5)

# ── Zero line ─────────────────────────────────────────────────────────
ax.axhline(0, color="#1a1a1a", linewidth=1.1, zorder=2)

# ── Dashed vertical separators ────────────────────────────────────────
for i in range(1, n):
    ax.axvline((gc[i - 1] + gc[i]) / 2, color="#888780",
               linewidth=0.9, linestyle=(0, (5, 4)), zorder=1)

# ── Case study labels ─────────────────────────────────────────────────
y_top = (np.maximum(op_disp, op_eng) + con_hi).max()
for i, name in enumerate(cases):
    ax.text(gc[i], y_top + 0.8, name,
            ha="center", va="bottom",
            fontsize=FS_TITLE, color="#1a1a1a")

# ── Axes ──────────────────────────────────────────────────────────────
y_min = 0
y_max = y_top + 4.0

ax.set_xlim(gc[0]  - group_pitch / 2 + 0.01,
            gc[-1] + group_pitch / 2 - 0.01)
ax.set_ylim(y_min, y_max)
ax.set_xticks([])

yticks = np.arange(0, int(np.floor(y_max / 5)) * 5 + 1, 5)
ax.set_yticks(yticks)
ax.set_yticklabels([str(int(v)) for v in yticks], fontsize=FS_YTICK)
ax.set_ylabel(
    r"GHG intensity (g $\mathregular{CO_2}$ eq $\mathregular{MJ^{-1}}$)",
    fontsize=FS_YLABEL, labelpad=8)

ax.tick_params(axis="y", which="both", direction="in",
               length=4, width=2.0)
ax.tick_params(axis="x", bottom=False, top=False)

for spine in ax.spines.values():
    spine.set_visible(True)
    spine.set_linewidth(2.0)

ax.yaxis.grid(True, linewidth=2, color="#CCCCCC", zorder=0)
ax.set_axisbelow(True)

# ── Legend ────────────────────────────────────────────────────────────
legend_items = [
    mpatches.Patch(facecolor=c_op_d, label="Displacement allocation"),
    mpatches.Patch(facecolor=c_op_e, label="Energy allocation"),
    mlines.Line2D([], [], marker="o", color="none",
                  markerfacecolor=c_con_lo, markeredgecolor="white",
                  markeredgewidth=MEW, markersize=MS,
                  label="Construction GHG — baseline"),
    mlines.Line2D([], [], marker="D", color="none",
                  markerfacecolor=c_con_hi, markeredgecolor="white",
                  markeredgewidth=MEW, markersize=MS,
                  label="Construction GHG — high estimate"),
]
ax.legend(
    handles=legend_items,
    fontsize=FS_LEGEND,
    loc="upper left",
    frameon=True,
    framealpha=0.93,
    edgecolor="#AAAAAA",
    fancybox=False,
    handlelength=1.6,
    handletextpad=0.6,
    borderpad=0.75,
    labelspacing=0.40,
)

fig.tight_layout(pad=0.6)

out_dir = Path(__file__).parent
fig.savefig(out_dir / "ghg_scenarios_barchart_v11.svg",
            bbox_inches="tight", format="svg")
fig.savefig(out_dir / "ghg_scenarios_barchart_v11.png",
            dpi=TARGET_DPI, bbox_inches="tight")
print("Done:", out_dir)
plt.close()