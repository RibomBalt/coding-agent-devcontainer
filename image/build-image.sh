#!/bin/bash

set -euo pipefail

WSL_CLASH_PROXY="http://host.docker.internal:7890"
DIR="$(dirname "$0")"
IMAGE=${IMAGE:-"opencode-sandbox-ribom:latest"}

pushd "$DIR"
trap 'popd' EXIT

docker build -f Dockerfile-base -t "$IMAGE" \
    --build-arg TZ="${TZ:-Asia/Shanghai}" \
    --build-arg NODE_VERSION="${NODE_VERSION:-24.19.0}" \
    --build-arg NODE_MIRROR="${NODE_MIRROR:-https://registry.npmmirror.com/-/binary/node}" \
    --build-arg ZSH_IN_DOCKER_VERSION="${ZSH_IN_DOCKER_VERSION:-1.2.0}" \
    --build-arg HTTP_PROXY="${HTTP_PROXY:-${WSL_CLASH_PROXY}}" \
    --build-arg HTTPS_PROXY="${HTTPS_PROXY:-${WSL_CLASH_PROXY}}" \
    --build-arg NO_PROXY="${NO_PROXY:-localhost,127.0.0.1,host.docker.internal}" \
    .
