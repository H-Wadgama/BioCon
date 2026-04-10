"""
Publication-quality Sankey diagram — Construction-phase GHG emissions
Humbird et al. biochemical ethanol biorefinery

EDITABLE SECTIONS:
  Section 1 — DATA      : change values, add/remove categories
  Section 2 — COLORS    : retheme by editing hex codes
  Section 3 — LAYOUT    : adjust sizing, column positions, fonts
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.path import Path
import numpy as np

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  SECTION 1 — DATA  (kg CO₂e)  ← edit values here                          ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# Level 1 → Level 2  (main cost components)
MAIN = {
    "Total equip. manufacturing":   69_548_543.90,
    "Equipment installation":       26_611_347.05,
    "Home office construction":      8_014_474.31,
    "Site development":              3_226_414.92,
    "Field emissions":               2_446_136.28,
    "Additional piping":             1_613_207.46,
    "Warehouse development":         1_559_004.19,
}

# Level 2 → Level 3  (equipment manufacturing breakdown)
EQUIP_SUB = {
    "All other equipment":          26_640_504.02,
    "Heavy metal tanks":            23_850_331.53,
    "HX equipment":                  9_084_911.34,
    "Conveyors":                     3_636_409.01,
    "Turbines":                      2_800_126.17,
    "Cooling & evap. systems":       1_820_864.93,
    "Pressure changing equip.":      1_715_396.88,
}

# Level 3 → Level 4  (further breakdowns — add/remove entries freely)
HX_CHILDREN     = {"Boiler":           8_773_640.30,
                   "All other HX":       311_271.04}
HMETAL_CHILDREN  = {"Pressure vessels": 22_415_812.17,
                   "Storage tanks":      1_434_519.36}
PCHANGE_CHILDREN = {"Compressors":       1_206_907.49,
                   "Pumps":               508_489.38}

# Which Level-3 nodes expand to Level 4
COL3_TO_COL4 = {
    "HX equipment":             HX_CHILDREN,
    "Heavy metal tanks":        HMETAL_CHILDREN,
    "Pressure changing equip.": PCHANGE_CHILDREN,
}

TOTAL = sum(MAIN.values())   # derived automatically

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  SECTION 2 — COLORS  ← edit hex codes to retheme                          ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

COLORS = {
    # Net Total bar
    "Net Total":                    "#2C3E50",

    # ── Main cost components (Level 2) ──────────────────────────────────────
    "Total equip. manufacturing":   "#4678A4",   # steel blue
    "Equipment installation":       "#C87C50",   # warm terracotta
    "Home office construction":     "#5A9472",   # sage green
    "Site development":             "#8A6AAA",   # soft violet
    "Field emissions":              "#B05050",   # muted brick
    "Additional piping":            "#6A8EA6",   # slate blue-grey
    "Warehouse development":        "#9A8A56",   # warm khaki

    # ── Equipment subcategories (Level 3, within blue family) ──────────────
    "All other equipment":          "#9AB8CC",   # pale steel blue (catchall)
    "Heavy metal tanks":            "#285A88",   # dark navy
    "HX equipment":                 "#4E8AAC",   # medium teal-blue
    "Conveyors":                    "#A08860",   # warm tan
    "Turbines":                     "#706898",   # muted indigo
    "Cooling & evap. systems":      "#5A9292",   # teal-green
    "Pressure changing equip.":     "#A88858",   # warm amber

    # ── Sub-subcategories (Level 4) ─────────────────────────────────────────
    "Boiler":                       "#3A6888",   # dark teal-blue  (from HX)
    "All other HX":                 "#7AAEC6",   # light teal-blue (from HX)
    "Pressure vessels":             "#1A4672",   # darkest navy    (from heavy metal)
    "Storage tanks":                "#5888A8",   # medium steel    (from heavy metal)
    "Compressors":                  "#886040",   # dark amber      (from press. chng)
    "Pumps":                        "#B89878",   # light amber     (from press. chng)
}

def C(name): return COLORS.get(name, "#888888")

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  SECTION 3 — LAYOUT  ← adjust sizing and positioning                      ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# Figure dimensions (mm → inches)
W_MM, H_MM = 170, 200
W_IN = W_MM / 25.4   # 6.693"
H_IN = H_MM / 25.4   # 7.874"

# Bar x-positions (left edge of each column bar, in axes fraction 0–1)
X1 = 0.04    # Net Total
X2 = 0.26    # Main cost components
X3 = 0.57    # Equipment subcategories
X4 = 0.79    # Sub-subcategories
BW = 0.044   # bar width

# Vertical margins
PAD_T = 0.91   # top of usable area
PAD_B = 0.04   # bottom of usable area

# Typography
import matplotlib.font_manager as fm
available = [f.name for f in fm.fontManager.ttflist]
FONT = "Liberation Sans" if "Liberation Sans" in available else "DejaVu Sans"
FS_L  = 5.3    # category label
FS_V  = 4.6    # value annotation
FS_H  = 5.0    # column header
BG    = "#F8F7F5"  # background colour

# Label visibility thresholds (fraction of figure height)
TH2   = 0.018   # show 2-line label above this height
TH1   = 0.008   # show 1-line label above this height

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  INTERNAL FUNCTIONS  (no editing needed below this point)                  ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

USABLE = PAD_T - PAD_B
SCALE  = USABLE / TOTAL   # consistent scale: figure-fraction per kg CO₂e

def place_bars(items_dict, y_start, sort_desc=True):
    """
    Position bars proportionally starting from y_start downward.
    Returns {name: {val, y_top, y_bot, mid}}
    """
    items = (sorted(items_dict.items(), key=lambda x: -x[1])
             if sort_desc else list(items_dict.items()))
    nodes, y = {}, y_start
    for name, val in items:
        h = val * SCALE
        nodes[name] = dict(val=val, y_top=y, y_bot=y - h, mid=y - h / 2)
        y -= h
    return nodes


def draw_ribbon(ax, x0r, b0, t0, x1l, b1, t1, color, alpha=0.27):
    """Smooth cubic-Bezier ribbon between two vertical bar segments."""
    mx = (x0r + x1l) / 2
    verts = [
        (x0r, b0),
        (mx,  b0), (mx,  b1), (x1l, b1),
        (x1l, t1),
        (mx,  t1), (mx,  t0), (x0r, t0),
        (x0r, b0),
    ]
    codes = [Path.MOVETO,
             Path.CURVE4, Path.CURVE4, Path.CURVE4,
             Path.LINETO,
             Path.CURVE4, Path.CURVE4, Path.CURVE4,
             Path.CLOSEPOLY]
    ax.add_patch(mpatches.PathPatch(
        Path(verts, codes), fc=color, ec='none', alpha=alpha, zorder=1))


def draw_bar(ax, x, y_bot, y_top, color, w=BW, lw=0.7):
    ax.add_patch(mpatches.FancyBboxPatch(
        (x, y_bot), w, y_top - y_bot,
        boxstyle="square,pad=0",
        fc=color, ec='white', lw=lw, zorder=3))


def fmt(v):
    if   v >= 1e9: return f"{v/1e9:.2f} Gt CO₂e"
    elif v >= 1e6: return f"{v/1e6:.2f} Mt CO₂e"
    elif v >= 1e3: return f"{v/1e3:.1f} kt CO₂e"
    return               f"{v:,.0f} kg CO₂e"


# ── Node positions ────────────────────────────────────────────────────────────

n2 = place_bars(MAIN, PAD_T)
equip_top = n2["Total equip. manufacturing"]["y_top"]
n3 = place_bars(EQUIP_SUB, equip_top)

n4 = {}
for parent, children in COL3_TO_COL4.items():
    n4.update(place_bars(children, n3[parent]["y_top"]))


# ── Canvas ────────────────────────────────────────────────────────────────────

fig, ax = plt.subplots(figsize=(W_IN, H_IN))
ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
fig.patch.set_facecolor(BG); ax.set_facecolor(BG)


# ── Ribbons: Net Total → Main categories ─────────────────────────────────────

src = PAD_T
for name, nd in sorted(n2.items(), key=lambda x: -x[1]['val']):
    h = nd['val'] * SCALE
    draw_ribbon(ax, X1+BW, src-h, src, X2, nd['y_bot'], nd['y_top'],
                C(name), alpha=0.30)
    src -= h


# ── Ribbons: equip mfg → equipment subcategories ─────────────────────────────

src = equip_top
for name, nd in sorted(n3.items(), key=lambda x: -x[1]['val']):
    h = nd['val'] * SCALE
    draw_ribbon(ax, X2+BW, src-h, src, X3, nd['y_bot'], nd['y_top'],
                C(name), alpha=0.28)
    src -= h


# ── Ribbons: equipment subcategories → sub-subcategories ─────────────────────

for parent, children in COL3_TO_COL4.items():
    src = n3[parent]["y_top"]
    for cname, cnd in sorted([(k, n4[k]) for k in children.keys()],
                              key=lambda x: -x[1]['val']):
        h = cnd['val'] * SCALE
        draw_ribbon(ax, X3+BW, src-h, src, X4, cnd['y_bot'], cnd['y_top'],
                    C(cname), alpha=0.30)
        src -= h


# ── Bars ──────────────────────────────────────────────────────────────────────

draw_bar(ax, X1, PAD_B, PAD_T, C("Net Total"))
for name, nd in n2.items(): draw_bar(ax, X2, nd['y_bot'], nd['y_top'], C(name))
for name, nd in n3.items(): draw_bar(ax, X3, nd['y_bot'], nd['y_top'], C(name))
for name, nd in n4.items(): draw_bar(ax, X4, nd['y_bot'], nd['y_top'], C(name))


# ── Labels ────────────────────────────────────────────────────────────────────

kw_name  = dict(fontfamily=FONT, fontsize=FS_L, color='#1A1A1A', va='center')
kw_val   = dict(fontfamily=FONT, fontsize=FS_V, color='#505050',
                va='center', style='italic')

# Net Total
mid = (PAD_T + PAD_B) / 2
ax.text(X1+BW+0.010, mid+0.012, "Net Total",   ha='left', fontweight='bold', **kw_name)
ax.text(X1+BW+0.010, mid-0.012, fmt(TOTAL),    ha='left', **kw_val)

# Col 2 — labels to the LEFT of bars
for name, nd in n2.items():
    h, m = nd['y_top'] - nd['y_bot'], nd['mid']
    if h >= TH2:
        ax.text(X2-0.011, m+0.011, name,            ha='right', **kw_name)
        ax.text(X2-0.011, m-0.011, fmt(nd['val']),  ha='right', **kw_val)
    elif h >= TH1:
        ax.text(X2-0.011, m,       name,            ha='right', fontsize=FS_V,
                fontfamily=FONT, color='#1A1A1A', va='center')

# Col 3 — labels to the RIGHT of bars
for name, nd in n3.items():
    h, m = nd['y_top'] - nd['y_bot'], nd['mid']
    if h >= TH2:
        ax.text(X3+BW+0.010, m+0.011, name,            ha='left', **kw_name)
        ax.text(X3+BW+0.010, m-0.011, fmt(nd['val']),  ha='left', **kw_val)
    elif h >= TH1:
        ax.text(X3+BW+0.010, m,       name,            ha='left', fontsize=FS_V,
                fontfamily=FONT, color='#1A1A1A', va='center')

# Col 4 — labels to the RIGHT of bars
for name, nd in n4.items():
    h, m = nd['y_top'] - nd['y_bot'], nd['mid']
    if h >= TH2:
        ax.text(X4+BW+0.010, m+0.011, name,            ha='left', **kw_name)
        ax.text(X4+BW+0.010, m-0.011, fmt(nd['val']),  ha='left', **kw_val)
    elif h >= TH1:
        ax.text(X4+BW+0.010, m,       name,            ha='left', fontsize=FS_V,
                fontfamily=FONT, color='#1A1A1A', va='center')


# ── Column headers ────────────────────────────────────────────────────────────

HDR_Y = PAD_T + 0.025
for x_bar, label in [
    (X1, "Net\nTotal"),
    (X2, "Cost\nComponents"),
    (X3, "Equip. Mfg.\nSubcategories"),
    (X4, "Sub-\ncategories"),
]:
    cx = x_bar + BW / 2
    ax.text(cx, HDR_Y, label, ha='center', va='bottom',
            fontsize=FS_H, fontfamily=FONT, fontweight='bold',
            color='#2A2A2A', multialignment='center')
    ax.plot([cx - 0.05, cx + 0.05],
            [HDR_Y - 0.007, HDR_Y - 0.007],
            color='#BBBBBB', lw=0.5, zorder=2)

# thin rule
ax.axhline(PAD_T + 0.010, color='#C8C8C8', lw=0.45, xmin=0.01, xmax=0.99)


# ── Title block ───────────────────────────────────────────────────────────────

ax.text(0.50, 0.998,
        "Construction-Phase GHG Emissions — Humbird Biochemical Ethanol Biorefinery",
        ha='center', va='top', fontsize=6.2,
        fontfamily=FONT, fontweight='bold', color='#1A1A2E',
        transform=ax.transAxes)
ax.text(0.50, 0.991,
        "kg CO₂e  ·  EIO-LCA (USEEIO v1.3)  ·  2022 USD  ·"
        "  Flow: Net Total → Cost components → Equipment subcategories → Sub-subcategories",
        ha='center', va='top', fontsize=4.3,
        fontfamily=FONT, color='#777777', style='italic',
        transform=ax.transAxes)

# ── Save ──────────────────────────────────────────────────────────────────────

plt.tight_layout(pad=0.1)
for ext in ("pdf", "png"):
    fig.savefig(f"/home/claude/sankey_publication.{ext}",
                dpi=300, bbox_inches='tight',
                facecolor=fig.get_facecolor())
plt.close()
print(f"Saved. TOTAL = {TOTAL:,.2f} kg CO₂e")
