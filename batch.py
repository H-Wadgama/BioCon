"""
batch.py — Batch CSV processing for the Pressure Vessel Weight Estimator
─────────────────────────────────────────────────────────────────────────
Reads a user-supplied CSV, validates and converts each row, calls the
design engine, and returns results + a list of per-row errors.

This module is UI-agnostic: it only imports from pressure_vessel.py and
the standard library / pandas. All Streamlit calls stay in app.py.
"""

import math
import pandas as pd
from pressure_vessel import design_pressure_vessel, MATERIALS

# ── Valid option sets (lowercase for matching) ────────────────────────────────
VALID_MATERIALS    = set(MATERIALS.keys())
VALID_CONFIG       = {"vertical", "horizontal"}
VALID_TEMP_INPUT   = {"operating", "design"}
VALID_PRESS_INPUT  = {"operating", "design"}
VALID_CORROSION    = {"yes", "no"}
VALID_WELD_EFF     = {1.0, 0.85, 0.70}
VALID_TEMP_UNITS   = {"k", "°c", "c", "°f", "f"}
VALID_PRESS_UNITS_OP  = {"pa", "bar", "atm", "psi"}
VALID_PRESS_UNITS_DES = {"psig", "barg", "atg"}

# ── Expected columns (canonical lowercase, stripped) ─────────────────────────
# Maps canonical name → list of accepted aliases (all lowercase, stripped)
COLUMN_ALIASES = {
    "name":                    ["name", "equipment", "equipment name", "tag", "id"],
    "material":                ["material", "material key", "mat", "material_key"],
    "configuration":           ["configuration", "config", "orientation", "vessel type"],
    "temperature_value":       ["temperature_value", "temperature value", "temp_value",
                                "temp value", "temperature", "temp"],
    "temperature_unit":        ["temperature_unit", "temperature unit", "temp_unit",
                                "temp unit", "t_unit"],
    "temperature_input":       ["temperature_input", "temperature input", "temp_input",
                                "temp input", "t_input", "temp mode", "temperature mode"],
    "pressure_value":          ["pressure_value", "pressure value", "press_value",
                                "press value", "pressure", "press"],
    "pressure_unit":           ["pressure_unit", "pressure unit", "press_unit",
                                "press unit", "p_unit"],
    "pressure_input":          ["pressure_input", "pressure input", "press_input",
                                "press input", "p_input", "press mode", "pressure mode"],
    "volume_m3":               ["volume_m3", "volume (m3)", "volume_m³", "volume (m³)",
                                "volume", "vol_m3", "vol"],
    "length_m":                ["length_m", "length (m)", "l_m", "l (m)",
                                "shell length", "shell length (m)", "length"],
    "diameter_m":              ["diameter_m", "diameter (m)", "d_m", "d (m)",
                                "inside diameter", "inside diameter (m)", "diameter"],
    "internals_allowance_pct": ["internals_allowance_pct", "internals allowance (%)",
                                "internals_allowance", "internals allowance",
                                "allowance (%)", "allowance_pct", "internals (%)"],
    "corrosion":               ["corrosion", "corrosive", "corrosive service",
                                "corrosion service"],
    "weld_efficiency":         ["weld_efficiency", "weld efficiency", "weld_eff",
                                "weld eff", "joint efficiency", "e"],
    "n_units":                 ["n_units", "n units", "number of units", "units",
                                "quantity", "qty", "count"],
}

# Build reverse lookup: alias → canonical
_ALIAS_TO_CANONICAL = {}
for canonical, aliases in COLUMN_ALIASES.items():
    for alias in aliases:
        _ALIAS_TO_CANONICAL[alias] = canonical


# ── Unit conversion (mirrors app.py helpers, kept here for independence) ──────
def _to_kelvin(value, unit):
    u = unit.strip().lower()
    if u == "k":             return float(value)
    if u in ("°c", "c"):    return float(value) + 273.15
    if u in ("°f", "f"):    return (float(value) - 32) * 5/9 + 273.15
    raise ValueError(f"Unknown temperature unit '{unit}'. Use K, °C, or °F.")

def _to_fahrenheit(value, unit):
    u = unit.strip().lower()
    if u in ("°f", "f"):    return float(value)
    if u in ("°c", "c"):    return float(value) * 9/5 + 32
    if u == "k":             return (float(value) - 273.15) * 9/5 + 32
    raise ValueError(f"Unknown temperature unit '{unit}'. Use K, °C, or °F.")

def _to_pascal_abs(value, unit):
    u = unit.strip().lower()
    if u == "pa":   return float(value)
    if u == "bar":  return float(value) * 1e5
    if u == "atm":  return float(value) * 101325.0
    if u == "psi":  return float(value) / 0.000145038
    raise ValueError(f"Unknown pressure unit '{unit}'. Use Pa, bar, atm, or psi.")

def _to_psig(value, unit):
    u = unit.strip().lower()
    if u == "psig": return float(value)
    if u == "barg": return float(value) * 14.5038
    if u == "atg":  return float(value) * 14.6959
    raise ValueError(f"Unknown design pressure unit '{unit}'. Use psig, barg, or atg.")


# ── Column normalisation ──────────────────────────────────────────────────────
def normalise_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Rename DataFrame columns to canonical names using case-insensitive alias
    matching. Returns (renamed_df, list_of_unrecognised_columns).
    """
    warnings = []
    rename_map = {}
    for col in df.columns:
        key = col.strip().lower()
        if key in _ALIAS_TO_CANONICAL:
            rename_map[col] = _ALIAS_TO_CANONICAL[key]
        else:
            warnings.append(f"Column '{col}' was not recognised and will be ignored.")
    return df.rename(columns=rename_map), warnings


def _get(row, col, default=None):
    """Safely get a value from a row dict, returning default if missing or NaN."""
    val = row.get(col, default)
    if val is None:
        return default
    try:
        if math.isnan(float(val)):
            return default
    except (TypeError, ValueError):
        pass
    return val


# ── Single-row processing ─────────────────────────────────────────────────────
def process_row(row: dict, row_num: int) -> tuple[dict | None, str | None]:
    """
    Parse one CSV row dict (with canonical column names) and call the engine.
    Returns (result_dict, None) on success or (None, error_message) on failure.
    """
    try:
        # ── Name ─────────────────────────────────────────────────────────────
        name = str(_get(row, "name", f"Row-{row_num}")).strip()

        # ── Material ─────────────────────────────────────────────────────────
        material_raw = _get(row, "material")
        if material_raw is None:
            return None, f"Row {row_num} ({name}): 'material' is required."
        material = str(material_raw).strip()
        if material not in VALID_MATERIALS:
            return None, (f"Row {row_num} ({name}): material '{material}' not recognised. "
                          f"Valid options: {', '.join(sorted(VALID_MATERIALS))}.")

        # ── Configuration ────────────────────────────────────────────────────
        config_raw = _get(row, "configuration")
        if config_raw is None:
            return None, f"Row {row_num} ({name}): 'configuration' is required."
        configuration = str(config_raw).strip().lower()
        if configuration not in VALID_CONFIG:
            return None, (f"Row {row_num} ({name}): configuration '{configuration}' not recognised. "
                          f"Use 'vertical' or 'horizontal'.")

        # ── Temperature ──────────────────────────────────────────────────────
        temp_val_raw = _get(row, "temperature_value")
        if temp_val_raw is None:
            return None, f"Row {row_num} ({name}): 'temperature_value' is required."
        try:
            temp_val = float(temp_val_raw)
        except ValueError:
            return None, f"Row {row_num} ({name}): temperature_value '{temp_val_raw}' is not a number."

        temp_unit = str(_get(row, "temperature_unit", "K")).strip()
        temp_input = str(_get(row, "temperature_input", "operating")).strip().lower()
        if temp_input not in VALID_TEMP_INPUT:
            return None, (f"Row {row_num} ({name}): temperature_input '{temp_input}' not recognised. "
                          f"Use 'operating' or 'design'.")

        if temp_input == "operating":
            T_op_K         = _to_kelvin(temp_val, temp_unit)
            T_d_F_override = None
        else:
            T_d_F_override = _to_fahrenheit(temp_val, temp_unit)
            T_op_K         = _to_kelvin(temp_val, temp_unit)  # nominal; engine uses override

        # ── Pressure ─────────────────────────────────────────────────────────
        press_val_raw = _get(row, "pressure_value")
        if press_val_raw is None:
            return None, f"Row {row_num} ({name}): 'pressure_value' is required."
        try:
            press_val = float(press_val_raw)
        except ValueError:
            return None, f"Row {row_num} ({name}): pressure_value '{press_val_raw}' is not a number."

        press_unit  = str(_get(row, "pressure_unit",  "Pa")).strip()
        press_input = str(_get(row, "pressure_input", "operating")).strip().lower()
        if press_input not in VALID_PRESS_INPUT:
            return None, (f"Row {row_num} ({name}): pressure_input '{press_input}' not recognised. "
                          f"Use 'operating' or 'design'.")

        if press_input == "operating":
            P_op_Pa           = _to_pascal_abs(press_val, press_unit)
            P_d_psig_override = None
        else:
            P_d_psig_override = _to_psig(press_val, press_unit)
            P_op_Pa           = 101325.0  # nominal placeholder

        # ── Geometry ─────────────────────────────────────────────────────────
        volume_raw = _get(row, "volume_m3")
        length_raw = _get(row, "length_m")
        diam_raw   = _get(row, "diameter_m")

        has_volume = volume_raw is not None
        has_ld     = (length_raw is not None) and (diam_raw is not None)

        if not has_volume and not has_ld:
            return None, (f"Row {row_num} ({name}): geometry is required. "
                          f"Provide either 'volume_m3' or both 'length_m' and 'diameter_m'.")
        if has_volume and has_ld:
            return None, (f"Row {row_num} ({name}): provide either 'volume_m3' OR "
                          f"'length_m'+'diameter_m', not both.")

        try:
            if has_volume:
                volume  = float(volume_raw)
                L_input = D_input = None
                internals_allowance_pct = 0.0  # not applicable when V given directly
            else:
                L_input = float(length_raw)
                D_input = float(diam_raw)
                volume  = None
                internals_pct_raw = _get(row, "internals_allowance_pct", 0.0)
                internals_allowance_pct = float(internals_pct_raw)
        except ValueError as e:
            return None, f"Row {row_num} ({name}): geometry value error — {e}."

        # ── Corrosion ─────────────────────────────────────────────────────────
        corrosion_raw = str(_get(row, "corrosion", "no")).strip().lower()
        if corrosion_raw not in VALID_CORROSION:
            return None, (f"Row {row_num} ({name}): corrosion '{corrosion_raw}' not recognised. "
                          f"Use 'yes' or 'no'.")
        corrosion = corrosion_raw == "yes"

        # ── Weld efficiency ───────────────────────────────────────────────────
        weld_raw = _get(row, "weld_efficiency", 1.0)
        try:
            weld_eff = float(weld_raw)
        except ValueError:
            return None, f"Row {row_num} ({name}): weld_efficiency '{weld_raw}' is not a number."
        if weld_eff not in VALID_WELD_EFF:
            return None, (f"Row {row_num} ({name}): weld_efficiency {weld_eff} not valid. "
                          f"Use 1.0, 0.85, or 0.70.")

        # ── Number of units ───────────────────────────────────────────────────
        n_units_raw = _get(row, "n_units", 1)
        try:
            n_units = int(float(n_units_raw))
        except ValueError:
            return None, f"Row {row_num} ({name}): n_units '{n_units_raw}' is not a number."
        if n_units < 1:
            return None, f"Row {row_num} ({name}): n_units must be ≥ 1."

        # ── Apply internals allowance (L&D mode only) ─────────────────────────
        if L_input is not None and D_input is not None and internals_allowance_pct > 0.0:
            V_geometric = math.pi / 4 * D_input**2 * L_input
            V_inflated  = V_geometric * (1 + internals_allowance_pct / 100.0)
            call_volume, call_L, call_D = V_inflated, None, None
        else:
            V_geometric = None
            V_inflated  = None
            call_volume, call_L, call_D = volume, L_input, D_input

        # ── Engine call ───────────────────────────────────────────────────────
        r = design_pressure_vessel(
            T_op_K=T_op_K, P_op_Pa=P_op_Pa,
            material=material, configuration=configuration,
            corrosion=corrosion, weld_efficiency=weld_eff,
            volume=call_volume, L=call_L, D=call_D,
            n_units=n_units, name=name,
            T_d_F_override=T_d_F_override,
            P_d_psig_override=P_d_psig_override,
        )

        # Restore original L and D if provided (internals allowance logic)
        if L_input is not None and D_input is not None:
            r['D_m'] = D_input
            r['L_m'] = L_input

        r['internals_allowance_pct'] = internals_allowance_pct
        r['V_geometric_m3']          = V_geometric
        r['V_inflated_m3']           = V_inflated

        return r, None

    except ValueError as e:
        return None, f"Row {row_num}: {e}"
    except Exception as e:
        return None, f"Row {row_num}: unexpected error — {e}"


# ── Batch runner ──────────────────────────────────────────────────────────────
def run_batch(df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    """
    Process a full DataFrame (already column-normalised).
    Returns:
        results : list of engine result dicts (successful rows)
        errors  : list of {'row': int, 'name': str, 'message': str}
    """
    results = []
    errors  = []
    for i, row in enumerate(df.to_dict(orient="records"), start=2):  # row 2 = first data row
        name = str(row.get("name", f"Row-{i}")).strip()
        result, err = process_row(row, row_num=i)
        if result is not None:
            results.append(result)
        else:
            errors.append({"Row": i, "Name": name, "Error": err})
    return results, errors


# ── Template CSV generator ────────────────────────────────────────────────────
TEMPLATE_ROWS = [
    {
        "name":                    "PV-001",
        "material":                "CS_A515",
        "configuration":           "vertical",
        "temperature_value":       303.15,
        "temperature_unit":        "K",
        "temperature_input":       "operating",
        "pressure_value":          101325,
        "pressure_unit":           "Pa",
        "pressure_input":          "operating",
        "volume_m3":               133.31,
        "length_m":                "",
        "diameter_m":              "",
        "internals_allowance_pct": 0,
        "corrosion":               "yes",
        "weld_efficiency":         0.85,
        "n_units":                 1,
    },
    {
        "name":                    "PV-002",
        "material":                "SS304",
        "configuration":           "vertical",
        "temperature_value":       30,
        "temperature_unit":        "°C",
        "temperature_input":       "operating",
        "pressure_value":          1.5,
        "pressure_unit":           "bar",
        "pressure_input":          "operating",
        "volume_m3":               "",
        "length_m":                10.0,
        "diameter_m":              2.5,
        "internals_allowance_pct": 15,
        "corrosion":               "no",
        "weld_efficiency":         1.0,
        "n_units":                 3,
    },
    {
        "name":                    "PV-003",
        "material":                "CS_A285",
        "configuration":           "horizontal",
        "temperature_value":       250,
        "temperature_unit":        "°F",
        "temperature_input":       "design",
        "pressure_value":          50,
        "pressure_unit":           "psig",
        "pressure_input":          "design",
        "volume_m3":               50.0,
        "length_m":                "",
        "diameter_m":              "",
        "internals_allowance_pct": 0,
        "corrosion":               "yes",
        "weld_efficiency":         0.70,
        "n_units":                 2,
    },
]

def make_template_csv() -> str:
    """Return a CSV string of the template with three example rows."""
    return pd.DataFrame(TEMPLATE_ROWS).to_csv(index=False)


# ── Results → export DataFrame ────────────────────────────────────────────────
def results_to_export_df(results: list[dict]) -> pd.DataFrame:
    """Convert a list of engine result dicts to the standard export DataFrame."""
    from pressure_vessel import m_to_ft
    rows = []
    for v in results:
        rows.append({
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
    return pd.DataFrame(rows)
