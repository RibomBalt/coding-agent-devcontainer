#!/bin/bash
# Build the Docker image for the coding agent
# default name is set to "opencode-sandbox-ribom"
DIR="$(dirname "$0")"
IMAGE=${1:-"opencode-sandbox-ribom:latest"}
exec env IMAGE="$IMAGE" "${DIR}/../image/build-image.sh"
