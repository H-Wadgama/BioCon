import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

font_pref = ["Arial", "Liberation Sans", "DejaVu Sans"]
available = [f.name for f in matplotlib.font_manager.fontManager.ttflist]
chosen = next((f for f in font_pref if f in available), "DejaVu Sans")
print(f"Font: {chosen}")

plt.rcParams.update({
    "font.family": chosen,
    "font.size": 7,
    "mathtext.fontset": "custom",
    "mathtext.rm": chosen,
    "mathtext.it": chosen,
    "mathtext.bf": chosen,
})

oi_colors = [
    "#E69F00", "#56B4E9", "#009E73", "#F0E442",
    "#0072B2", "#D55E00", "#CC79A7",
]

categories = [
    "Equipment manufacturing", "Equipment installation",
    "Miscellaneous", "Site development", "Additional piping",
    "Field emissions", "Warehouse development",
]

insitu_kg     = [4.01e7, 4.85e7, 9.33e6, 4.55e6, 4.55e6, 2.85e6, 1.97e6]
exsitu_kg     = [4.01e7, 5.43e7, 1.01e7, 5.56e6, 5.56e6, 3.08e6, 2.41e6]
cellulosic_kg = [6.95e7, 2.66e7, 8.01e6, 3.23e6, 1.61e6, 2.45e6, 1.56e6]

all_data = [insitu_kg, exsitu_kg, cellulosic_kg]
titles   = ["In-situ pyrolysis", "Ex-situ pyrolysis", "Cellulosic ethanol"]

fig_w_mm, fig_h_mm = 170, 115
fig, axes = plt.subplots(1, 3, figsize=(fig_w_mm / 25.4, fig_h_mm / 25.4))

def draw_pie(ax, vals, title):
    total_kg = sum(vals)
    total_kt = total_kg / 1e6
    fracs    = [v / total_kg for v in vals]

    wedges, _ = ax.pie(
        vals, colors=oi_colors, startangle=90, counterclock=False,
        wedgeprops=dict(linewidth=0.6, edgecolor="white"),
    )

    label_data = []
    for i, (wedge, frac) in enumerate(zip(wedges, fracs)):
        pct   = frac * 100
        theta = np.deg2rad((wedge.theta1 + wedge.theta2) / 2)
        if pct >= 20:   r_out = 1.13
        elif pct >= 10: r_out = 1.20
        elif pct >= 5:  r_out = 1.28
        else:           r_out = 1.38
        label_data.append(dict(theta=theta, pct=pct, r_out=r_out, r_in=0.78, idx=i))

    small_indices = [d["idx"] for d in label_data if d["pct"] < 5]
    for j, idx in enumerate(small_indices):
        label_data[idx]["r_out"] = 1.35 if j % 2 == 0 else 1.45

    for d in label_data:
        theta, r_in, r_out, pct = d["theta"], d["r_in"], d["r_out"], d["pct"]
        ax.annotate(
            f"{pct:.1f}%",
            xy=(r_in * np.cos(theta), r_in * np.sin(theta)),
            xytext=(r_out * np.cos(theta), r_out * np.sin(theta)),
            fontsize=5.5, ha="center", va="center",
            arrowprops=dict(arrowstyle="-", color="#666666", lw=0.45,
                            shrinkA=0, shrinkB=2),
        )

    ax.set_title(title, fontsize=8, fontweight="bold", pad=5)
    ax.text(0, -1.72,
            r"Total: " + f"{total_kt:.1f}" + r" kt CO$_2$ eq",
            ha="center", va="top", fontsize=7.5,
            color="#222222", fontweight="bold", style="normal")

    ax.set_xlim(-1.65, 1.65)
    ax.set_ylim(-1.95, 1.45)

for ax, title, data in zip(axes, titles, all_data):
    draw_pie(ax, data, title)

handles = [
    mpatches.Patch(facecolor=c, edgecolor="white", linewidth=0.6, label=lbl)
    for c, lbl in zip(oi_colors, categories)
]
fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=7,
           frameon=False, columnspacing=1.0, handlelength=2.4,
           handleheight=0.75, handletextpad=0.5, bbox_to_anchor=(0.5, 0.0))

fig.tight_layout(rect=[0, 0.13, 1, 1])
fig.savefig("ghg_pie_charts.png", dpi=300, bbox_inches="tight")
fig.savefig("ghg_pie_charts.svg", format="svg", bbox_inches="tight")