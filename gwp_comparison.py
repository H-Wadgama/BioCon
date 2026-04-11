"""
GWP Parity Plot — Individual case study figures with Spearman rho annotation
=============================================================================
Generates one publication-quality figure per case study, annotated with
Spearman rank correlation. Exports SVG (editable) and PNG.

Dependencies:
    pip install matplotlib numpy scipy

Usage:
    python gwp_parity_plot_individual.py

Figure sizing:
    Target display: 550 x 685 px per panel.
    At 300 DPI: FIG_SIZE = (550/300, 685/300) = (1.833", 2.283").
    Three panels side by side = 1650 px total width.

Reported statistic:
    Spearman rho -- rank-order agreement between methods, robust to the
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
        "label":    "Dutta et al. (2015) — in-situ pyrolysis",
        "filename": "gwp_parity_plot_dutta_2015_insitu",
        "color":    "#1D9E75",
        "edge":     "#0F6E56",
        "marker":   "o",
        "process": [
            256353.2719, 2445458.499, 988094.1595, 256353.2719, 123596.7856,
            115687.5215, 40869.13462, 18610.24217, 56028.43916, 3522.832894,
            4238.347001, 3732.735945, 25476.3181,  4311.644914, 4654.523111,
            2384.229888, 3732.735945, 25476.3181,  446.2550939, 5419.31291,
            5419.31291,  5419.31291,  4786.19608,  4639.960763, 3888.028623,
            3888.028623, 3009.50318,
        ],
        "eio": [
            201000, 2700000, 464000, 238000, 412000,
            426000, 177000,  110000, 124000, 18900,
            22100,  18400,   282000, 14600,  50000,
            12600,  5330,    46500,  3260,   18800,
            26300,  9690,    7650,   9150,   9520,
            8950,   7220,
        ],
    },
    {
        "label":    "Humbird et al. (2011)",
        "filename": "gwp_parity_plot_humbird_2011",
        "color":    "#185FA5",
        "edge":     "#0C447C",
        "marker":   "s",
        # n=22. Updated process-based values. Pretreatment reactor (vessel 1
        # from original report) excluded on system boundary grounds — documented
        # in manuscript supplementary.
        "process": [
            5308.012206, 40823.97084, 8281.954677, 118437.3078, 52621.36961,
            124062.1625, 368512.1093, 2612933.555, 96869.22568, 25188.43692,
            40703.1218, 224514.5405, 6134362.624, 499.729704, 499.729704,
            10729.76577, 80614.1424, 351751.8131, 96869.22568, 579.0807123,
            2473.506112, 15447.54352,
        ],
        "eio": [
            3651.550301, 7759.815211, 6979.413871, 239167.6617, 95011.80489,
            106294.0424, 198716.3534, 1734729.483, 127633.5342, 47016.03919,
            79790.29558, 1451707.686, 4418051.311, 32891.25159, 50863.44813,
            68748.54825, 153550.1384, 514741.1976, 1572360.506, 80264.77612,
            100330.7535, 166462.0757,
        ],
    },
    {
        "label":    "Dutta et al. (2015) — ex-situ pyrolysis",
        "filename": "gwp_parity_plot_dutta_2015_exsitu",
        "color":    "#D85A30",
        "edge":     "#993C1D",
        "marker":   "^",
        "process": [
            123617.5956, 115706.9757, 40875.96472, 18613.18037,
            256396.0844, 1857198.478, 988261.2889, 256396.0844, 56037.8527,
            3523.411067, 4238.940599, 3733.181675, 25480.37807, 4312.40606,
            4655.309256, 2384.709129, 3733.181675, 25480.37807, 446.4758316,
            5420.208626, 5420.208626, 5420.208626, 4786.912015,
            4640.730477, 3888.630822, 3888.630822, 3009.936554,
        ],
        "eio": [
            440097.4067, 421959.3066, 181041.2737, 178388.3681,
            207835.037,  1951463.354, 800119.4335, 237377.3271, 118266.7252,
            22358.26068, 26246.46794, 17948.8012,  229202.8796, 12771.6511,
            31383.97022, 22956.08761, 8308.161748, 44350.75079, 3543.815414,
            18971.87043, 25590.7241,  10063.93823, 8326.042138,
            9235.609766, 9791.067946, 9145.819116, 7791.57398,
        ],
    },
    # -- Add further case studies here -----------------------------------------
    # {
    #     "label":    "Case study 4",
    #     "filename": "gwp_parity_plot_case4",
    #     "color":    "#7F77DD",
    #     "edge":     "#534AB7",
    #     "marker":   "D",
    #     "process":  [...],
    #     "eio":      [...],
    # },
]

# ==============================================================================
# 2. OUTPUT SETTINGS
# ==============================================================================
PNG_DPI  = 300
# Target display: 550 x 685 px per panel.
# At 300 DPI: 550/300 = 1.833" wide, 685/300 = 2.283" tall.
FIG_SIZE = (550 / 300, 685 / 300)   # (1.833, 2.283) inches

# ==============================================================================
# 3. STYLE SETTINGS
# Line weights and marker size scaled up to remain visually substantial
# at the 550x685 px display target.
# ==============================================================================
FONT_FAMILY      = ["Arial"]
AXIS_LABEL_FS    = 6.5    # axis label font size (pt)
TICK_FS          = 6.0    # tick label font size (pt)
LEGEND_FS        = 5.5    # legend font size (pt)
ANNOT_FS         = 5.5    # stats annotation font size (pt)
POINT_SIZE       = 9     # scatter marker area — doubled from previous 7
POINT_ALPHA      = 0.80
PARITY_COLOR     = "#555555"
PARITY_LINESTYLE = (0, (6, 3))   # dashed 1:1 line
RATIO_LINESTYLE  = (0, (5, 3))   # reserved if ratio line needed later


# ==============================================================================
# 4. STATISTICS
# Only Spearman rho is computed and annotated on each figure.
# ==============================================================================
def compute_stats(process, eio):
    """
    Returns Spearman rank correlation and aggregate ratio.

    Parameters
    ----------
    process : array-like  -- process-based GWP values (reference method)
    eio     : array-like  -- EIO-LCA GWP values (method under evaluation)
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
        "axes.linewidth":    2,
        "xtick.major.width": 2,
        "ytick.major.width": 2,
        "xtick.minor.width": 1.5,
        "ytick.minor.width": 1.5,
        "xtick.major.size":  6.0,
        "ytick.major.size":  6.0,
        "xtick.minor.size":  3,
        "ytick.minor.size":  3,
        "xtick.direction":   "in",
        "ytick.direction":   "in",
    })
    plt.rcParams['svg.fonttype'] = 'none'

    p = np.array(cs["process"], dtype=float)
    e = np.array(cs["eio"],     dtype=float)

    fig, ax = plt.subplots(figsize=FIG_SIZE)

    # -- axis limits: auto-fit with 0.3 log-decade padding --------------------
    combined  = np.concatenate([p, e])
    ax_min    = 10 ** (np.floor(np.log10(combined.min())) - 0.01)
    ax_max    = 10 ** (np.ceil( np.log10(combined.max())) + 0.01)
    ax_range  = [ax_min, ax_max]

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(ax_range)
    ax.set_ylim(ax_range)

    # -- grid lines -----------------------------------------------------------
    ax.grid(True, which="major", color="#dedede", linewidth=1, zorder=0)
    ax.grid(True, which="minor", color="#dedede", linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)

    # -- factor-of-2 shading band (EEIO/process between 0.5x and 2.0x) ------
    ax.fill_between(ax_range,
                    [v * 0.5 for v in ax_range],
                    [v * 2.0 for v in ax_range],
                    color=cs["color"], alpha=0.10, zorder=0,
                    label="Within 2\u00d7 of 1:1")

    # -- 1:1 parity line: dashed ----------------------------------------------
    ax.plot(ax_range, ax_range,
            color=PARITY_COLOR, linewidth=1.0,
            linestyle=PARITY_LINESTYLE,
            zorder=1, label="1:1 line")

    # -- scatter points -------------------------------------------------------
    ax.scatter(
        p, e,
        s=POINT_SIZE, color=cs["color"], marker=cs["marker"],
        alpha=POINT_ALPHA, edgecolors=cs["edge"], linewidths=0.5,
        zorder=3,
    )

    # -- axis labels ----------------------------------------------------------
    ax.set_xlabel(r"Process-based GWP (kg CO$_2$ eq.)",
                  fontsize=AXIS_LABEL_FS, labelpad=4)
    ax.set_ylabel(r"EEIO GWP (kg CO$_2$ eq.)",
                  fontsize=AXIS_LABEL_FS, labelpad=4)

    # -- tick format: 10^2, 10^3, etc. ----------------------------------------
    ax.xaxis.set_major_formatter(ticker.LogFormatterMathtext())
    ax.yaxis.set_major_formatter(ticker.LogFormatterMathtext())
    # Minor locators forced with numticks and NullFormatter — required to
    # prevent LogFormatterMathtext from suppressing x-axis minor ticks.
    ax.xaxis.set_minor_locator(ticker.LogLocator(base=10, subs=np.arange(2, 10), numticks=100))
    ax.yaxis.set_minor_locator(ticker.LogLocator(base=10, subs=np.arange(2, 10), numticks=100))
    ax.xaxis.set_minor_formatter(ticker.NullFormatter())
    ax.yaxis.set_minor_formatter(ticker.NullFormatter())
    ax.tick_params(which="major", direction="in", labelsize=TICK_FS, pad=3.5,
                   length=4.0, width=0.7)
    ax.tick_params(which="minor", direction="in", length=2.5, width=0.5,
                   left=True, bottom=True, labelbottom=False, labelleft=False)

    # -- legend ---------------------------------------------------------------
    legend = ax.legend(fontsize=LEGEND_FS, frameon=True, framealpha=0.9,
                       edgecolor="#cccccc", loc="upper left",
                       handlelength=2.0, borderpad=0.4, labelspacing=0.25)
    legend.get_frame().set_linewidth(0.4)

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
        bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="#cccccc", lw=0.4),
    )

    # -- title ----------------------------------------------------------------
    ax.set_title(cs["label"], fontsize=6.5, fontweight="normal",
                 pad=4, color="#333333")

    plt.tight_layout(pad=0.7)

    # -- export ---------------------------------------------------------------
    svg_path = cs["filename"] + ".svg"
    #png_path = cs["filename"] + ".png"

    fig.savefig(svg_path, format="svg", bbox_inches="tight")
    print(f"  Saved: {svg_path}")

    #fig.savefig(png_path, format="png", dpi=PNG_DPI, bbox_inches="tight")
    #print(f"  Saved: {png_path}  ({PNG_DPI} DPI)")

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
