import math
import os
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from ddrone_msgs.msg import DroneTelemetry
from geometry_msgs.msg import Point
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image, Imu, NavSatFix
from std_msgs.msg import Header

from .fault_catalog import CLASS_COLORS_BGR, FAULT_CLASSES


@dataclass
class SyntheticFault:
    defect_class: str
    kp_m: float
    lateral_m: float
    bbox: Tuple[int, int, int, int]
    confidence: float


DEFAULT_FAULTS = [
    SyntheticFault("person_on_track", 42.0, -2.0, (316, 214, 358, 296), 0.91),
    SyntheticFault("rock_or_debris", 78.0, 2.4, (413, 310, 466, 346), 0.86),
    SyntheticFault("fastener_missing", 116.0, -1.55, (248, 360, 282, 386), 0.82),
    SyntheticFault("fallen_branch", 153.0, 3.0, (382, 255, 492, 294), 0.88),
    SyntheticFault("rail_surface_defect", 188.0, 1.45, (357, 338, 420, 362), 0.79),
    SyntheticFault("fence_intrusion_damage", 222.0, -7.0, (104, 244, 174, 330), 0.83),
    SyntheticFault("catenary_or_pole_abnormal", 246.0, 6.7, (488, 92, 548, 232), 0.84),
]


class SyntheticScenePublisher(Node):
    """Publishes deterministic railway inspection imagery for offline and CI acceptance."""

    def __init__(self) -> None:
        super().__init__("synthetic_scene_publisher")
        self.declare_parameter("front_topic", "/dri/camera/front/image_raw")
        self.declare_parameter("down_topic", "/dri/camera/down/image_raw")
        self.declare_parameter("width", 640)
        self.declare_parameter("height", 480)
        self.declare_parameter("fps", 8.0)
        self.declare_parameter("camera_frame", "front_camera_optical")
        self.declare_parameter("save_reference_frames", True)

        self.width = int(self.get_parameter("width").value)
        self.height = int(self.get_parameter("height").value)
        fps = float(self.get_parameter("fps").value)
        self.camera_frame = str(self.get_parameter("camera_frame").value)
        self.bridge = CvBridge()
        self.frame_index = 0
        self.start_time = time.monotonic()
        self.latest_telemetry: Optional[DroneTelemetry] = None

        self.front_pub = self.create_publisher(Image, str(self.get_parameter("front_topic").value), 10)
        self.down_pub = self.create_publisher(Image, str(self.get_parameter("down_topic").value), 10)
        self.info_pub = self.create_publisher(CameraInfo, "/dri/camera/front/camera_info", 10)
        self.imu_pub = self.create_publisher(Imu, "/dri/imu", 20)
        self.gps_pub = self.create_publisher(NavSatFix, "/dri/gps/fix", 10)
        self.telemetry_sub = self.create_subscription(DroneTelemetry, "/dri/drone/telemetry", self._on_telemetry, 10)
        self.timer = self.create_timer(1.0 / max(1.0, fps), self._publish)

        self.evidence_dir = os.environ.get("DRI_EVIDENCE_DIR", "/workspace/data/evidence")
        os.makedirs(self.evidence_dir, exist_ok=True)

    def _on_telemetry(self, msg: DroneTelemetry) -> None:
        self.latest_telemetry = msg

    def _header(self, frame_id: str) -> Header:
        header = Header()
        header.stamp = self.get_clock().now().to_msg()
        header.frame_id = frame_id
        return header

    def _publish(self) -> None:
        progress_m = self._progress_m()
        front, visible_faults = self._render_front(progress_m)
        down = self._render_down(progress_m)

        front_msg = self.bridge.cv2_to_imgmsg(front, encoding="bgr8")
        front_msg.header = self._header(self.camera_frame)
        # Attach compact metadata for the fallback detector. ROS Image has no custom field,
        # so the detector also uses visual markers and the mission telemetry.
        self.front_pub.publish(front_msg)

        down_msg = self.bridge.cv2_to_imgmsg(down, encoding="bgr8")
        down_msg.header = self._header("down_camera_optical")
        self.down_pub.publish(down_msg)
        self.info_pub.publish(self._camera_info(front_msg.header))
        self.imu_pub.publish(self._imu(front_msg.header))
        self.gps_pub.publish(self._gps(front_msg.header, progress_m))

        if self.frame_index % 40 == 0 and visible_faults:
            path = os.path.join(self.evidence_dir, f"synthetic_reference_{self.frame_index:05d}.jpg")
            cv2.imwrite(path, front)
        self.frame_index += 1

    def _progress_m(self) -> float:
        if self.latest_telemetry:
            return max(0.0, float(self.latest_telemetry.pose.position.x))
        elapsed = time.monotonic() - self.start_time
        return (elapsed * 4.0) % 265.0

    def _render_front(self, progress_m: float) -> Tuple[np.ndarray, List[SyntheticFault]]:
        img = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        img[:] = (185, 205, 220)
        horizon = int(self.height * 0.38)
        cv2.rectangle(img, (0, horizon), (self.width, self.height), (80, 125, 80), -1)
        cv2.rectangle(img, (0, horizon + 72), (self.width, self.height), (72, 72, 78), -1)

        vanishing = (self.width // 2, horizon + 5)
        rail_offsets = [-88, -42, 42, 88]
        for offset in rail_offsets:
            lower = (self.width // 2 + int(offset * 2.3), self.height)
            upper = (vanishing[0] + int(offset * 0.15), vanishing[1])
            cv2.line(img, lower, upper, (35, 35, 36), 5)
            cv2.line(img, lower, upper, (170, 170, 170), 2)

        for i in range(18):
            y = self.height - i * 22 - int(progress_m % 22)
            if y < horizon + 25:
                continue
            scale = (y - horizon) / max(1, self.height - horizon)
            half = int(132 * scale + 12)
            x1 = self.width // 2 - half
            x2 = self.width // 2 + half
            cv2.line(img, (x1, y), (x2, y), (115, 115, 118), max(1, int(5 * scale)))

        for side in [-1, 1]:
            base_x = 82 if side < 0 else self.width - 82
            for i in range(8):
                y = horizon + 20 + i * 42 - int((progress_m * 0.55) % 42)
                if y < horizon or y > self.height:
                    continue
                h = int(88 * ((y - horizon) / (self.height - horizon)) + 22)
                x = int(base_x + side * math.sin(i * 0.7) * 7)
                cv2.line(img, (x, y), (x, max(horizon, y - h)), (45, 65, 70), 4)
                cv2.line(img, (x, y - h + 10), (self.width // 2, horizon + 10), (35, 45, 48), 1)

        # Tunnel portal / viaduct cues near the end of the corridor.
        if progress_m > 210:
            tunnel_scale = min(1.0, (progress_m - 210) / 40.0)
            top = int(horizon - 18 * tunnel_scale)
            left = int(236 - 42 * tunnel_scale)
            right = int(404 + 42 * tunnel_scale)
            cv2.rectangle(img, (left, top), (right, horizon + 82), (62, 64, 70), 14)
            cv2.ellipse(img, (self.width // 2, horizon + 82), ((right - left) // 2, 92), 180, 0, 180, (50, 50, 55), 14)

        cv2.putText(img, f"KP {progress_m/1000.0:.3f} km", (18, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20, 30, 35), 2)
        visible = []
        for fault in DEFAULT_FAULTS:
            distance = fault.kp_m - progress_m
            if -5.0 <= distance <= 32.0:
                visible.append(fault)
                self._draw_fault(img, fault, distance)
        return img, visible

    def _draw_fault(self, img: np.ndarray, fault: SyntheticFault, distance: float) -> None:
        x1, y1, x2, y2 = fault.bbox
        grow = max(0.65, min(1.8, 1.6 - distance / 40.0))
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)
        w = int((x2 - x1) * grow)
        h = int((y2 - y1) * grow)
        x1 = max(0, cx - w // 2)
        y1 = max(0, cy - h // 2)
        x2 = min(self.width - 1, cx + w // 2)
        y2 = min(self.height - 1, cy + h // 2)
        color = CLASS_COLORS_BGR.get(fault.defect_class, (0, 0, 255))

        if fault.defect_class == "person_on_track":
            cv2.circle(img, (cx, y1 + 12), 11, color, -1)
            cv2.line(img, (cx, y1 + 24), (cx, y2 - 16), color, 5)
            cv2.line(img, (cx, y1 + 40), (x1, y2), color, 4)
            cv2.line(img, (cx, y1 + 40), (x2, y2), color, 4)
        elif fault.defect_class == "fallen_branch":
            cv2.line(img, (x1, y2), (x2, y1), color, 8)
            cv2.line(img, (x1 + 18, y2 - 8), (x1 + 55, y1 + 12), color, 4)
            cv2.line(img, (x2 - 20, y1 + 10), (x2 - 65, y2 - 6), color, 4)
        elif fault.defect_class == "catenary_or_pole_abnormal":
            cv2.line(img, (cx, y1), (cx + 20, y2), color, 7)
            cv2.circle(img, (cx + 20, y2), 10, (30, 30, 30), -1)
        else:
            cv2.rectangle(img, (x1, y1), (x2, y2), color, -1)

        cv2.rectangle(img, (x1, y1), (x2, y2), (255, 255, 255), 2)
        cv2.putText(img, fault.defect_class, (x1, max(14, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (5, 5, 5), 2)

    def _render_down(self, progress_m: float) -> np.ndarray:
        img = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        img[:] = (88, 92, 88)
        cv2.rectangle(img, (0, 0), (self.width, self.height), (90, 122, 90), -1)
        slab_w = 76
        center = self.width // 2
        for lane_center in (center - 82, center + 82):
            cv2.rectangle(img, (lane_center - slab_w, 0), (lane_center + slab_w, self.height), (128, 128, 126), -1)
            cv2.line(img, (lane_center - 34, 0), (lane_center - 34, self.height), (42, 42, 42), 4)
            cv2.line(img, (lane_center + 34, 0), (lane_center + 34, self.height), (42, 42, 42), 4)
        for y in range(-20, self.height + 24, 32):
            yy = y + int((progress_m * 2.5) % 32)
            cv2.line(img, (center - 180, yy), (center + 180, yy), (100, 100, 100), 3)
        cv2.putText(img, "DOWNWARD TRACK CAMERA", (18, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (20, 20, 20), 2)
        return img

    def _camera_info(self, header: Header) -> CameraInfo:
        info = CameraInfo()
        info.header = header
        info.height = self.height
        info.width = self.width
        fx = fy = 520.0
        cx = self.width / 2.0
        cy = self.height / 2.0
        info.k = [fx, 0.0, cx, 0.0, fy, cy, 0.0, 0.0, 1.0]
        info.p = [fx, 0.0, cx, 0.0, 0.0, fy, cy, 0.0, 0.0, 0.0, 1.0, 0.0]
        info.distortion_model = "plumb_bob"
        info.d = [0.0, 0.0, 0.0, 0.0, 0.0]
        return info

    def _imu(self, header: Header) -> Imu:
        imu = Imu()
        imu.header = header
        imu.header.frame_id = "base_link"
        imu.orientation.w = 1.0
        imu.angular_velocity.z = 0.005 * math.sin(self.frame_index * 0.05)
        imu.linear_acceleration.z = 9.81
        return imu

    def _gps(self, header: Header, progress_m: float) -> NavSatFix:
        gps = NavSatFix()
        gps.header = header
        gps.header.frame_id = "gps_link"
        gps.latitude = 34.275 + progress_m / 111_000.0
        gps.longitude = 108.945 + 0.00002 * math.sin(progress_m / 70.0)
        gps.altitude = 420.0 + (self.latest_telemetry.altitude_m if self.latest_telemetry else 8.0)
        gps.position_covariance_type = NavSatFix.COVARIANCE_TYPE_APPROXIMATED
        gps.position_covariance = [0.04, 0.0, 0.0, 0.0, 0.04, 0.0, 0.0, 0.0, 0.09]
        return gps


def main(args: Optional[List[str]] = None) -> None:
    rclpy.init(args=args)
    node = SyntheticScenePublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
