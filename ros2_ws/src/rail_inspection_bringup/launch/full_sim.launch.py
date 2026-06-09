import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    world = LaunchConfiguration("world")
    dashboard_port = LaunchConfiguration("dashboard_port")
    start_rviz = LaunchConfiguration("rviz")
    use_px4_offboard = LaunchConfiguration("use_px4_offboard")
    simulate_state = LaunchConfiguration("simulate_state")
    synthetic_camera = LaunchConfiguration("synthetic_camera")
    px4_home = LaunchConfiguration("px4_home")
    px4_model = LaunchConfiguration("px4_model")
    mission_profile_path = LaunchConfiguration("mission_profile_path")
    scenario_path = LaunchConfiguration("scenario_path")

    gazebo_share = get_package_share_directory("rail_inspection_gazebo")
    default_world = os.path.join(gazebo_share, "worlds", "high_speed_rail_corridor.sdf")
    rviz_config = PathJoinSubstitution(
        [FindPackageShare("rail_inspection_bringup"), "rviz", "rail_inspection.rviz"]
    )

    gz_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare("ros_gz_sim"), "launch", "gz_sim.launch.py"])
        ),
        launch_arguments={"gz_args": ["-r -s ", world]}.items(),
    )

    px4_process = ExecuteProcess(
        cmd=[
            "bash",
            "-lc",
            "cd \"$PX4_HOME\" && "
            "source \"$PX4_HOME/build/px4_sitl_default/rootfs/gz_env.sh\" && "
            "PX4_GZ_STANDALONE=1 "
            "PX4_SYS_AUTOSTART=4001 "
            "PX4_SIM_MODEL=\"$PX4_MODEL\" "
            "PX4_GZ_MODEL_POSE='0,-22,0.5,0,0,0' "
            "\"$PX4_HOME/build/px4_sitl_default/bin/px4\"",
        ],
        additional_env={"PX4_HOME": px4_home, "PX4_MODEL": px4_model},
        output="screen",
    )

    xrce_agent = ExecuteProcess(
        cmd=["MicroXRCEAgent", "udp4", "-p", "8888"],
        output="screen",
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("world", default_value=default_world),
            DeclareLaunchArgument("dashboard_port", default_value="8080"),
            DeclareLaunchArgument("rviz", default_value="true"),
            DeclareLaunchArgument("use_px4_offboard", default_value="true"),
            DeclareLaunchArgument("simulate_state", default_value="true"),
            DeclareLaunchArgument("synthetic_camera", default_value="true"),
            DeclareLaunchArgument("px4_home", default_value="/opt/PX4-Autopilot"),
            DeclareLaunchArgument("px4_model", default_value="gz_x500_depth"),
            DeclareLaunchArgument("mission_profile_path", default_value="/workspace/data/missions/default_corridor_profile.json"),
            DeclareLaunchArgument("scenario_path", default_value="/workspace/data/scenarios/default_synthetic_faults.json"),
            gz_launch,
            TimerAction(period=2.0, actions=[xrce_agent]),
            TimerAction(period=4.0, actions=[px4_process]),
            Node(
                package="ros_gz_bridge",
                executable="parameter_bridge",
                arguments=[
                    "/dri/gz/front_camera@sensor_msgs/msg/Image[gz.msgs.Image",
                    "/dri/gz/down_camera@sensor_msgs/msg/Image[gz.msgs.Image",
                    "/dri/gz/imu@sensor_msgs/msg/Imu[gz.msgs.IMU",
                    "/world/high_speed_rail_corridor/model/x500_depth_0/link/camera_link/sensor/IMX214/image@sensor_msgs/msg/Image[gz.msgs.Image",
                    "/world/high_speed_rail_corridor/model/x500_depth_0/link/camera_link/sensor/IMX214/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo",
                ],
                remappings=[
                    ("/dri/gz/front_camera", "/dri/camera/static_front/image_raw"),
                    ("/dri/gz/down_camera", "/dri/camera/static_down/image_raw"),
                    ("/dri/gz/imu", "/dri/imu"),
                    (
                        "/world/high_speed_rail_corridor/model/x500_depth_0/link/camera_link/sensor/IMX214/image",
                        "/dri/camera/front/image_raw",
                    ),
                    (
                        "/world/high_speed_rail_corridor/model/x500_depth_0/link/camera_link/sensor/IMX214/camera_info",
                        "/dri/camera/front/camera_info",
                    ),
                ],
                output="screen",
            ),
            TimerAction(
                period=6.0,
                actions=[
                    Node(
                        package="rail_inspection_control",
                        executable="mission_manager",
                        output="screen",
                        parameters=[
                            {
                                "use_px4_offboard": use_px4_offboard,
                                "simulate_state": simulate_state,
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
                                "mode": "px4_gazebo_sitl",
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
                        condition=IfCondition(synthetic_camera),
                    ),
                    Node(
                        package="rail_inspection_perception",
                        executable="yolo_detector",
                        output="screen",
                        parameters=[{"fallback_enabled": True}],
                    ),
                    Node(package="rail_inspection_report", executable="report_generator", output="screen"),
                    Node(
                        package="rail_inspection_dashboard",
                        executable="web_dashboard",
                        output="screen",
                        additional_env={"DRI_DASHBOARD_PORT": dashboard_port},
                    ),
                ],
            ),
            Node(
                package="rviz2",
                executable="rviz2",
                arguments=["-d", rviz_config],
                condition=IfCondition(start_rviz),
                output="screen",
            ),
        ]
    )
