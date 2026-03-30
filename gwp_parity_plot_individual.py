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
    240 px x 170 px at 96 DPI (Word screen resolution) = 2.5" x 1.77".
    PNG exported at 300 DPI -> 750 x 531 px for print quality.

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
            246871.43, 2406668.17, 970949.23, 246871.43, 119675.39,
            112102.47, 39355.90,   17637.19,  54132.05,  3235.05,
            3851.57,   3445.62,    23584.10,  4016.57,   4332.32,
            2185.02,   3445.62,    23584.10,  372.85,    5063.56,
            5063.56,   5063.56,    4458.98,   4317.80,   3602.95,
            3602.95,   2769.10,
        ],
        "eio": [
            201000.00, 2700000.00, 464000.00, 238000.00, 412000.00,
            426000.00, 177000.00,  110000.00, 124000.00, 18900.00,
            22100.00,  18400.00,   282000.00, 14600.00,  50000.00,
            12600.00,  5330.00,    46500.00,  3260.00,   18800.00,
            26300.00,  9690.00,    7650.00,   9150.00,   9520.00,
            8950.00,   7220.00,
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
    {
        "label":    "Dutta et al. (2015) — ex-situ pyrolysis",
        "filename": "gwp_parity_plot_dutta_2015_exsitu",
        "color":    "#D85A30",
        "edge":     "#993C1D",
        "marker":   "^",
        "process": [
            119695.88, 112121.63, 39362.63, 17640.08,
            246913.59, 1827541.32, 971114.55, 246913.59, 54141.32,
            3235.62, 3852.16, 3446.06, 23588.10, 4017.32, 4333.10,
            2185.49, 3446.06, 23588.10, 373.07,
            5064.44, 5064.44, 5064.44, 4459.69,
            4318.55, 3603.54, 3603.54, 2769.52,
        ],
        "eio": [
            440097.41, 421959.31, 181041.27, 178388.37,
            207835.04, 1951463.35, 800119.43, 237377.33, 118266.73,
            22358.26, 26246.47, 17948.80, 229202.88, 12771.65, 31383.97,
            22956.09, 8308.16, 44350.75, 3543.82,
            18971.87, 25590.72, 10063.94, 8326.04,
            9235.61, 9791.07, 9145.82, 7791.57,
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
# Each panel: 52mm x 65mm for a 170mm double-column artboard (3 panels side by side).
# 3 x 52mm = 156mm, leaving 14mm for gaps and margins.
# At 300 DPI: 614 x 768 px per panel.
FIG_SIZE = (52 / 25.4, 65 / 25.4)   # (2.047, 2.559) inches

# ==============================================================================
# 3. STYLE SETTINGS
# Fonts tuned for 52x65mm panels in a 170mm double-column 3-up artboard.
# ==============================================================================
FONT_FAMILY   = ["Arial", "Helvetica", "Verdana", "Liberation Sans"]
AXIS_LABEL_FS = 7     # axis label font size (pt)
TICK_FS       = 6.5   # tick label font size (pt)
LEGEND_FS     = 6     # legend font size (pt)
ANNOT_FS      = 6     # stats annotation font size (pt)
POINT_SIZE    = 8     # scatter marker area (s= parameter)
POINT_ALPHA   = 0.80
PARITY_COLOR  = "#555555"   # 1:1 line -- dense dots
RATIO_COLOR   = None        # set per case study (matches scatter color)

# Line styles -- visually distinct:
#   1:1 parity    -> densely dotted  (0, (1, 2))
#   Aggregate ratio -> longer dashes (0, (5, 3))
PARITY_LINESTYLE = (0, (1, 2))   # dotted
RATIO_LINESTYLE  = (0, (5, 3))   # dashed


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
        "axes.linewidth":    0.5,
        "xtick.major.width": 0.5,
        "ytick.major.width": 0.5,
        "xtick.major.size":  2.5,
        "ytick.major.size":  2.5,
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

    # -- grid lines -----------------------------------------------------------
    ax.grid(True, which="major", color="#dedede", linewidth=0.4, zorder=0)
    ax.grid(True, which="minor", color="#dedede", linewidth=0.2,
            linestyle=":", zorder=0)
    ax.set_axisbelow(True)

    # -- 1:1 parity line: densely dotted --------------------------------------
    ax.plot(ax_range, ax_range,
            color=PARITY_COLOR, linewidth=0.9,
            linestyle=PARITY_LINESTYLE,
            zorder=1, label="1:1 parity")

    # -- aggregate ratio line: dashed, case study color -----------------------
    ratio_y = [v * s["agg_ratio"] for v in ax_range]
    ax.plot(ax_range, ratio_y,
            color=cs["color"], linewidth=0.9,
            linestyle=RATIO_LINESTYLE,
            alpha=0.75, zorder=1,
            label=f"Aggregate ratio ({s['agg_ratio']:.2f}\u00d7)")

    # -- scatter points -------------------------------------------------------
    ax.scatter(
        p, e,
        s=POINT_SIZE, color=cs["color"], marker=cs["marker"],
        alpha=POINT_ALPHA, edgecolors=cs["edge"], linewidths=0.4,
        zorder=3,
    )

    # -- axis labels with correct CO2 subscript via mathtext ------------------
    ax.set_xlabel(r"Process-based GWP (kg CO$_2$ eq.)",
                  fontsize=AXIS_LABEL_FS, labelpad=3)
    ax.set_ylabel(r"EEIO GWP (kg CO$_2$ eq.)",
                  fontsize=AXIS_LABEL_FS, labelpad=3)

    # -- tick format: 10^2, 10^3, etc. ----------------------------------------
    ax.xaxis.set_major_formatter(ticker.LogFormatterMathtext())
    ax.yaxis.set_major_formatter(ticker.LogFormatterMathtext())
    ax.tick_params(labelsize=TICK_FS, pad=1.5)

    # -- legend ---------------------------------------------------------------
    legend = ax.legend(fontsize=LEGEND_FS, frameon=True, framealpha=0.9,
                       edgecolor="#cccccc", loc="upper left",
                       handlelength=2.2, borderpad=0.5, labelspacing=0.3)
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
        bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#cccccc", lw=0.4),
    )

    # -- title ----------------------------------------------------------------
    ax.set_title(cs["label"], fontsize=7, fontweight="normal",
                 pad=5, color="#333333")

    plt.tight_layout(pad=0.5)

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