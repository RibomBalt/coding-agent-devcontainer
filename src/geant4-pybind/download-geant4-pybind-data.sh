#!/usr/bin/env bash
set -e
# THIS FILE SHOULD BE EXECUTED by USER node

UV="${UV:-/home/node/.local/bin/uv}"

mkdir -p /tmp/geant4-pybind-test
cd /tmp/geant4-pybind-test
$UV init
$UV add geant4-pybind
$UV sync

cat >main.py <<EOF
import geant4_pybind as g4
print("geant4-pybind version:", g4.__version__)
EOF
$UV run python main.py

cd /tmp
rm -rf /tmp/geant4-pybind-test
