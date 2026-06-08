import json
import math
import os
import time
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from ddrone_msgs.msg import Alert, Detection, DroneTelemetry
from geometry_msgs.msg import Point, Pose
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Header

from .fault_catalog import CLASS_COLORS_BGR, FAULT_CLASSES, SEVERITY_BY_CLASS

try:
    from ultralytics import YOLO

    ULTRALYTICS_AVAILABLE = True
except Exception:  # pragma: no cover - optional runtime dependency
    YOLO = None
    ULTRALYTICS_AVAILABLE = False


@dataclass
class DetectionCandidate:
    defect_class: str
    confidence: float
    bbox: Tuple[int, int, int, int]
    source: str


class YoloDetector(Node):
    """YOLO detector with deterministic synthetic fallback for acceptance runs."""

    def __init__(self) -> None:
        super().__init__("yolo_detector")
        self.declare_parameter("image_topic", "/dri/camera/front/image_raw")
        self.declare_parameter("model_path", "/workspace/data/models/rail_defects.pt")
        self.declare_parameter("fallback_enabled", True)
        self.declare_parameter("confidence_threshold", 0.45)
        self.declare_parameter("alert_cooldown_seconds", 6.0)
        self.declare_parameter("save_evidence", True)
        self.declare_parameter("device", "auto")

        self.bridge = CvBridge()
        self.model = self._load_model()
        self.latest_telemetry: Optional[DroneTelemetry] = None
        self.last_alert_by_class: Dict[str, float] = {}
        self.evidence_dir = os.environ.get("DRI_EVIDENCE_DIR", "/workspace/data/evidence")
        os.makedirs(self.evidence_dir, exist_ok=True)

        self.detection_pub = self.create_publisher(Detection, "/dri/detections", 20)
        self.alert_pub = self.create_publisher(Alert, "/dri/alerts", 20)
        self.debug_image_pub = self.create_publisher(Image, "/dri/perception/debug_image", 10)
        self.telemetry_sub = self.create_subscription(DroneTelemetry, "/dri/drone/telemetry", self._on_telemetry, 20)
        self.image_sub = self.create_subscription(Image, str(self.get_parameter("image_topic").value), self._on_image, 10)

    def _load_model(self):
        model_path = str(self.get_parameter("model_path").value)
        if not ULTRALYTICS_AVAILABLE:
            self.get_logger().warn("ultralytics is unavailable; using synthetic fallback detector.")
            return None
        if os.path.exists(model_path):
            try:
                model = YOLO(model_path)
                self.get_logger().info(f"Loaded YOLO model: {model_path}")
                return model
            except Exception as exc:
                self.get_logger().warn(f"Failed to load YOLO model {model_path}: {exc}; using fallback.")
        else:
            alt = "/workspace/data/models/yolov8n.pt"
            if os.path.exists(alt):
                try:
                    model = YOLO(alt)
                    self.get_logger().info(f"Loaded generic YOLO model: {alt}")
                    return model
                except Exception as exc:
                    self.get_logger().warn(f"Failed to load generic YOLO model {alt}: {exc}; using fallback.")
            self.get_logger().warn(f"No YOLO weights at {model_path}; using synthetic fallback detector.")
        return None

    @staticmethod
    def _as_bool(value) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    def _on_telemetry(self, msg: DroneTelemetry) -> None:
        self.latest_telemetry = msg

    def _on_image(self, msg: Image) -> None:
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        candidates = self._infer(frame)
        debug = frame.copy()
        for candidate in candidates:
            if candidate.confidence < float(self.get_parameter("confidence_threshold").value):
                continue
            detection = self._candidate_to_detection(msg.header, candidate)
            self.detection_pub.publish(detection)
            evidence_path = ""
            if self._as_bool(self.get_parameter("save_evidence").value):
                evidence_path = self._save_evidence(frame, candidate, detection)
            if self._should_alert(candidate):
                alert = self._detection_to_alert(detection, evidence_path, candidate)
                self.alert_pub.publish(alert)
            self._draw_candidate(debug, candidate)

        debug_msg = self.bridge.cv2_to_imgmsg(debug, encoding="bgr8")
        debug_msg.header = msg.header
        self.debug_image_pub.publish(debug_msg)

    def _infer(self, frame: np.ndarray) -> List[DetectionCandidate]:
        candidates: List[DetectionCandidate] = []
        if self.model is not None:
            try:
                device = str(self.get_parameter("device").value)
                kwargs = {"verbose": False, "conf": float(self.get_parameter("confidence_threshold").value)}
                if device != "auto":
                    kwargs["device"] = device
                results = self.model.predict(frame, **kwargs)
                names = getattr(self.model, "names", {})
                for result in results:
                    for box in getattr(result, "boxes", []):
                        xyxy = box.xyxy[0].cpu().numpy().astype(int).tolist()
                        conf = float(box.conf[0].cpu().numpy())
                        cls_idx = int(box.cls[0].cpu().numpy())
                        label = str(names.get(cls_idx, f"class_{cls_idx}"))
                        mapped = self._map_model_label(label)
                        if mapped:
                            candidates.append(DetectionCandidate(mapped, conf, tuple(xyxy), "yolo"))
            except Exception as exc:
                self.get_logger().warn(f"YOLO inference failed, falling back for this frame: {exc}")

        if not candidates and self._as_bool(self.get_parameter("fallback_enabled").value):
            candidates = self._fallback_detect(frame)
        return candidates

    def _map_model_label(self, label: str) -> Optional[str]:
        normalized = label.lower().replace(" ", "_").replace("-", "_")
        if normalized in FAULT_CLASSES:
            return normalized
        aliases = {
            "person": "person_on_track",
            "backpack": "foreign_object",
            "suitcase": "foreign_object",
            "sports_ball": "foreign_object",
            "rock": "rock_or_debris",
            "tree": "fallen_branch",
            "branch": "fallen_branch",
            "pole": "catenary_or_pole_abnormal",
        }
        return aliases.get(normalized)

    def _fallback_detect(self, frame: np.ndarray) -> List[DetectionCandidate]:
        candidates: List[DetectionCandidate] = []
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        for defect_class, bgr in CLASS_COLORS_BGR.items():
            color = np.uint8([[bgr]])
            hsv_color = cv2.cvtColor(color, cv2.COLOR_BGR2HSV)[0][0]
            lower = np.array([max(0, int(hsv_color[0]) - 8), max(35, int(hsv_color[1]) - 70), max(35, int(hsv_color[2]) - 90)])
            upper = np.array([min(179, int(hsv_color[0]) + 8), min(255, int(hsv_color[1]) + 70), min(255, int(hsv_color[2]) + 90)])
            mask = cv2.inRange(hsv, lower, upper)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), dtype=np.uint8))
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < 90:
                    continue
                x, y, w, h = cv2.boundingRect(contour)
                if y < 32 and w > 60:
                    continue
                confidence = min(0.96, 0.62 + math.log10(max(area, 100.0)) * 0.08)
                candidates.append(
                    DetectionCandidate(
                        defect_class=defect_class,
                        confidence=float(confidence),
                        bbox=(x, y, x + w, y + h),
                        source="synthetic_fallback",
                    )
                )
        return self._non_max_merge(candidates)

    def _non_max_merge(self, candidates: List[DetectionCandidate]) -> List[DetectionCandidate]:
        by_class: Dict[str, List[DetectionCandidate]] = {}
        for candidate in candidates:
            by_class.setdefault(candidate.defect_class, []).append(candidate)
        merged: List[DetectionCandidate] = []
        for defect_class, items in by_class.items():
            items.sort(key=lambda item: item.confidence, reverse=True)
            kept: List[DetectionCandidate] = []
            for item in items:
                if all(self._iou(item.bbox, kept_item.bbox) < 0.35 for kept_item in kept):
                    kept.append(item)
            merged.extend(kept[:2])
        return merged

    @staticmethod
    def _iou(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> float:
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)
        inter = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)
        area_a = max(1, ax2 - ax1) * max(1, ay2 - ay1)
        area_b = max(1, bx2 - bx1) * max(1, by2 - by1)
        return inter / float(area_a + area_b - inter + 1e-6)

    def _candidate_to_detection(self, header: Header, candidate: DetectionCandidate) -> Detection:
        detection = Detection()
        detection.header = header
        detection.detection_id = str(uuid.uuid4())
        detection.defect_class = candidate.defect_class
        detection.confidence = float(candidate.confidence)
        detection.xmin, detection.ymin, detection.xmax, detection.ymax = map(int, candidate.bbox)
        detection.camera_frame = header.frame_id
        detection.track_side = self._track_side(candidate.bbox)
        detection.source_image = f"frame_time_{header.stamp.sec}_{header.stamp.nanosec}"
        detection.estimated_position = self._estimate_world_position(candidate.bbox)
        return detection

    def _track_side(self, bbox: Tuple[int, int, int, int]) -> str:
        cx = (bbox[0] + bbox[2]) / 2.0
        if cx < 260:
            return "left_corridor"
        if cx > 380:
            return "right_corridor"
        return "track_center"

    def _estimate_world_position(self, bbox: Tuple[int, int, int, int]) -> Point:
        telemetry = self.latest_telemetry
        base_x = telemetry.pose.position.x if telemetry else 0.0
        base_y = telemetry.pose.position.y if telemetry else 0.0
        base_z = telemetry.pose.position.z if telemetry else 7.0
        cx = (bbox[0] + bbox[2]) / 2.0
        cy = (bbox[1] + bbox[3]) / 2.0
        forward = max(3.0, 24.0 - (cy - 180.0) * 0.055)
        lateral = (cx - 320.0) * 0.035
        return Point(x=float(base_x + forward), y=float(base_y + lateral), z=max(0.0, float(base_z - 5.5)))

    def _save_evidence(self, frame: np.ndarray, candidate: DetectionCandidate, detection: Detection) -> str:
        annotated = frame.copy()
        self._draw_candidate(annotated, candidate)
        stamp = f"{detection.header.stamp.sec}_{detection.header.stamp.nanosec}"
        filename = f"{stamp}_{candidate.defect_class}_{detection.detection_id[:8]}.jpg"
        path = os.path.join(self.evidence_dir, filename)
        cv2.imwrite(path, annotated)
        metadata_path = os.path.splitext(path)[0] + ".json"
        with open(metadata_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "detection_id": detection.detection_id,
                    "defect_class": candidate.defect_class,
                    "confidence": candidate.confidence,
                    "bbox": candidate.bbox,
                    "source": candidate.source,
                    "estimated_position": {
                        "x": detection.estimated_position.x,
                        "y": detection.estimated_position.y,
                        "z": detection.estimated_position.z,
                    },
                },
                handle,
                ensure_ascii=False,
                indent=2,
            )
        return path

    def _should_alert(self, candidate: DetectionCandidate) -> bool:
        now = time.monotonic()
        cooldown = float(self.get_parameter("alert_cooldown_seconds").value)
        previous = self.last_alert_by_class.get(candidate.defect_class, 0.0)
        if now - previous < cooldown:
            return False
        self.last_alert_by_class[candidate.defect_class] = now
        return True

    def _detection_to_alert(self, detection: Detection, evidence_path: str, candidate: DetectionCandidate) -> Alert:
        alert = Alert()
        alert.header = detection.header
        alert.alert_id = str(uuid.uuid4())
        alert.defect_class = detection.defect_class
        alert.confidence = detection.confidence
        alert.pose = Pose()
        alert.pose.position = detection.estimated_position
        alert.pose.orientation.w = 1.0
        alert.severity = SEVERITY_BY_CLASS.get(detection.defect_class, "medium")
        alert.evidence_path = evidence_path
        alert.source_image = detection.source_image
        alert.mission_phase = self.latest_telemetry.nav_state if self.latest_telemetry else "UNKNOWN"
        alert.status = "open"
        alert.notes = f"source={candidate.source}; track_side={detection.track_side}; bbox={candidate.bbox}"
        return alert

    def _draw_candidate(self, image: np.ndarray, candidate: DetectionCandidate) -> None:
        x1, y1, x2, y2 = candidate.bbox
        color = CLASS_COLORS_BGR.get(candidate.defect_class, (0, 0, 255))
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
        label = f"{candidate.defect_class} {candidate.confidence:.2f}"
        cv2.rectangle(image, (x1, max(0, y1 - 22)), (min(image.shape[1] - 1, x1 + 9 * len(label)), y1), color, -1)
        cv2.putText(image, label, (x1 + 3, max(14, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)


def main(args: Optional[List[str]] = None) -> None:
    rclpy.init(args=args)
    node = YoloDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
