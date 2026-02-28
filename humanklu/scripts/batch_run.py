#!/usr/bin/env python3
"""
HumanKlu™ Batch Runner — HKP v1.1
Runs pipeline.py for every *.json file in an input directory,
then produces batch_run/summary.json and batch_run/summary.csv.

Usage:
    python scripts/batch_run.py --inputs ./inputs --output ./batch_run
"""

import argparse
import csv
import json
import sys
from pathlib import Path

# Allow importing pipeline from the same scripts/ directory
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from pipeline import run_pipeline


def run_batch(inputs_dir: str, output_dir: str) -> None:
    inputs_path = Path(inputs_dir)
    output_path = Path(output_dir)
    runs_path   = output_path / "runs"
    runs_path.mkdir(parents=True, exist_ok=True)

    input_files = sorted(inputs_path.glob("*.json"))
    if not input_files:
        print(f"⚠  No *.json files found in {inputs_path}")
        sys.exit(1)

    print(f"\n🔬 HumanKlu™ Batch Runner — {len(input_files)} input(s)\n")

    run_records = []
    level_counts: dict[str, int] = {}

    for inp_file in input_files:
        run_id_stem = inp_file.stem            # e.g. "01_rejected"
        run_out     = runs_path / run_id_stem
        print(f"── {inp_file.name} ──────────────────────────────────")
        try:
            result = run_pipeline(str(inp_file), str(run_out))
        except Exception as exc:
            print(f"  ✗ ERROR: {exc}")
            result = {
                "report_id":           "ERROR",
                "certification_level": "ERROR",
                "hci":                 None,
                "evid_raw":            None,
                "evid_effective":      None,
                "inferred_ratio":      None,
                "flags":               [str(exc)],
            }

        # Load title from input file for summary
        try:
            title = json.loads(inp_file.read_text()).get("title", inp_file.stem)
        except Exception:
            title = inp_file.stem

        rec = {
            "run_id":              run_id_stem,
            "input_file":          inp_file.name,
            "title":               title,
            "report_id":           result.get("report_id"),
            "certification_level": result.get("certification_level"),
            "hci":                 result.get("hci"),
            "evid_effective":      result.get("evid_effective"),
            "inferred_ratio":      result.get("inferred_ratio"),
            "flags":               result.get("flags", []),
        }
        run_records.append(rec)

        level = result.get("certification_level", "ERROR")
        level_counts[level] = level_counts.get(level, 0) + 1

        print()

    # ── Aggregate metrics ─────────────────────────────────────────
    total = len(run_records)
    valid = [r for r in run_records if r["hci"] is not None]

    avg_hci            = round(sum(r["hci"] for r in valid) / len(valid), 3)            if valid else None
    avg_evid_effective = round(sum(r["evid_effective"] for r in valid) / len(valid), 3) if valid else None
    avg_inferred_ratio = round(sum(r["inferred_ratio"] for r in valid) / len(valid), 4) if valid else None

    summary = {
        "total_runs":          total,
        "counts_by_level":     level_counts,
        "avg_hci":             avg_hci,
        "avg_evid_effective":  avg_evid_effective,
        "avg_inferred_ratio":  avg_inferred_ratio,
        "runs":                run_records,
    }

    # ── summary.json ──────────────────────────────────────────────
    summary_json_path = output_path / "summary.json"
    summary_json_path.write_text(json.dumps(summary, indent=2))
    print(f"✓ summary.json  → {summary_json_path}")

    # ── summary.csv ───────────────────────────────────────────────
    summary_csv_path = output_path / "summary.csv"
    csv_fields = [
        "run_id", "input_file", "title", "report_id",
        "certification_level", "hci", "evid_effective",
        "inferred_ratio", "flags",
    ]
    with open(summary_csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for r in run_records:
            row = {k: r.get(k) for k in csv_fields}
            row["flags"] = "|".join(r.get("flags", []))
            writer.writerow(row)
    print(f"✓ summary.csv   → {summary_csv_path}")

    # ── Console summary ───────────────────────────────────────────
    print(f"\n{'═'*55}")
    print(f"  Batch complete: {total} runs")
    print(f"  avg HCI:            {avg_hci}")
    print(f"  avg EVID_effective: {avg_evid_effective}")
    print(f"  avg inferred_ratio: {avg_inferred_ratio}")
    print(f"  Level distribution:")
    for lvl in ["HK-INSTITUTIONAL", "HK-PRO", "HK-VERIFIED", "HK-REVIEWED", "HK-REJECTED", "ERROR"]:
        n = level_counts.get(lvl, 0)
        if n:
            print(f"    {lvl:<22} {n}")
    print(f"{'═'*55}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HumanKlu™ Batch Runner HKP v1.1")
    parser.add_argument("--inputs", required=True, help="Directory containing input JSON files")
    parser.add_argument("--output", required=True, help="Output directory (batch_run/)")
    args = parser.parse_args()
    run_batch(args.inputs, args.output)
