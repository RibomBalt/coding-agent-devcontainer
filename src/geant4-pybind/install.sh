#!/usr/bin/env bash
set -e

USERNAME="${_REMOTE_USER:-node}"
USER_HOME="${_REMOTE_USER_HOME:-$(getent passwd "$USERNAME" | cut -d: -f6)}"
FEATURE_DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p ~/.geant4_pybind && chown -R $USERNAME:$USERNAME ~/.geant4_pybind
cp "$FEATURE_DIR/download-geant4-pybind-data.sh" ~/.local/bin/ && chmod +x ~/.local/bin/download-geant4-pybind-data.sh
