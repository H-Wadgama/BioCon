"""
emissions.py — GHG emission factor estimates for pressure vessel fabrication.

─────────────────────────────────────────────────────────────────────────────
SECTION 1 — MATERIAL EMBODIED EMISSIONS
─────────────────────────────────────────────────────────────────────────────
Emission factors (kg CO₂ eq. per kg of material):

  Material category    Average factor    High factor    Source basis
  ─────────────────    ──────────────    ───────────    ────────────
  SS (all grades)           2.31             3.26        Literature average for
    SS304, SS316,                                        austenitic stainless steel
    SS347, SS321, SS410                                  plate/fabrication

  CS (plain grades)         1.41             2.63        Literature average for
    CS_A285, CS_A515                                     carbon steel plate/fabrication

  LA_A387                   3.26              —          High SS factor used as proxy;
    (proxy for CS+Inconel                                A387 is the material model for
     or CS+Incoloy vessels)                              Inconel/Incoloy-clad CS vessels.
                                                         The higher SS factor is applied
                                                         as a conservative approximation.

Usage notes:
  - Vessel shell and internals are treated as the same MOC. The full
    post-internals weight (W_total/unit including internals multiplier)
    is multiplied by the emission factor.
  - The high CS factor (2.63) is not currently used.
  - All SS grades use the same average factor — grade distinctions
    (304 vs 316 vs 347 etc.) are not reflected in the emission factor.
  - n_units scaling is handled by the caller; this module works per-unit.

─────────────────────────────────────────────────────────────────────────────
SECTION 2 — WELDING EMISSIONS
─────────────────────────────────────────────────────────────────────────────
Base emission factors at 25 mm plate thickness, per metre of weld
(SAW = submerged arc welding applied on outside;
 SMAW = shielded metal arc welding applied on inside):

  Process / MOC category    Factor (kg CO₂ eq/m)
  ──────────────────────    ────────────────────
  SAW  — CS                       10.10
  SMAW — CS                       19.40
  SAW  — SS                       23.10
  SMAW — SS                       29.30

Both SAW and SMAW are applied for every weld (outside + inside pass),
so the combined base factor is:
  CS total: 10.10 + 19.40 = 29.50 kg CO₂ eq/m  (at 25 mm)
  SS total: 23.10 + 29.30 = 52.40 kg CO₂ eq/m  (at 25 mm)

Thickness normalisation (regression fit from CS data; applied to both CS and SS):
  ef_weld (kg CO₂ eq/m) = 0.4419 × t_mm × (combined_factor / 11)

  At 25 mm this recovers ~100.4% of the base factor (0.4419×25/11 = 1.0043),
  consistent with the formula being a regression fit rather than an exact identity.

Welding categories by vessel MOC:
  SS316, SS304, SS347, SS321, SS410  → SS welding factors
  CS_A515, CS_A285                   → CS welding factors
  LA_A387                            → CS welding factors
    (low-alloy Cr-Mo steel; welded with CS-compatible SAW/SMAW consumables)

Weld length geometry (per vessel unit):
  Head welds : 2 × π × D_i   (two circumferential welds, one per head)
  Plate weld : L               (one longitudinal seam, tangent-to-tangent length)
  Total      : 2πD_i + L

  D_i is the inside diameter (conservative — slightly larger than mean diameter).
  L is the tangent-to-tangent length.
  Both must be supplied in metres.
"""

# ── Emission factor table ──────────────────────────────────────────────────────
# Keys match MATERIALS dict in pressure_vessel.py

_SS_GRADES = {'SS304', 'SS316', 'SS347', 'SS321', 'SS410'}
_CS_GRADES = {'CS_A285', 'CS_A515'}

EMISSION_FACTORS = {
    # SS grades — average factor
    'SS304':   {'factor_avg': 2.31, 'factor_high': 3.26, 'category': 'SS',     'basis': 'SS average'},
    'SS316':   {'factor_avg': 2.31, 'factor_high': 3.26, 'category': 'SS',     'basis': 'SS average'},
    'SS347':   {'factor_avg': 2.31, 'factor_high': 3.26, 'category': 'SS',     'basis': 'SS average'},
    'SS321':   {'factor_avg': 2.31, 'factor_high': 3.26, 'category': 'SS',     'basis': 'SS average'},
    'SS410':   {'factor_avg': 2.31, 'factor_high': 3.26, 'category': 'SS',     'basis': 'SS average'},
    # CS grades — average factor
    'CS_A285': {'factor_avg': 1.41, 'factor_high': 2.63, 'category': 'CS',     'basis': 'CS average'},
    'CS_A515': {'factor_avg': 1.41, 'factor_high': 2.63, 'category': 'CS',     'basis': 'CS average'},
    # LA_A387 — high SS factor (proxy for CS+Inconel / CS+Incoloy vessels)
    'LA_A387': {'factor_avg': 3.26, 'factor_high': 3.26, 'category': 'SS_HIGH','basis': 'SS high (A387 proxy for CS+Inconel/Incoloy)'},
}


def estimate_ghg(material_key: str, weight_kg: float) -> dict:
    """
    Estimate GHG emissions for a single pressure vessel.

    Parameters
    ----------
    material_key : str
        Material key from pressure_vessel.MATERIALS (e.g. 'SS316', 'CS_A515').
    weight_kg : float
        Total vessel weight in kg, including internals multiplier if applicable.
        This should be W_total/unit (post-internals), NOT W_all_units.

    Returns
    -------
    dict with keys:
        material_key        : str   — as supplied
        emission_factor     : float — kg CO₂ eq. / kg material (factor applied)
        emission_basis      : str   — description of which factor was used
        ghg_kg_co2_eq       : float — kg CO₂ eq. for this vessel unit
        ghg_t_co2_eq        : float — tonnes CO₂ eq. for this vessel unit
    """
    if material_key not in EMISSION_FACTORS:
        raise ValueError(
            f"No emission factor for material key '{material_key}'. "
            f"Valid keys: {sorted(EMISSION_FACTORS.keys())}"
        )

    ef = EMISSION_FACTORS[material_key]
    factor = ef['factor_avg']   # always use average (high CS not currently applied)
    basis  = ef['basis']

    ghg_kg = weight_kg * factor

    return {
        'material_key':     material_key,
        'emission_factor':  factor,
        'emission_basis':   basis,
        'ghg_kg_co2_eq':    round(ghg_kg, 1),
        'ghg_t_co2_eq':     round(ghg_kg / 1000, 3),
    }


def estimate_ghg_from_results(r: dict, weight_kg_override: float = None) -> dict:
    """
    Convenience wrapper: accepts a results dict from design_pressure_vessel()
    and calls estimate_ghg().

    Parameters
    ----------
    r : dict
        Results dict from design_pressure_vessel().
    weight_kg_override : float, optional
        If supplied, use this weight instead of W_total_lb from the results dict.
        Use this when internals have been applied as an external multiplier
        (i.e. the engine version in use does not have internals_pct built in).

    Returns
    -------
    dict — same as estimate_ghg(), plus 'weight_kg_used' for traceability.
    """
    KG_PER_LB = 0.453592
    if weight_kg_override is not None:
        weight_kg = weight_kg_override
    else:
        weight_kg = r['W_total_lb'] * KG_PER_LB

    result = estimate_ghg(r['material_key'], weight_kg)
    result['weight_kg_used'] = round(weight_kg, 1)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — WELDING EMISSIONS
# ══════════════════════════════════════════════════════════════════════════════

import math as _math

# Base emission factors at 25 mm plate thickness (kg CO₂ eq. per metre of weld)
_WELD_FACTORS = {
    'CS': {'SAW': 10.10, 'SMAW': 19.40},   # combined: 29.50
    'SS': {'SAW': 23.10, 'SMAW': 29.30},   # combined: 52.40
}

# Pre-computed combined (SAW + SMAW) totals
_WELD_COMBINED = {
    cat: sum(v.values()) for cat, v in _WELD_FACTORS.items()
}   # {'CS': 29.50, 'SS': 52.40}

# Regression constant from CS thickness-vs-emissions data
# Normalisation formula: ef = K × t_mm × (combined_factor / 11)
# At 25 mm: K×25/11 ≈ 1.004 → recovers base factor to within 0.4%
_WELD_K = 0.4419

# Welding category by material key
# LA_A387 → CS: low-alloy Cr-Mo steel, welded with CS-compatible consumables
_WELD_CATEGORY = {
    'SS316': 'SS', 'SS304': 'SS', 'SS347': 'SS', 'SS321': 'SS', 'SS410': 'SS',
    'CS_A515': 'CS', 'CS_A285': 'CS',
    'LA_A387': 'CS',
}


def weld_emission_factor(material_key: str, t_mm: float) -> dict:
    """
    Compute the thickness-normalised welding emission factor for one metre
    of weld seam.

    Parameters
    ----------
    material_key : str
        Material key from pressure_vessel.MATERIALS.
    t_mm : float
        Plate wall thickness in millimetres (t_total converted from inches).

    Returns
    -------
    dict with keys:
        weld_category           : str   — 'CS' or 'SS'
        SAW_base (kg CO₂/m)     : float — base SAW factor at 25 mm
        SMAW_base (kg CO₂/m)    : float — base SMAW factor at 25 mm
        combined_base (kg CO₂/m): float — SAW + SMAW at 25 mm
        t_mm                    : float — thickness used
        ef_weld (kg CO₂/m)      : float — thickness-normalised factor
    """
    if material_key not in _WELD_CATEGORY:
        raise ValueError(
            f"No welding category for material key '{material_key}'. "
            f"Valid keys: {sorted(_WELD_CATEGORY.keys())}"
        )
    cat      = _WELD_CATEGORY[material_key]
    f        = _WELD_FACTORS[cat]
    combined = _WELD_COMBINED[cat]
    ef_weld  = _WELD_K * t_mm * (combined / 11)

    return {
        'weld_category':    cat,
        'SAW_base':         f['SAW'],
        'SMAW_base':        f['SMAW'],
        'combined_base':    combined,
        't_mm':             round(t_mm, 2),
        'ef_weld':          round(ef_weld, 4),   # kg CO₂ eq / m of weld
    }


def weld_length(D_i_m: float, L_m: float) -> dict:
    """
    Compute total weld seam length for a cylindrical pressure vessel.

    Geometry:
      Head welds : 2 × π × D_i   (circumferential weld, one per head × 2 heads)
      Plate weld : L               (longitudinal seam, tangent-to-tangent length)
      Total      : 2πD_i + L

    Parameters
    ----------
    D_i_m : float  Inside diameter in metres.
    L_m   : float  Tangent-to-tangent length in metres.

    Returns
    -------
    dict with keys:
        D_i_m, L_m, head_weld_m, plate_weld_m, total_weld_m
    """
    head_weld_m  = 2 * _math.pi * D_i_m
    plate_weld_m = L_m
    total_weld_m = head_weld_m + plate_weld_m
    return {
        'D_i_m':          round(D_i_m, 4),
        'L_m':            round(L_m, 4),
        'head_weld_m':    round(head_weld_m, 4),
        'plate_weld_m':   round(plate_weld_m, 4),
        'total_weld_m':   round(total_weld_m, 4),
    }


def estimate_welding_ghg(material_key: str, D_i_m: float, L_m: float,
                         t_total_in: float) -> dict:
    """
    Estimate GHG emissions from welding for a single pressure vessel unit.

    Parameters
    ----------
    material_key : str    Material key from pressure_vessel.MATERIALS.
    D_i_m        : float  Inside diameter in metres.
    L_m          : float  Tangent-to-tangent length in metres.
    t_total_in   : float  Total wall thickness in inches (from engine output).

    Returns
    -------
    dict with keys:
        weld_category           : str
        t_mm                    : float — wall thickness in mm
        ef_weld (kg CO₂/m)      : float — thickness-normalised emission factor
        head_weld_m             : float
        plate_weld_m            : float
        total_weld_m            : float
        weld_ghg_kg_co2_eq      : float — kg CO₂ eq from welding, this unit
        weld_ghg_t_co2_eq       : float — tonnes CO₂ eq from welding, this unit
    """
    t_mm    = t_total_in * 25.4
    wf      = weld_emission_factor(material_key, t_mm)
    wl      = weld_length(D_i_m, L_m)
    ghg_kg  = wf['ef_weld'] * wl['total_weld_m']

    return {
        'weld_category':       wf['weld_category'],
        't_mm':                wf['t_mm'],
        'ef_weld (kg CO₂/m)':  wf['ef_weld'],
        'head_weld_m':         wl['head_weld_m'],
        'plate_weld_m':        wl['plate_weld_m'],
        'total_weld_m':        wl['total_weld_m'],
        'weld_ghg_kg_co2_eq':  round(ghg_kg, 2),
        'weld_ghg_t_co2_eq':   round(ghg_kg / 1000, 6),
    }
