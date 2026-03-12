"""
Heat Exchanger Weight Estimator
Estimates the weight of a shell-and-tube heat exchanger (tubes + shell).

Methodology:
  - Tube weight: hollow cylinder wall volume × tube material density
  - Shell thickness: ASME formula t = P·R / (S·E - 0.6·P)
  - Shell weight: cylindrical shell volume × shell material density
  - Weld efficiency E = 1.0 (seamless shell, standard for HX)
  - Stress and density drawn from pressure_vessel.py MATERIALS table

References: Turton et al. (2018), ASME BPV Code VIII Div.1
"""

import math
from pressure_vessel import (
    MATERIALS, STRESS_TEMPS_F,
    Pa_to_psi, K_to_F, mm_to_in, m_to_in, m_to_ft,
    allowable_stress_psi, design_temperature_F, design_pressure_psig,
)

# ── BWG lookup table ──────────────────────────────────────────────────────────
# Source: Table 12.4, Heat Exchanger Tube Data
# Key: (tube_OD_in_fraction_str, BWG) → wall thickness (in)
# OD stored as float (in), BWG as int → thickness (in)

BWG_TABLE = {
    # OD = 1/2 in
    (0.500, 12): 0.109,
    (0.500, 14): 0.083,
    (0.500, 16): 0.065,
    (0.500, 18): 0.049,
    (0.500, 20): 0.035,
    # OD = 3/4 in
    (0.750, 10): 0.134,
    (0.750, 11): 0.120,
    (0.750, 12): 0.109,
    (0.750, 13): 0.095,
    (0.750, 14): 0.083,
    (0.750, 15): 0.072,
    (0.750, 16): 0.065,
    (0.750, 17): 0.058,
    (0.750, 18): 0.049,
    # OD = 1 in
    (1.000,  8): 0.165,
    (1.000,  9): 0.148,
    (1.000, 10): 0.134,
    (1.000, 11): 0.120,
    (1.000, 12): 0.109,
    (1.000, 13): 0.095,
    (1.000, 14): 0.083,
    (1.000, 15): 0.072,
    (1.000, 16): 0.065,
    (1.000, 17): 0.058,
    (1.000, 18): 0.049,
    # OD = 1-1/4 in
    (1.250,  8): 0.165,
    (1.250,  9): 0.148,
    (1.250, 10): 0.134,
    (1.250, 11): 0.120,
    (1.250, 12): 0.109,
    (1.250, 13): 0.095,
    (1.250, 14): 0.083,
    (1.250, 15): 0.072,
    (1.250, 16): 0.065,
    (1.250, 17): 0.058,
    (1.250, 18): 0.049,
    # OD = 1-1/2 in
    (1.500,  8): 0.165,
    (1.500,  9): 0.148,
    (1.500, 10): 0.134,
    (1.500, 11): 0.120,
    (1.500, 12): 0.109,
    (1.500, 13): 0.095,
    (1.500, 14): 0.083,
    (1.500, 15): 0.072,
    (1.500, 16): 0.065,
    (1.500, 17): 0.058,
    (1.500, 18): 0.049,
}

VALID_TUBE_ODS = sorted({od for (od, _) in BWG_TABLE})
VALID_BWG      = sorted({bwg for (_, bwg) in BWG_TABLE})


def get_bwg_thickness(tube_od_in: float, bwg: int) -> float:
    """
    Return wall thickness (in) for a given tube OD and BWG gauge.
    Raises ValueError if the combination is not in the table.
    """
    key = (tube_od_in, bwg)
    if key not in BWG_TABLE:
        available = [b for (od, b) in BWG_TABLE if od == tube_od_in]
        if not available:
            raise ValueError(
                f"Tube OD {tube_od_in} in not in BWG table. "
                f"Valid ODs: {VALID_TUBE_ODS}"
            )
        raise ValueError(
            f"BWG {bwg} not available for tube OD {tube_od_in} in. "
            f"Valid BWG for this OD: {sorted(available)}"
        )
    return BWG_TABLE[key]


# ── Core calculation ──────────────────────────────────────────────────────────

def design_heat_exchanger(
    T_op_K: float,
    P_op_Pa: float,
    tube_od_in: float,
    bwg: int,
    tube_length_m: float,
    n_tubes: int,
    shell_id_m: float,
    tube_material: str,
    shell_material: str,
    weld_efficiency: float = 1.0,
    n_units: int = 1,
    name: str = "HX-001",
    T_d_F_override: float = None,
    P_d_psig_override: float = None,
) -> dict:
    """
    Estimate weight of a shell-and-tube heat exchanger.

    Parameters
    ----------
    T_op_K           : Operating temperature (K)
    P_op_Pa          : Operating pressure, absolute (Pa)
    tube_od_in       : Tube outside diameter (in) — one of 0.5, 0.75, 1.0, 1.25, 1.5
    bwg              : BWG gauge number (integer)
    tube_length_m    : Tube length (m)
    n_tubes          : Number of tubes
    shell_id_m       : Shell inside diameter (m)
    tube_material    : Material key for tubes (from MATERIALS dict)
    shell_material   : Material key for shell (from MATERIALS dict)
    weld_efficiency  : Weld efficiency E (default 1.0 for seamless HX shell)
    n_units          : Number of identical units
    name             : Equipment reference tag
    T_d_F_override   : Design temperature (°F) — skips +50°F step if provided
    P_d_psig_override: Design pressure (psig) — skips S&L correlation if provided
    """

    results = {
        'name': name, 'n_units': n_units,
        'tube_material': MATERIALS[tube_material]['name'],
        'shell_material': MATERIALS[shell_material]['name'],
        'tube_material_key': tube_material,
        'shell_material_key': shell_material,
        'weld_efficiency': weld_efficiency,
    }

    # ── Step 1 — Design pressure ──────────────────────────────────────────────
    if P_d_psig_override is not None:
        P_atm_Pa   = 101325.0
        P_o_psig   = max(Pa_to_psi(P_op_Pa - P_atm_Pa), 0.0)
        P_d_psig   = P_d_psig_override
        results['direct_P_d'] = True
    else:
        P_o_psig, P_d_psig = design_pressure_psig(P_op_Pa)
        results['direct_P_d'] = False
    results.update({'P_op_Pa': P_op_Pa, 'P_op_psig': P_o_psig, 'P_d_psig': P_d_psig})

    # ── Step 2 — Design temperature ───────────────────────────────────────────
    T_op_F = K_to_F(T_op_K)
    if T_d_F_override is not None:
        T_d_F = T_d_F_override
        results['direct_T_d'] = True
    else:
        _, T_d_F = design_temperature_F(T_op_K)
        results['direct_T_d'] = False
    results.update({'T_op_K': T_op_K, 'T_op_F': T_op_F, 'T_d_F': T_d_F})

    # ── Step 3 — Allowable stresses ───────────────────────────────────────────
    S_tube_psi  = allowable_stress_psi(tube_material,  T_d_F)
    S_shell_psi = allowable_stress_psi(shell_material, T_d_F)
    results.update({'S_tube_psi': S_tube_psi, 'S_shell_psi': S_shell_psi})

    # ── Step 4 — BWG tube wall thickness ──────────────────────────────────────
    t_tube_in  = get_bwg_thickness(tube_od_in, bwg)
    tube_id_in = tube_od_in - 2 * t_tube_in        # inside diameter of tube
    results.update({
        'tube_od_in': tube_od_in,
        'bwg': bwg,
        't_tube_in': t_tube_in,
        'tube_id_in': tube_id_in,
        'tube_length_m': tube_length_m,
        'n_tubes': n_tubes,
    })

    # ── Step 5 — Tube bundle weight ───────────────────────────────────────────
    # Volume of hollow tube wall = π/4 × (OD² - ID²) × L
    tube_length_in   = tube_length_m * 39.3701
    V_one_tube_in3   = (math.pi / 4) * (tube_od_in**2 - tube_id_in**2) * tube_length_in
    V_all_tubes_in3  = V_one_tube_in3 * n_tubes
    density_tube     = MATERIALS[tube_material]['density']   # lb/in³
    W_tubes_lb       = V_all_tubes_in3 * density_tube
    results.update({
        'tube_length_in': tube_length_in,
        'V_one_tube_in3': V_one_tube_in3,
        'V_all_tubes_in3': V_all_tubes_in3,
        'density_tube_lb_in3': density_tube,
        'W_tubes_lb': W_tubes_lb,
    })

    # ── Step 6 — Shell thickness (ASME formula) ───────────────────────────────
    # t = P·R / (S·E - 0.6·P)   where R = inside radius of shell
    shell_id_in = shell_id_m * 39.3701
    R_shell_in  = shell_id_in / 2.0
    denom       = S_shell_psi * weld_efficiency - 0.6 * P_d_psig
    if denom <= 0:
        raise ValueError(
            f"Shell thickness denominator ≤ 0 (S·E - 0.6·P = {denom:.2f}). "
            f"Design pressure too high for this material at this temperature."
        )
    t_shell_in = (P_d_psig * R_shell_in) / denom
    results.update({
        'shell_id_m': shell_id_m,
        'shell_id_in': shell_id_in,
        'R_shell_in': R_shell_in,
        't_shell_in': t_shell_in,
    })

    # ── Step 7 — Shell weight ─────────────────────────────────────────────────
    # Shell is a hollow cylinder: V = π/4 × (OD² − ID²) × L
    # where OD = shell_id + 2×t_shell
    shell_od_in      = shell_id_in + 2 * t_shell_in
    shell_length_in  = tube_length_in        # shell length ≈ tube length
    V_shell_in3      = (math.pi / 4
                        * (shell_od_in**2 - shell_id_in**2)
                        * shell_length_in)
    density_shell    = MATERIALS[shell_material]['density']  # lb/in³
    W_shell_lb       = V_shell_in3 * density_shell
    results.update({
        'shell_od_in': shell_od_in,
        'shell_length_in': shell_length_in,
        'V_shell_in3': V_shell_in3,
        'density_shell_lb_in3': density_shell,
        'W_shell_lb': W_shell_lb,
    })

    # ── Step 8 — Total weight ─────────────────────────────────────────────────
    W_total_lb = W_tubes_lb + W_shell_lb
    results.update({
        'W_total_lb':           W_total_lb,
        'W_total_per_unit_lb':  W_total_lb,
        'W_total_all_units_lb': W_total_lb * n_units,
    })

    return results
