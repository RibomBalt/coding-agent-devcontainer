#!/usr/bin/env bash
set -e

USERNAME="${_REMOTE_USER:-node}"
USER_HOME="${_REMOTE_USER_HOME:-$(getent passwd "$USERNAME" | cut -d: -f6)}"
FEATURE_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${PYTHON:-python3}"

mkdir -p /tmp/geant4-pybind-test
mkdir -p ~/.geant4_pybind
cd /tmp/geant4-pybind-test
uv init
uv add geant4-pybind
uv sync

cat >main.py <<EOF
import geant4_pybind as g4
print("geant4-pybind version:", g4.__version__)
EOF
uv run python main.py

cd /tmp
rm -rf /tmp/geant4-pybind-test
