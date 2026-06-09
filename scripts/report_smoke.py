#!/usr/bin/env python3
import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_MODULE = ROOT / "ros2_ws/src/rail_inspection_report/rail_inspection_report/report_templates.py"


def load_report_module():
    spec = importlib.util.spec_from_file_location("report_generator", REPORT_MODULE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a standalone Chinese report smoke artifact.")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "data",
        help="Output root containing reports/ and evidence/ directories. Defaults to project data/.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    module = load_report_module()
    output_root = args.output_root.resolve()
    out_dir = output_root / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir = output_root / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = evidence_dir / "report_smoke_person_on_track.txt"
    evidence_path.write_text("synthetic report smoke evidence", encoding="utf-8")
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "summary": {
            "started_at_utc": now,
            "updated_at_utc": now,
            "mission_phase": "REINSPECT",
            "mission_progress": 0.25,
            "detections_seen": 12,
            "alerts_count": 1,
            "latest_position": {"x": 42.0, "y": -2.0, "z": 6.5},
            "battery_percentage": 97.5,
        },
        "alerts": [
            {
                "alert_id": "report-smoke-001",
                "time_utc": now,
                "defect_class": "person_on_track",
                "confidence": 0.91,
                "severity": "critical",
                "position": {"x": 42.0, "y": -2.2, "z": 1.3},
                "evidence_path": str(evidence_path),
                "source_image": "report_smoke",
                "mission_phase": "REINSPECT",
                "status": "open",
                "notes": "report smoke test",
            }
        ],
    }
    enriched = module.enrich_payload(payload)
    json_path = out_dir / "inspection_report_smoke.json"
    md_path = out_dir / "inspection_report_smoke.md"
    html_path = out_dir / "inspection_report_smoke.html"
    json_path.write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8")
    md = module.render_markdown(payload)
    html = module.render_html(payload)
    md_path.write_text(md, encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")
    required_terms = ["高铁无人机巡检报告", "轨道上人员", "严重", "异常复查", "证据路径"]
    missing = [term for term in required_terms if term not in md + html]
    if missing:
        print(f"[FAIL] Report smoke missing terms: {missing}")
        return 1
    print(f"[PASS] Chinese report smoke generated: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
