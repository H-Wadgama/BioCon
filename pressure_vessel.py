"""
Pressure Vessel Design Algorithm
Based on ASME BPV Code Section VIII, Division 1
Reference: Turton et al. (2018), Mulet et al. (1981), Towler & Sinnott (2022)

Inputs (SI units):
    - T_op_K:            Operating temperature (K)  — used if T_d_F_override is None
    - P_op_Pa:           Operating pressure, absolute (Pa) — used if P_d_psig_override is None
    - T_d_F_override:    Design temperature (°F), directly supplied — skips +50°F step
    - P_d_psig_override: Design pressure (psig), directly supplied — skips S&L correlation
    - volume:            Total vessel volume (m³) — used if L and D are not provided
    - L:                 Tangent-to-tangent shell length (m) — optional
    - D:                 Inside diameter (m) — optional
    - material:          One of 'CS_A285', 'CS_A515', 'LA_A387', 'SS410',
                         'SS304', 'SS347', 'SS321', 'SS316'
    - configuration:     'horizontal' or 'vertical'
    - corrosion:         True/False
    - weld_efficiency:   e.g. 1.0 (full), 0.85, 0.7
    - n_units:           number of units (default 1)
    - name:              reference name (string)

Returns a dict with all intermediate and final design values.
"""

import math

def Pa_to_psi(Pa):   return Pa * 0.000145038
def psi_to_Pa(psi):  return psi / 0.000145038
def K_to_F(K):       return (K - 273.15) * 9/5 + 32
def m_to_in(m):      return m * 39.3701
def m_to_ft(m):      return m * 3.28084
def in_to_m(inch):   return inch / 39.3701
def mm_to_in(mm):    return mm / 25.4

MATERIALS = {
    'CS_A285':  {'name': 'Carbon steel A285 Gr A',         'max_temp_F': 900,  'stress_ksi': [12.9, 12.9, 12.9, 11.5, 5.9],  'density': 0.2833, 'is_alloy': False},
    'CS_A515':  {'name': 'Killed carbon steel A515 Gr 60', 'max_temp_F': 1000, 'stress_ksi': [17.1, 17.1, 17.1, 14.3, 5.9],  'density': 0.2833, 'is_alloy': False},
    'LA_A387':  {'name': 'Low-alloy steel A387 Gr 22',     'max_temp_F': 1200, 'stress_ksi': [17.1, 16.6, 16.6, 16.6, 13.6], 'density': 0.2833, 'is_alloy': True},
    'SS410':    {'name': 'Stainless steel 410 (13 Cr)',    'max_temp_F': 1200, 'stress_ksi': [18.6, 17.8, 17.2, 16.2, 12.3], 'density': 0.283,  'is_alloy': True},
    'SS304':    {'name': 'Stainless steel 304',            'max_temp_F': 1500, 'stress_ksi': [20.0, 15.0, 12.9, 11.7, 10.8], 'density': 0.286,  'is_alloy': True},
    'SS347':    {'name': 'Stainless steel 347',            'max_temp_F': 1500, 'stress_ksi': [20.0, 17.1, 15.0, 13.8, 13.4], 'density': 0.283,  'is_alloy': True},
    'SS321':    {'name': 'Stainless steel 321',            'max_temp_F': 1500, 'stress_ksi': [20.0, 16.5, 14.3, 13.0, 12.3], 'density': 0.283,  'is_alloy': True},
    'SS316':    {'name': 'Stainless steel 316',            'max_temp_F': 1500, 'stress_ksi': [20.0, 15.6, 13.3, 12.1, 11.5], 'density': 0.283,  'is_alloy': True},
}

STRESS_TEMPS_F = [100, 300, 500, 700, 900]


def design_pressure_psig(P_op_Pa):
    P_atm_Pa   = 101325.0
    P_gauge_Pa = P_op_Pa - P_atm_Pa
    P_gauge_psi = Pa_to_psi(P_gauge_Pa)
    P_o = max(P_gauge_psi, 0.0)
    if P_o <= 10:
        P_d = 10.0
    elif P_o <= 1000:
        ln_Po = math.log(P_o)
        P_d = math.exp(0.60608 + 0.91615 * ln_Po + 0.0015655 * ln_Po**2)
    else:
        P_d = 1.1 * P_o
    return P_o, P_d


def design_temperature_F(T_op_K):
    T_op_F = K_to_F(T_op_K)
    T_d_F  = T_op_F + 50.0
    return T_op_F, T_d_F


def allowable_stress_psi(material_key, T_d_F):
    mat = MATERIALS[material_key]
    if T_d_F > mat['max_temp_F']:
        raise ValueError(
            f"Design temperature {T_d_F:.1f}°F exceeds maximum rated temperature "
            f"{mat['max_temp_F']}°F for {mat['name']}. "
            f"Select a more refractory material or reduce the operating temperature."
        )
    # Ceiling bracket: smallest standard bracket >= T_d_F
    idx = len(STRESS_TEMPS_F) - 1
    for i, T_bracket in enumerate(STRESS_TEMPS_F):
        if T_bracket >= T_d_F:
            idx = i
            break
    return mat['stress_ksi'][idx] * 1000.0


def ld_ratio(P_d_psig):
    if P_d_psig <= 250:
        return 3
    elif P_d_psig <= 500:
        return 4
    else:
        return 5


def compute_diameter_from_volume(V_m3, ld):
    # V = pi * ld * D^3 / 4  →  D = (4V / (pi*ld))^(1/3)
    return (4 * V_m3 / (math.pi * ld)) ** (1/3)


def compute_LDV(V_m3=None, L_m=None, D_m=None, ld=None):
    if L_m is not None and D_m is not None:
        V = math.pi * (D_m / 2)**2 * L_m
        return L_m, D_m, V
    elif V_m3 is not None:
        D = compute_diameter_from_volume(V_m3, ld)
        L = ld * D
        return L, D, V_m3
    else:
        raise ValueError("Must provide either (L and D) or V.")


def pressure_thickness_in(P_d_psig, D_i_in, S_psi, E):
    return (P_d_psig * D_i_in) / (2 * S_psi * E - 1.2 * P_d_psig)


def min_thickness_from_diameter_in(D_i_ft):
    if D_i_ft <= 4:    return 0.250
    elif D_i_ft <= 6:  return 0.3125
    elif D_i_ft <= 8:  return 0.375
    elif D_i_ft <= 10: return 0.4375
    else:              return 0.500


def wind_seismic_thickness_in(D_o_in, L_in, S_psi):
    return 0.22 * (D_o_in + 18) * L_in**2 / (S_psi * D_o_in**2)


def round_up_plate_thickness(t_in):
    import math as _math
    if t_in <= 0.5:   inc = 1/16
    elif t_in <= 2.0: inc = 1/8
    else:             inc = 1/4
    return _math.ceil(t_in / inc) * inc


def corrosion_allowance_in(material_key, corrosion):
    mat = MATERIALS[material_key]
    if mat['is_alloy']:
        ca_mm = 1.0
    else:
        ca_mm = 4.0 if corrosion else 2.0
    return mm_to_in(ca_mm)


def vessel_weight_lb(D_i_in, L_in, t_s_in, density_lb_in3):
    return math.pi * (D_i_in + t_s_in) * (L_in + 0.8 * D_i_in) * t_s_in * density_lb_in3


def weight_with_allowance(W_lb):
    if W_lb < 50000:    factor = 1.10
    elif W_lb < 75000:  factor = 1.08
    elif W_lb < 100000: factor = 1.06
    else:               factor = 1.05
    return W_lb * factor


def design_pressure_vessel(
    T_op_K, P_op_Pa, material, configuration, corrosion, weld_efficiency,
    volume=None, L=None, D=None, n_units=1, name="PV-001",
    T_d_F_override=None, P_d_psig_override=None,
):
    """
    T_d_F_override:    If provided, skips the +50°F step and uses this value
                       directly as the design temperature for stress lookup.
                       T_op_K is still recorded in results but not used for
                       the stress bracket.

    P_d_psig_override: If provided, skips the Sandler & Luckiewicz correlation
                       and uses this value directly as the design pressure.
                       P_op_Pa is still recorded in results but not used for
                       the correlation.
    """
    results = {
        'name': name, 'n_units': n_units, 'configuration': configuration,
        'material': MATERIALS[material]['name'], 'corrosion': corrosion,
        'weld_efficiency': weld_efficiency,
        'material_key': material,
    }

    # ── Pressure ─────────────────────────────────────────────────────────────
    if P_d_psig_override is not None:
        # User supplied design pressure directly — record operating too
        P_atm_Pa    = 101325.0
        P_gauge_Pa  = P_op_Pa - P_atm_Pa
        P_o_psig    = max(Pa_to_psi(P_gauge_Pa), 0.0)
        P_d_psig    = P_d_psig_override
        results['direct_P_d'] = True
    else:
        P_o_psig, P_d_psig = design_pressure_psig(P_op_Pa)
        results['direct_P_d'] = False

    results.update({'P_op_Pa': P_op_Pa, 'P_op_psig': P_o_psig, 'P_d_psig': P_d_psig})

    # ── Temperature ──────────────────────────────────────────────────────────
    T_op_F = K_to_F(T_op_K)
    if T_d_F_override is not None:
        T_d_F = T_d_F_override
        results['direct_T_d'] = True
    else:
        T_d_F = T_op_F + 50.0
        results['direct_T_d'] = False

    results.update({'T_op_K': T_op_K, 'T_op_F': T_op_F, 'T_d_F': T_d_F})

    # ── Stress, geometry, thickness, weight (unchanged) ──────────────────────
    S_psi = allowable_stress_psi(material, T_d_F)
    results['S_psi'] = S_psi

    ld = ld_ratio(P_d_psig)
    results['LD_ratio'] = ld

    L_m, D_m, V_m3 = compute_LDV(volume, L, D, ld)
    results.update({'L_m': L_m, 'D_m': D_m, 'V_m3': V_m3})

    D_i_in = m_to_in(D_m)
    L_in   = m_to_in(L_m)
    D_i_ft = m_to_ft(D_m)

    t_p_in   = pressure_thickness_in(P_d_psig, D_i_in, S_psi, weld_efficiency)
    t_min_in = min_thickness_from_diameter_in(D_i_ft)
    t_s_in   = max(t_p_in, t_min_in)

    if configuration.lower() == 'vertical':
        D_o_in      = D_i_in + 2 * t_s_in
        t_w_in      = wind_seismic_thickness_in(D_o_in, L_in, S_psi)
        t_design_in = t_s_in + t_w_in / 2.0
    else:
        t_w_in      = None
        t_design_in = t_s_in

    t_corr_in         = corrosion_allowance_in(material, corrosion)
    t_before_round_in = t_design_in + t_corr_in
    t_total_in        = round_up_plate_thickness(t_before_round_in)

    results.update({
        't_p_in': t_p_in, 't_min_in': t_min_in, 't_s_in': t_s_in,
        't_w_in': t_w_in, 't_design_in': t_design_in,
        't_corr_in': t_corr_in, 't_before_round_in': t_before_round_in,
        't_total_in': t_total_in,
    })

    density    = MATERIALS[material]['density']
    W_shell_lb = vessel_weight_lb(D_i_in, L_in, t_total_in, density)
    W_total_lb = weight_with_allowance(W_shell_lb)

    results.update({
        'W_shell_lb':           W_shell_lb,
        'W_total_lb':           W_total_lb,
        'W_total_per_unit_lb':  W_total_lb,
        'W_total_all_units_lb': W_total_lb * n_units,
    })
    return results
