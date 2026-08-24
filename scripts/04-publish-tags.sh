#!/bin/bash
# 打 tag 触发 GitHub Actions 发布。两种模式（按 tag 是否存在自动判断）：
#   1) 新 tag：本地/远端均不存在 → git tag + git push
#   2) 重建 tag：本地或远端任一存在 → 删除存在侧 + 重建指向 HEAD + push
# 用法: ./scripts/04-publish-tags.sh <version> [remote]
#   version: 形如 v0.3.0
#   remote:  默认取当前分支的上游 remote（无上游则回退 origin）
set -euo pipefail

VERSION=${1:?"用法: $0 <version> [remote]"}

# 校验版本形如 vX.Y.Z
if ! [[ "${VERSION}" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "版本号格式错误（应为 vX.Y.Z）: ${VERSION}" >&2
    exit 1
fi

# 默认 remote = 当前分支上游 remote，回退 origin
if [ $# -ge 2 ]; then
    REMOTE="$2"
else
    BRANCH="$(git branch --show-current)"
    REMOTE="$(git config "branch.${BRANCH}.remote" || true)"
    if [ -z "${REMOTE}" ]; then
        REMOTE="origin"
    fi
fi

if ! git remote | grep -qx "${REMOTE}"; then
    echo "未知 remote: ${REMOTE}" >&2
    echo "可用: $(git remote | tr '\n' ' ')" >&2
    exit 1
fi

echo ">> remote: ${REMOTE}"

LOCAL_EXISTS=0
REMOTE_EXISTS=0
git rev-parse -q --verify "refs/tags/${VERSION}" >/dev/null 2>&1 && LOCAL_EXISTS=1
if git ls-remote --exit-code "${REMOTE}" "refs/tags/${VERSION}" >/dev/null 2>&1; then
    REMOTE_EXISTS=1
fi

if [ "${LOCAL_EXISTS}" -eq 0 ] && [ "${REMOTE_EXISTS}" -eq 0 ]; then
    echo ">> 新 tag 模式：${VERSION}"
    git tag "${VERSION}"
else
    echo ">> 重建 tag 模式：${VERSION} (local=${LOCAL_EXISTS} remote=${REMOTE_EXISTS})"
    echo "   HEAD: $(git rev-parse --short HEAD) $(git log -1 --oneline)"
    if [ "${LOCAL_EXISTS}" -eq 1 ]; then
        echo "   >> 删除本地 tag"
        git tag -d "${VERSION}"
    fi
    if [ "${REMOTE_EXISTS}" -eq 1 ]; then
        echo "   >> 删除远端 tag"
        git push "${REMOTE}" ":refs/tags/${VERSION}"
    fi
    git tag "${VERSION}"
fi

echo ">> 推送 ${VERSION} → ${REMOTE}"
git push "${REMOTE}" "${VERSION}"

# 远端为 github 时 echo Actions 地址
REMOTE_URL="$(git remote get-url "${REMOTE}")"
if [[ "${REMOTE_URL}" =~ ^git@github\.com:([^/]+)/([^/]+)(\.git)?$ ]]; then
    OWNER="${BASH_REMATCH[1]}"
    REPO="${BASH_REMATCH[2]}"
    echo ">> Actions: https://github.com/${OWNER}/${REPO}/actions"
elif [[ "${REMOTE_URL}" =~ ^https://github\.com/([^/]+)/([^/]+)(\.git)?$ ]]; then
    OWNER="${BASH_REMATCH[1]}"
    REPO="${BASH_REMATCH[2]}"
    echo ">> Actions: https://github.com/${OWNER}/${REPO}/actions"
fi

echo ">> 完成"
