import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

import rclpy
from ddrone_msgs.msg import Alert, Detection, DroneTelemetry, MissionState
from rclpy.node import Node


from rail_inspection_report.report_templates import enrich_alert, label_phase, render_html, render_markdown


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
        base = {
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
        return enrich_alert(base)

    def _summary(self) -> Dict:
        mission = self.latest_mission
        telemetry = self.latest_telemetry
        phase = mission.phase if mission else "UNKNOWN"
        summary = {
            "started_at_utc": self.started_at.isoformat(),
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "mission_phase": phase,
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
        summary["mission_phase_label"] = label_phase(phase)
        return summary

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
            handle.write(render_markdown(payload))
        with open(html_path, "w", encoding="utf-8") as handle:
            handle.write(render_html(payload))

    def _markdown(self, payload: Dict) -> str:
        return render_markdown(payload)

    def _html(self, payload: Dict) -> str:
        return render_html(payload)


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