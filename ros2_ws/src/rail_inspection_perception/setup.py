from setuptools import find_packages, setup

package_name = "rail_inspection_perception"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Drone Rail Inspection Team",
    maintainer_email="ops@example.com",
    description="YOLO and synthetic camera pipeline for high-speed railway inspection.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "synthetic_scene_publisher = rail_inspection_perception.synthetic_scene_publisher:main",
            "yolo_detector = rail_inspection_perception.yolo_detector:main",
        ],
    },
)
