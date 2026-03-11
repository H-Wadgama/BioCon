"""
calculate_vessels.py — Batch Pressure Vessel Weight Calculator (CLI)
─────────────────────────────────────────────────────────────────────
Reads a CSV of vessel inputs, calculates weights using the ASME BPV
Code VIII Div.1 methodology, and writes a results CSV.

Usage:
    python calculate_vessels.py input.csv
    python calculate_vessels.py input.csv --output results.csv
    python calculate_vessels.py input.csv --template   # generate a blank template

Requirements:
    pip install pandas
    pressure_vessel.py and batch.py must be in the same directory.
"""

import sys
import argparse
import pathlib
import pandas as pd
from batch import normalise_columns, run_batch, make_template_csv, results_to_export_df


def main():
    parser = argparse.ArgumentParser(
        description="Batch pressure vessel weight estimator (ASME BPV Code VIII Div.1)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python calculate_vessels.py vessels.csv
  python calculate_vessels.py vessels.csv --output my_results.csv
  python calculate_vessels.py --template              # writes vessel_template.csv
  python calculate_vessels.py --template --output my_template.csv
        """
    )
    parser.add_argument(
        "input", nargs="?",
        help="Path to input CSV file"
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help="Path for output CSV (default: <input_stem>_results.csv)"
    )
    parser.add_argument(
        "--template", "-t", action="store_true",
        help="Generate a blank input template CSV and exit"
    )
    args = parser.parse_args()

    # ── Template mode ─────────────────────────────────────────────────────────
    if args.template:
        out_path = pathlib.Path(args.output) if args.output else pathlib.Path("vessel_template.csv")
        out_path.write_text(make_template_csv())
        print(f"✅  Template written to: {out_path}")
        print("    Fill in your vessel data and run:")
        print(f"    python calculate_vessels.py {out_path}")
        sys.exit(0)

    # ── Input validation ──────────────────────────────────────────────────────
    if args.input is None:
        parser.print_help()
        sys.exit(1)

    input_path = pathlib.Path(args.input)
    if not input_path.exists():
        print(f"❌  File not found: {input_path}", file=sys.stderr)
        sys.exit(1)
    if input_path.suffix.lower() != ".csv":
        print(f"❌  Expected a .csv file, got: {input_path.suffix}", file=sys.stderr)
        sys.exit(1)

    # ── Default output path ───────────────────────────────────────────────────
    if args.output:
        output_path = pathlib.Path(args.output)
    else:
        output_path = input_path.with_name(input_path.stem + "_results.csv")

    # ── Read CSV ──────────────────────────────────────────────────────────────
    print(f"\n📂  Reading: {input_path}")
    try:
        df_raw = pd.read_csv(input_path)
    except Exception as e:
        print(f"❌  Could not read CSV: {e}", file=sys.stderr)
        sys.exit(1)

    if df_raw.empty:
        print("❌  CSV file has no data rows.", file=sys.stderr)
        sys.exit(1)

    print(f"    {len(df_raw)} row(s) found")

    # ── Normalise columns ─────────────────────────────────────────────────────
    df_norm, col_warnings = normalise_columns(df_raw)
    if col_warnings:
        print(f"\n⚠️   {len(col_warnings)} unrecognised column(s) — these will be ignored:")
        for w in col_warnings:
            print(f"    • {w}")

    # ── Run batch ─────────────────────────────────────────────────────────────
    print("\n⚙️   Processing vessels…")
    results, errors = run_batch(df_norm)

    # ── Print error report ────────────────────────────────────────────────────
    if errors:
        print(f"\n❌  {len(errors)} row(s) skipped due to errors:")
        for e in errors:
            print(f"    Row {e['Row']} ({e['Name']}): {e['Error']}")

    # ── Print success summary ─────────────────────────────────────────────────
    if not results:
        print("\n❌  No vessels could be processed. Check errors above.", file=sys.stderr)
        sys.exit(1)

    grand_kg      = sum(v["W_total_all_units_lb"] * 0.453592 for v in results)
    grand_t       = grand_kg / 1000
    n_units_total = sum(v["n_units"] for v in results)

    print(f"\n✅  {len(results)} vessel(s) processed successfully")
    print(f"    Total units:        {n_units_total}")
    print(f"    Grand total weight: {grand_kg:,.0f} kg  ({grand_t:,.1f} t)")

    # ── Write results CSV ─────────────────────────────────────────────────────
    df_export = results_to_export_df(results)
    try:
        df_export.to_csv(output_path, index=False)
    except Exception as e:
        print(f"\n❌  Could not write output CSV: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\n💾  Results written to: {output_path}")

    # ── Per-vessel summary in terminal ────────────────────────────────────────
    print("\n" + "─" * 72)
    print(f"{'Name':<12} {'Material':<32} {'t (in)':<10} {'W/unit (kg)':<14} {'Units':<6} {'Total (kg)'}")
    print("─" * 72)
    for v in results:
        w_unit_kg = v["W_total_lb"] * 0.453592
        w_all_kg  = v["W_total_all_units_lb"] * 0.453592
        print(
            f"{v['name']:<12} "
            f"{v['material']:<32} "
            f"{v['t_total_in']:<10.4f} "
            f"{w_unit_kg:<14,.0f} "
            f"{v['n_units']:<6} "
            f"{w_all_kg:,.0f}"
        )
    print("─" * 72)
    print(f"{'GRAND TOTAL':<56} {n_units_total:<6} {grand_kg:,.0f}")
    print()


if __name__ == "__main__":
    main()
