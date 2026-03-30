"""
emissions.py — GHG emission factor estimates for pressure vessel fabrication.

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
