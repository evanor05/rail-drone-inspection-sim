from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    dashboard_port = LaunchConfiguration("dashboard_port")
    model_path = LaunchConfiguration("model_path")
    use_px4_offboard = LaunchConfiguration("use_px4_offboard")
    mission_profile_path = LaunchConfiguration("mission_profile_path")
    scenario_path = LaunchConfiguration("scenario_path")

    return LaunchDescription(
        [
            DeclareLaunchArgument("dashboard_port", default_value="8080"),
            DeclareLaunchArgument("model_path", default_value="/workspace/data/models/rail_defects.pt"),
            DeclareLaunchArgument("use_px4_offboard", default_value="false"),
            DeclareLaunchArgument("mission_profile_path", default_value="/workspace/data/missions/default_corridor_profile.json"),
            DeclareLaunchArgument("scenario_path", default_value="/workspace/data/scenarios/default_synthetic_faults.json"),
            Node(
                package="rail_inspection_control",
                executable="mission_manager",
                output="screen",
                parameters=[
                    {
                        "use_px4_offboard": use_px4_offboard,
                        "simulate_state": True,
                        "mission_profile_path": mission_profile_path,
                    }
                ],
            ),
            Node(
                package="rail_inspection_control",
                executable="runtime_info_publisher",
                output="screen",
                parameters=[
                    {
                        "mode": "offline_demo",
                        "mission_profile_path": mission_profile_path,
                        "scenario_path": scenario_path,
                        "model_dir": "/workspace/data/models",
                    }
                ],
            ),
            Node(
                package="rail_inspection_perception",
                executable="synthetic_scene_publisher",
                output="screen",
                parameters=[{"fps": 8.0, "scenario_path": scenario_path}],
            ),
            Node(
                package="rail_inspection_perception",
                executable="yolo_detector",
                output="screen",
                parameters=[{"model_path": model_path, "fallback_enabled": True}],
            ),
            Node(
                package="rail_inspection_report",
                executable="report_generator",
                output="screen",
            ),
            Node(
                package="rail_inspection_dashboard",
                executable="web_dashboard",
                output="screen",
                additional_env={"DRI_DASHBOARD_PORT": dashboard_port},
            ),
        ]
    )
