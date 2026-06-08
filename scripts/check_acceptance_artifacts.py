#!/usr/bin/env python3
import argparse
import json
import os
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="data/reports/inspection_report.json")
    parser.add_argument("--min-alerts", type=int, default=1)
    args = parser.parse_args()

    if not os.path.exists(args.report):
        print(f"[FAIL] Report not found: {args.report}", file=sys.stderr)
        return 2
    with open(args.report, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    alerts = payload.get("alerts", [])
    summary = payload.get("summary", {})
    if len(alerts) < args.min_alerts:
        print(f"[FAIL] Expected at least {args.min_alerts} alerts, got {len(alerts)}", file=sys.stderr)
        return 3
    missing_evidence = [a for a in alerts if a.get("evidence_path") and not os.path.exists(a["evidence_path"])]
    if missing_evidence:
        print(f"[FAIL] Evidence files missing: {missing_evidence[:3]}", file=sys.stderr)
        return 4
    required_classes = {
        "person_on_track",
        "rock_or_debris",
        "fallen_branch",
        "fastener_missing",
        "rail_surface_defect",
        "fence_intrusion_damage",
        "catenary_or_pole_abnormal",
    }
    seen_classes = {a.get("defect_class") for a in alerts}
    if not (required_classes & seen_classes):
        print(f"[FAIL] No expected rail defect classes found in alerts: {seen_classes}", file=sys.stderr)
        return 5
    print("[PASS] Offline acceptance artifacts valid")
    print(json.dumps({"summary": summary, "alerts": len(alerts), "classes": sorted(seen_classes)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
