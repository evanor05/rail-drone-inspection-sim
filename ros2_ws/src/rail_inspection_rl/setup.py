from setuptools import find_packages, setup

package_name = "rail_inspection_rl"

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
    description="Gymnasium-compatible extension points for future railway inspection RL policies.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "rl_env_smoke = rail_inspection_rl.env:main",
        ],
    },
)
