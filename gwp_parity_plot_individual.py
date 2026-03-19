"""
GWP Parity Plot — Individual case study figures with Spearman rho annotation
=============================================================================
Generates one publication-quality figure per case study, annotated with
Spearman rank correlation. Exports SVG (editable) and PNG.

Dependencies:
    pip install matplotlib numpy scipy

Usage:
    python gwp_parity_plot_individual.py

Reported statistic:
    Spearman rho — rank-order agreement between methods, robust to the
    multi-order-of-magnitude spread in the data.

    Magnitude-sensitive statistics (mean ratio, GSD, MAPE, Pearson R2) were
    evaluated and rejected: they are dominated by either the smallest vessels
    (small-denominator amplification) or the largest vessels (leverage on the
    log-log regression), and do not cleanly characterise method agreement.

    Within-a-factor-of-2 coverage is reported separately in the manuscript.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from scipy import stats

# ==============================================================================
# 1. DATA
# ==============================================================================
CASE_STUDIES = [
    {
        "label":    "Dutta et al. (2015)",
        "filename": "gwp_parity_plot_dutta_2015",
        "color":    "#1D9E75",
        "edge":     "#0F6E56",
        "marker":   "o",
        "process": [
            247000, 1710000, 688000, 247000, 120000, 112000, 39400, 17600,
            54100,  3240,    3850,   3450,   23600,  4020,   4330,  2190,
            3450,   23600,   373,    5060,   5060,   5060,   4460,  7070,
            5900,   5900,    4540,
        ],
        "eio": [
            201000,  2700000, 464000, 238000, 412000, 426000, 177000, 110000,
            124000,  18900,   22100,  18400,  282000, 14600,  50000,  12600,
            53300,   46500,   3260,   18800,  26300,  9690,   7650,   9150,
            9520,    8950,    7220,
        ],
    },
    {
        "label":    "Humbird et al. (2011)",
        "filename": "gwp_parity_plot_humbird_2011",
        "color":    "#185FA5",
        "edge":     "#0C447C",
        "marker":   "s",
        # Vessel 1 (pretreatment reactor, process=402000, EIO=8640000) excluded:
        # EIO-LCA cost aggregates multiple distinct unit operations (rolling storage
        # bins, pin drum feeders, screw feeders, pressurized heating screws) reported
        # as one line item in Humbird et al. (2011), whereas the process-based value
        # covers only the reactor vessel. Incompatible system boundaries.
        "process": [
            4910,    38700,  7770,   115000, 50700,  120000, 359000,
            2540000, 93900,  24100,  39100,  215000, 6000000, 395,   395,
            10000,   77400,  342000, 93900,  493,    2270,   14700,
        ],
        "eio": [
            3650,    7760,   6980,   239000, 95000,  106000, 199000,
            1730000, 128000, 47000,  79800,  1450000, 4420000, 32900, 50900,
            68700,   154000, 515000, 1570000, 80300, 100000, 166000,
        ],
    },
    # -- Add further case studies here -----------------------------------------
    # {
    #     "label":    "Case study 3",
    #     "filename": "gwp_parity_plot_case3",
    #     "color":    "#D85A30",
    #     "edge":     "#993C1D",
    #     "marker":   "^",
    #     "process":  [...],
    #     "eio":      [...],
    # },
]

# ==============================================================================
# 2. OUTPUT SETTINGS
# ==============================================================================
PNG_DPI  = 300          # use 600 for stricter journal requirements
FIG_SIZE = (5.5, 5.2)   # inches -- standard single-column journal width

# ==============================================================================
# 3. STYLE SETTINGS
# ==============================================================================
FONT_FAMILY   = "Arial"   # swap to "Helvetica" or "Times New Roman" per journal
AXIS_LABEL_FS = 10
TICK_FS       = 8.5
LEGEND_FS     = 8.5
ANNOT_FS      = 7.5
POINT_SIZE    = 30
POINT_ALPHA   = 0.75
PARITY_COLOR  = "#888780"
GRID_COLOR    = "#dedede"


# ==============================================================================
# 4. STATISTICS
# Only Spearman rho is computed and annotated on each figure.
#
# Rationale: magnitude-sensitive statistics (mean ratio, GSD, MAPE, Pearson R2)
# are dominated by either the smallest vessels (small-denominator amplification)
# or the largest vessels (leverage on regression). Spearman rho is robust to
# both because it operates on ranks, making it the only statistic that cleanly
# characterises vessel-level agreement across a multi-order-of-magnitude dataset.
# Within-a-factor-of-2 coverage is reported separately in the manuscript text.
# ==============================================================================
def compute_stats(process, eio):
    """
    Returns Spearman rank correlation and aggregate ratio.

    Parameters
    ----------
    process : array-like  -- process-based GWP values (reference method)
    eio     : array-like  -- EIO-LCA GWP values (method under evaluation)

    Notes
    -----
    Spearman rho is the sole reported statistic. Magnitude-sensitive measures
    (mean ratio, GSD, MAPE, Pearson R2) are dominated by either the smallest
    vessels (small-denominator amplification) or the largest vessels (leverage
    on regression) and are not reported. Within-a-factor-of-2 coverage is
    reported separately in the manuscript text.
    """
    p = np.array(process, dtype=float)
    e = np.array(eio,     dtype=float)

    rho, p_spear = stats.spearmanr(p, e)
    agg_r        = e.sum() / p.sum()

    return {
        "n":         len(p),
        "agg_ratio": agg_r,
        "rho":       rho,
        "p_spear":   p_spear,
    }


# ==============================================================================
# 5. PLOT FUNCTION
# ==============================================================================
def make_parity_plot(cs, s):
    """
    Parameters
    ----------
    cs : dict  -- one entry from CASE_STUDIES
    s  : dict  -- output of compute_stats() for this case study
    """
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

    p = np.array(cs["process"], dtype=float)
    e = np.array(cs["eio"],     dtype=float)

    fig, ax = plt.subplots(figsize=FIG_SIZE)

    # -- axis limits: auto-fit with 0.3 log-decade padding --------------------
    combined  = np.concatenate([p, e])
    ax_min    = 10 ** (np.floor(np.log10(combined.min())) - 0.3)
    ax_max    = 10 ** (np.ceil( np.log10(combined.max())) + 0.3)
    ax_range  = [ax_min, ax_max]

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(ax_range)
    ax.set_ylim(ax_range)

    # -- grid -----------------------------------------------------------------
    ax.grid(True, which="major", color=GRID_COLOR, linewidth=0.5, zorder=0)
    ax.grid(True, which="minor", color=GRID_COLOR, linewidth=0.25,
            linestyle=":", zorder=0)
    ax.set_axisbelow(True)

    # -- 1:1 parity line ------------------------------------------------------
    ax.plot(ax_range, ax_range,
            color=PARITY_COLOR, linewidth=1.2, linestyle=(0, (5, 4)),
            zorder=1, label="1:1 parity")

    # -- aggregate ratio line -------------------------------------------------
    ratio_y = [v * s["agg_ratio"] for v in ax_range]
    ax.plot(ax_range, ratio_y,
            color=cs["color"], linewidth=1.2, linestyle=(0, (7, 4)),
            alpha=0.65, zorder=1,
            label=f"Aggregate ratio ({s['agg_ratio']:.2f}\u00d7)")

    # -- scatter points -------------------------------------------------------
    ax.scatter(
        p, e,
        s=POINT_SIZE, color=cs["color"], marker=cs["marker"],
        alpha=POINT_ALPHA, edgecolors=cs["edge"], linewidths=0.6,
        zorder=3,
    )

    # -- axis labels ----------------------------------------------------------
    ax.set_xlabel("Process-based GWP (kg CO\u2082 eq.)",
                  fontsize=AXIS_LABEL_FS, labelpad=8)
    ax.set_ylabel("EIO-LCA GWP (kg CO\u2082 eq.)",
                  fontsize=AXIS_LABEL_FS, labelpad=8)

    # -- tick format: 10^2, 10^3, etc. ----------------------------------------
    ax.xaxis.set_major_formatter(ticker.LogFormatterMathtext())
    ax.yaxis.set_major_formatter(ticker.LogFormatterMathtext())
    ax.tick_params(labelsize=TICK_FS)

    # -- legend ---------------------------------------------------------------
    legend = ax.legend(fontsize=LEGEND_FS, frameon=True, framealpha=0.9,
                       edgecolor="#cccccc", loc="upper left")
    legend.get_frame().set_linewidth(0.5)

    # -- Spearman rho annotation (upper right) --------------------------------
    def fmt_p(pv):
        return "< 0.0001" if pv < 0.0001 else f"= {pv:.4f}"

    stat_lines = [
        f"$n$ = {s['n']}",
        f"Spearman $\\rho$ = {s['rho']:.3f}  ($p$ {fmt_p(s['p_spear'])})",
    ]
    ax.annotate(
        "\n".join(stat_lines),
        xy=(0.97, 0.97), xycoords="axes fraction",
        ha="right", va="top",
        fontsize=ANNOT_FS, color="#444444",
        bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="#cccccc", lw=0.5),
    )

    # -- title ----------------------------------------------------------------
    ax.set_title(cs["label"], fontsize=10, fontweight="normal", pad=10,
                 color="#333333")

    plt.tight_layout(pad=1.2)

    # -- export ---------------------------------------------------------------
    svg_path = cs["filename"] + ".svg"
    png_path = cs["filename"] + ".png"

    fig.savefig(svg_path, format="svg", bbox_inches="tight")
    print(f"  Saved: {svg_path}")

    fig.savefig(png_path, format="png", dpi=PNG_DPI, bbox_inches="tight")
    print(f"  Saved: {png_path}  ({PNG_DPI} DPI)")

    plt.close(fig)


# ==============================================================================
# 6. RUN
# ==============================================================================
if __name__ == "__main__":
    print("\nGWP parity plots -- per case study")
    print("=" * 45)

    for cs in CASE_STUDIES:
        print(f"\n{cs['label']}")
        s = compute_stats(cs["process"], cs["eio"])
        make_parity_plot(cs, s)

        def fmt_p(pv):
            return "< 0.0001" if pv < 0.0001 else f"= {pv:.4f}"

        print(f"  n               : {s['n']}")
        print(f"  Aggregate ratio : {s['agg_ratio']:.3f}\u00d7")
        print(f"  Spearman \u03c1      : {s['rho']:.3f}  (p {fmt_p(s['p_spear'])})")

    print("\nDone.")
