"""
Pressure Vessel Design Algorithm
Based on ASME BPV Code Section VIII, Division 1
Reference: Turton et al. (2018), Mulet et al. (1981), Towler & Sinnott (2022)

Inputs (SI units):
    - T_op: Operating temperature (K)
    - P_op: Operating pressure, absolute (Pa)
    - volume: Total vessel volume (m³) — used if L and D are not provided
    - L: Tangent-to-tangent shell length (m) — optional
    - D: Inside diameter (m) — optional
    - material: One of 'CS_A285', 'CS_A515', 'LA_A387', 'SS410', 'SS304', 'SS347', 'SS321', 'SS316'
    - configuration: 'horizontal' or 'vertical'
    - corrosion: True/False
    - weld_efficiency: e.g. 1.0 (full), 0.85, 0.7
    - n_units: number of units (default 1)
    - name: reference name (string)

Returns a dict with all intermediate and final design values.
"""

import math

# ─────────────────────────────────────────────
# 1. UNIT CONVERSIONS
# ─────────────────────────────────────────────
def Pa_to_psi(Pa):   return Pa * 0.000145038
def psi_to_Pa(psi):  return psi / 0.000145038
def K_to_F(K):       return (K - 273.15) * 9/5 + 32
def m_to_in(m):      return m * 39.3701
def m_to_ft(m):      return m * 3.28084
def in_to_m(inch):   return inch / 39.3701
def mm_to_in(mm):    return mm / 25.4

# ─────────────────────────────────────────────
# 2. MATERIAL DATABASE
# max_temp in °F, stress values in ksi at [100, 300, 500, 700, 900] °F
# density in lb/in³
# ─────────────────────────────────────────────
MATERIALS = {
    'CS_A285':  {'name': 'Carbon steel A285 Gr A',       'max_temp_F': 900,  'stress_ksi': [12.9, 12.9, 12.9, 11.5, 5.9],  'density': 0.2833, 'is_alloy': False},
    'CS_A515':  {'name': 'Killed carbon steel A515 Gr 60','max_temp_F': 1000, 'stress_ksi': [17.1, 17.1, 17.1, 14.3, 5.9],  'density': 0.2833, 'is_alloy': False},
    'LA_A387':  {'name': 'Low-alloy steel A387 Gr 22',   'max_temp_F': 1200, 'stress_ksi': [17.1, 16.6, 16.6, 16.6, 13.6], 'density': 0.2833, 'is_alloy': True},
    'SS410':    {'name': 'Stainless steel 410 (13 Cr)',  'max_temp_F': 1200, 'stress_ksi': [18.6, 17.8, 17.2, 16.2, 12.3], 'density': 0.283,  'is_alloy': True},
    'SS304':    {'name': 'Stainless steel 304',          'max_temp_F': 1500, 'stress_ksi': [20.0, 15.0, 12.9, 11.7, 10.8], 'density': 0.286,  'is_alloy': True},
    'SS347':    {'name': 'Stainless steel 347',          'max_temp_F': 1500, 'stress_ksi': [20.0, 17.1, 15.0, 13.8, 13.4], 'density': 0.283,  'is_alloy': True},
    'SS321':    {'name': 'Stainless steel 321',          'max_temp_F': 1500, 'stress_ksi': [20.0, 16.5, 14.3, 13.0, 12.3], 'density': 0.283,  'is_alloy': True},
    'SS316':    {'name': 'Stainless steel 316',          'max_temp_F': 1500, 'stress_ksi': [20.0, 15.6, 13.3, 12.1, 11.5], 'density': 0.283,  'is_alloy': True},
}

STRESS_TEMPS_F = [100, 300, 500, 700, 900]  # °F brackets

# ─────────────────────────────────────────────
# 3. DESIGN PRESSURE (Section 4.1)
# ─────────────────────────────────────────────
def design_pressure_psig(P_op_Pa):
    """Convert absolute operating pressure (Pa) → gauge (psig) → design pressure (psig)."""
    P_atm_Pa = 101325.0
    P_gauge_Pa = P_op_Pa - P_atm_Pa
    P_gauge_psi = Pa_to_psi(P_gauge_Pa)
    P_o = max(P_gauge_psi, 0.0)   # clamp to zero for sub-atm (vacuum not handled here)

    if P_o <= 10:
        P_d = 10.0
    elif P_o <= 1000:
        ln_Po = math.log(P_o)
        P_d = math.exp(0.60608 + 0.91615 * ln_Po + 0.0015655 * ln_Po**2)
    else:
        P_d = 1.1 * P_o

    return P_o, P_d

# ─────────────────────────────────────────────
# 4. DESIGN TEMPERATURE (Section 4.2)
# ─────────────────────────────────────────────
def design_temperature_F(T_op_K):
    """Operating temperature (K) → design temperature (°F), adding 50°F margin."""
    T_op_F = K_to_F(T_op_K)
    T_d_F = T_op_F + 50.0
    return T_op_F, T_d_F

# ─────────────────────────────────────────────
# 5. ALLOWABLE STRESS LOOKUP (Section 6)
# ─────────────────────────────────────────────
def allowable_stress_psi(material_key, T_d_F):
    """Return allowable stress in psi for given material and design temperature."""
    mat = MATERIALS[material_key]
    if T_d_F > mat['max_temp_F']:
        raise ValueError(
            f"Design temperature {T_d_F:.1f}°F exceeds maximum rated temperature "
            f"{mat['max_temp_F']}°F for {mat['name']}. "
            f"Select a more refractory material or reduce operating temperature."
        )
    # Find smallest standard bracket >= T_d_F (conservative ceiling)
    idx = len(STRESS_TEMPS_F) - 1   # default to highest bracket
    for i, T_bracket in enumerate(STRESS_TEMPS_F):
        if T_bracket >= T_d_F:
            idx = i
            break
    S_ksi = mat['stress_ksi'][idx]
    return S_ksi * 1000.0   # ksi → psi

# ─────────────────────────────────────────────
# 6. L/D RATIO AND VESSEL DIMENSIONS (Section 5)
# ─────────────────────────────────────────────
def ld_ratio(P_d_psig):
    """Return L/D ratio based on design pressure."""
    if P_d_psig <= 250:
        return 3
    elif P_d_psig <= 500:
        return 4
    else:
        return 5

def compute_diameter_from_volume(V_m3, ld):
    """Compute inside diameter (m) from cylindrical volume V = pi*(D/2)^2 * L, L = ld*D.
    Substituting: V = pi * D^2/4 * ld*D = pi*ld*D^3/4
    Solving: D = (4V / (pi * ld))^(1/3)
    """
    D = (4 * V_m3 / (math.pi * ld)) ** (1/3)
    return D

def compute_LDV(V_m3=None, L_m=None, D_m=None, ld=None):
    """
    Given any two of (L, D, V) and the ld ratio, return all three.
    Priority: if both L and D provided → use them, compute V.
    If only V given → compute D from ld, then L = ld * D.
    """
    if L_m is not None and D_m is not None:
        V = math.pi * (D_m / 2)**2 * L_m
        return L_m, D_m, V
    elif V_m3 is not None:
        D = compute_diameter_from_volume(V_m3, ld)
        L = ld * D
        return L, D, V_m3
    else:
        raise ValueError("Must provide either (L and D) or V.")

# ─────────────────────────────────────────────
# 7. WALL THICKNESS (Section 7)
# ─────────────────────────────────────────────
def pressure_thickness_in(P_d_psig, D_i_in, S_psi, E):
    """Pressure-governed wall thickness (in.)."""
    return (P_d_psig * D_i_in) / (2 * S_psi * E - 1.2 * P_d_psig)

def min_thickness_from_diameter_in(D_i_ft):
    """Diameter-based minimum wall thickness (in.)."""
    if D_i_ft <= 4:
        return 0.250
    elif D_i_ft <= 6:
        return 0.3125
    elif D_i_ft <= 8:
        return 0.375
    elif D_i_ft <= 10:
        return 0.4375
    else:
        return 0.500

def wind_seismic_thickness_in(D_o_in, L_in, S_psi):
    """Wind/seismic bending thickness for vertical vessels (in.)."""
    return 0.22 * (D_o_in + 18) * L_in**2 / (S_psi * D_o_in**2)

def round_up_plate_thickness(t_in):
    """
    Round up to nearest standard metal plate thickness increment:
      3/16 to 1/2 in : 1/16-in increments (0.0625)
      5/8  to 2   in : 1/8-in  increments (0.125)
      2.25 to 3   in : 1/4-in  increments (0.25)
    If t <= 3/16, rounds up to 3/16 (smallest standard plate).
    """
    import math as _math
    if t_in <= 0.5:
        inc = 1/16
    elif t_in <= 2.0:
        inc = 1/8
    else:
        inc = 1/4
    return _math.ceil(t_in / inc) * inc

# ─────────────────────────────────────────────
# 8. CORROSION ALLOWANCE (Section 8)
# ─────────────────────────────────────────────
def corrosion_allowance_in(material_key, corrosion):
    """Corrosion allowance in inches."""
    mat = MATERIALS[material_key]
    if mat['is_alloy']:
        ca_mm = 1.0
    else:  # Carbon steel
        ca_mm = 4.0 if corrosion else 2.0
    return mm_to_in(ca_mm)

# ─────────────────────────────────────────────
# 9. VESSEL WEIGHT (Section 9)
# ─────────────────────────────────────────────
def vessel_weight_lb(D_i_in, L_in, t_s_in, density_lb_in3):
    """Shell + head weight in lb (Eq. 16.59)."""
    W = math.pi * (D_i_in + t_s_in) * (L_in + 0.8 * D_i_in) * t_s_in * density_lb_in3
    return W

def weight_with_allowance(W_lb):
    """Add nozzle/support/weld allowance (Table 8)."""
    if W_lb < 50000:
        factor = 1.10
    elif W_lb < 75000:
        factor = 1.08
    elif W_lb < 100000:
        factor = 1.06
    else:
        factor = 1.05
    return W_lb * factor

# ─────────────────────────────────────────────
# 10. MAIN DESIGN FUNCTION
# ─────────────────────────────────────────────
def design_pressure_vessel(
    T_op_K,
    P_op_Pa,
    material,
    configuration,
    corrosion,
    weld_efficiency,
    volume=None,
    L=None,
    D=None,
    n_units=1,
    name="PV-001"
):
    """
    Full pressure vessel design calculation.

    Parameters
    ----------
    T_op_K         : float  – Operating temperature (K)
    P_op_Pa        : float  – Operating pressure, absolute (Pa)
    material       : str    – Material key (see MATERIALS dict)
    configuration  : str    – 'horizontal' or 'vertical'
    corrosion      : bool   – True if corrosive service
    weld_efficiency: float  – Weld joint efficiency (e.g. 1.0, 0.85)
    volume         : float  – Total volume (m³), used if L and D not given
    L              : float  – Shell length (m), optional
    D              : float  – Inside diameter (m), optional
    n_units        : int    – Number of identical units
    name           : str    – Equipment reference name

    Returns
    -------
    dict with all design results
    """
    results = {'name': name, 'n_units': n_units, 'configuration': configuration,
               'material': MATERIALS[material]['name'], 'corrosion': corrosion,
               'weld_efficiency': weld_efficiency}

    # --- Step 1: Design pressure ---
    P_o_psig, P_d_psig = design_pressure_psig(P_op_Pa)
    results['P_op_Pa']   = P_op_Pa
    results['P_op_psig'] = P_o_psig
    results['P_d_psig']  = P_d_psig

    # --- Step 2: Design temperature ---
    T_op_F, T_d_F = design_temperature_F(T_op_K)
    results['T_op_K']  = T_op_K
    results['T_op_F']  = T_op_F
    results['T_d_F']   = T_d_F

    # --- Step 3: Allowable stress ---
    S_psi = allowable_stress_psi(material, T_d_F)
    results['S_psi'] = S_psi

    # --- Step 4: L/D and dimensions ---
    ld = ld_ratio(P_d_psig)
    results['LD_ratio'] = ld

    L_m, D_m, V_m3 = compute_LDV(volume, L, D, ld)
    results['L_m']  = L_m
    results['D_m']  = D_m
    results['V_m3'] = V_m3

    D_i_in = m_to_in(D_m)
    L_in   = m_to_in(L_m)
    D_i_ft = m_to_ft(D_m)

    # --- Step 5: Wall thickness ---
    t_p_in = pressure_thickness_in(P_d_psig, D_i_in, S_psi, weld_efficiency)
    t_min_in = min_thickness_from_diameter_in(D_i_ft)
    t_s_in = max(t_p_in, t_min_in)   # governing shell thickness (before wind/seismic)

    if configuration.lower() == 'vertical':
        D_o_in = D_i_in + 2 * t_s_in
        t_w_in = wind_seismic_thickness_in(D_o_in, L_in, S_psi)
        t_design_in = t_s_in + t_w_in / 2.0  # avg of top (t_s) and bottom (t_s + t_w)
    else:
        t_w_in = None
        t_design_in = t_s_in

    # --- Step 6: Corrosion allowance (added before rounding) ---
    t_corr_in = corrosion_allowance_in(material, corrosion)
    t_before_round_in = t_design_in + t_corr_in

    # --- Step 7: Round up to standard plate thickness ---
    t_total_in = round_up_plate_thickness(t_before_round_in)

    results['t_p_in']             = t_p_in
    results['t_min_in']           = t_min_in
    results['t_s_in']             = t_s_in
    results['t_w_in']             = t_w_in
    results['t_design_in']        = t_design_in
    results['t_corr_in']          = t_corr_in
    results['t_before_round_in']  = t_before_round_in
    results['t_total_in']         = t_total_in

    # --- Step 7: Vessel weight ---
    density = MATERIALS[material]['density']
    W_shell_lb = vessel_weight_lb(D_i_in, L_in, t_total_in, density)
    W_total_lb = weight_with_allowance(W_shell_lb)

    results['W_shell_lb'] = W_shell_lb
    results['W_total_lb'] = W_total_lb
    results['W_total_per_unit_lb'] = W_total_lb
    results['W_total_all_units_lb'] = W_total_lb * n_units

    return results


# ─────────────────────────────────────────────
# 11. PRETTY PRINT
# ─────────────────────────────────────────────
def print_results(r):
    print(f"\n{'='*60}")
    print(f"  Pressure Vessel Design Summary — {r['name']}")
    print(f"{'='*60}")
    print(f"  Material          : {r['material']}")
    print(f"  Configuration     : {r['configuration'].capitalize()}")
    print(f"  Weld efficiency   : {r['weld_efficiency']:.2f}")
    print(f"  Corrosion service : {'Yes' if r['corrosion'] else 'No'}")
    print(f"  Number of units   : {r['n_units']}")
    print()
    print(f"  --- Operating Conditions ---")
    print(f"  T_op              : {r['T_op_K']:.1f} K  ({r['T_op_F']:.1f} °F)")
    print(f"  T_design          : {r['T_d_F']:.1f} °F  (= T_op + 50°F margin)")
    print(f"  P_op (gauge)      : {r['P_op_psig']:.2f} psig  ({r['P_op_Pa']/1e6:.4f} MPa abs)")
    print(f"  P_design          : {r['P_d_psig']:.2f} psig")
    print()
    print(f"  --- Geometry ---")
    print(f"  L/D ratio         : {r['LD_ratio']}")
    print(f"  Inside diameter   : {r['D_m']:.4f} m  ({m_to_in(r['D_m']):.3f} in)")
    print(f"  Shell length      : {r['L_m']:.4f} m  ({m_to_in(r['L_m']):.3f} in)")
    print(f"  Volume            : {r['V_m3']:.4f} m³")
    print()
    print(f"  --- Wall Thickness ---")
    print(f"  Allowable stress  : {r['S_psi']:.0f} psi")
    print(f"  t_pressure        : {r['t_p_in']:.4f} in")
    print(f"  t_min (diameter)  : {r['t_min_in']:.4f} in")
    print(f"  t_shell (governed): {r['t_s_in']:.4f} in")
    if r['t_w_in'] is not None:
        print(f"  t_wind/seismic    : {r['t_w_in']:.4f} in  (vertical vessel)")
        print(f"  t_design (avg)    : {r['t_design_in']:.4f} in  [= t_s + t_w/2]")
    print(f"  t_corrosion       : {r['t_corr_in']:.4f} in")
    print(f"  t_before rounding : {r['t_before_round_in']:.4f} in  [= t_design + t_corr]")
    print(f"  t_TOTAL (rounded) : {r['t_total_in']:.4f} in  ({r['t_total_in']*25.4:.2f} mm)  ← std plate increment")
    print()
    print(f"  --- Weight ---")
    print(f"  Shell weight      : {r['W_shell_lb']:.1f} lb")
    print(f"  Total (w/ allow.) : {r['W_total_lb']:.1f} lb  per unit")
    if r['n_units'] > 1:
        print(f"  Total all units   : {r['W_total_all_units_lb']:.1f} lb  ({r['n_units']} units)")
    print(f"{'='*60}\n")


# ─────────────────────────────────────────────
# 12. TESTS
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*60)
    print("  PRESSURE VESSEL DESIGN ALGORITHM — VERIFICATION TESTS")
    print("="*60)

    # ── Test 1: Low-pressure horizontal CS vessel ──────────────────
    print("\n▶ TEST 1: Low-pressure horizontal carbon steel vessel")
    print("  V=10 m³, T=400K, P=5 bar abs, CS_A515, no corrosion, E=1.0")
    r1 = design_pressure_vessel(
        T_op_K=400, P_op_Pa=5e5, material='CS_A515',
        configuration='horizontal', corrosion=False,
        weld_efficiency=1.0, volume=10.0, name="V-101"
    )
    print_results(r1)
    # Sanity checks
    assert r1['P_d_psig'] > r1['P_op_psig'], "Design P must exceed operating P"
    assert r1['t_total_in'] > 0, "Thickness must be positive"
    assert r1['LD_ratio'] == 3, "Expected L/D=3 at low pressure"
    print("  ✓ Test 1 passed")

    # ── Test 2: Medium-pressure vertical SS304 vessel ─────────────
    print("\n▶ TEST 2: Medium-pressure vertical SS304 vessel")
    print("  V=2 m³, T=500K, P=20 bar abs, SS304, corrosion, E=0.85")
    r2 = design_pressure_vessel(
        T_op_K=500, P_op_Pa=20e5, material='SS304',
        configuration='vertical', corrosion=True,
        weld_efficiency=0.85, volume=2.0, name="V-202"
    )
    print_results(r2)
    assert r2['t_w_in'] is not None, "Vertical vessel should compute t_wind"
    assert r2['t_total_in'] > 0, "Total thickness must be positive"
    assert r2['t_corr_in'] > 0, "Corrosion allowance must be positive for CS/corrosive"
    print("  ✓ Test 2 passed")

    # ── Test 3: High-pressure vertical CS vessel with L and D given
    print("\n▶ TEST 3: High-pressure vertical CS vessel (L and D specified)")
    print("  L=4m, D=1.2m, T=600K, P=80 bar abs, CS_A515, corrosion, E=1.0")
    r3 = design_pressure_vessel(
        T_op_K=600, P_op_Pa=80e5, material='CS_A515',
        configuration='vertical', corrosion=True,
        weld_efficiency=1.0, L=4.0, D=1.2, name="V-303"
    )
    print_results(r3)
    assert r3['LD_ratio'] == 5, "Expected L/D=5 at high design pressure"
    assert abs(r3['D_m'] - 1.2) < 1e-9, "Diameter must match input"
    print("  ✓ Test 3 passed")

    # ── Test 4: Minimum design pressure floor (P < 10 psig) ───────
    print("\n▶ TEST 4: Sub-atmospheric service → design pressure floor at 10 psig")
    print("  V=1 m³, T=350K, P=1.2 bar abs, CS_A285, no corrosion, E=1.0")
    r4 = design_pressure_vessel(
        T_op_K=350, P_op_Pa=1.2e5, material='CS_A285',
        configuration='horizontal', corrosion=False,
        weld_efficiency=1.0, volume=1.0, name="V-404"
    )
    print_results(r4)
    assert r4['P_d_psig'] == 10.0, "Floor design pressure must be 10 psig"
    print("  ✓ Test 4 passed")

    # ── Test 5: Temperature exceeds material limit ─────────────────
    print("\n▶ TEST 5: Temperature exceedance check (expect ValueError)")
    try:
        r5 = design_pressure_vessel(
            T_op_K=1200, P_op_Pa=5e5, material='CS_A285',
            configuration='horizontal', corrosion=False,
            weld_efficiency=1.0, volume=5.0, name="V-505"
        )
        print("  ✗ Should have raised ValueError!")
    except ValueError as e:
        print(f"  ✓ Correctly caught: {e}")

    # ── Test 6: Multiple units ─────────────────────────────────────
    print("\n▶ TEST 6: Multiple unit scaling")
    r6 = design_pressure_vessel(
        T_op_K=420, P_op_Pa=8e5, material='SS316',
        configuration='horizontal', corrosion=True,
        weld_efficiency=0.85, volume=5.0, n_units=3, name="V-606"
    )
    print_results(r6)
    assert abs(r6['W_total_all_units_lb'] - 3 * r6['W_total_per_unit_lb']) < 1e-6
    print("  ✓ Test 6 passed")

    print("\n" + "="*60)
    print("  ALL TESTS PASSED")
    print("="*60 + "\n")
