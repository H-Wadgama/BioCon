import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

TARGET_DPI = 300
FIG_W      = 6.0
FIG_H      = 4.0

FONTS = ["Gill Sans MT", "Gill Sans", "Arial", "Liberation Sans"]
plt.rcParams["font.family"]      = "sans-serif"
plt.rcParams["font.sans-serif"]  = FONTS
plt.rcParams["axes.linewidth"]   = 1.0
plt.rcParams["xtick.direction"]  = "in"
plt.rcParams["ytick.direction"]  = "in"
plt.rcParams["mathtext.fontset"] = "custom"
plt.rcParams["mathtext.sf"]      = "Arial"
plt.rcParams["svg.fonttype"]     = "none"

FS_TITLE  = 11.0
FS_SUBLBL =  8.5
FS_YLABEL = 11.0
FS_YTICK  =  9.5
FS_LEGEND =  8.0

# ── Data ──────────────────────────────────────────────────────────────
cases   = ["In-situ pyrolysis", "Ex-situ pyrolysis", "Humbird et al."]
op_disp = np.array([ 9.18, 10.15,  5.84])
op_eng  = np.array([12.11, 12.22, 19.12])
con_lo  = np.array([ 0.56,  0.58,  0.73])

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
c_op_d = "#185FA5"
c_op_e = "#0F6E56"
c_con  = "#EF9F27"

# ── Figure ────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))

for i in range(n):
    ax.bar(x_d[i], op_disp[i], bar_w, color=c_op_d, zorder=3, linewidth=0)
    ax.bar(x_e[i], op_eng[i],  bar_w, color=c_op_e, zorder=3, linewidth=0)

    ax.bar(x_d[i], con_lo[i], bar_w, bottom=op_disp[i],
           color=c_con, zorder=3, linewidth=0)
    ax.bar(x_e[i], con_lo[i], bar_w, bottom=op_eng[i],
           color=c_con, zorder=3, linewidth=0)

# ── Zero line ─────────────────────────────────────────────────────────
ax.axhline(0, color="#1a1a1a", linewidth=1.1, zorder=2)

# ── Dashed vertical separators ────────────────────────────────────────
for i in range(1, n):
    ax.axvline((gc[i - 1] + gc[i]) / 2, color="#888780",
               linewidth=0.9, linestyle=(0, (5, 4)), zorder=1)

# ── Case study labels ─────────────────────────────────────────────────
y_top = (np.maximum(op_disp, op_eng) + con_lo).max()
for i, name in enumerate(cases):
    ax.text(gc[i], y_top + 0.8, name,
            ha="center", va="bottom",
            fontsize=FS_TITLE, color="#1a1a1a")

# ── Sub-bar labels ─────────────────────────────────────────────────────
y_sub = -0.6
for i in range(n):
    ax.text(x_d[i], y_sub, "Displacement\nallocation",
            ha="center", va="top", fontsize=FS_SUBLBL,
            color="#3a3a3a", linespacing=1.4, clip_on=False)
    ax.text(x_e[i], y_sub, "Energy\nallocation",
            ha="center", va="top", fontsize=FS_SUBLBL,
            color="#3a3a3a", linespacing=1.4, clip_on=False)

# ── Axes ──────────────────────────────────────────────────────────────
y_min = -3.5
y_max = y_top + 4.0

ax.set_xlim(gc[0]  - group_pitch / 2 + 0.1,
            gc[-1] + group_pitch / 2 - 0.1)
ax.set_ylim(y_min, y_max)
ax.set_xticks([])

yticks = np.arange(0, int(np.floor(y_max / 5)) * 5 + 1, 5)
ax.set_yticks(yticks)
ax.set_yticklabels([str(int(v)) for v in yticks], fontsize=FS_YTICK)
ax.set_ylabel(
    r"GHG intensity (g $\mathregular{CO_2}$ eq $\mathregular{MJ^{-1}}$)",
    fontsize=FS_YLABEL, labelpad=8)

ax.tick_params(axis="y", which="both", direction="in",
               length=4, width=1.0)
ax.tick_params(axis="x", bottom=False, top=False)

for spine in ax.spines.values():
    spine.set_visible(True)
    spine.set_linewidth(1.0)

ax.yaxis.grid(True, linewidth=0.5, color="#CCCCCC", zorder=0)
ax.set_axisbelow(True)

# ── Legend ────────────────────────────────────────────────────────────
legend_items = [
    mpatches.Patch(facecolor=c_op_d, label="Operational GHG — displacement allocation"),
    mpatches.Patch(facecolor=c_op_e, label="Operational GHG — energy allocation"),
    mpatches.Patch(facecolor=c_con,  label="Construction GHG (baseline)"),
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
fig.savefig(out_dir / "ghg_scenarios_barchart_v9.svg",
            bbox_inches="tight", format="svg")
fig.savefig(out_dir / "ghg_scenarios_barchart_v9.png",
            dpi=TARGET_DPI, bbox_inches="tight")
print("Done:", out_dir)
plt.close()
