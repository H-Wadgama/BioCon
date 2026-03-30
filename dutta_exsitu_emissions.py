"""
Dutta et al. (2015) — Ex-situ Pyrolysis Case
Construction Share Lifecycle Emissions & Contour Plot
=====================================================
Case study: Ex-situ catalytic fast pyrolysis (Dutta et al. 2015)
  Gasoline yield : 35.7 GGE/US dry ton  @ 10.2 gCO2e/MJ
  Diesel yield   : 38.6 GGE/US dry ton  @ 10.3 gCO2e/MJ
  Feed rate      : 2,205 dry ton/day
  Base OF        : 0.9
  Base lifetime  : 30 years
  Construction   : 121,062,653,974.03 gCO2e

Calculation chain (per stream, then summed):
  1. Annual GGE  = feed_rate × gge_per_dry_ton × days_per_year × OF
  2. Annual BTU  = GGE/yr × btu_per_gge
  3. Annual MJ   = BTU/yr × mj_per_btu
  4. Annual gCO2e = MJ/yr × ef_g_per_mj
  5. Lifetime gCO2e = annual × lifetime_years
  6. Construction share = construction / (construction + lifetime_op) × 100
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd

# ── Fixed parameters ──────────────────────────────────────────────────────────
CONSTRUCTION_G             = 121_062_653_974.03   # gCO2e
FEED_RATE_DRY_TON_PER_DAY = 2205.0
DAYS_PER_YEAR              = 365.0
BTU_PER_GGE                = 116_090.0
MJ_PER_BTU                 = 0.001055056

# ── Fuel stream parameters ────────────────────────────────────────────────────
GGE_PER_DRY_TON_GAS  = 35.7    # GGE/US dry ton
EF_GAS_G_PER_MJ      = 10.2    # gCO2e/MJ
GGE_PER_DRY_TON_DIE  = 38.6    # GGE/US dry ton
EF_DIE_G_PER_MJ      = 10.3    # gCO2e/MJ


# ── Core calculator ───────────────────────────────────────────────────────────

def calc_exsitu(operating_factor: float, lifetime_years: float = 30.0) -> dict:
    """
    Calculate construction share for a given operating factor and lifetime.
    Both gasoline and diesel streams calculated independently then summed.
    """
    def _stream(gge_per_dry_ton, ef):
        gge_yr = FEED_RATE_DRY_TON_PER_DAY * gge_per_dry_ton * DAYS_PER_YEAR * operating_factor
        btu_yr = gge_yr  * BTU_PER_GGE
        mj_yr  = btu_yr  * MJ_PER_BTU
        ann_g  = mj_yr   * ef
        return gge_yr, btu_yr, mj_yr, ann_g

    gge_yr_gas, btu_yr_gas, mj_yr_gas, ann_g_gas = _stream(GGE_PER_DRY_TON_GAS, EF_GAS_G_PER_MJ)
    gge_yr_die, btu_yr_die, mj_yr_die, ann_g_die = _stream(GGE_PER_DRY_TON_DIE, EF_DIE_G_PER_MJ)

    ann_g_total   = ann_g_gas + ann_g_die
    lifetime_g    = ann_g_total * lifetime_years
    total_g       = CONSTRUCTION_G + lifetime_g
    share_pct     = (CONSTRUCTION_G / total_g) * 100.0

    return {
        "operating_factor":      operating_factor,
        "lifetime_years":        lifetime_years,
        # gasoline
        "gge_yr_gas":            gge_yr_gas,
        "mj_yr_gas":             mj_yr_gas,
        "ann_g_gas":             ann_g_gas,
        # diesel
        "gge_yr_die":            gge_yr_die,
        "mj_yr_die":             mj_yr_die,
        "ann_g_die":             ann_g_die,
        # combined
        "ann_g_total":           ann_g_total,
        "lifetime_g":            lifetime_g,
        "construction_g":        CONSTRUCTION_G,
        "total_g":               total_g,
        "share_pct":             share_pct,
    }


# ── Base case verification ────────────────────────────────────────────────────

def print_base_case():
    r = calc_exsitu(0.9, 30.0)
    sep = "─" * 65
    print(sep)
    print("  DUTTA ET AL. (2015) EX-SITU — BASE CASE (OF=0.9, LT=30 yr)")
    print(sep)
    print(f"\n  INPUTS")
    print(f"    Feed rate              : {FEED_RATE_DRY_TON_PER_DAY:,.0f} dry ton/day")
    print(f"    Operating factor       : 0.9")
    print(f"    Plant lifetime         : 30 years")
    print(f"    BTU per GGE            : {BTU_PER_GGE:,.0f}")
    print(f"    MJ per BTU             : {MJ_PER_BTU}")
    print(f"    Construction emissions : {CONSTRUCTION_G:.5e} gCO2e")
    print(f"\n  ── GASOLINE STREAM ──────────────────────────────────────")
    print(f"    Yield                  : {GGE_PER_DRY_TON_GAS} GGE/dry ton")
    print(f"    Emissions factor       : {EF_GAS_G_PER_MJ} gCO2e/MJ")
    print(f"    Annual GGE             : {r['gge_yr_gas']:,.2f}")
    print(f"    Annual MJ              : {r['mj_yr_gas']:.4e}")
    print(f"    Annual emissions       : {r['ann_g_gas']:.4e} gCO2e/yr")
    print(f"\n  ── DIESEL STREAM ────────────────────────────────────────")
    print(f"    Yield                  : {GGE_PER_DRY_TON_DIE} GGE/dry ton")
    print(f"    Emissions factor       : {EF_DIE_G_PER_MJ} gCO2e/MJ")
    print(f"    Annual GGE             : {r['gge_yr_die']:,.2f}")
    print(f"    Annual MJ              : {r['mj_yr_die']:.4e}")
    print(f"    Annual emissions       : {r['ann_g_die']:.4e} gCO2e/yr")
    print(f"\n  ── COMBINED ─────────────────────────────────────────────")
    print(f"    Annual emissions       : {r['ann_g_total']:.4e} gCO2e/yr")
    print(f"    Lifetime emissions     : {r['lifetime_g']:.4e} gCO2e")
    print(f"    Construction emissions : {CONSTRUCTION_G:.4e} gCO2e")
    print(f"    Total emissions        : {r['total_g']:.4e} gCO2e")
    print(f"\n  CONSTRUCTION SHARE     : {r['share_pct']:.2f}%")
    print(sep)


# ── Contour data generator ────────────────────────────────────────────────────

def generate_contour_data(
    of_range=(0.5, 0.9),
    lt_range=(10, 30),
    of_steps=9,
    lt_steps=5,
):
    of_vals = np.linspace(of_range[0], of_range[1], of_steps)
    lt_vals = np.linspace(lt_range[0], lt_range[1], lt_steps, dtype=float)

    Z_pct = np.zeros((len(lt_vals), len(of_vals)))
    rows  = []

    for i, lt in enumerate(lt_vals):
        for j, of in enumerate(of_vals):
            r = calc_exsitu(of, lt)
            Z_pct[i, j] = r["share_pct"]
            rows.append({
                "Operating Factor":                        round(of, 4),
                "Lifetime (yr)":                           int(lt),
                "Annual Op. Emissions - Gasoline (gCO2e)": f"{r['ann_g_gas']:.4e}",
                "Annual Op. Emissions - Diesel (gCO2e)":   f"{r['ann_g_die']:.4e}",
                "Annual Op. Emissions - Total (gCO2e)":    f"{r['ann_g_total']:.4e}",
                "Lifetime Op. Emissions (gCO2e)":          f"{r['lifetime_g']:.4e}",
                "Construction Emissions (gCO2e)":          f"{CONSTRUCTION_G:.4e}",
                "Total Emissions (gCO2e)":                 f"{r['total_g']:.4e}",
                "Construction Share (%)":                  round(r["share_pct"], 4),
            })

    return of_vals, lt_vals, Z_pct, pd.DataFrame(rows)


# ── Contour plot ──────────────────────────────────────────────────────────────

def plot_contour(of_vals, lt_vals, Z_pct,
                 output_path="dutta_exsitu_construction_share_contour.png"):
    DPI      = 300
    FIG_W_IN = 2.165
    FIG_H_IN = 1.535

    FS_TITLE      = 6.0
    FS_AXLABEL    = 6.5
    FS_TICK       = 6.5
    FS_CLABEL     = 5.5
    FS_CBAR_LABEL = 6.0
    FS_LEGEND     = 6.0

    import matplotlib as mpl
    import matplotlib.font_manager as fm
    for _p in ["/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
               "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]:
        try: fm.fontManager.addfont(_p)
        except Exception: pass
    mpl.rcParams["font.family"] = "sans-serif"
    mpl.rcParams["font.sans-serif"] = ["Arial", "Liberation Sans", "DejaVu Sans"]

    fig, ax = plt.subplots(figsize=(FIG_W_IN, FIG_H_IN))

    OF, LT = np.meshgrid(of_vals, lt_vals)

    levels = np.arange(2, 28, 2)
    cf = ax.contourf(OF, LT, Z_pct, levels=levels, cmap="YlOrRd", extend="neither")
    cs = ax.contour(OF, LT, Z_pct, levels=levels, colors="black",
                    linewidths=0.25, alpha=0.6)
    ax.clabel(cs, fmt="%.0f%%", fontsize=FS_CLABEL, inline=True)

    ax.plot(0.9, 30, marker="*", markersize=3, color="white",
            markeredgecolor="black", markeredgewidth=0.4, zorder=5,
            label="Base case\n(OF=0.9, LT=30 yr)")

    cbar = fig.colorbar(cf, ax=ax, pad=0.03)
    cbar.set_label("Construction share (%)", fontsize=FS_CBAR_LABEL)
    cbar.ax.tick_params(labelsize=FS_TICK, width=0.3, length=1.5)

    ax.set_xlabel("Operating Factor", fontsize=FS_AXLABEL)
    ax.set_ylabel("Biorefinery Lifetime (years)", fontsize=FS_AXLABEL)
    ax.set_title("Ex-situ pyrolysis to biofuels", fontsize=FS_TITLE)
    ax.set_xlim(of_vals[0], of_vals[-1])
    ax.set_ylim(lt_vals[0], lt_vals[-1])
    ax.set_xticks([0.50, 0.60, 0.70, 0.80, 0.90])
    ax.xaxis.set_major_formatter(ticker.FormatStrFormatter("%.2f"))
    ax.tick_params(axis="both", labelsize=FS_TICK, width=0.3, length=1.5)
    ax.legend(fontsize=FS_LEGEND, loc="upper right",
              handlelength=0.8, borderpad=0.4, labelspacing=0.3)
    for spine in ax.spines.values():
        spine.set_linewidth(0.3)

    plt.subplots_adjust(left=0.14, right=0.74, top=0.88, bottom=0.18)
    plt.savefig(output_path, dpi=DPI)
    svg_path = output_path.rsplit(".", 1)[0] + ".svg"
    plt.savefig(svg_path, format="svg")
    plt.close()
    print(f"\n  Plot saved → {output_path}")
    print(f"  Plot saved → {svg_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    print("\n[1] BASE CASE VERIFICATION")
    print_base_case()

    print("\n[2] GENERATING CONTOUR DATA ...")
    of_vals, lt_vals, Z_pct, df = generate_contour_data(
        of_range=(0.50, 0.90),
        lt_range=(10, 30),
        of_steps=9,
        lt_steps=5,
    )

    print("\n[3] VALIDATION TABLE")
    pd.set_option("display.width", 220)
    pd.set_option("display.max_rows", 100)
    print(df.to_string(index=False))

    df.to_csv("dutta_exsitu_contour_data.csv", index=False)
    print("\n  Data saved → dutta_exsitu_contour_data.csv")

    print("\n[4] GENERATING CONTOUR PLOT ...")
    plot_contour(of_vals, lt_vals, Z_pct)
