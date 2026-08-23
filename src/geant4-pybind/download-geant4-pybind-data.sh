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
from geant4_pybind import G4Version
print("geant4-pybind version:", g4.G4Version)
EOF

$UV run python main.py <<EOF
Y
EOF

cd /tmp
rm -rf /tmp/geant4-pybind-test
