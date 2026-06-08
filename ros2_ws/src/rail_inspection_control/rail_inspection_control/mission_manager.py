import math
import time
import uuid
from dataclasses import dataclass
from typing import List, Optional, Tuple

import rclpy
from ddrone_msgs.msg import Alert, DroneTelemetry, MissionState
from geometry_msgs.msg import Point, Pose, PoseStamped, Quaternion, Twist, Vector3
from nav_msgs.msg import Path
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Header, String
from visualization_msgs.msg import Marker, MarkerArray

try:
    from px4_msgs.msg import (
        OffboardControlMode,
        TrajectorySetpoint,
        VehicleCommand,
        VehicleLocalPosition,
        VehicleStatus,
    )

    PX4_MSGS_AVAILABLE = True
except Exception:  # pragma: no cover - optional runtime dependency
    OffboardControlMode = None
    TrajectorySetpoint = None
    VehicleCommand = None
    VehicleLocalPosition = None
    VehicleStatus = None
    PX4_MSGS_AVAILABLE = False


@dataclass(frozen=True)
class Waypoint:
    name: str
    x: float
    y: float
    z: float
    speed: float
    phase: str


def _yaw_to_quaternion(yaw: float) -> Quaternion:
    q = Quaternion()
    q.z = math.sin(yaw * 0.5)
    q.w = math.cos(yaw * 0.5)
    return q


def _distance(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


class MissionManager(Node):
    """Rule-based first-stage inspection policy with optional PX4 offboard output."""

    def __init__(self) -> None:
        super().__init__("mission_manager")

        self.declare_parameter("use_px4_offboard", True)
        self.declare_parameter("simulate_state", True)
        self.declare_parameter("home_x", 0.0)
        self.declare_parameter("home_y", -22.0)
        self.declare_parameter("cruise_altitude_m", 9.0)
        self.declare_parameter("corridor_y", 0.0)
        self.declare_parameter("track_length_m", 260.0)
        self.declare_parameter("alert_pause_seconds", 7.0)

        self.use_px4_offboard = _as_bool(self.get_parameter("use_px4_offboard").value)
        self.simulate_state = _as_bool(self.get_parameter("simulate_state").value)
        home_x = float(self.get_parameter("home_x").value)
        home_y = float(self.get_parameter("home_y").value)
        cruise_alt = float(self.get_parameter("cruise_altitude_m").value)
        corridor_y = float(self.get_parameter("corridor_y").value)
        track_length = float(self.get_parameter("track_length_m").value)

        self.waypoints: List[Waypoint] = [
            Waypoint("takeoff", home_x, home_y, cruise_alt, 2.0, "TAKEOFF"),
            Waypoint("enter_corridor", 20.0, corridor_y, cruise_alt, 3.0, "ENTER_CORRIDOR"),
            Waypoint("inspect_kp_000_060", 60.0, corridor_y, cruise_alt, 4.0, "INSPECT"),
            Waypoint("inspect_kp_000_120", 120.0, corridor_y, cruise_alt, 4.0, "INSPECT"),
            Waypoint("inspect_kp_000_180", 180.0, corridor_y, cruise_alt, 4.0, "INSPECT"),
            Waypoint("inspect_kp_000_240", track_length - 20.0, corridor_y + 4.0, cruise_alt, 4.0, "INSPECT"),
            Waypoint("turn_back", track_length - 10.0, -12.0, cruise_alt, 3.0, "RETURN"),
            Waypoint("home_approach", home_x + 10.0, home_y, cruise_alt, 3.0, "RETURN"),
            Waypoint("land", home_x, home_y, 0.4, 1.0, "LAND"),
        ]

        self.current_position = [home_x, home_y, 0.2]
        self.current_velocity = [0.0, 0.0, 0.0]
        self.current_wp_index = 0
        self.phase = "INIT"
        self.last_tick = time.monotonic()
        self.mission_started = time.monotonic()
        self.reinspection_until = 0.0
        self.active_alert: Optional[Alert] = None
        self.alert_history: List[str] = []
        self.offboard_sequence = 0
        self.px4_status = None
        self.last_px4_state_time = 0.0

        self.telemetry_pub = self.create_publisher(DroneTelemetry, "/dri/drone/telemetry", 10)
        self.mission_pub = self.create_publisher(MissionState, "/dri/mission/state", 10)
        self.setpoint_pub = self.create_publisher(PoseStamped, "/dri/offboard/setpoint", 10)
        self.phase_event_pub = self.create_publisher(String, "/dri/mission/events", 10)
        self.path_pub = self.create_publisher(Path, "/dri/mission/path", 10)
        self.marker_pub = self.create_publisher(MarkerArray, "/dri/mission/markers", 10)
        self.alert_sub = self.create_subscription(Alert, "/dri/alerts", self._on_alert, 20)

        self.px4_offboard_pub = None
        self.px4_setpoint_pub = None
        self.px4_command_pub = None
        if self.use_px4_offboard and PX4_MSGS_AVAILABLE:
            px4_out_qos = QoSProfile(
                reliability=ReliabilityPolicy.BEST_EFFORT,
                durability=DurabilityPolicy.VOLATILE,
                history=HistoryPolicy.KEEP_LAST,
                depth=10,
            )
            self.px4_offboard_pub = self.create_publisher(OffboardControlMode, "/fmu/in/offboard_control_mode", 10)
            self.px4_setpoint_pub = self.create_publisher(TrajectorySetpoint, "/fmu/in/trajectory_setpoint", 10)
            self.px4_command_pub = self.create_publisher(VehicleCommand, "/fmu/in/vehicle_command", 10)
            self.create_subscription(
                VehicleLocalPosition, "/fmu/out/vehicle_local_position", self._on_px4_local_position, px4_out_qos
            )
            self.create_subscription(VehicleStatus, "/fmu/out/vehicle_status", self._on_px4_status, px4_out_qos)
            self.get_logger().info("PX4 offboard publishers enabled.")
        elif self.use_px4_offboard:
            self.get_logger().warn("px4_msgs are not sourced; publishing generic /dri/offboard/setpoint only.")

        self.timer = self.create_timer(0.1, self._tick)
        self._publish_static_markers()

    def _header(self, frame_id: str = "map") -> Header:
        header = Header()
        header.stamp = self.get_clock().now().to_msg()
        header.frame_id = frame_id
        return header

    def _on_alert(self, msg: Alert) -> None:
        if msg.alert_id in self.alert_history:
            return
        self.alert_history.append(msg.alert_id)
        self.active_alert = msg
        self.reinspection_until = time.monotonic() + float(self.get_parameter("alert_pause_seconds").value)
        self.phase = "REINSPECT"
        event = String()
        event.data = f"reinspection_started:{msg.alert_id}:{msg.defect_class}:{msg.confidence:.2f}"
        self.phase_event_pub.publish(event)
        self.get_logger().warn(
            f"Alert {msg.alert_id} {msg.defect_class} confidence={msg.confidence:.2f}; slowing for reinspection."
        )

    def _on_px4_local_position(self, msg) -> None:
        if self.simulate_state:
            return
        self.current_position = [float(msg.x), float(msg.y), float(-msg.z)]
        self.current_velocity = [float(msg.vx), float(msg.vy), float(-msg.vz)]
        self.last_px4_state_time = time.monotonic()

    def _on_px4_status(self, msg) -> None:
        self.px4_status = msg

    def _tick(self) -> None:
        now = time.monotonic()
        dt = max(0.02, min(0.25, now - self.last_tick))
        self.last_tick = now

        if now < self.reinspection_until and self.active_alert is not None:
            target = self._reinspection_target(self.active_alert)
            speed_scale = 0.25
        else:
            self.active_alert = None
            target_wp = self.waypoints[self.current_wp_index]
            target = (target_wp.x, target_wp.y, target_wp.z, target_wp.phase)
            speed_scale = 1.0

        if self.simulate_state:
            self._advance_simulated_state(target, dt, speed_scale)
        elif self.use_px4_offboard and PX4_MSGS_AVAILABLE and time.monotonic() - self.last_px4_state_time > 5.0:
            self.get_logger().warn(
                "Waiting for /fmu/out/vehicle_local_position from PX4 uXRCE-DDS bridge.",
                throttle_duration_sec=5.0,
            )

        self._update_waypoint_progress()
        self._publish_setpoint(target)
        self._publish_px4_setpoint(target)
        self._publish_telemetry()
        self._publish_mission_state()
        self._publish_path()

    def _reinspection_target(self, alert: Alert) -> Tuple[float, float, float, str]:
        x = alert.pose.position.x - 5.0
        y = alert.pose.position.y - 3.0
        z = max(5.0, min(9.0, alert.pose.position.z + 4.0))
        return (x, y, z, "REINSPECT")

    def _advance_simulated_state(self, target: Tuple[float, float, float, str], dt: float, speed_scale: float) -> None:
        tx, ty, tz, _phase = target
        current = tuple(self.current_position)
        target_xyz = (tx, ty, tz)
        dist = _distance(current, target_xyz)
        wp_speed = self.waypoints[min(self.current_wp_index, len(self.waypoints) - 1)].speed
        max_step = max(0.15, wp_speed * speed_scale * dt)
        if dist < 0.01:
            self.current_velocity = [0.0, 0.0, 0.0]
            return

        ratio = min(1.0, max_step / dist)
        previous = self.current_position[:]
        self.current_position[0] += (tx - self.current_position[0]) * ratio
        self.current_position[1] += (ty - self.current_position[1]) * ratio
        self.current_position[2] += (tz - self.current_position[2]) * ratio
        self.current_velocity = [
            (self.current_position[0] - previous[0]) / dt,
            (self.current_position[1] - previous[1]) / dt,
            (self.current_position[2] - previous[2]) / dt,
        ]

    def _update_waypoint_progress(self) -> None:
        if self.active_alert is not None:
            return
        wp = self.waypoints[self.current_wp_index]
        if _distance(tuple(self.current_position), (wp.x, wp.y, wp.z)) < 1.2:
            if self.current_wp_index < len(self.waypoints) - 1:
                self.current_wp_index += 1
                next_phase = self.waypoints[self.current_wp_index].phase
                if next_phase != self.phase:
                    self.phase = next_phase
                    event = String()
                    event.data = f"phase:{self.phase}:wp={self.current_wp_index}"
                    self.phase_event_pub.publish(event)
            else:
                self.phase = "COMPLETE"
        else:
            self.phase = wp.phase if self.phase != "REINSPECT" else self.phase

    def _publish_setpoint(self, target: Tuple[float, float, float, str]) -> None:
        pose = PoseStamped()
        pose.header = self._header()
        pose.pose.position.x = float(target[0])
        pose.pose.position.y = float(target[1])
        pose.pose.position.z = float(target[2])
        pose.pose.orientation = _yaw_to_quaternion(0.0)
        self.setpoint_pub.publish(pose)

    def _publish_px4_setpoint(self, target: Tuple[float, float, float, str]) -> None:
        if not (self.use_px4_offboard and PX4_MSGS_AVAILABLE and self.px4_offboard_pub and self.px4_setpoint_pub):
            return

        timestamp = int(self.get_clock().now().nanoseconds / 1000)
        offboard = OffboardControlMode()
        offboard.timestamp = timestamp
        offboard.position = True
        offboard.velocity = False
        offboard.acceleration = False
        offboard.attitude = False
        offboard.body_rate = False
        self.px4_offboard_pub.publish(offboard)

        setpoint = TrajectorySetpoint()
        setpoint.timestamp = timestamp
        # PX4 local NED: x north, y east, z down. The project map uses ENU-like x-forward/y-left/z-up.
        setpoint.position = [float(target[0]), float(target[1]), -float(target[2])]
        setpoint.yaw = 0.0
        self.px4_setpoint_pub.publish(setpoint)

        if self.offboard_sequence in (20, 25) and self.px4_command_pub:
            command = VehicleCommand()
            command.timestamp = timestamp
            command.param1 = 1.0
            command.param2 = 6.0
            command.command = VehicleCommand.VEHICLE_CMD_DO_SET_MODE
            command.target_system = 1
            command.target_component = 1
            command.source_system = 1
            command.source_component = 1
            command.from_external = True
            self.px4_command_pub.publish(command)
        if self.offboard_sequence == 30 and self.px4_command_pub:
            command = VehicleCommand()
            command.timestamp = timestamp
            command.param1 = 1.0
            command.command = VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM
            command.target_system = 1
            command.target_component = 1
            command.source_system = 1
            command.source_component = 1
            command.from_external = True
            self.px4_command_pub.publish(command)
        self.offboard_sequence += 1

    def _publish_telemetry(self) -> None:
        msg = DroneTelemetry()
        msg.header = self._header()
        msg.pose.position = Point(x=self.current_position[0], y=self.current_position[1], z=self.current_position[2])
        yaw = math.atan2(self.current_velocity[1], self.current_velocity[0]) if any(self.current_velocity[:2]) else 0.0
        msg.pose.orientation = _yaw_to_quaternion(yaw)
        msg.velocity = Twist(linear=Vector3(x=self.current_velocity[0], y=self.current_velocity[1], z=self.current_velocity[2]))
        elapsed = max(0.0, time.monotonic() - self.mission_started)
        msg.battery_percentage = max(20.0, 100.0 - elapsed * 0.015)
        msg.nav_state = self._nav_state_label()
        msg.armed = self._is_armed()
        msg.offboard_available = self.use_px4_offboard and PX4_MSGS_AVAILABLE
        msg.ground_speed_mps = math.sqrt(self.current_velocity[0] ** 2 + self.current_velocity[1] ** 2)
        msg.altitude_m = self.current_position[2]
        self.telemetry_pub.publish(msg)

    def _nav_state_label(self) -> str:
        if self.px4_status is None or VehicleStatus is None:
            return self.phase
        nav_state = int(getattr(self.px4_status, "nav_state", -1))
        labels = {
            getattr(VehicleStatus, "NAVIGATION_STATE_MANUAL", -100): "PX4_MANUAL",
            getattr(VehicleStatus, "NAVIGATION_STATE_ALTCTL", -101): "PX4_ALTCTL",
            getattr(VehicleStatus, "NAVIGATION_STATE_POSCTL", -102): "PX4_POSCTL",
            getattr(VehicleStatus, "NAVIGATION_STATE_AUTO_MISSION", -103): "PX4_AUTO_MISSION",
            getattr(VehicleStatus, "NAVIGATION_STATE_AUTO_LOITER", -104): "PX4_AUTO_LOITER",
            getattr(VehicleStatus, "NAVIGATION_STATE_AUTO_RTL", -105): "PX4_AUTO_RTL",
            getattr(VehicleStatus, "NAVIGATION_STATE_OFFBOARD", -106): "PX4_OFFBOARD",
        }
        return f"{self.phase}:{labels.get(nav_state, f'PX4_NAV_{nav_state}')}"

    def _is_armed(self) -> bool:
        if self.px4_status is None or VehicleStatus is None:
            return self.phase not in ("INIT", "COMPLETE")
        return int(getattr(self.px4_status, "arming_state", -1)) == int(
            getattr(VehicleStatus, "ARMING_STATE_ARMED", 2)
        )

    def _publish_mission_state(self) -> None:
        msg = MissionState()
        msg.header = self._header()
        msg.phase = self.phase
        msg.progress = float(self.current_wp_index) / float(max(1, len(self.waypoints) - 1))
        msg.active_target = self.waypoints[self.current_wp_index].name
        msg.paused_for_reinspection = self.active_alert is not None
        msg.waypoint_index = self.current_wp_index
        msg.total_waypoints = len(self.waypoints)
        msg.summary = f"{self.phase} {self.current_wp_index + 1}/{len(self.waypoints)} alerts={len(self.alert_history)}"
        self.mission_pub.publish(msg)

    def _publish_path(self) -> None:
        path = Path()
        path.header = self._header()
        for wp in self.waypoints:
            pose = PoseStamped()
            pose.header = path.header
            pose.pose.position.x = wp.x
            pose.pose.position.y = wp.y
            pose.pose.position.z = wp.z
            pose.pose.orientation = _yaw_to_quaternion(0.0)
            path.poses.append(pose)
        self.path_pub.publish(path)

    def _publish_static_markers(self) -> None:
        markers = MarkerArray()
        for i, wp in enumerate(self.waypoints):
            marker = Marker()
            marker.header = self._header()
            marker.ns = "mission_waypoints"
            marker.id = i
            marker.type = Marker.SPHERE
            marker.action = Marker.ADD
            marker.pose = Pose()
            marker.pose.position.x = wp.x
            marker.pose.position.y = wp.y
            marker.pose.position.z = wp.z
            marker.scale.x = 1.2
            marker.scale.y = 1.2
            marker.scale.z = 1.2
            marker.color.a = 0.9
            marker.color.r = 0.1
            marker.color.g = 0.6
            marker.color.b = 1.0
            markers.markers.append(marker)

            label = Marker()
            label.header = marker.header
            label.ns = "mission_labels"
            label.id = 100 + i
            label.type = Marker.TEXT_VIEW_FACING
            label.action = Marker.ADD
            label.pose = Pose()
            label.pose.position.x = wp.x
            label.pose.position.y = wp.y
            label.pose.position.z = wp.z + 1.8
            label.scale.z = 1.0
            label.color.a = 1.0
            label.color.r = 1.0
            label.color.g = 1.0
            label.color.b = 1.0
            label.text = wp.name
            markers.markers.append(label)
        self.marker_pub.publish(markers)


def main(args: Optional[List[str]] = None) -> None:
    rclpy.init(args=args)
    node = MissionManager()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
