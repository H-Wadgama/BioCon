"""
Lifecycle CO2 Emissions Calculator — Construction + Operational
================================================================
Calculates and compares:
  - Operational phase emissions (function of operating factor & lifetime)
  - Construction phase emissions (fixed, user-supplied)
  - Construction share (%) = construction / (construction + operational)

Fuel yield is split between gasoline and diesel, each with its own
lifecycle GHG emissions factor (gCO2e/MJ).

Operational calculation chain (per fuel stream, then summed):
  1. Annual GGE   = feed_rate × gge_per_dry_ton × days_per_year × operating_factor
  2. Annual BTU   = GGE/yr × btu_per_gge
  3. Annual MJ    = BTU/yr × mj_per_btu
  4. Annual gCO2e = MJ/yr × emissions_factor_g_per_mj
  → Total annual gCO2e = gasoline + diesel contributions
  5. Lifetime gCO2e = total_annual × lifetime_years

Usage:
  python lifecycle_emissions.py          → prints summary + saves plot & CSV
  from lifecycle_emissions import calculate_emissions, construction_share_pct
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd


# ── Core operational emissions calculator ─────────────────────────────────────

def calculate_emissions(
    # ── Gasoline stream ───────────────────────────────────────────
    gge_per_dry_ton_gasoline:         float = 55.8,
    emissions_factor_g_per_mj_gas:    float = 9.2,

    # ── Diesel stream ─────────────────────────────────────────────
    gge_per_dry_ton_diesel:           float = 19.1,
    emissions_factor_g_per_mj_diesel: float = 9.3,

    # ── Plant operation ───────────────────────────────────────────
    feed_rate_dry_ton_per_day:        float = 2205.0,
    days_per_year:                    float = 365.0,
    operating_factor:                 float = 0.9,
    lifetime_years:                   float = 30.0,

    # ── Unit conversion factors ───────────────────────────────────
    btu_per_gge:                      float = 116_090.0,
    mj_per_btu:                       float = 0.001055056,

    verbose:                          bool  = True,
) -> dict:
    """
    Calculate total lifetime operational CO2e emissions for combined
    gasoline + diesel fuel streams. Each stream is calculated independently
    then summed before applying the lifetime multiplier.
    """

    def _stream(gge_per_dry_ton, ef_g_per_mj):
        """Calculate annual emissions (gCO2e) for one fuel stream."""
        gge_yr = feed_rate_dry_ton_per_day * gge_per_dry_ton * days_per_year * operating_factor
        btu_yr = gge_yr * btu_per_gge
        mj_yr  = btu_yr * mj_per_btu
        ann_g  = mj_yr  * ef_g_per_mj
        return gge_yr, btu_yr, mj_yr, ann_g

    # ── Gasoline ──────────────────────────────────────────────────
    gge_yr_gas, btu_yr_gas, mj_yr_gas, ann_g_gas = _stream(
        gge_per_dry_ton_gasoline, emissions_factor_g_per_mj_gas)

    # ── Diesel ────────────────────────────────────────────────────
    gge_yr_die, btu_yr_die, mj_yr_die, ann_g_die = _stream(
        gge_per_dry_ton_diesel, emissions_factor_g_per_mj_diesel)

    # ── Combined ──────────────────────────────────────────────────
    ann_g_total       = ann_g_gas + ann_g_die
    ann_t_total       = ann_g_total / 1_000_000
    lifetime_g_total  = ann_g_total * lifetime_years
    lifetime_t_total  = ann_t_total * lifetime_years
    lifetime_Mt_total = lifetime_t_total / 1_000_000

    results = {
        # inputs
        "gge_per_dry_ton_gasoline":         gge_per_dry_ton_gasoline,
        "emissions_factor_g_per_mj_gas":    emissions_factor_g_per_mj_gas,
        "gge_per_dry_ton_diesel":           gge_per_dry_ton_diesel,
        "emissions_factor_g_per_mj_diesel": emissions_factor_g_per_mj_diesel,
        "feed_rate_dry_ton_per_day":        feed_rate_dry_ton_per_day,
        "days_per_year":                    days_per_year,
        "operating_factor":                 operating_factor,
        "lifetime_years":                   lifetime_years,
        "btu_per_gge":                      btu_per_gge,
        "mj_per_btu":                       mj_per_btu,
        # gasoline stream intermediates
        "gge_per_year_gasoline":            gge_yr_gas,
        "btu_per_year_gasoline":            btu_yr_gas,
        "mj_per_year_gasoline":             mj_yr_gas,
        "annual_emissions_g_gasoline":      ann_g_gas,
        # diesel stream intermediates
        "gge_per_year_diesel":              gge_yr_die,
        "btu_per_year_diesel":              btu_yr_die,
        "mj_per_year_diesel":              mj_yr_die,
        "annual_emissions_g_diesel":        ann_g_die,
        # combined outputs
        "annual_emissions_g_total":         ann_g_total,
        "annual_emissions_tco2e":           ann_t_total,
        "lifetime_emissions_g":             lifetime_g_total,
        "lifetime_emissions_tco2e":         lifetime_t_total,
        "lifetime_emissions_Mtco2e":        lifetime_Mt_total,
    }

    if verbose:
        _print_summary(results)
    return results


# ── Construction share calculator ─────────────────────────────────────────────

def construction_share_pct(
    construction_emissions_g: float,
    operational_emissions_g:  float,
) -> float:
    """
    % share of construction in total lifecycle emissions.
    construction_share = construction / (construction + operational) × 100
    """
    return (construction_emissions_g / (construction_emissions_g + operational_emissions_g)) * 100.0


# ── Contour data generator ────────────────────────────────────────────────────

def generate_contour_data(
    construction_emissions_g:         float,
    of_range:                         tuple = (0.5, 0.9),
    lt_range:                         tuple = (10, 30),
    of_steps:                         int   = 9,
    lt_steps:                         int   = 5,
    gge_per_dry_ton_gasoline:         float = 55.8,
    emissions_factor_g_per_mj_gas:    float = 9.2,
    gge_per_dry_ton_diesel:           float = 19.1,
    emissions_factor_g_per_mj_diesel: float = 9.3,
    feed_rate_dry_ton_per_day:        float = 2205.0,
    days_per_year:                    float = 365.0,
    btu_per_gge:                      float = 116_090.0,
    mj_per_btu:                       float = 0.001055056,
) -> tuple:
    """
    Returns (of_vals, lt_vals, Z_pct, df_table).
    Z_pct is a 2-D array [lt × of] of construction share (%).
    """
    of_vals = np.linspace(of_range[0], of_range[1], of_steps)
    lt_vals = np.linspace(lt_range[0], lt_range[1], lt_steps, dtype=float)

    Z_pct = np.zeros((len(lt_vals), len(of_vals)))
    rows  = []

    for i, lt in enumerate(lt_vals):
        for j, of in enumerate(of_vals):
            r = calculate_emissions(
                gge_per_dry_ton_gasoline=gge_per_dry_ton_gasoline,
                emissions_factor_g_per_mj_gas=emissions_factor_g_per_mj_gas,
                gge_per_dry_ton_diesel=gge_per_dry_ton_diesel,
                emissions_factor_g_per_mj_diesel=emissions_factor_g_per_mj_diesel,
                feed_rate_dry_ton_per_day=feed_rate_dry_ton_per_day,
                days_per_year=days_per_year,
                operating_factor=of,
                lifetime_years=lt,
                btu_per_gge=btu_per_gge,
                mj_per_btu=mj_per_btu,
                verbose=False,
            )
            op_g  = r["lifetime_emissions_g"]
            share = construction_share_pct(construction_emissions_g, op_g)
            Z_pct[i, j] = share
            rows.append({
                "Operating Factor":                        round(of, 4),
                "Lifetime (yr)":                           int(lt),
                "Annual Op. Emissions - Gasoline (gCO2e)": f"{r['annual_emissions_g_gasoline']:.4e}",
                "Annual Op. Emissions - Diesel (gCO2e)":   f"{r['annual_emissions_g_diesel']:.4e}",
                "Annual Op. Emissions - Total (gCO2e)":    f"{r['annual_emissions_g_total']:.4e}",
                "Lifetime Op. Emissions (gCO2e)":          f"{op_g:.4e}",
                "Construction Emissions (gCO2e)":          f"{construction_emissions_g:.4e}",
                "Total Emissions (gCO2e)":                 f"{construction_emissions_g + op_g:.4e}",
                "Construction Share (%)":                  round(share, 4),
            })

    return of_vals, lt_vals, Z_pct, pd.DataFrame(rows)


# ── Contour plot ──────────────────────────────────────────────────────────────

def plot_contour(
    of_vals, lt_vals, Z_pct,
    construction_emissions_g: float,
    output_path: str = "construction_share_contour.png",
):
    fig, ax = plt.subplots(figsize=(9, 6))

    OF, LT = np.meshgrid(of_vals, lt_vals)

    levels = np.arange(2, 28, 2)
    cf = ax.contourf(OF, LT, Z_pct, levels=levels, cmap="YlOrRd", extend="neither")
    cs = ax.contour(OF, LT, Z_pct, levels=levels, colors="black", linewidths=0.7, alpha=0.6)
    ax.clabel(cs, fmt="%.1f%%", fontsize=8, inline=True)

    ax.plot(0.9, 30, marker="*", markersize=14, color="white",
            markeredgecolor="black", markeredgewidth=0.8, zorder=5,
            label="Base case (OF=0.9, LT=30 yr)")

    cbar = fig.colorbar(cf, ax=ax, pad=0.02)
    cbar.set_label("Construction share of total lifecycle emissions (%)", fontsize=10)

    ax.set_xlabel("Operating Factor", fontsize=11)
    ax.set_ylabel("Biorefinery Lifetime (years)", fontsize=11)
    ax.set_title(
        "Construction Phase Share of Total Lifecycle CO₂e Emissions\n"
        f"Construction = {construction_emissions_g:.4e} gCO₂e  |  "
        f"Gasoline: 55.8 GGE/t @ 9.2 gCO₂e/MJ  |  Diesel: 19.1 GGE/t @ 9.3 gCO₂e/MJ",
        fontsize=9,
    )
    ax.set_xlim(of_vals[0], of_vals[-1])
    ax.set_ylim(lt_vals[0], lt_vals[-1])
    ax.xaxis.set_major_formatter(ticker.FormatStrFormatter("%.2f"))
    ax.legend(fontsize=9, loc="upper right")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n  Plot saved → {output_path}")


# ── Summary printer ───────────────────────────────────────────────────────────

def _print_summary(r: dict) -> None:
    sep = "─" * 65
    print(sep)
    print("  LIFECYCLE OPERATIONAL CO2 EMISSIONS — GASOLINE + DIESEL")
    print(sep)
    print(f"\n  INPUTS")
    print(f"    Feed rate              : {r['feed_rate_dry_ton_per_day']:,.0f} dry ton/day")
    print(f"    Operating factor       : {r['operating_factor']}")
    print(f"    Plant lifetime         : {r['lifetime_years']:.0f} years")
    print(f"    BTU per GGE            : {r['btu_per_gge']:,.0f}")
    print(f"    MJ per BTU             : {r['mj_per_btu']}")
    print(f"\n  ── GASOLINE STREAM ──────────────────────────────────────")
    print(f"    Yield                  : {r['gge_per_dry_ton_gasoline']} GGE/dry ton")
    print(f"    Emissions factor       : {r['emissions_factor_g_per_mj_gas']} gCO2e/MJ")
    print(f"    Annual GGE             : {r['gge_per_year_gasoline']:,.2f}")
    print(f"    Annual MJ              : {r['mj_per_year_gasoline']:.4e}")
    print(f"    Annual emissions       : {r['annual_emissions_g_gasoline']:.4e} gCO2e")
    print(f"\n  ── DIESEL STREAM ────────────────────────────────────────")
    print(f"    Yield                  : {r['gge_per_dry_ton_diesel']} GGE/dry ton")
    print(f"    Emissions factor       : {r['emissions_factor_g_per_mj_diesel']} gCO2e/MJ")
    print(f"    Annual GGE             : {r['gge_per_year_diesel']:,.2f}")
    print(f"    Annual MJ              : {r['mj_per_year_diesel']:.4e}")
    print(f"    Annual emissions       : {r['annual_emissions_g_diesel']:.4e} gCO2e")
    print(f"\n  ── COMBINED ─────────────────────────────────────────────")
    print(f"    Annual emissions       : {r['annual_emissions_g_total']:.4e} gCO2e"
          f"  ({r['annual_emissions_tco2e']:,.1f} tCO2e)")
    print(f"    Lifetime emissions     : {r['lifetime_emissions_g']:.4e} gCO2e"
          f"  ({r['lifetime_emissions_tco2e']:,.0f} tCO2e"
          f" / {r['lifetime_emissions_Mtco2e']:.4f} MtCO2e)")
    print(sep)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    CONSTRUCTION_G = 112_862_307_381.24   # gCO2e — fixed, from LCA

    # ── 1. Base case ──────────────────────────────────────────────
    print("\n[1] BASE CASE OPERATIONAL EMISSIONS (OF=0.9, LT=30 yr)")
    r_base = calculate_emissions(operating_factor=0.9, lifetime_years=30)

    op_g_base  = r_base["lifetime_emissions_g"]
    share_base = construction_share_pct(CONSTRUCTION_G, op_g_base)

    print(f"\n[2] CONSTRUCTION VS OPERATIONAL (base case)")
    print(f"    Construction           : {CONSTRUCTION_G:.4e} gCO2e")
    print(f"    Operational (lifetime) : {op_g_base:.4e} gCO2e")
    print(f"    Total                  : {CONSTRUCTION_G + op_g_base:.4e} gCO2e")
    print(f"    Construction share     : {share_base:.2f}%")
    print(f"    Operational share      : {100 - share_base:.2f}%")

    # ── 2. Contour data ───────────────────────────────────────────
    print("\n[3] GENERATING CONTOUR DATA ...")
    of_vals, lt_vals, Z_pct, df_table = generate_contour_data(
        construction_emissions_g=CONSTRUCTION_G,
        of_range=(0.5, 0.9),
        lt_range=(10, 30),
        of_steps=9,
        lt_steps=5,
    )

    # ── 3. Validation table ───────────────────────────────────────
    print("\n[4] VALIDATION TABLE (all contour data points)")
    pd.set_option("display.max_rows", 200)
    pd.set_option("display.width", 220)
    print(df_table.to_string(index=False))

    # ── 4. Save CSV ───────────────────────────────────────────────
    csv_path = "construction_share_contour_data.csv"
    df_table.to_csv(csv_path, index=False)
    print(f"\n  Data saved → {csv_path}")

    # ── 5. Plot ───────────────────────────────────────────────────
    print("\n[5] GENERATING CONTOUR PLOT ...")
    plot_contour(of_vals, lt_vals, Z_pct,
                 construction_emissions_g=CONSTRUCTION_G,
                 output_path="construction_share_contour.png")
