#!/usr/bin/env bash
set -e

if [ ! -d "$HOME/.geant4_pybind" ] || [ -z "$(ls -A "$HOME/.geant4_pybind")" ]; then
    echo "FAIL: $HOME/.geant4_pybind 不存在或为空" >&2
    exit 1
fi
echo "OK: $HOME/.geant4_pybind 存在且含数据"

UV="${UV:-/home/node/.local/bin/uv}"
TMP="$(mktemp -d)"
cd "$TMP"
"$UV" init
"$UV" add geant4-pybind
"$UV" sync
if ! timeout 10 "$UV" run python -c "from geant4_pybind import G4Version; print('G4Version:', G4Version)"; then
    echo "FAIL: G4Version import 超时或失败（可能触发数据下载）" >&2
    exit 1
fi
rm -rf "$TMP"
echo "OK: G4Version import 快速完成（未触发数据下载）"
