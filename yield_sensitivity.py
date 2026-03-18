"""
Gasoline Yield Sensitivity — Construction Share Line Plot
=========================================================
Varies total gasoline yield from 75 to 142 gal/ton (GGE/dry ton),
applying only the gasoline lifecycle GHG factor (9.2 gCO2e/MJ).
Plots construction share (%) vs gasoline yield, and prints full
validation table.

Fixed parameters (base case):
  Feed rate        : 2,205 dry ton/day
  Operating factor : 0.9
  Lifetime         : 30 years
  BTU per GGE      : 116,090
  MJ per BTU       : 0.001055056
  EF gasoline      : 9.2 gCO2e/MJ
  Construction     : 112,862,307,381.24 gCO2e
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd

# ── Fixed parameters ──────────────────────────────────────────────────────────
CONSTRUCTION_G             = 112_862_307_381.24   # gCO2e
FEED_RATE_DRY_TON_PER_DAY = 2205.0
DAYS_PER_YEAR              = 365.0
OPERATING_FACTOR           = 0.9
LIFETIME_YEARS             = 30.0
BTU_PER_GGE                = 116_090.0
MJ_PER_BTU                 = 0.001055056
EF_GAS_G_PER_MJ            = 9.2                  # gCO2e/MJ — gasoline only


def calc_construction_share(gge_per_dry_ton: float) -> dict:
    """
    For a given gasoline yield (GGE/dry ton), calculate:
      - Annual MJ from gasoline stream
      - Lifetime operational emissions (gCO2e) — gasoline only
      - Construction share (%)
    """
    # Annual fuel production
    gge_per_year   = FEED_RATE_DRY_TON_PER_DAY * gge_per_dry_ton * DAYS_PER_YEAR * OPERATING_FACTOR

    # Energy content
    btu_per_year   = gge_per_year * BTU_PER_GGE
    mj_per_year    = btu_per_year * MJ_PER_BTU

    # Annual and lifetime emissions — gasoline EF only
    annual_g       = mj_per_year * EF_GAS_G_PER_MJ
    lifetime_g     = annual_g * LIFETIME_YEARS

    # Construction share
    total_g        = CONSTRUCTION_G + lifetime_g
    share_pct      = (CONSTRUCTION_G / total_g) * 100.0

    return {
        "gge_per_dry_ton":   gge_per_dry_ton,
        "gge_per_year":      gge_per_year,
        "mj_per_year":       mj_per_year,
        "annual_g":          annual_g,
        "lifetime_g":        lifetime_g,
        "construction_g":    CONSTRUCTION_G,
        "total_g":           total_g,
        "share_pct":         share_pct,
    }


# ── Sweep yield from 75 to 142 GGE/dry ton ───────────────────────────────────
yield_vals = np.linspace(75, 142, 14)   # ~5 gal/ton steps: 75, 80.2, ..., 142
rows       = []

for y in yield_vals:
    r = calc_construction_share(y)
    rows.append({
        "Gasoline Yield (GGE/dry ton)":         round(y, 2),
        "Annual GGE":                           f"{r['gge_per_year']:,.1f}",
        "Annual MJ":                            f"{r['mj_per_year']:.4e}",
        "Annual Op. Emissions (gCO2e)":         f"{r['annual_g']:.4e}",
        "Lifetime Op. Emissions (gCO2e)":       f"{r['lifetime_g']:.4e}",
        "Construction Emissions (gCO2e)":       f"{r['construction_g']:.4e}",
        "Total Emissions (gCO2e)":              f"{r['total_g']:.4e}",
        "Construction Share (%)":               round(r['share_pct'], 4),
    })

df = pd.DataFrame(rows)

# ── Print validation table ────────────────────────────────────────────────────
print("\nVALIDATION TABLE — Gasoline Yield Sensitivity")
print("─" * 120)
pd.set_option("display.width", 200)
pd.set_option("display.max_rows", 50)
print(df.to_string(index=False))
print("─" * 120)

# ── Save CSV ──────────────────────────────────────────────────────────────────
df.to_csv("yield_sensitivity_data.csv", index=False)
print("\n  Data saved → yield_sensitivity_data.csv")

# ── Line plot ─────────────────────────────────────────────────────────────────
shares = [calc_construction_share(y)["share_pct"] for y in yield_vals]

# Highlight points
y_75  = calc_construction_share(75.0)["share_pct"]
y_142 = calc_construction_share(142.0)["share_pct"]

fig, ax = plt.subplots(figsize=(9, 5.5))

ax.plot(yield_vals, shares, color="#c0392b", linewidth=2.2, marker="o",
        markersize=6, markerfacecolor="white", markeredgecolor="#c0392b",
        markeredgewidth=1.8, zorder=3)

# Annotate endpoints
ax.annotate(f"{y_75:.2f}%",  xy=(75,  y_75),  xytext=(77,  y_75  + 0.3),
            fontsize=9, color="#2c3e50")
ax.annotate(f"{y_142:.2f}%", xy=(142, y_142), xytext=(136, y_142 + 0.3),
            fontsize=9, color="#2c3e50")

# Vertical reference lines at 75 and 142
ax.axvline(75,  color="grey", linewidth=1.0, linestyle="--", alpha=0.6)
ax.axvline(142, color="grey", linewidth=1.0, linestyle="--", alpha=0.6)

ax.set_xlabel("Gasoline Yield (GGE / US dry ton)", fontsize=11)
ax.set_ylabel("Construction Share of Total Lifecycle Emissions (%)", fontsize=11)
ax.set_title(
    "Impact of Gasoline Yield on Construction Phase Emissions Share\n"
    f"(EF = 9.2 gCO₂e/MJ  |  OF = {OPERATING_FACTOR}  |  LT = {int(LIFETIME_YEARS)} yr  |  "
    f"Feed = {int(FEED_RATE_DRY_TON_PER_DAY):,} dry ton/day)",
    fontsize=9.5,
)

ax.set_xlim(72, 145)
ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.1f%%"))
ax.grid(True, linestyle="--", alpha=0.4)
ax.tick_params(axis="both", labelsize=10)

plt.tight_layout()
plt.savefig("yield_sensitivity_plot.png", dpi=150, bbox_inches="tight")
plt.close()
print("  Plot saved  → yield_sensitivity_plot.png")
