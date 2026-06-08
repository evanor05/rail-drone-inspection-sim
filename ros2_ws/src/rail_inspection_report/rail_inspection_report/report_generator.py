import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

import rclpy
from ddrone_msgs.msg import Alert, Detection, DroneTelemetry, MissionState
from rclpy.node import Node


class ReportGenerator(Node):
    """Persists alerts and produces machine-readable plus human-readable reports."""

    def __init__(self) -> None:
        super().__init__("report_generator")
        self.declare_parameter("report_interval_seconds", 5.0)
        self.report_dir = os.environ.get("DRI_REPORT_DIR", "/workspace/data/reports")
        os.makedirs(self.report_dir, exist_ok=True)

        self.alerts: List[Dict] = []
        self.detections_seen = 0
        self.latest_telemetry: Optional[DroneTelemetry] = None
        self.latest_mission: Optional[MissionState] = None
        self.started_at = datetime.now(timezone.utc)
        self.last_write = 0.0

        self.alert_sub = self.create_subscription(Alert, "/dri/alerts", self._on_alert, 50)
        self.detection_sub = self.create_subscription(Detection, "/dri/detections", self._on_detection, 50)
        self.telemetry_sub = self.create_subscription(DroneTelemetry, "/dri/drone/telemetry", self._on_telemetry, 20)
        self.mission_sub = self.create_subscription(MissionState, "/dri/mission/state", self._on_mission, 20)
        self.timer = self.create_timer(float(self.get_parameter("report_interval_seconds").value), self.write_reports)

    def _on_alert(self, msg: Alert) -> None:
        if any(alert["alert_id"] == msg.alert_id for alert in self.alerts):
            return
        self.alerts.append(self._alert_to_dict(msg))
        self.write_reports()

    def _on_detection(self, _msg: Detection) -> None:
        self.detections_seen += 1

    def _on_telemetry(self, msg: DroneTelemetry) -> None:
        self.latest_telemetry = msg

    def _on_mission(self, msg: MissionState) -> None:
        self.latest_mission = msg

    def _alert_to_dict(self, msg: Alert) -> Dict:
        return {
            "alert_id": msg.alert_id,
            "time_ros": {"sec": msg.header.stamp.sec, "nanosec": msg.header.stamp.nanosec},
            "time_utc": datetime.now(timezone.utc).isoformat(),
            "defect_class": msg.defect_class,
            "confidence": round(float(msg.confidence), 4),
            "severity": msg.severity,
            "position": {
                "x": round(float(msg.pose.position.x), 3),
                "y": round(float(msg.pose.position.y), 3),
                "z": round(float(msg.pose.position.z), 3),
            },
            "evidence_path": msg.evidence_path,
            "source_image": msg.source_image,
            "mission_phase": msg.mission_phase,
            "status": msg.status,
            "notes": msg.notes,
        }

    def _summary(self) -> Dict:
        mission = self.latest_mission
        telemetry = self.latest_telemetry
        return {
            "started_at_utc": self.started_at.isoformat(),
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "mission_phase": mission.phase if mission else "UNKNOWN",
            "mission_progress": round(float(mission.progress), 3) if mission else 0.0,
            "detections_seen": self.detections_seen,
            "alerts_count": len(self.alerts),
            "latest_position": {
                "x": round(float(telemetry.pose.position.x), 3) if telemetry else 0.0,
                "y": round(float(telemetry.pose.position.y), 3) if telemetry else 0.0,
                "z": round(float(telemetry.pose.position.z), 3) if telemetry else 0.0,
            },
            "battery_percentage": round(float(telemetry.battery_percentage), 2) if telemetry else None,
        }

    def write_reports(self) -> None:
        now = time.monotonic()
        if now - self.last_write < 0.5:
            return
        self.last_write = now
        payload = {
            "summary": self._summary(),
            "alerts": self.alerts,
        }
        json_path = os.path.join(self.report_dir, "inspection_report.json")
        md_path = os.path.join(self.report_dir, "inspection_report.md")
        html_path = os.path.join(self.report_dir, "inspection_report.html")
        with open(json_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        with open(md_path, "w", encoding="utf-8") as handle:
            handle.write(self._markdown(payload))
        with open(html_path, "w", encoding="utf-8") as handle:
            handle.write(self._html(payload))

    def _markdown(self, payload: Dict) -> str:
        summary = payload["summary"]
        lines = [
            "# High-Speed Railway Drone Inspection Report",
            "",
            f"- Started UTC: {summary['started_at_utc']}",
            f"- Updated UTC: {summary['updated_at_utc']}",
            f"- Mission phase: {summary['mission_phase']}",
            f"- Mission progress: {summary['mission_progress']}",
            f"- Detections seen: {summary['detections_seen']}",
            f"- Alerts count: {summary['alerts_count']}",
            "",
            "## Alerts",
            "",
        ]
        if not payload["alerts"]:
            lines.append("No alerts recorded yet.")
        for alert in payload["alerts"]:
            lines.extend(
                [
                    f"### {alert['defect_class']} ({alert['severity']})",
                    f"- Alert ID: {alert['alert_id']}",
                    f"- Time UTC: {alert['time_utc']}",
                    f"- Confidence: {alert['confidence']}",
                    f"- Position: x={alert['position']['x']}, y={alert['position']['y']}, z={alert['position']['z']}",
                    f"- Mission phase: {alert['mission_phase']}",
                    f"- Evidence: {alert['evidence_path']}",
                    f"- Notes: {alert['notes']}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _html(self, payload: Dict) -> str:
        summary = payload["summary"]
        rows = []
        for alert in payload["alerts"]:
            evidence = alert["evidence_path"]
            evidence_html = f"<a href='file://{evidence}'>{os.path.basename(evidence)}</a>" if evidence else ""
            rows.append(
                "<tr>"
                f"<td>{alert['time_utc']}</td>"
                f"<td>{alert['defect_class']}</td>"
                f"<td>{alert['severity']}</td>"
                f"<td>{alert['confidence']:.2f}</td>"
                f"<td>{alert['position']['x']}, {alert['position']['y']}, {alert['position']['z']}</td>"
                f"<td>{alert['mission_phase']}</td>"
                f"<td>{evidence_html}</td>"
                "</tr>"
            )
        rows_html = "\n".join(rows) if rows else "<tr><td colspan='7'>No alerts recorded yet.</td></tr>"
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Drone Rail Inspection Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2933; }}
    h1 {{ margin-bottom: 8px; }}
    .summary {{ display: grid; grid-template-columns: repeat(4, minmax(140px, 1fr)); gap: 12px; margin: 20px 0; }}
    .metric {{ border: 1px solid #d7dde5; padding: 12px; border-radius: 6px; background: #f8fafc; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border-bottom: 1px solid #d7dde5; padding: 9px; text-align: left; font-size: 14px; }}
    th {{ background: #eef2f6; }}
  </style>
</head>
<body>
  <h1>High-Speed Railway Drone Inspection Report</h1>
  <p>Started UTC: {summary['started_at_utc']} | Updated UTC: {summary['updated_at_utc']}</p>
  <section class="summary">
    <div class="metric"><strong>Mission phase</strong><br>{summary['mission_phase']}</div>
    <div class="metric"><strong>Progress</strong><br>{summary['mission_progress']}</div>
    <div class="metric"><strong>Detections</strong><br>{summary['detections_seen']}</div>
    <div class="metric"><strong>Alerts</strong><br>{summary['alerts_count']}</div>
  </section>
  <table>
    <thead><tr><th>Time</th><th>Class</th><th>Severity</th><th>Confidence</th><th>Position</th><th>Phase</th><th>Evidence</th></tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
</body>
</html>"""


def main(args: Optional[List[str]] = None) -> None:
    rclpy.init(args=args)
    node = ReportGenerator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.write_reports()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
