#!/usr/bin/env bash
set -euo pipefail

export GIT_TERMINAL_PROMPT=0
export PATH=/usr/local/share/pnpm-global/bin:/usr/local/share/npm-global/bin:$PATH

DSH_SOURCE_DIR="${HOME}/deepseek-harness"
DSH_SOURCE_REF="$(cat /usr/local/share/dsh/source-ref 2>/dev/null || true)"
DSH_SOURCE_REF="${DSH_SOURCE_REF:-master}"

if [ -e "$DSH_SOURCE_DIR" ] && [ ! -d "$DSH_SOURCE_DIR/.git" ]; then
    echo "dsh source directory exists but is not a git checkout: $DSH_SOURCE_DIR" >&2
    exit 1
fi

if [ ! -d "$DSH_SOURCE_DIR/.git" ]; then
    git clone --depth 1 --branch "$DSH_SOURCE_REF" \
        https://github.com/deepseek-ai/deepseek-harness.git \
        "$DSH_SOURCE_DIR"
fi

cd "$DSH_SOURCE_DIR"
pnpm install --dangerously-allow-all-builds
pnpm run build
