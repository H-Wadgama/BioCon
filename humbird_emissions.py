"""
Humbird 2011 — Bioethanol Lifecycle Emissions & Construction Share
==================================================================
Based on: Humbird et al. (2011) NREL/TP-5100-47764

Production basis:
  - 61 MM gal/yr ethanol at 96% uptime (operating factor)
  - Varying OF scales production proportionally:
      annual_gal = 61e6 × (OF / 0.96)

Calculation chain:
  1. Annual ethanol production (gal/yr) = base_production × (OF / base_OF)
  2. Annual energy (MMBTU/yr)           = gal/yr × lhv_mmbtu_per_gal
  3. Annual energy (MJ/yr)              = MMBTU/yr × mj_per_mmbtu
  4. Annual emissions (gCO2e/yr)        = MJ/yr × ef_g_per_mj
  5. Lifetime emissions (gCO2e)         = annual × lifetime_years
  6. Construction share (%)             = construction / (construction + lifetime_op)
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd


# ── Fixed parameters ──────────────────────────────────────────────────────────
CONSTRUCTION_G        = 1.13019e+11       # gCO2e
BASE_PRODUCTION_GAL   = 61e6              # gal/yr at base uptime
BASE_OPERATING_FACTOR = 0.96              # uptime corresponding to 61 MM gal/yr
LHV_MMBTU_PER_GAL     = 0.08             # ethanol LHV (MMBTU/gal)
MJ_PER_MMBTU          = 1055.056         # 1 MMBTU = 1055.056 MJ
EF_G_PER_MJ           = 23.0             # bioethanol lifecycle GHG (gCO2e/MJ)
EF_G_PER_MMBTU        = 24_266.38        # same, in gCO2e/MMBTU (cross-check)
LIFETIME_YEARS        = 30.0


def calc_humbird(operating_factor: float, lifetime_years: float = LIFETIME_YEARS) -> dict:
    """
    Calculate construction share for a given operating factor and lifetime.
    Production scales linearly with operating factor from the 96% base case.
    """
    # Scale annual production from base case
    annual_gal    = BASE_PRODUCTION_GAL * (operating_factor / BASE_OPERATING_FACTOR)

    # Energy
    annual_mmbtu  = annual_gal   * LHV_MMBTU_PER_GAL
    annual_mj     = annual_mmbtu * MJ_PER_MMBTU

    # Emissions
    annual_g      = annual_mj    * EF_G_PER_MJ
    lifetime_g    = annual_g     * lifetime_years

    # Construction share
    total_g       = CONSTRUCTION_G + lifetime_g
    share_pct     = (CONSTRUCTION_G / total_g) * 100.0

    return {
        "operating_factor":  operating_factor,
        "lifetime_years":    lifetime_years,
        "annual_gal":        annual_gal,
        "annual_mmbtu":      annual_mmbtu,
        "annual_mj":         annual_mj,
        "annual_g":          annual_g,
        "lifetime_g":        lifetime_g,
        "construction_g":    CONSTRUCTION_G,
        "total_g":           total_g,
        "share_pct":         share_pct,
    }


# ── Base case verification ────────────────────────────────────────────────────
def print_base_case():
    r = calc_humbird(BASE_OPERATING_FACTOR, LIFETIME_YEARS)
    sep = "─" * 65
    print(sep)
    print("  HUMBIRD 2011 — BASE CASE (OF=0.96, LT=30 yr)")
    print(sep)
    print(f"\n  INPUTS")
    print(f"    Base production        : {BASE_PRODUCTION_GAL/1e6:.0f} MM gal/yr  (at OF={BASE_OPERATING_FACTOR})")
    print(f"    Ethanol LHV            : {LHV_MMBTU_PER_GAL} MMBTU/gal")
    print(f"    MJ per MMBTU           : {MJ_PER_MMBTU}")
    print(f"    Emissions factor       : {EF_G_PER_MJ} gCO2e/MJ  ({EF_G_PER_MMBTU:,.2f} gCO2e/MMBTU)")
    print(f"    Construction emissions : {CONSTRUCTION_G:.5e} gCO2e")
    print(f"    Lifetime               : {int(LIFETIME_YEARS)} years")
    print(f"\n  STEP 1 — Annual ethanol production")
    print(f"    = {BASE_PRODUCTION_GAL/1e6:.0f}e6 × ({BASE_OPERATING_FACTOR}/{BASE_OPERATING_FACTOR})")
    print(f"    = {r['annual_gal']/1e6:.4f} MM gal/yr")
    print(f"\n  STEP 2 — Annual energy (MMBTU)")
    print(f"    = {r['annual_gal']/1e6:.4f}e6 × {LHV_MMBTU_PER_GAL}")
    print(f"    = {r['annual_mmbtu']:.4e} MMBTU/yr")
    print(f"\n  STEP 3 — Annual energy (MJ)")
    print(f"    = {r['annual_mmbtu']:.4e} × {MJ_PER_MMBTU}")
    print(f"    = {r['annual_mj']:.4e} MJ/yr")
    print(f"\n  STEP 4 — Annual emissions")
    print(f"    = {r['annual_mj']:.4e} × {EF_G_PER_MJ}")
    print(f"    = {r['annual_g']:.4e} gCO2e/yr")
    print(f"\n  STEP 5 — Lifetime emissions ({int(LIFETIME_YEARS)} yr)")
    print(f"    = {r['annual_g']:.4e} × {int(LIFETIME_YEARS)}")
    print(f"    = {r['lifetime_g']:.4e} gCO2e")
    print(f"\n  STEP 6 — Construction share")
    print(f"    = {CONSTRUCTION_G:.4e} / ({CONSTRUCTION_G:.4e} + {r['lifetime_g']:.4e})")
    print(f"    = {CONSTRUCTION_G:.4e} / {r['total_g']:.4e}")
    print(f"    = {r['share_pct']:.2f}%")
    print(sep)


# ── Contour data ──────────────────────────────────────────────────────────────
def generate_contour_data(
    of_range=(0.5, 0.96),
    lt_range=(10, 30),
    of_steps=10,
    lt_steps=5,
):
    of_vals = np.linspace(of_range[0], of_range[1], of_steps)
    lt_vals = np.linspace(lt_range[0], lt_range[1], lt_steps, dtype=float)

    Z_pct = np.zeros((len(lt_vals), len(of_vals)))
    rows  = []

    for i, lt in enumerate(lt_vals):
        for j, of in enumerate(of_vals):
            r = calc_humbird(of, lt)
            Z_pct[i, j] = r["share_pct"]
            rows.append({
                "Operating Factor":                  round(of, 4),
                "Lifetime (yr)":                     int(lt),
                "Annual Production (MM gal/yr)":     round(r["annual_gal"] / 1e6, 3),
                "Annual Energy (MJ/yr)":             f"{r['annual_mj']:.4e}",
                "Annual Op. Emissions (gCO2e/yr)":   f"{r['annual_g']:.4e}",
                "Lifetime Op. Emissions (gCO2e)":    f"{r['lifetime_g']:.4e}",
                "Construction Emissions (gCO2e)":    f"{r['construction_g']:.4e}",
                "Total Emissions (gCO2e)":           f"{r['total_g']:.4e}",
                "Construction Share (%)":            round(r["share_pct"], 4),
            })

    return of_vals, lt_vals, Z_pct, pd.DataFrame(rows)


# ── Contour plot ──────────────────────────────────────────────────────────────
def plot_contour(of_vals, lt_vals, Z_pct, output_path="humbird_construction_share_contour.png"):
    # ── Figure dimensions: 240 × 170 px at 96 DPI = 2.5" × 1.77"
    #    Export at 300 DPI → 750 × 531 px PNG ─────────────────────
    DPI        = 300
    FIG_W_IN   = 2.165
    FIG_H_IN   = 1.535

    # ── Font sizes scaled to single-column figure ─────────────────
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
    cs = ax.contour(OF, LT, Z_pct, levels=levels, colors="black", linewidths=0.25, alpha=0.6)
    ax.clabel(cs, fmt="%.0f%%", fontsize=FS_CLABEL, inline=True)

    # Mark base case (OF=0.96, LT=30)
    ax.plot(0.96, 30, marker="*", markersize=3, color="white",
            markeredgecolor="black", markeredgewidth=0.4, zorder=5,
            label="Base case\n(OF=0.96, LT=30 yr)")

    cbar = fig.colorbar(cf, ax=ax, pad=0.03)
    cbar.set_label("Construction share (%)", fontsize=FS_CBAR_LABEL)
    cbar.ax.tick_params(labelsize=FS_TICK, width=0.3, length=1.5)

    ax.set_xlabel("Operating Factor", fontsize=FS_AXLABEL)
    ax.set_ylabel("Biorefinery Lifetime (years)", fontsize=FS_AXLABEL)
    ax.set_title("Biochemical conversion to cellulosic ethanol", fontsize=FS_TITLE)
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
        of_range=(0.50, 0.96),
        lt_range=(10, 30),
        of_steps=10,
        lt_steps=5,
    )

    print("\n[3] VALIDATION TABLE")
    pd.set_option("display.width", 220)
    pd.set_option("display.max_rows", 100)
    print(df.to_string(index=False))

    df.to_csv("humbird_contour_data.csv", index=False)
    print("\n  Data saved → humbird_contour_data.csv")

    print("\n[4] GENERATING CONTOUR PLOT ...")
    plot_contour(of_vals, lt_vals, Z_pct)
