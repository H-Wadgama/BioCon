"""
Pressure Vessel Weight Estimator
Streamlit web application — companion tool to manuscript

Architecture
------------
  pressure_vessel.py   ← calculation engine (ASME methodology)
  app.py               ← this file: UI layer only
  cost.py              ← future: cost correlation module (drop-in)

To run locally:
    pip install streamlit
    streamlit run app.py

To deploy (free):
    Push both files to a GitHub repo, then connect at
    https://share.streamlit.io
"""

import streamlit as st
import math
from pressure_vessel import (
    design_pressure_vessel, MATERIALS,
    m_to_in, m_to_ft, K_to_F
)

# ── Optional: import cost module when ready ────────────────────
# from cost import estimate_cost   # uncomment when cost.py exists

# ─────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Pressure Vessel Estimator",
    page_icon="⚙️",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────
st.title("⚙️ Pressure Vessel Weight Estimator")
st.markdown(
    """
    This tool estimates the **shell weight** of cylindrical pressure vessels with 2:1 semi-ellipsoidal heads,
    following the **ASME BPV Code Section VIII, Division 1** methodology.
    Refer to the companion manuscript for full methodological details and assumptions.
    """
)
st.divider()

# ─────────────────────────────────────────────────────────────────
# MATERIAL DISPLAY NAMES
# ─────────────────────────────────────────────────────────────────
MATERIAL_OPTIONS = {k: v['name'] for k, v in MATERIALS.items()}

# ─────────────────────────────────────────────────────────────────
# SIDEBAR — INPUTS
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("📋 Vessel Inputs")

    name = st.text_input("Equipment reference name", value="PV-001")

    st.subheader("Operating Conditions")
    T_op_K   = st.number_input("Operating temperature (K)",  min_value=273.15, max_value=1500.0, value=303.15, step=1.0)
    P_op_Pa  = st.number_input("Operating pressure, absolute (Pa)", min_value=0.0, max_value=1e8, value=101325.0, step=1000.0, format="%.2f")

    st.subheader("Geometry")
    geom_mode = st.radio("Geometry input mode", ["Volume only", "Length and Diameter"])
    if geom_mode == "Volume only":
        volume = st.number_input("Total volume (m³)", min_value=0.01, value=10.0, step=1.0)
        L_input = None
        D_input = None
    else:
        volume = None
        L_input = st.number_input("Shell length, L (m)", min_value=0.01, value=5.0, step=0.1)
        D_input = st.number_input("Inside diameter, D (m)", min_value=0.01, value=1.5, step=0.1)

    st.subheader("Design Parameters")
    material_key  = st.selectbox("Material of construction", options=list(MATERIAL_OPTIONS.keys()),
                                  format_func=lambda k: MATERIAL_OPTIONS[k], index=4)  # SS304 default
    configuration = st.selectbox("Configuration", ["Vertical", "Horizontal"])
    corrosion     = st.selectbox("Corrosive service?", ["Yes", "No"]) == "Yes"
    weld_eff      = st.selectbox("Weld joint efficiency", [1.0, 0.85, 0.70],
                                  format_func=lambda x: f"{x:.2f}  ({'Full' if x==1.0 else 'Spot' if x==0.85 else 'None'})")
    n_units       = st.number_input("Number of units", min_value=1, max_value=500, value=1, step=1)

    calculate = st.button("▶  Calculate", type="primary", use_container_width=True)

# ─────────────────────────────────────────────────────────────────
# MAIN PANEL — RESULTS
# ─────────────────────────────────────────────────────────────────
if calculate:
    try:
        r = design_pressure_vessel(
            T_op_K        = T_op_K,
            P_op_Pa       = P_op_Pa,
            material      = material_key,
            configuration = configuration.lower(),
            corrosion     = corrosion,
            weld_efficiency = weld_eff,
            volume        = volume,
            L             = L_input,
            D             = D_input,
            n_units       = int(n_units),
            name          = name,
        )

        # ── KPI metrics row ──────────────────────────────────────
        st.subheader(f"Results — {r['name']}")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Wall Thickness",
                    f"{r['t_total_in']:.4f} in",
                    f"{r['t_total_in']*25.4:.2f} mm")
        col2.metric("Inside Diameter",
                    f"{r['D_m']:.3f} m",
                    f"{m_to_in(r['D_m']):.2f} in")
        col3.metric("Shell Weight (per unit)",
                    f"{r['W_shell_lb']:,.0f} lb",
                    f"{r['W_shell_lb']*0.453592/1000:.1f} tonne")
        col4.metric("Total Weight (per unit)",
                    f"{r['W_total_lb']:,.0f} lb",
                    f"{r['W_total_lb']*0.453592/1000:.1f} tonne")

        if r['n_units'] > 1:
            st.info(f"**{r['n_units']} units** → Total weight for all units: "
                    f"**{r['W_total_all_units_lb']:,.0f} lb "
                    f"({r['W_total_all_units_lb']*0.453592/1000:.1f} tonne)**")

        st.divider()

        # ── Two-column detail tables ─────────────────────────────
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("#### 🌡️ Design Conditions")
            st.table({
                "Parameter": [
                    "Operating temperature",
                    "Design temperature (+ 50°F margin)",
                    "Operating pressure (gauge)",
                    "Design pressure",
                    "Allowable stress (S)",
                    "Weld efficiency (E)",
                ],
                "Value": [
                    f"{r['T_op_K']:.2f} K  ({r['T_op_F']:.1f} °F)",
                    f"{r['T_d_F']:.1f} °F",
                    f"{r['P_op_psig']:.2f} psig",
                    f"{r['P_d_psig']:.2f} psig",
                    f"{r['S_psi']:,.0f} psi  ({r['S_psi']/1000:.1f} ksi)",
                    f"{r['weld_efficiency']:.2f}",
                ],
            })

            st.markdown("#### 📐 Geometry")
            st.table({
                "Parameter": [
                    "L/D ratio",
                    "Inside diameter (Dᵢ)",
                    "Shell length (L)",
                    "Volume",
                ],
                "Value": [
                    str(r['LD_ratio']),
                    f"{r['D_m']:.4f} m  ({m_to_in(r['D_m']):.3f} in,  {m_to_ft(r['D_m']):.3f} ft)",
                    f"{r['L_m']:.4f} m  ({m_to_in(r['L_m']):.3f} in)",
                    f"{r['V_m3']:.4f} m³",
                ],
            })

        with col_b:
            st.markdown("#### 🔩 Wall Thickness")
            tw_params  = ["t_pressure (tₚ)", "t_min (diameter)", "t_shell governed (tₛ)"]
            tw_values  = [
                f"{r['t_p_in']:.4f} in",
                f"{r['t_min_in']:.4f} in",
                f"{r['t_s_in']:.4f} in",
            ]
            if r['t_w_in'] is not None:
                tw_params += ["t_wind/seismic (t_w)", "t_design = tₛ + t_w/2"]
                tw_values += [f"{r['t_w_in']:.4f} in", f"{r['t_design_in']:.4f} in"]
            tw_params += ["Corrosion allowance", "Before rounding", "**t_TOTAL (std plate)**"]
            tw_values += [
                f"{r['t_corr_in']:.4f} in  ({r['t_corr_in']*25.4:.2f} mm)",
                f"{r['t_before_round_in']:.4f} in",
                f"**{r['t_total_in']:.4f} in  ({r['t_total_in']*25.4:.2f} mm)**",
            ]
            st.table({"Parameter": tw_params, "Value": tw_values})

            st.markdown("#### ⚖️ Weight")
            st.table({
                "Parameter": [
                    "Material density (ρ)",
                    "Shell weight (Eq. 16.59)",
                    "Weight allowance",
                    "Total weight (per unit)",
                ],
                "Value": [
                    f"{MATERIALS[material_key]['density']} lb/in³",
                    f"{r['W_shell_lb']:,.1f} lb",
                    f"+{int(round((r['W_total_lb']/r['W_shell_lb']-1)*100))}%",
                    f"{r['W_total_lb']:,.1f} lb  ({r['W_total_lb']*0.453592/1000:.2f} tonne)",
                ],
            })

        # ── Collapsible step-by-step summary ────────────────────
        with st.expander("🔍 Step-by-step calculation summary"):
            st.markdown(f"""
**Step 1 — Design Pressure**
Operating gauge pressure = {r['P_op_psig']:.2f} psig →
{"floor applied" if r['P_op_psig'] < 10 else "log-linear formula" if r['P_op_psig'] <= 1000 else "×1.1 rule"} →
P_design = **{r['P_d_psig']:.2f} psig**

**Step 2 — Design Temperature**
T_op = {r['T_op_F']:.1f} °F + 50°F margin = **T_design = {r['T_d_F']:.1f} °F**

**Step 3 — Allowable Stress**
Material: {r['material']} | T_design = {r['T_d_F']:.1f} °F →
smallest ASME bracket ≥ T_design → **S = {r['S_psi']:,.0f} psi**

**Step 4 — L/D Ratio and Geometry**
P_design = {r['P_d_psig']:.2f} psig → L/D = **{r['LD_ratio']}** →
D_i = **{r['D_m']:.4f} m** ({m_to_in(r['D_m']):.3f} in), L = **{r['L_m']:.4f} m** ({m_to_in(r['L_m']):.3f} in)

**Step 5 — Wall Thickness**
tₚ = P_d·D_i / (2SE − 1.2P_d) = **{r['t_p_in']:.4f} in**
t_min (diameter-based) = **{r['t_min_in']:.4f} in**
tₛ = max(tₚ, t_min) = **{r['t_s_in']:.4f} in**
{"t_w (wind/seismic) = **" + f"{r['t_w_in']:.4f} in**" + chr(10) + "t_design = tₛ + t_w/2 = **" + f"{r['t_design_in']:.4f} in**" if r['t_w_in'] is not None else "Horizontal vessel — wind/seismic term not applicable; t_design = tₛ = **" + f"{r['t_s_in']:.4f} in**"}

**Step 6 — Corrosion Allowance**
{"Carbon steel, corrosive service → 4.0 mm" if not MATERIALS[material_key]['is_alloy'] and corrosion else "Carbon steel, non-corrosive → 2.0 mm" if not MATERIALS[material_key]['is_alloy'] else "Stainless/alloy → 1.0 mm"} = **{r['t_corr_in']:.4f} in**

**Step 7 — Round Up to Standard Plate**
t_design + t_corr = {r['t_before_round_in']:.4f} in → rounded up → **t_TOTAL = {r['t_total_in']:.4f} in ({r['t_total_in']*25.4:.2f} mm)**

**Step 8 — Vessel Weight**
W = π(D_i + t_s)(L + 0.8D_i) · t_s · ρ = {r['W_shell_lb']:,.1f} lb → with allowance → **{r['W_total_lb']:,.1f} lb**
""")

        # ── Future: cost section placeholder ────────────────────
        # Uncomment and implement cost.py to activate this section
        # st.divider()
        # st.subheader("💰 Cost Estimation")
        # cost = estimate_cost(r)
        # st.metric("Purchased equipment cost", f"${cost['C_p']:,.0f}")

    except ValueError as e:
        st.error(f"⚠️ Design error: {e}")

else:
    # ── Landing state ────────────────────────────────────────────
    st.info("👈  Enter vessel parameters in the sidebar and click **Calculate**.")

    with st.expander("ℹ️ Methodology overview"):
        st.markdown("""
        The tool implements the ASME BPV Code Section VIII, Division 1 sizing procedure:

        1. **Design pressure** — operating gauge pressure mapped to design pressure via Sandler & Luckiewicz (1987) rules; minimum floor of 10 psig applied
        2. **Design temperature** — operating temperature + 50°F margin (Turton et al., 2018)
        3. **Allowable stress** — tabulated ASME values for the selected material; conservative ceiling bracket selection
        4. **Vessel geometry** — L/D ratio assigned by design pressure; diameter solved from cylindrical volume equation
        5. **Wall thickness** — pressure formula (Eq. 16.60); diameter-based minimum (Table 5); wind/seismic contribution for vertical vessels (Mulet et al., 1981)
        6. **Corrosion allowance** — material and service dependent (Towler & Sinnott, 2022)
        7. **Standard plate rounding** — t_total rounded up to nearest 1/16, 1/8, or 1/4 in increment
        8. **Weight** — shell + 2:1 SE head weight (Eq. 16.59) with nozzle/support allowance

        **References:**
        - ASME (2021). *Boiler and Pressure Vessel Code*, Section VIII, Division 1
        - Turton, R. et al. (2018). *Analysis, Synthesis and Design of Chemical Processes*, 5th ed.
        - Mulet, A. et al. (1981). Chem. Eng., 88(21), 145–150
        - Sandler, H.J. & Luckiewicz, E.T. (1987). *Practical Process Engineering*
        - Towler, G. & Sinnott, R. (2022). *Chemical Engineering Design*, 3rd ed.
        """)

# ─────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "Pressure Vessel Weight Estimator · ASME BPV Code Section VIII, Div. 1 · "
    "For preliminary design and cost-estimation purposes only. "
    "Not a substitute for detailed engineering analysis."
)
