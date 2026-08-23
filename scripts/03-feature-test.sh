#!/bin/bash
# 单 feature 本地测试：基于 01-build-image.sh 构建的 base image。
# 用法: ./scripts/03-feature-test.sh <feature> [镜像名]
set -euo pipefail

DIR="$(dirname "$0")"
ROOT="$(cd "${DIR}/.." && pwd)"
FEATURE=${1:?"用法: $0 <feature> [镜像名]"}
IMAGE=${2:-"opencode-sandbox-ribom:latest"}

if [ ! -f "${ROOT}/src/${FEATURE}/devcontainer-feature.json" ]; then
    echo "未找到 feature: src/${FEATURE}/devcontainer-feature.json" >&2
    exit 1
fi

exec devcontainer features test -p "${ROOT}" -i "${IMAGE}" -u node -f "${FEATURE}"
