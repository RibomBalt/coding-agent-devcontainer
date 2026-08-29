# AGENTS.md

Dev container **features 分发**项目（不是应用）：产物是 GHCR 上的 base image + 一组发布为 OCI artifact 的 feature（内部为 tgz 打包，消费方用 `ghcr.io/.../feature:1` 引用，不直接碰 tgz），消费方是其他项目的 `devcontainer.json`。整体遵循 `~/.config/opencode/AGENTS.md` 的全局 Python 规范（uv、ruff、中文回复）。

## 架构：两层

- **base image** — `image/Dockerfile-base`（`debian:13-slim` + 系统包 + Node.js + pnpm + shell + SSH + 通用配置），所有项目共用，`docker build` 构建。
- **optional features** — `src/<id>/`（`devcontainer-feature.json` + `install.sh`），按项目选择。当前：`opencode`、`codex`、`playwright`、`python-uv`、`golang`、`git-delta`、`geant4-pybind`。

关键边界：**coding agent（opencode、codex）是 feature，不烘焙进 base image**。agent 更新频繁，靠 feature 的 `postCreateCommand`（运行时 `pnpm add -g`）安装、`postStartCommand` 启动；`install.sh` 只做目录/脚本/git 身份。注意 `@openai/codex` 二进制通过 optionalDependencies（`@openai/codex-linux-x64` 等）提供、无 postinstall，pnpm 全局安装可行且 codex.js 内置 pnpm 布局检测，无需 `--allow-build`（与 opencode 不同）。

CLI 通过扫描 `src/*/devcontainer-feature.json` 自动发现 feature（`coding_agent_devcontainer/features.py`），该 JSON 同时是发布管线消费的唯一权威源。新增 feature 只需创建 `src/<id>/devcontainer-feature.json` + `install.sh`；若要注入 containerEnv/mounts/端口等 devcontainer.json 配置，在 `render.py` 加对应分支。CLI 生成 devcontainer.json 的逻辑在 `render.py`。

## 命令

- CLI 入口名是 **`coding-agent-devcontainer`**（不是 `opencode-devcontainer`），见 `pyproject.toml` `[project.scripts]`。子命令：`init` / `update` / `list` / `up`。
- 单测一个 feature：`devcontainer features test -p . -i <base-image> -u node -f <feature>`（需 Docker daemon 运行；`-i` 必须是含 node 用户/wget 的 base image，默认 `ubuntu:focal` 会失败）。
- 打包验证（不发布）：`devcontainer features package -f src`（生成 `output/`，已 gitignore）。
- lint：`uv run ruff check coding_agent_devcontainer/ scripts/`。
- 单测（Python，pytest）：`uv run pytest`（收集 `test/cli/`，见 `pyproject.toml` 的 `testpaths`）。
- 本地构建 base image：`./scripts/01-build-image.sh [name]`（等价 `docker build -f image/Dockerfile-base image`，需传 `HTTP_PROXY`/`HTTPS_PROXY` 给 zsh-in-docker 下载）。
- 单 feature 测试：`./scripts/03-feature-test.sh <feature> [image]`（基于 `01-build-image.sh` 构建的镜像，默认 `opencode-sandbox-ribom:latest`；等价 `devcontainer features test -p . -i <image> -u node -f <feature>`）。
  - 测试脚本放仓库根 `test/<feature-id>/test.sh`（与 `src/` 平级，**不是** `src/<id>/test/`）；CLI 的 Python 单测在同级 `test/cli/`。feature 测试以 remote user（node）运行。`devcontainer features test` 会执行该 feature 的 `postCreateCommand`。现有：`test/opencode/test.sh`（校验数据目录 + git 身份）、`test/codex/test.sh`（校验 `~/.codex` 目录 + `codex` 命令 + git 身份）、`test/geant4-pybind/test.sh`（校验 `~/.geant4_pybind` 数据目录非空 + `from geant4_pybind import G4Version` 10s 内不超时）。

## 关键坑（容易踩）

- **pnpm PATH 必须 `$PNPM_HOME/bin`**，不是 `$PNPM_HOME`。否则 `pnpm add -g` 报 `global bin directory ... not in PATH`。`Dockerfile-base` 的 `ENV PATH` 已含 `/bin`，feature 的 `postCreateCommand` 里也显式 `export PATH=/usr/local/share/pnpm-global/bin:...` 兜底。
- **feature 的 `containerEnv` 不支持 `${localEnv:...}`**（被写成 Dockerfile `ENV`，Docker 报 `unsupported modifier (:O)`）。需要宿主机变量的值放 devcontainer.json 的 `remoteEnv`（`render.py` 的 `_REMOTE_ENV`）。
- **feature 的 `install.sh` 以 root 运行**，切 node 用户用 `su -l -s /bin/bash -c "..." node`（`sudo` 不行——node 无 sudo 权限；`su` 从 root 免密）。
- **镜像默认 `USER node`**：`docker run` 不指定 `--user` 时以 node 运行，此时 `su node`/`sudo` 会失败；但 feature 安装时是 root，`su node` 正常。
- **feature 的 `test.sh` 以 remote user（node）运行**，不要在里面用 `su`，直接 `git config --global` 等即可。
- **`installsAfter` 是软依赖**，`devcontainer features test` 单测不会自动装依赖；feature 依赖的 node 用户、wget、git 由 base image 提供。
- **中国镜像源**：apt=tuna（`debian-tuna.sources`，trixie）；node 用 npmmirror 二进制（`https://registry.npmmirror.com/-/binary/node`，**tuna 的 `nodejs-release` 滞后**，无新版）；npm/pnpm=npmmirror。本地测试代理**按环境动态设置、别写死 IP**（WSL2 宿主机 IP 每次重启会变；可从 `/etc/resolv.conf` 的 `nameserver` 或 `ip route` 默认网关获取）。`render.py` 里容器内代理固定用 `host.docker.internal:7890`。

## 发布（CI）

`.github/workflows/release.yaml`：推 **`v*` tag** 触发。两个 job 并行：`publish-features`（`devcontainers/action` 发布 `src/` 到 GHCR）+ `build-base-image`（`docker build` + push）。命名空间 `ghcr.io/ribombalt/coding-agent-devcontainer`，base image 为 `...-base:latest` + `...-base:<tag>`。

- CI 里 owner/repo 必须转小写（`${OWNER,,}`），否则 GHCR 报 `repository name must be lowercase`。
- git 有两个 remote：`origin`=Gitee（`claude-code-devcontainer`），`github`=GitHub（`RibomBalt/coding-agent-devcontainer`）；GHCR 发布走 `github`。

## 约定

- `scripts/02-devcontainer-up.py` 是**兼容入口**（转发到 `coding-agent-devcontainer up`），勿删；`scripts/01-build-image.sh` 是 base image 构建入口；`scripts/03-feature-test.sh` 是单 feature 本地测试入口。
- 已删除（勿恢复）：`gpu/`、`nogpu/`、`scripts/03-gpus-from-nogpus.py`、`image/Dockerfile`（旧 node:20-slim 全量版）、`image/start-opencode-web.py`（已移入 `src/opencode/`）。
- git 身份：base image 写通用 `devcontainer@localhost`，opencode feature 的 install.sh 覆盖为 `opencode`，codex feature 的 install.sh 覆盖为 `codex`（`codex@openai.com`）。
