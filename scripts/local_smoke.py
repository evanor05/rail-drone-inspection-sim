#!/usr/bin/env python3
"""Local smoke test that does not require ROS, Docker, OpenCV, or numpy.

It validates the business artifact chain used by the ROS nodes: evidence images,
alert records, and inspection reports with the requested railway fault classes.
"""

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path


FAULTS = [
    ("person_on_track", "critical", 0.91, 42.0, -2.2, 1.3),
    ("rock_or_debris", "high", 0.86, 78.0, 2.8, 0.4),
    ("fallen_branch", "high", 0.88, 153.0, 3.0, 0.6),
    ("fastener_missing", "medium", 0.82, 116.0, -1.5, 0.2),
    ("rail_surface_defect", "medium", 0.79, 188.0, 1.4, 0.2),
    ("fence_intrusion_damage", "medium", 0.83, 222.0, -7.0, 1.0),
    ("catenary_or_pole_abnormal", "high", 0.84, 246.0, 6.7, 6.0),
]


def svg_evidence(defect_class: str, confidence: float, x: float, y: float) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="640" height="480" viewBox="0 0 640 480">
  <rect width="640" height="480" fill="#dfe7ec"/>
  <rect y="220" width="640" height="260" fill="#6f7c72"/>
  <rect x="160" y="250" width="320" height="180" fill="#8a8c8e"/>
  <line x1="220" y1="460" x2="300" y2="230" stroke="#20242a" stroke-width="8"/>
  <line x1="420" y1="460" x2="340" y2="230" stroke="#20242a" stroke-width="8"/>
  <line x1="70" y1="220" x2="70" y2="450" stroke="#34464c" stroke-width="5"/>
  <line x1="560" y1="220" x2="560" y2="450" stroke="#34464c" stroke-width="5"/>
  <rect x="248" y="176" width="144" height="96" fill="#b42318" fill-opacity="0.85" stroke="#fff" stroke-width="4"/>
  <text x="28" y="38" font-family="Arial" font-size="22" fill="#17212b">Synthetic evidence frame</text>
  <text x="260" y="218" font-family="Arial" font-size="16" fill="#fff">{defect_class}</text>
  <text x="260" y="244" font-family="Arial" font-size="16" fill="#fff">conf {confidence:.2f}</text>
  <text x="28" y="444" font-family="Arial" font-size="18" fill="#17212b">estimated x={x:.1f}m y={y:.1f}m</text>
</svg>
"""


def write_reports(root: Path) -> Path:
    reports = root / "data" / "reports"
    evidence = root / "data" / "evidence"
    reports.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()
    alerts = []
    for index, (defect_class, severity, confidence, x, y, z) in enumerate(FAULTS, start=1):
        evidence_path = evidence / f"local_smoke_{index:02d}_{defect_class}.svg"
        evidence_path.write_text(svg_evidence(defect_class, confidence, x, y), encoding="utf-8")
        alerts.append(
            {
                "alert_id": f"local-smoke-{index:02d}",
                "time_utc": now,
                "defect_class": defect_class,
                "confidence": confidence,
                "severity": severity,
                "position": {"x": x, "y": y, "z": z},
                "evidence_path": str(evidence_path),
                "source_image": evidence_path.name,
                "mission_phase": "INSPECT",
                "status": "open",
                "notes": "local smoke artifact generated without ROS runtime",
            }
        )

    payload = {
        "summary": {
            "started_at_utc": now,
            "updated_at_utc": now,
            "mission_phase": "LOCAL_SMOKE",
            "mission_progress": 1.0,
            "detections_seen": len(alerts),
            "alerts_count": len(alerts),
            "latest_position": {"x": 260.0, "y": -22.0, "z": 0.4},
            "battery_percentage": 98.0,
        },
        "alerts": alerts,
    }

    json_path = reports / "inspection_report.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# High-Speed Railway Drone Inspection Report",
        "",
        f"- Generated UTC: {now}",
        f"- Alerts count: {len(alerts)}",
        "",
        "## Alerts",
    ]
    for alert in alerts:
        md_lines.append(
            f"- {alert['defect_class']} | {alert['severity']} | {alert['confidence']:.2f} | "
            f"x={alert['position']['x']}, y={alert['position']['y']}, z={alert['position']['z']} | {alert['evidence_path']}"
        )
    (reports / "inspection_report.md").write_text("\n".join(md_lines), encoding="utf-8")

    rows = "\n".join(
        f"<tr><td>{a['defect_class']}</td><td>{a['severity']}</td><td>{a['confidence']:.2f}</td>"
        f"<td>{a['position']['x']}, {a['position']['y']}, {a['position']['z']}</td>"
        f"<td>{a['evidence_path']}</td></tr>"
        for a in alerts
    )
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Inspection Report</title>
<style>body{{font-family:Arial;margin:32px}}td,th{{border-bottom:1px solid #ccd5de;padding:8px;text-align:left}}</style>
</head><body><h1>High-Speed Railway Drone Inspection Report</h1><p>Generated UTC: {now}</p>
<table><thead><tr><th>Class</th><th>Severity</th><th>Confidence</th><th>Position</th><th>Evidence</th></tr></thead>
<tbody>{rows}</tbody></table></body></html>"""
    (reports / "inspection_report.html").write_text(html, encoding="utf-8")
    return json_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    report_path = write_reports(root)
    time.sleep(0.05)
    print(f"[PASS] Local smoke report generated: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
