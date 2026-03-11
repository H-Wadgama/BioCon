"""
Pressure Vessel Weight Estimator — Streamlit UI
Architecture:
  pressure_vessel.py  ← calculation engine (do not mix UI here)
  batch.py            ← batch CSV processing
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
from batch import (
    normalise_columns, run_batch,
    make_template_csv, results_to_export_df,
    VALID_MATERIALS,
)

# ── Unit conversion helpers (UI layer only) ───────────────────────────────────
def to_kelvin(value, unit):
    if unit == "K":  return value
    if unit == "°C": return value + 273.15
    if unit == "°F": return (value - 32) * 5/9 + 273.15

def to_fahrenheit(value, unit):
    if unit == "°F": return value
    if unit == "°C": return value * 9/5 + 32
    if unit == "K":  return (value - 273.15) * 9/5 + 32

def to_pascal_abs(value, unit):
    if unit == "Pa":  return value
    if unit == "bar": return value * 1e5
    if unit == "atm": return value * 101325.0
    if unit == "psi": return value / 0.000145038

def to_psig(value, unit):
    if unit == "psig": return value
    if unit == "barg": return value * 14.5038
    if unit == "atg":  return value * 14.6959
    return value


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Pressure Vessel Estimator", page_icon="⚙️", layout="wide")

st.title("⚙️ Pressure Vessel Weight Estimator")
st.markdown(
    "This tool estimates the **shell weight** of cylindrical pressure vessels with 2:1 "
    "semi-ellipsoidal heads, following the **ASME BPV Code Section VIII, Division 1** methodology. "
    "Refer to the companion manuscript for full methodological details and assumptions."
)
st.divider()

# ── Session state ─────────────────────────────────────────────────────────────
if "vessel_inventory" not in st.session_state:
    st.session_state.vessel_inventory = []
if "last_result" not in st.session_state:
    st.session_state.last_result = None

MATERIAL_OPTIONS = {k: v['name'] for k, v in MATERIALS.items()}

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["🔧 Manual Entry", "📂 Batch CSV"])


# ════════════════════════════════════════════════════════════════════════════════
# SIDEBAR — Manual Entry inputs (sidebar is global but only relevant to Tab 1)
# ════════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("📋 Vessel Inputs")
    st.caption("Used in the Manual Entry tab only.")
    name = st.text_input("Equipment reference name", value="PV-001")

    # ── Temperature ──────────────────────────────────────────────────────────
    st.subheader("Temperature")
    temp_mode = st.radio(
        "Input type",
        ["Operating temperature", "Design temperature (direct)"],
        key="temp_mode",
        help="Operating → design T = T_op + 50°F applied automatically.\n"
             "Design (direct) → value used as-is for stress lookup, no margin added."
    )
    temp_unit = st.selectbox("Unit", ["K", "°C", "°F"], key="temp_unit")
    _t_defaults = {"K": 303.15, "°C": 30.0, "°F": 86.0}
    temp_value = st.number_input(
        f"{'Operating' if temp_mode == 'Operating temperature' else 'Design'} temperature ({temp_unit})",
        value=_t_defaults[temp_unit], step=1.0, format="%.2f", key="temp_value"
    )
    if temp_mode == "Operating temperature":
        T_op_K         = to_kelvin(temp_value, temp_unit)
        T_d_F_override = None
    else:
        T_d_F_override = to_fahrenheit(temp_value, temp_unit)
        T_op_K         = to_kelvin(temp_value, temp_unit)

    # ── Pressure ─────────────────────────────────────────────────────────────
    st.subheader("Pressure")
    press_mode = st.radio(
        "Input type",
        ["Operating pressure (absolute)", "Design pressure (direct)"],
        key="press_mode",
        help="Operating → design P calculated via Sandler & Luckiewicz correlation.\n"
             "Design (direct) → gauge value used as-is, correlation skipped."
    )
    if press_mode == "Operating pressure (absolute)":
        press_unit  = st.selectbox("Unit", ["Pa", "bar", "atm", "psi"], key="press_unit")
        _p_defaults = {"Pa": 101325.0, "bar": 1.01325, "atm": 1.0, "psi": 14.696}
        press_value = st.number_input(
            f"Operating pressure ({press_unit}, absolute)",
            value=_p_defaults[press_unit], min_value=0.0, format="%.4f", key="press_value"
        )
        P_op_Pa           = to_pascal_abs(press_value, press_unit)
        P_d_psig_override = None
    else:
        press_unit  = st.selectbox("Unit", ["psig", "barg", "atg"], key="press_unit_d",
                                    help="Gauge pressure units — atmospheric reference already subtracted.")
        _p_defaults_g = {"psig": 0.0, "barg": 0.0, "atg": 0.0}
        press_value = st.number_input(
            f"Design pressure ({press_unit}, gauge)",
            value=_p_defaults_g[press_unit], min_value=0.0, format="%.4f", key="press_value_d"
        )
        P_d_psig_override = to_psig(press_value, press_unit)
        P_op_Pa           = 101325.0

    # ── Geometry ─────────────────────────────────────────────────────────────
    st.subheader("Geometry")
    geom_mode = st.radio("Geometry input mode", ["Volume only", "Length and Diameter"])
    if geom_mode == "Volume only":
        volume  = st.number_input("Total volume (m³)", min_value=0.01, value=10.0, step=1.0)
        L_input = D_input = None
        internals_allowance_pct = 0.0
    else:
        volume  = None
        L_input = st.number_input("Shell length, L (m)", min_value=0.01, value=5.0, step=0.1)
        D_input = st.number_input("Inside diameter, D (m)", min_value=0.01, value=1.5, step=0.1)
        internals_allowance_pct = st.number_input(
            "Internals volume allowance (%)",
            min_value=0.0, max_value=100.0, value=0.0, step=1.0,
            help="Extra volume added on top of the geometric volume (π/4 · D² · L) to "
                 "account for vessel internals (e.g. trays, packing, coils). "
                 "The inflated volume is used for sizing but D and L remain as entered."
        )

    # ── Design parameters ────────────────────────────────────────────────────
    st.subheader("Design Parameters")
    material_key  = st.selectbox(
        "Material of construction", options=list(MATERIAL_OPTIONS.keys()),
        format_func=lambda k: MATERIAL_OPTIONS[k], index=4
    )
    configuration = st.selectbox("Configuration", ["Vertical", "Horizontal"])
    corrosion     = st.selectbox("Corrosive service?", ["Yes", "No"]) == "Yes"
    weld_eff      = st.selectbox(
        "Weld joint efficiency", [1.0, 0.85, 0.70],
        format_func=lambda x: f"{x:.2f}  ({'Full' if x==1.0 else 'Spot' if x==0.85 else 'None'})"
    )
    n_units = st.number_input("Number of units", min_value=1, max_value=500, value=1, step=1)

    st.divider()
    col_calc, col_add = st.columns(2)
    calculate = col_calc.button("▶ Calculate",    type="primary",   use_container_width=True)
    add_btn   = col_add.button( "＋ Add to List", type="secondary", use_container_width=True)


# ── Manual entry calculation helper ──────────────────────────────────────────
def run_calculation():
    import math as _math
    if L_input is not None and D_input is not None and internals_allowance_pct > 0.0:
        V_geometric = _math.pi / 4 * D_input**2 * L_input
        V_inflated  = V_geometric * (1 + internals_allowance_pct / 100.0)
        call_volume, call_L, call_D = V_inflated, None, None
    else:
        V_geometric = None
        V_inflated  = None
        call_volume, call_L, call_D = volume, L_input, D_input

    r = design_pressure_vessel(
        T_op_K=T_op_K, P_op_Pa=P_op_Pa, material=material_key,
        configuration=configuration.lower(), corrosion=corrosion,
        weld_efficiency=weld_eff, volume=call_volume, L=call_L, D=call_D,
        n_units=int(n_units), name=name,
        T_d_F_override=T_d_F_override, P_d_psig_override=P_d_psig_override,
    )
    if L_input is not None and D_input is not None:
        r['D_m'] = D_input
        r['L_m'] = L_input
    r['internals_allowance_pct'] = internals_allowance_pct
    r['V_geometric_m3']          = V_geometric
    r['V_inflated_m3']           = V_inflated
    return r


# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — Manual Entry
# ════════════════════════════════════════════════════════════════════════════════
with tab1:

    # ── Button logic ─────────────────────────────────────────────────────────
    if calculate or add_btn:
        try:
            r = run_calculation()
            st.session_state.last_result = r
            if add_btn:
                st.session_state.vessel_inventory.append(r)
                st.toast(
                    f"✅ {r['name']} added to inventory "
                    f"({len(st.session_state.vessel_inventory)} vessels total)", icon="✅"
                )
        except ValueError as e:
            st.error(f"⚠️ Design error: {e}")
            st.session_state.last_result = None

    # ── Individual result panel ───────────────────────────────────────────────
    r = st.session_state.last_result

    if r is not None:
        st.subheader(f"Results — {r['name']}")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Wall Thickness",    f"{r['t_total_in']:.4f} in",  f"{r['t_total_in']*25.4:.2f} mm")
        col2.metric("Inside Diameter",   f"{r['D_m']:.3f} m",          f"{m_to_in(r['D_m']):.2f} in")
        col3.metric("Shell Weight/unit", f"{r['W_shell_lb']:,.0f} lb", f"{r['W_shell_lb']*0.453592/1000:.1f} t")
        col4.metric("Total Weight/unit", f"{r['W_total_lb']:,.0f} lb", f"{r['W_total_lb']*0.453592/1000:.1f} t")

        if r['n_units'] > 1:
            st.info(
                f"**{r['n_units']} units** → All units total: "
                f"**{r['W_total_all_units_lb']:,.0f} lb "
                f"({r['W_total_all_units_lb']*0.453592/1000:.1f} t)**"
            )

        st.divider()
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("#### 🌡️ Design Conditions")
            if r.get('direct_T_d'):
                t_rows = {
                    "Parameter": ["Design temperature (direct input)",
                                  "Allowable stress (S)", "Weld efficiency (E)"],
                    "Value": [f"{r['T_d_F']:.1f} °F",
                              f"{r['S_psi']:,.0f} psi ({r['S_psi']/1000:.1f} ksi)",
                              f"{r['weld_efficiency']:.2f}"]
                }
                st.info("ℹ️ Design temperature entered directly — +50°F margin step skipped.")
            else:
                t_rows = {
                    "Parameter": ["Operating temperature",
                                  "Design temperature (T_op + 50°F)",
                                  "Allowable stress (S)", "Weld efficiency (E)"],
                    "Value": [f"{r['T_op_K']:.2f} K ({r['T_op_F']:.1f} °F)",
                              f"{r['T_d_F']:.1f} °F",
                              f"{r['S_psi']:,.0f} psi ({r['S_psi']/1000:.1f} ksi)",
                              f"{r['weld_efficiency']:.2f}"]
                }
            if r.get('direct_P_d'):
                t_rows["Parameter"] += ["Design pressure (direct input)",
                                        "Operating pressure (gauge)"]
                t_rows["Value"]     += [f"{r['P_d_psig']:.2f} psig",
                                        f"{r['P_op_psig']:.2f} psig"]
                st.info("ℹ️ Design pressure entered directly — S&L correlation step skipped.")
            else:
                t_rows["Parameter"] += ["Operating pressure (gauge)",
                                        "Design pressure (S&L corr.)"]
                t_rows["Value"]     += [f"{r['P_op_psig']:.2f} psig",
                                        f"{r['P_d_psig']:.2f} psig"]
            st.table(t_rows)

            st.markdown("#### 📐 Geometry")
            st.table({
                "Parameter": ["L/D ratio", "Inside diameter (Dᵢ)",
                               "Shell length (L)", "Volume"],
                "Value": [str(r['LD_ratio']),
                          f"{r['D_m']:.4f} m ({m_to_in(r['D_m']):.3f} in, {m_to_ft(r['D_m']):.3f} ft)",
                          f"{r['L_m']:.4f} m ({m_to_in(r['L_m']):.3f} in)",
                          f"{r['V_m3']:.4f} m³"]
            })

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
            st.table({
                "Parameter": ["Material density (ρ)", "Shell weight (Eq. 16.59)",
                              "Weight allowance", "Total weight/unit"],
                "Value": [f"{MATERIALS[material_key]['density']} lb/in³",
                          f"{r['W_shell_lb']:,.1f} lb",
                          f"+{int(round((r['W_total_lb']/r['W_shell_lb']-1)*100))}%",
                          f"{r['W_total_lb']:,.1f} lb ({r['W_total_lb']*0.453592/1000:.2f} t)"]
            })

        with st.expander("🔍 Step-by-step calculation summary"):
            t_line = (
                f"Design temperature entered directly: **{r['T_d_F']:.1f}°F** (+50°F step skipped)"
                if r.get('direct_T_d')
                else f"{r['T_op_F']:.1f}°F + 50°F = **{r['T_d_F']:.1f}°F**"
            )
            p_line = (
                f"Design pressure entered directly: **{r['P_d_psig']:.2f} psig** (S&L step skipped)"
                if r.get('direct_P_d')
                else f"P_op(gauge)={r['P_op_psig']:.2f} psig → P_design=**{r['P_d_psig']:.2f} psig**"
            )
            st.markdown(f"""
**Step 1 — Design Pressure:** {p_line}
**Step 2 — Design Temperature:** {t_line}
**Step 3 — Allowable Stress:** ceiling bracket ≥ T_design → **S={r['S_psi']:,.0f} psi**
**Step 4 — Geometry:** L/D={r['LD_ratio']} → D_i=**{r['D_m']:.4f} m**, L=**{r['L_m']:.4f} m**{
    (chr(10) + f"  *Internals allowance: geometric V={r['V_geometric_m3']:.4f} m³ × "
               f"(1 + {r['internals_allowance_pct']:.1f}%) = **{r['V_inflated_m3']:.4f} m³** used for sizing*")
    if r.get('V_inflated_m3') is not None else
    (chr(10) + f"  Volume = **{r['V_m3']:.4f} m³**")
}
**Step 5 — Wall Thickness:** tₚ={r['t_p_in']:.4f} in, t_min={r['t_min_in']:.4f} in, tₛ=**{r['t_s_in']:.4f} in**{(chr(10)+'**t_w='+f"{r['t_w_in']:.4f} in, t_design="+f"{r['t_design_in']:.4f} in**") if r['t_w_in'] else ''}
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

    # ── Vessel Inventory ──────────────────────────────────────────────────────
    inventory = st.session_state.vessel_inventory
    if inventory:
        st.divider()
        st.subheader(f"📦 Vessel Inventory — {len(inventory)} vessel(s)")

        display_rows = []
        for v in inventory:
            display_rows.append({
                "Name":              v["name"],
                "Material":          v["material"],
                "Config.":           v["configuration"].capitalize(),
                "V (m³)":            round(v["V_m3"], 3),
                "D_i (m)":           round(v["D_m"], 4),
                "L (m)":             round(v["L_m"], 4),
                "P_d (psig)":        round(v["P_d_psig"], 2),
                "T_d (°F)":          round(v["T_d_F"], 1),
                "t_total (in)":      round(v["t_total_in"], 4),
                "t_total (mm)":      round(v["t_total_in"] * 25.4, 2),
                "W_shell (lb)":      round(v["W_shell_lb"], 0),
                "W_total/unit (lb)": round(v["W_total_lb"], 0),
                "No. units":         v["n_units"],
                "W_all units (lb)":  round(v["W_total_all_units_lb"], 0),
                "W_all units (t)":   round(v["W_total_all_units_lb"] * 0.453592 / 1000, 2),
            })

        export_rows = []
        for v in inventory:
            export_rows.append({
                "Equipment Name":                 v["name"],
                "Material":                       v["material"],
                "Configuration":                  v["configuration"].capitalize(),
                "Volume (m³)":                    round(v["V_m3"], 3),
                "Internals Allowance (%)":        v.get("internals_allowance_pct", 0.0),
                "Internal Diameter (ft)":         round(m_to_ft(v["D_m"]), 4),
                "Tangent to Tangent Length (ft)": round(m_to_ft(v["L_m"]), 4),
                "Total Wall Thickness (in)":      round(v["t_total_in"], 4),
                "Vessel Weight per Unit (kg)":    round(v["W_total_lb"] * 0.453592, 1),
                "Number of Units":                v["n_units"],
                "Total Weight All Units (kg)":    round(v["W_total_all_units_lb"] * 0.453592, 1),
            })

        df_display = pd.DataFrame(display_rows)
        df_export  = pd.DataFrame(export_rows)
        grand_lb   = sum(v["W_total_all_units_lb"] for v in inventory)
        grand_t    = grand_lb * 0.453592 / 1000

        st.dataframe(df_display, use_container_width=True, hide_index=True)

        n_total_units = sum(v["n_units"] for v in inventory)
        col_t1, col_t2, col_t3 = st.columns(3)
        col_t1.metric("Total vessels (types)", len(inventory))
        col_t2.metric("Total units",           n_total_units)
        col_t3.metric("Grand total weight",    f"{grand_lb:,.0f} lb  ({grand_t:,.1f} t)")

        col_csv, col_clr, _ = st.columns([1, 1, 3])
        csv_buf = io.StringIO()
        df_export.to_csv(csv_buf, index=False)
        col_csv.download_button(
            label="⬇️ Export CSV", data=csv_buf.getvalue(),
            file_name="vessel_inventory.csv", mime="text/csv",
            use_container_width=True,
        )
        if col_clr.button("🗑️ Clear Inventory", use_container_width=True):
            st.session_state.vessel_inventory = []
            st.session_state.last_result = None
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — Batch CSV
# ════════════════════════════════════════════════════════════════════════════════
with tab2:

    st.subheader("📂 Batch CSV Processing")
    st.markdown(
        "Upload a CSV containing multiple vessels. The tool will calculate the weight "
        "of each vessel and return a results CSV. Rows with errors are skipped and reported separately."
    )

    # ── Template download & column reference ─────────────────────────────────
    with st.expander("📋 Column reference & template download", expanded=True):
        st.markdown("""
**Required columns** (case-insensitive, extra spaces ignored):

| Column | Accepted values | Notes |
|---|---|---|
| `name` | any string | Equipment tag / reference |
| `material` | `CS_A285` `CS_A515` `LA_A387` `SS410` `SS304` `SS347` `SS321` `SS316` | Exact key |
| `configuration` | `vertical` `horizontal` | |
| `temperature_value` | number | Value in the unit specified below |
| `temperature_unit` | `K` `°C` `C` `°F` `F` | |
| `temperature_input` | `operating` `design` | Operating → +50°F added. Design → used as-is |
| `pressure_value` | number | Value in the unit specified below |
| `pressure_unit` | `Pa` `bar` `atm` `psi` *(operating)* or `psig` `barg` `atg` *(design)* | |
| `pressure_input` | `operating` `design` | Operating → S&L correlation. Design → used as-is |
| `volume_m3` | number | Provide this **or** length + diameter, not both |
| `length_m` | number | Shell length in metres |
| `diameter_m` | number | Inside diameter in metres |
| `internals_allowance_pct` | number ≥ 0 | Only applies when length + diameter are given. Default 0 |
| `corrosion` | `yes` `no` | Default `no` |
| `weld_efficiency` | `1.0` `0.85` `0.70` | Default `1.0` |
| `n_units` | integer ≥ 1 | Default `1` |
""")
        st.download_button(
            label="⬇️ Download template CSV",
            data=make_template_csv(),
            file_name="vessel_batch_template.csv",
            mime="text/csv",
        )

    # ── File uploader ─────────────────────────────────────────────────────────
    uploaded = st.file_uploader(
        "Upload your completed CSV", type=["csv"],
        help="Must follow the column structure above. Download the template to get started."
    )

    if uploaded is not None:
        try:
            df_raw = pd.read_csv(uploaded)
        except Exception as e:
            st.error(f"⚠️ Could not read CSV: {e}")
            df_raw = None

        if df_raw is not None:
            if df_raw.empty:
                st.warning("The uploaded CSV has no data rows.")
            else:
                df_norm, col_warnings = normalise_columns(df_raw)
                if col_warnings:
                    with st.expander(f"⚠️ {len(col_warnings)} unrecognised column(s)"):
                        for w in col_warnings:
                            st.warning(w)

                with st.spinner(f"Processing {len(df_norm)} vessel(s)…"):
                    results, errors = run_batch(df_norm)

                # ── Summary metrics ───────────────────────────────────────────
                c1, c2, c3 = st.columns(3)
                c1.metric("Rows in file",       len(df_norm))
                c2.metric("✅ Processed",        len(results))
                c3.metric("❌ Errors / skipped", len(errors))

                # ── Error report ──────────────────────────────────────────────
                if errors:
                    st.divider()
                    st.markdown("#### ❌ Rows with errors (skipped)")
                    st.dataframe(
                        pd.DataFrame(errors), use_container_width=True, hide_index=True
                    )

                # ── Results ───────────────────────────────────────────────────
                if results:
                    st.divider()
                    st.markdown(f"#### ✅ Results — {len(results)} vessel(s) processed")

                    df_export = results_to_export_df(results)

                    grand_kg      = sum(v["W_total_all_units_lb"] * 0.453592 for v in results)
                    grand_t       = grand_kg / 1000
                    n_units_total = sum(v["n_units"] for v in results)

                    col_g1, col_g2, col_g3 = st.columns(3)
                    col_g1.metric("Vessel types",       len(results))
                    col_g2.metric("Total units",        n_units_total)
                    col_g3.metric("Grand total weight", f"{grand_kg:,.0f} kg  ({grand_t:,.1f} t)")

                    st.dataframe(df_export, use_container_width=True, hide_index=True)

                    res_buf = io.StringIO()
                    df_export.to_csv(res_buf, index=False)
                    st.download_button(
                        label="⬇️ Download results CSV",
                        data=res_buf.getvalue(),
                        file_name="vessel_batch_results.csv",
                        mime="text/csv",
                    )

                    st.divider()
                    if st.button("➕ Add all batch results to Manual Inventory", type="secondary"):
                        st.session_state.vessel_inventory.extend(results)
                        st.success(
                            f"{len(results)} vessel(s) added to inventory. "
                            "Switch to the Manual Entry tab to view them."
                        )
                else:
                    st.error("No vessels could be processed. Check the error report above.")
    else:
        st.info("⬆️ Upload a CSV file above to get started, or download the template first.")


# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("Pressure Vessel Weight Estimator · ASME BPV Code VIII Div.1 · Preliminary design only.")
