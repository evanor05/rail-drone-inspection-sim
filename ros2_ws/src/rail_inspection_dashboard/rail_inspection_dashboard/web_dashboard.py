import base64
import json
import os
import threading
import time
from typing import Dict, List, Optional

import cv2
import numpy as np
import rclpy
import uvicorn
from cv_bridge import CvBridge
from ddrone_msgs.msg import Alert, Detection, DroneTelemetry, MissionState
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String


class DashboardState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.telemetry: Optional[Dict] = None
        self.mission: Optional[Dict] = None
        self.detections: List[Dict] = []
        self.alerts: List[Dict] = []
        self.runtime: Optional[Dict] = None
        self.last_image_jpeg_b64: Optional[str] = None
        self.started_at = time.time()

    def snapshot(self) -> Dict:
        with self.lock:
            return {
                "uptime_seconds": round(time.time() - self.started_at, 1),
                "telemetry": self.telemetry,
                "mission": self.mission,
                "detections": self.detections[-30:],
                "alerts": self.alerts[-100:],
                "runtime": self.runtime,
                "last_image_jpeg_b64": self.last_image_jpeg_b64,
            }


STATE = DashboardState()


class DashboardBridge(Node):
    def __init__(self) -> None:
        super().__init__("web_dashboard_bridge")
        self.bridge = CvBridge()
        self.create_subscription(DroneTelemetry, "/dri/drone/telemetry", self._on_telemetry, 20)
        self.create_subscription(MissionState, "/dri/mission/state", self._on_mission, 20)
        self.create_subscription(Detection, "/dri/detections", self._on_detection, 50)
        self.create_subscription(Alert, "/dri/alerts", self._on_alert, 50)
        self.create_subscription(Image, "/dri/perception/debug_image", self._on_image, 5)
        self.create_subscription(String, "/dri/runtime/info", self._on_runtime_info, 10)

    def _on_telemetry(self, msg: DroneTelemetry) -> None:
        with STATE.lock:
            STATE.telemetry = {
                "stamp": msg.header.stamp.sec + msg.header.stamp.nanosec / 1e9,
                "position": {
                    "x": round(float(msg.pose.position.x), 2),
                    "y": round(float(msg.pose.position.y), 2),
                    "z": round(float(msg.pose.position.z), 2),
                },
                "ground_speed_mps": round(float(msg.ground_speed_mps), 2),
                "altitude_m": round(float(msg.altitude_m), 2),
                "battery_percentage": round(float(msg.battery_percentage), 1),
                "nav_state": msg.nav_state,
                "armed": bool(msg.armed),
                "offboard_available": bool(msg.offboard_available),
            }

    def _on_mission(self, msg: MissionState) -> None:
        with STATE.lock:
            STATE.mission = {
                "phase": msg.phase,
                "progress": round(float(msg.progress), 3),
                "active_target": msg.active_target,
                "paused_for_reinspection": bool(msg.paused_for_reinspection),
                "waypoint_index": int(msg.waypoint_index),
                "total_waypoints": int(msg.total_waypoints),
                "summary": msg.summary,
            }

    def _on_detection(self, msg: Detection) -> None:
        record = {
            "id": msg.detection_id,
            "class": msg.defect_class,
            "confidence": round(float(msg.confidence), 3),
            "bbox": [int(msg.xmin), int(msg.ymin), int(msg.xmax), int(msg.ymax)],
            "position": {
                "x": round(float(msg.estimated_position.x), 2),
                "y": round(float(msg.estimated_position.y), 2),
                "z": round(float(msg.estimated_position.z), 2),
            },
            "track_side": msg.track_side,
        }
        with STATE.lock:
            STATE.detections.append(record)
            STATE.detections = STATE.detections[-200:]

    def _on_alert(self, msg: Alert) -> None:
        record = {
            "id": msg.alert_id,
            "class": msg.defect_class,
            "confidence": round(float(msg.confidence), 3),
            "severity": msg.severity,
            "position": {
                "x": round(float(msg.pose.position.x), 2),
                "y": round(float(msg.pose.position.y), 2),
                "z": round(float(msg.pose.position.z), 2),
            },
            "evidence_path": msg.evidence_path,
            "mission_phase": msg.mission_phase,
            "status": msg.status,
            "notes": msg.notes,
        }
        with STATE.lock:
            if all(existing["id"] != record["id"] for existing in STATE.alerts):
                STATE.alerts.append(record)
                STATE.alerts = STATE.alerts[-200:]

    def _on_image(self, msg: Image) -> None:
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 78])
        if not ok:
            return
        with STATE.lock:
            STATE.last_image_jpeg_b64 = base64.b64encode(encoded.tobytes()).decode("ascii")

    def _on_runtime_info(self, msg: String) -> None:
        try:
            runtime = json.loads(msg.data)
        except json.JSONDecodeError:
            runtime = {"raw": msg.data, "parse_error": "invalid JSON"}
        with STATE.lock:
            STATE.runtime = runtime


def create_app(static_dir: str, report_dir: str) -> FastAPI:
    app = FastAPI(title="Drone Rail Inspection Dashboard")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def index():
        index_path = os.path.join(static_dir, "index.html")
        return FileResponse(index_path)

    @app.get("/api/status")
    async def status():
        return JSONResponse(STATE.snapshot())

    @app.get("/api/alerts")
    async def alerts():
        return JSONResponse(STATE.snapshot()["alerts"])

    @app.get("/api/reports")
    async def reports():
        files = []
        if os.path.isdir(report_dir):
            for name in sorted(os.listdir(report_dir)):
                path = os.path.join(report_dir, name)
                if os.path.isfile(path):
                    files.append({"name": name, "path": path, "size": os.path.getsize(path)})
        return JSONResponse(files)

    @app.get("/api/report/json")
    async def report_json():
        path = os.path.join(report_dir, "inspection_report.json")
        if not os.path.exists(path):
            return JSONResponse({"summary": {}, "alerts": []})
        with open(path, "r", encoding="utf-8") as handle:
            return JSONResponse(json.load(handle))

    @app.get("/reports/{name}")
    async def report_file(name: str):
        allowed = {"inspection_report.json", "inspection_report.md", "inspection_report.html"}
        if name not in allowed:
            return JSONResponse({"error": "not found"}, status_code=404)
        path = os.path.join(report_dir, name)
        if not os.path.exists(path):
            return JSONResponse({"error": "not generated yet"}, status_code=404)
        return FileResponse(path)

    return app


def ros_spin_thread(node: DashboardBridge) -> None:
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    finally:
        executor.shutdown()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = DashboardBridge()
    thread = threading.Thread(target=ros_spin_thread, args=(node,), daemon=True)
    thread.start()

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if not os.path.exists(os.path.join(static_dir, "index.html")):
        # Installed packages place static files under share; fallback for editable source runs.
        static_dir = os.path.abspath(os.path.join(os.getcwd(), "ros2_ws/src/rail_inspection_dashboard/rail_inspection_dashboard/static"))
    report_dir = os.environ.get("DRI_REPORT_DIR", "/workspace/data/reports")
    app = create_app(static_dir=static_dir, report_dir=report_dir)
    port = int(os.environ.get("DRI_DASHBOARD_PORT", "8080"))
    try:
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
