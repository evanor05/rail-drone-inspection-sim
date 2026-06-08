# Host Check - 2026-06-07

Observed from the current Windows host:

- Target drive `E:\` exists.
- `E:\DroneRailInspection` did not exist before project creation was attempted.
- NVIDIA GPU is visible from Windows:
  - GPU: NVIDIA GeForce RTX 4050 Laptop GPU
  - Driver: 595.97
  - Driver CUDA capability: 13.2
- Docker CLI exists:
  - Docker version 29.3.1
- Docker Desktop daemon is not running:
  - `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`
- Docker Desktop service exists but is stopped:
  - `com.docker.service`, status `Stopped`, start type `Manual`
- WSL service is running, but `wsl -l -v` returned the Windows message for no installed Linux distributions.
- Checking optional Windows features requires elevated privileges.

Current implication:

- Static and local artifact validation can run.
- Full Docker/ROS2/PX4/Gazebo acceptance is blocked until WSL2 Ubuntu and Docker Desktop daemon are available.
- Copying this project from the staging workspace to `E:\DroneRailInspection` requires filesystem approval because `E:\` is outside the current writable sandbox root.
- If Codex approval is unavailable, run `.\scripts\install_to_target.ps1` from the staging project in a normal PowerShell terminal to install the project to `E:\DroneRailInspection`.

Recommended host actions:

```powershell
wsl --install -d Ubuntu-22.04
```

Restart Windows if prompted, initialize Ubuntu, then start Docker Desktop and enable WSL integration.

```powershell
cd E:\DroneRailInspection
.\scripts\doctor.ps1
.\scripts\build.ps1
.\scripts\acceptance_offline.ps1 -Seconds 35
.\scripts\start_full_sim.ps1
```
