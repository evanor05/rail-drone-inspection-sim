#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

export PX4_VERSION="${PX4_VERSION:-v1.16.2}"
export INSTALL_TORCH_CUDA="${INSTALL_TORCH_CUDA:-false}"
export INSTALL_ULTRALYTICS="${INSTALL_ULTRALYTICS:-false}"
export GIT_MIRROR_PREFIX="${GIT_MIRROR_PREFIX:-}"

echo "[DRI] Project root: ${ROOT}"
docker version
docker compose --progress=plain build
