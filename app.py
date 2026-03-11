"""
Pressure Vessel Weight Estimator — Streamlit UI
Architecture:
  pressure_vessel.py  ← calculation engine (do not mix UI here)
  app.py              ← this file: UI only
  cost.py             ← FUTURE: cost correlations (drop-in module)

Run locally:  streamlit run app.py
Deploy:       push to GitHub → auto-deploys on Streamlit Community Cloud
"""

import streamlit as st
import pandas as pd
import io
from pressure_vessel import (
    design_pressure_vessel, MATERIALS,
    m_to_in, m_to_ft, K_to_F
)

# from cost import estimate_cost   # uncomment when cost.py is ready

st.set_page_config(page_title="Pressure Vessel Estimator", page_icon="⚙️", layout="wide")

st.title("⚙️ Pressure Vessel Weight Estimator")
st.markdown(
    "This tool estimates the **shell weight** of cylindrical pressure vessels with 2:1 "
    "semi-ellipsoidal heads, following the **ASME BPV Code Section VIII, Division 1** methodology. "
    "Refer to the companion manuscript for full methodological details and assumptions."
)
st.divider()

# ── Session state initialisation ────────────────────────────────────────────
if "vessel_inventory" not in st.session_state:
    st.session_state.vessel_inventory = []   # list of result dicts
if "last_result" not in st.session_state:
    st.session_state.last_result = None

MATERIAL_OPTIONS = {k: v['name'] for k, v in MATERIALS.items()}

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("📋 Vessel Inputs")
    name = st.text_input("Equipment reference name", value="PV-001")

    st.subheader("Operating Conditions")
    T_op_K  = st.number_input("Operating temperature (K)", min_value=273.15, max_value=1500.0, value=303.15, step=1.0)
    P_op_Pa = st.number_input("Operating pressure, absolute (Pa)", min_value=0.0, max_value=1e8,
                               value=101325.0, step=1000.0, format="%.2f")

    st.subheader("Geometry")
    geom_mode = st.radio("Geometry input mode", ["Volume only", "Length and Diameter"])
    if geom_mode == "Volume only":
        volume  = st.number_input("Total volume (m³)", min_value=0.01, value=10.0, step=1.0)
        L_input = D_input = None
    else:
        volume  = None
        L_input = st.number_input("Shell length, L (m)", min_value=0.01, value=5.0, step=0.1)
        D_input = st.number_input("Inside diameter, D (m)", min_value=0.01, value=1.5, step=0.1)

    st.subheader("Design Parameters")
    material_key  = st.selectbox("Material of construction", options=list(MATERIAL_OPTIONS.keys()),
                                  format_func=lambda k: MATERIAL_OPTIONS[k], index=4)
    configuration = st.selectbox("Configuration", ["Vertical", "Horizontal"])
    corrosion     = st.selectbox("Corrosive service?", ["Yes", "No"]) == "Yes"
    weld_eff      = st.selectbox("Weld joint efficiency", [1.0, 0.85, 0.70],
                                  format_func=lambda x: f"{x:.2f}  ({'Full' if x==1.0 else 'Spot' if x==0.85 else 'None'})")
    n_units       = st.number_input("Number of units", min_value=1, max_value=500, value=1, step=1)

    st.divider()
    col_calc, col_add = st.columns(2)
    calculate = col_calc.button("▶ Calculate",    type="primary",   use_container_width=True)
    add_btn   = col_add.button( "＋ Add to List", type="secondary", use_container_width=True)


# ── Helper: run the engine ───────────────────────────────────────────────────
def run_calculation():
    return design_pressure_vessel(
        T_op_K=T_op_K, P_op_Pa=P_op_Pa, material=material_key,
        configuration=configuration.lower(), corrosion=corrosion,
        weld_efficiency=weld_eff, volume=volume, L=L_input, D=D_input,
        n_units=int(n_units), name=name,
    )


# ── Button logic ─────────────────────────────────────────────────────────────
if calculate or add_btn:
    try:
        r = run_calculation()
        st.session_state.last_result = r
        if add_btn:
            st.session_state.vessel_inventory.append(r)
            st.toast(f"✅ {r['name']} added to inventory ({len(st.session_state.vessel_inventory)} vessels total)", icon="✅")
    except ValueError as e:
        st.error(f"⚠️ Design error: {e}")
        st.session_state.last_result = None


# ── Individual result panel ──────────────────────────────────────────────────
r = st.session_state.last_result

if r is not None:
    st.subheader(f"Results — {r['name']}")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Wall Thickness",    f"{r['t_total_in']:.4f} in",  f"{r['t_total_in']*25.4:.2f} mm")
    col2.metric("Inside Diameter",   f"{r['D_m']:.3f} m",          f"{m_to_in(r['D_m']):.2f} in")
    col3.metric("Shell Weight/unit", f"{r['W_shell_lb']:,.0f} lb", f"{r['W_shell_lb']*0.453592/1000:.1f} t")
    col4.metric("Total Weight/unit", f"{r['W_total_lb']:,.0f} lb", f"{r['W_total_lb']*0.453592/1000:.1f} t")

    if r['n_units'] > 1:
        st.info(f"**{r['n_units']} units** → All units total: "
                f"**{r['W_total_all_units_lb']:,.0f} lb "
                f"({r['W_total_all_units_lb']*0.453592/1000:.1f} t)**")

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### 🌡️ Design Conditions")
        st.table({"Parameter": ["Operating temperature", "Design temperature",
                                 "Operating pressure (gauge)", "Design pressure",
                                 "Allowable stress (S)", "Weld efficiency (E)"],
                  "Value": [f"{r['T_op_K']:.2f} K ({r['T_op_F']:.1f} °F)",
                             f"{r['T_d_F']:.1f} °F",
                             f"{r['P_op_psig']:.2f} psig",
                             f"{r['P_d_psig']:.2f} psig",
                             f"{r['S_psi']:,.0f} psi ({r['S_psi']/1000:.1f} ksi)",
                             f"{r['weld_efficiency']:.2f}"]})
        st.markdown("#### 📐 Geometry")
        st.table({"Parameter": ["L/D ratio", "Inside diameter (Dᵢ)", "Shell length (L)", "Volume"],
                  "Value": [str(r['LD_ratio']),
                             f"{r['D_m']:.4f} m ({m_to_in(r['D_m']):.3f} in, {m_to_ft(r['D_m']):.3f} ft)",
                             f"{r['L_m']:.4f} m ({m_to_in(r['L_m']):.3f} in)",
                             f"{r['V_m3']:.4f} m³"]})

    with col_b:
        st.markdown("#### 🔩 Wall Thickness")
        tw_p = ["t_pressure (tₚ)", "t_min (diameter)", "t_shell governed (tₛ)"]
        tw_v = [f"{r['t_p_in']:.4f} in", f"{r['t_min_in']:.4f} in", f"{r['t_s_in']:.4f} in"]
        if r['t_w_in'] is not None:
            tw_p += ["t_wind/seismic (t_w)", "t_design = tₛ + t_w/2"]
            tw_v += [f"{r['t_w_in']:.4f} in", f"{r['t_design_in']:.4f} in"]
        tw_p += ["Corrosion allowance", "Before rounding", "t_TOTAL (std plate)"]
        tw_v += [f"{r['t_corr_in']:.4f} in ({r['t_corr_in']*25.4:.2f} mm)",
                 f"{r['t_before_round_in']:.4f} in",
                 f"{r['t_total_in']:.4f} in ({r['t_total_in']*25.4:.2f} mm)"]
        st.table({"Parameter": tw_p, "Value": tw_v})

        st.markdown("#### ⚖️ Weight")
        st.table({"Parameter": ["Material density (ρ)", "Shell weight (Eq. 16.59)",
                                 "Weight allowance", "Total weight/unit"],
                  "Value": [f"{MATERIALS[material_key]['density']} lb/in³",
                             f"{r['W_shell_lb']:,.1f} lb",
                             f"+{int(round((r['W_total_lb']/r['W_shell_lb']-1)*100))}%",
                             f"{r['W_total_lb']:,.1f} lb ({r['W_total_lb']*0.453592/1000:.2f} t)"]})

    with st.expander("🔍 Step-by-step calculation summary"):
        st.markdown(f"""
**Step 1 — Design Pressure:** P_op(gauge)={r['P_op_psig']:.2f} psig → P_design=**{r['P_d_psig']:.2f} psig**
**Step 2 — Design Temperature:** {r['T_op_F']:.1f}°F + 50°F = **{r['T_d_F']:.1f}°F**
**Step 3 — Allowable Stress:** ceiling bracket ≥ T_design → **S={r['S_psi']:,.0f} psi**
**Step 4 — Geometry:** L/D={r['LD_ratio']} → D_i=**{r['D_m']:.4f} m**, L=**{r['L_m']:.4f} m**
**Step 5 — Wall Thickness:** tₚ={r['t_p_in']:.4f} in, t_min={r['t_min_in']:.4f} in, tₛ=**{r['t_s_in']:.4f} in**{(chr(10)+'t_w='+f"{r['t_w_in']:.4f} in, t_design=**"+f"{r['t_design_in']:.4f} in**") if r['t_w_in'] else ''}
**Step 6 — Corrosion:** +{r['t_corr_in']:.4f} in → before rounding={r['t_before_round_in']:.4f} in
**Step 7 — Plate rounding:** → **t_TOTAL={r['t_total_in']:.4f} in ({r['t_total_in']*25.4:.2f} mm)**
**Step 8 — Weight:** W_shell={r['W_shell_lb']:,.0f} lb → **W_total={r['W_total_lb']:,.0f} lb/unit**
""")

else:
    st.info("👈  Enter vessel parameters in the sidebar and click **Calculate** to preview, "
            "or **＋ Add to List** to calculate and add directly to the inventory.")
    with st.expander("ℹ️ Methodology overview"):
        st.markdown("""
        ASME BPV Code Section VIII, Division 1 procedure:
        1. Design pressure — Sandler & Luckiewicz (1987); floor 10 psig
        2. Design temperature — T_op + 50°F (Turton et al., 2018)
        3. Allowable stress — ASME tables; ceiling bracket selection
        4. Geometry — L/D by pressure; D from cylindrical volume
        5. Wall thickness — pressure eq.; diameter min.; wind/seismic (Mulet et al., 1981)
        6. Corrosion allowance — Towler & Sinnott (2022)
        7. Plate rounding — 1/16, 1/8, 1/4 in increments
        8. Weight — Eq. 16.59 + nozzle/support allowance

        References: ASME (2021), Turton et al. (2018), Mulet et al. (1981),
        Sandler & Luckiewicz (1987), Towler & Sinnott (2022)
        """)


# ── Vessel Inventory summary table ──────────────────────────────────────────
inventory = st.session_state.vessel_inventory

if inventory:
    st.divider()
    st.subheader(f"📦 Vessel Inventory — {len(inventory)} vessel(s)")

    # Build display rows
    rows = []
    for v in inventory:
        rows.append({
            "Name":               v["name"],
            "Material":           v["material"],
            "Config.":            v["configuration"].capitalize(),
            "V (m³)":             round(v["V_m3"], 3),
            "D_i (m)":            round(v["D_m"], 4),
            "L (m)":              round(v["L_m"], 4),
            "P_d (psig)":         round(v["P_d_psig"], 2),
            "t_total (in)":       round(v["t_total_in"], 4),
            "t_total (mm)":       round(v["t_total_in"] * 25.4, 2),
            "W_shell (lb)":       round(v["W_shell_lb"], 0),
            "W_total/unit (lb)":  round(v["W_total_lb"], 0),
            "No. units":          v["n_units"],
            "W_all units (lb)":   round(v["W_total_all_units_lb"], 0),
            "W_all units (t)":    round(v["W_total_all_units_lb"] * 0.453592 / 1000, 2),
        })

    df = pd.DataFrame(rows)

    # Grand total row
    grand_lb = sum(v["W_total_all_units_lb"] for v in inventory)
    grand_t  = grand_lb * 0.453592 / 1000

    st.dataframe(df, use_container_width=True, hide_index=True)

    # Grand total metrics
    n_total_units = sum(v["n_units"] for v in inventory)
    col_t1, col_t2, col_t3 = st.columns(3)
    col_t1.metric("Total vessels (types)",   len(inventory))
    col_t2.metric("Total units",             n_total_units)
    col_t3.metric("Grand total weight",      f"{grand_lb:,.0f} lb  ({grand_t:,.1f} t)")

    # Action buttons row
    col_csv, col_clr, _ = st.columns([1, 1, 3])

    # CSV export
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    col_csv.download_button(
        label="⬇️ Export CSV",
        data=csv_buffer.getvalue(),
        file_name="vessel_inventory.csv",
        mime="text/csv",
        use_container_width=True,
    )

    # Clear inventory
    if col_clr.button("🗑️ Clear Inventory", use_container_width=True):
        st.session_state.vessel_inventory = []
        st.session_state.last_result = None
        st.rerun()

st.divider()
st.caption("Pressure Vessel Weight Estimator · ASME BPV Code VIII Div.1 · Preliminary design only.")
