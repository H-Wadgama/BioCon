import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

FONTS = ["Gill Sans MT", "Gill Sans", "Arial", "Liberation Sans"]
plt.rcParams["font.family"]      = "sans-serif"
plt.rcParams["font.sans-serif"]  = FONTS
plt.rcParams["axes.linewidth"]   = 0.6
plt.rcParams["xtick.direction"]  = "in"
plt.rcParams["ytick.direction"]  = "in"
plt.rcParams["mathtext.fontset"] = "custom"
plt.rcParams["mathtext.sf"]      = "Arial"

# ── Data ──────────────────────────────────────────────────────────────
cases   = ["In-situ pyrolysis", "Ex-situ pyrolysis", "Humbird et al."]
op_wo   = np.array([13.10, 12.56, 23.00])   # operational w/o credits (bar height)
op_disp = np.array([ 9.18, 10.15,  5.84])   # net value with displacement (diamond)
op_eng  = np.array([12.11, 12.22, 19.12])   # net value with energy alloc (diamond)
con_lo  = np.array([ 0.56,  0.58,  0.73])   # construction baseline

cr_disp = op_disp - op_wo    # negative credit, displacement
cr_eng  = op_eng  - op_wo    # negative credit, energy

# ── Layout ────────────────────────────────────────────────────────────
n           = len(cases)
bar_w       = 0.34
pair_gap    = 0.08
group_gap   = 0.65
group_pitch = bar_w * 2 + pair_gap + group_gap

gc  = np.arange(n) * group_pitch
x_d = gc - bar_w / 2 - pair_gap / 2
x_e = gc + bar_w / 2 + pair_gap / 2

# ── Colours ───────────────────────────────────────────────────────────
c_op_d = "#185FA5"   # deep blue  — displacement operational
c_cr_d = "#85B7EB"   # light blue — displacement credit (negative)
c_op_e = "#0F6E56"   # deep teal  — energy operational
c_cr_e = "#5DCAA5"   # light teal — energy credit (negative)
c_con  = "#EF9F27"   # amber      — construction baseline

# ── Figure ────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(5.5, 3.8))

for i in range(n):
    # ── Credit segments (negative, below zero) ────────────────────────
    ax.bar(x_d[i], cr_disp[i], bar_w, color=c_cr_d, zorder=3, linewidth=0)
    ax.bar(x_e[i], cr_eng[i],  bar_w, color=c_cr_e, zorder=3, linewidth=0)

    # ── Operational segments: full op_wo height ────────────────────────
    ax.bar(x_d[i], op_wo[i], bar_w, color=c_op_d, zorder=3, linewidth=0)
    ax.bar(x_e[i], op_wo[i], bar_w, color=c_op_e, zorder=3, linewidth=0)

    # ── Construction stacked on top of op_wo ──────────────────────────
    ax.bar(x_d[i], con_lo[i], bar_w, bottom=op_wo[i],
           color=c_con, zorder=3, linewidth=0)
    ax.bar(x_e[i], con_lo[i], bar_w, bottom=op_wo[i],
           color=c_con, zorder=3, linewidth=0)

    # ── Diamond marker at net value ────────────────────────────────────
    ax.plot(x_d[i], op_disp[i], marker="D", markersize=4.5,
            color="white", markeredgecolor="#2C2C2A",
            markeredgewidth=0.8, zorder=5)
    ax.plot(x_e[i], op_eng[i],  marker="D", markersize=4.5,
            color="white", markeredgecolor="#2C2C2A",
            markeredgewidth=0.8, zorder=5)

# ── Zero line ─────────────────────────────────────────────────────────
ax.axhline(0, color="#2C2C2A", linewidth=0.8, zorder=2)

# ── Dashed vertical separators ────────────────────────────────────────
for i in range(1, n):
    ax.axvline((gc[i - 1] + gc[i]) / 2, color="#B4B2A9",
               linewidth=0.7, linestyle=(0, (4, 3)), zorder=1)

# ── Case study labels ─────────────────────────────────────────────────
y_top = (op_wo + con_lo).max()
for i, name in enumerate(cases):
    ax.text(gc[i], y_top + 1.1, name,
            ha="center", va="bottom", fontsize=7.5, color="#2C2C2A")

# ── Sub-bar labels ────────────────────────────────────────────────────
y_sub = cr_disp.min() - 0.8
for i in range(n):
    ax.text(x_d[i], y_sub, "Displacement\nallocation",
            ha="center", va="top", fontsize=5.5,
            color="#5F5E5A", linespacing=1.3, clip_on=False)
    ax.text(x_e[i], y_sub, "Energy\nallocation",
            ha="center", va="top", fontsize=5.5,
            color="#5F5E5A", linespacing=1.3, clip_on=False)

# ── Axes ──────────────────────────────────────────────────────────────
y_min = cr_disp.min() - 4.5
y_max = y_top + 4.0

ax.set_xlim(gc[0]  - group_pitch / 2 + 0.1,
            gc[-1] + group_pitch / 2 - 0.1)
ax.set_ylim(y_min, y_max)
ax.set_xticks([])

yticks = np.arange(int(np.ceil(y_min / 5)) * 5,
                   int(np.floor(y_max / 5)) * 5 + 1, 5)
ax.set_yticks(yticks)
ax.set_yticklabels([str(int(v)) for v in yticks], fontsize=7)
ax.set_ylabel(
    r"GHG intensity (g $\mathregular{CO_2}$ eq $\mathregular{MJ^{-1}}$)",
    fontsize=8)

ax.tick_params(axis="y", which="both", direction="in",
               length=3, width=0.6)
ax.tick_params(axis="x", bottom=False, top=False)

# Full box — all four spines visible
for spine in ax.spines.values():
    spine.set_visible(True)
    spine.set_linewidth(0.6)

ax.yaxis.grid(True, linewidth=0.3, color="#D3D1C7", zorder=0)
ax.set_axisbelow(True)

# ── Legend ────────────────────────────────────────────────────────────
legend_items = [
    mpatches.Patch(facecolor=c_op_d, label="Operational w/o elec. credits — displacement"),
    mpatches.Patch(facecolor=c_cr_d, label="Electricity credit — displacement allocation"),
    mpatches.Patch(facecolor=c_op_e, label="Operational w/o elec. credits — energy"),
    mpatches.Patch(facecolor=c_cr_e, label="Electricity credit — energy allocation"),
    mpatches.Patch(facecolor=c_con,  label="Construction GHG (baseline)"),
    plt.Line2D([0], [0], marker="D", color="none",
               markerfacecolor="white", markeredgecolor="#2C2C2A",
               markeredgewidth=0.8, markersize=4.5,
               label="Net GHG intensity"),
]
ax.legend(
    handles=legend_items,
    fontsize=5.5,
    loc="lower left",
    frameon=True,
    framealpha=0.92,
    edgecolor="#D3D1C7",
    fancybox=False,
    handlelength=1.4,
    handletextpad=0.5,
    borderpad=0.65,
    labelspacing=0.32,
)

fig.tight_layout(pad=0.5)

out_dir = Path(__file__).parent
fig.savefig(out_dir / "ghg_scenarios_barchart_v6.png", dpi=300, bbox_inches="tight")
fig.savefig(out_dir / "ghg_scenarios_barchart_v6.pdf",           bbox_inches="tight")
print("Done:", out_dir)
plt.close()
