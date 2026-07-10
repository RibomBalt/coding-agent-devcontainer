#!/bin/bash

set -euo pipefail

WSL_CLASH_PROXY="http://host.docker.internal:7890"
DIR="$(dirname "$0")"
IMAGE=${IMAGE:-"opencode-sandbox-ribom:latest"}

pushd "$DIR"
trap 'popd' EXIT

docker build -t "$IMAGE" \
    --build-arg TZ="${TZ:-Asia/Shanghai}" \
    --build-arg GIT_DELTA_VERSION="${GIT_DELTA_VERSION:-0.18.2}" \
    --build-arg ZSH_IN_DOCKER_VERSION="${ZSH_IN_DOCKER_VERSION:-1.2.0}" \
    --build-arg PLAYWRIGHT_VERSION="${PLAYWRIGHT_VERSION:-1.59.1}" \
    --build-arg HTTP_PROXY="${WSL_CLASH_PROXY:-}" \
    --build-arg HTTPS_PROXY="${WSL_CLASH_PROXY:-}" \
    --build-arg NO_PROXY="localhost,127.0.0.1,host.docker.internal" \
    --build-arg GO_VERSION=${GO_VERSION-1.26.5} \
    .
