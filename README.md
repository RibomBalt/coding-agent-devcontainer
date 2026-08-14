# OpenCode Dev Container

基于 `node:20-slim` 构建的全栈 AI 开发容器，集成 [OpenCode](https://opencode.ai) 编程助手，适用于 Python + Node.js + TypeScript 项目开发。容器启动后自动运行 `opencode serve` ，提供 Web UI 和 API 接口，可通过浏览器或 CLI 远程使用。

## Feature 架构

本项目采用 [Dev Container Features](https://containers.dev/implementors/features) 将原本的单一 Dockerfile 拆分为可组合的 feature 模块，每个项目按需选择所需工具链，避免拉取厚重的全量镜像。

### 架构总览

```
┌─ 本仓库 ────────────────────────────────────────────┐
│  src/                    CI (GitHub Actions)          │
│  ├─ system-tools/  ─┐                                  │
│  ├─ shell-setup/    │  Common features   devcontainer  │
│  ├─ ssh-firewall/   ├── 构建为 ──────►  build ──► GHCR │
│  ├─ opencode-config─┘  base image         base image   │
│  ├─ node-tooling/        (可选)      发布 tgz ──► GHCR │
│  ├─ python-uv/           (可选)                        │
│  ├─ golang/              (可选)                        │
│  └─ git-delta/           (可选)                        │
│                                                         │
│  coding_agent_devcontainer/  CLI 工具                  │
│    init / update 交互式生成 devcontainer.json          │
└─────────────────────────────────────────────────────────┘

   项目A                        项目B
   .devcontainer/               .devcontainer/
   └─ devcontainer.json         └─ devcontainer.json
      image: base                  image: base
      features:                    features:
        python-uv ✓                  node-tooling ✓
        golang ✓                    golang ✓
```

### Feature 清单

| Feature | 类型 | 说明 |
|---------|------|------|
| `system-tools` | 公共 | 系统软件包、locale、Playwright 系统依赖 |
| `shell-setup` | 公共 | zsh + powerlevel10k + fzf |
| `ssh-firewall` | 公共 | SSH 初始化、OpenCode Web 启动、防火墙 |
| `opencode-config` | 公共 | vimrc、git 身份、OpenCode 目录 |
| `node-tooling` | 可选 | pnpm + npm 镜像 + Playwright 浏览器 |
| `python-uv` | 可选 | uv 包管理器 + PyPI 镜像 |
| `golang` | 可选 | Go 工具链 + GOPROXY |
| `git-delta` | 可选 | 语法高亮 git diff |

公共 feature 内置于预构建的 base image（`ghcr.io/<owner>/<repo>-base:latest`），可选 feature 在容器创建时按需安装。

### 生成项目配置（CLI）

```bash
# 交互式创建
opencode-devcontainer init -w /path/to/your/project

# 非交互模式
opencode-devcontainer init -w /path/to/your/project --non-interactive \
    --features python-uv,golang --gpu

# 更新已有配置
opencode-devcontainer update -w /path/to/your/project

# 查看所有可用 feature
opencode-devcontainer list
```

CLI 会在目标项目生成 `.devcontainer/devcontainer.json`，引用 base image 并启用所选 feature。

## 容器能力

### 语言与运行时

| 组件 | 版本/说明 |
|------|----------|
| Node.js | 20 (slim) |
| Python | 可通过 uv 安装指定版本 |
| OpenCode | `opencode` CLI（最新版），自动启动 Web UI（`opencode serve`） |

### 包管理器与镜像

| 工具 | 镜像源 |
|------|--------|
| npm / pnpm | npmmirror.com |
| uv / pip | TUNA (清华大学) |
| apt | TUNA (清华大学) |

### 预装工具

- **Shell**: zsh + powerlevel10k 主题 + fzf
- **Git 增强**: git-delta（语法高亮 diff）
- **编辑器**: vim + VSCode 集成 Prettier / Ruff / ESLint
- **网络工具**: iptables, ipset, dnsutils, curl, wget
- **其他**: gh (GitHub CLI), jq, ripgrep (fd-find), man-db, ssh server

### VSCode 插件（自动安装）

- ESLint, Prettier, GitLens
- Python, Pylance, Ruff
- 默认启用 format-on-save

### 安全特性

- **SSH 远程访问**：自动挂载宿主机公钥，免密登录（容器内监听 2222 端口，宿主机映射端口自动分配）
- **非 root 运行**：以 `node` 用户运行，安全命令通过 sudoers 白名单控制
- **网络防火墙**：白名单出站模式（`init-firewall.sh`，当前为 TODO 状态，参见文末说明）

## 依赖安装

前置条件：

1. **Docker** — 安装 [Docker Engine](https://docs.docker.com/engine/install/) 或 [Docker Desktop](https://docs.docker.com/get-docker/)
2. **npx 或 bun** — devcontainer CLI（`@devcontainers/cli`）将通过以下任一方式自动检测：
   - `devcontainer`（独立安装）
   - `npx @devcontainers/cli`
   - `pnpx @devcontainers/cli`
   - `bun x @devcontainers/cli`
3. **SSH 公钥** — 宿主机需存在 `~/.ssh/id_ed25519.pub`，用于容器免密登录
4. **CLI 工具** — 生成 devcontainer.json 用的 `opencode-devcontainer`：

```bash
uv tool install .    # 或 pip install .
```

## 使用方法

### 生成项目配置

使用 CLI 交互式选择项目所需 feature，生成 `.devcontainer/devcontainer.json`：

```bash
opencode-devcontainer init -w /path/to/your/project
```

或使用非交互模式：

```bash
# 无 GPU，选择 python-uv 和 golang
opencode-devcontainer init -w /path/to/your/project --non-interactive \
    --features python-uv,golang

# 启用 GPU
opencode-devcontainer init -w /path/to/your/project --non-interactive \
    --features python-uv,golang --gpu
```

### 启动容器

> 使用 `scripts/02-devcontainer-up.py`（优先使用项目本地 `.devcontainer/devcontainer.json`，否则回退到仓库 `gpu/`/`nogpu/` 配置）：

```bash
# 无 GPU
python scripts/02-devcontainer-up.py -w /path/to/your/workspace

# 启用 GPU
python scripts/02-devcontainer-up.py -w /path/to/your/workspace --gpus

# 指定 SSH 起始端口（默认 40022，自动寻找第一个可用端口）
python scripts/02-devcontainer-up.py -w /path/to/your/workspace -p 2222
```

### VSCode

生成配置后（见上文），在 VSCode 中打开项目，按 `F1` → 选择 **"Dev Containers: Reopen in Container"**。

### Zed / 其他编辑器（SSH 连接）

容器启动后，SSH 服务监听在容器内 2222 端口，宿主机映射端口由脚本自动分配并输出。通过 SSH 远程开发：

```bash
ssh -p <宿主机映射端口> -o StrictHostKeyChecking=no node@localhost
```

在 Zed 中，添加 SSH 远程服务器即可连接开发。

### OpenCode Web UI

容器启动后自动运行 `opencode serve`，监听容器内 `4096` 端口。外部映射端口通过 `02-devcontainer-up.py` 动态分配：从 SSH 起始端口向上扫描**连续两个**空闲端口，第一个用于 SSH，第二个用于 OpenCode Web UI（即启动脚本输出的第二个端口）。若直接通过 VSCode 使用 devcontainer（不走脚本），则回退为 `devcontainer.json` 中的默认值 `50096`。

```bash
# 浏览器访问（使用脚本输出的 opencode 端口）
http://localhost:<opencode 外部端口>

# 或通过 CLI 连接
opencode attach <opencode 外部端口>
```

**认证配置**：通过以下环境变量控制（不设置时自动生成随机密码）：

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `OPENCODE_SERVER_USERNAME` | Web UI 登录用户名 | `opencode` |
| `OPENCODE_SERVER_PASSWORD` | Web UI 登录密码 | 随机 32 字符 |
| `DEVCONTAINER_OPCD_PORT` | 外部映射端口（仅 devcontainer.json 回退值） | `50096` |

若需自定义端口，不建议手动设置 `DEVCONTAINER_OPCD_PORT`，而应通过 `-p` 参数指定 SSH 起始端口，脚本会自动分配后续可用端口：

```bash
python scripts/02-devcontainer-up.py -w /path/to/your/workspace -p 40022
```

### 数据持久化

以下目录通过 Docker Volume 持久化，容器重建后数据不丢失：

| Volume | 挂载路径 | 用途 |
|--------|---------|------|
| `opencode-bashhistory-*` | `/commandhistory` | Bash/Zsh 历史 |
| `opencode-config` | `/home/node/.config/opencode` | OpenCode 配置 |
| `opencode-local-share` | `/home/node/.local/share/opencode` | OpenCode 本地数据 |
| `opencode-cache` | `/home/node/.cache/opencode` | OpenCode 缓存 |
| `devcontainer-ssh-hostkey` | `/home/node/.ssh/host_ssh_key` | SSH Host Key |
| `devcontainer-uv-cache` | `/home/node/.cache/uv` | UV 包管理器缓存 |
| `devcontainer-pnpm-home` | `/usr/local/share/pnpm-global` | pnpm 全局包及 store |

## 开发

### 项目结构

```
.
├── src/                        # Dev Container Feature 源码（一个 feature 一个目录）
│   ├── system-tools/           # 公共：系统软件包 + locale
│   ├── shell-setup/            # 公共：zsh + powerlevel10k
│   ├── ssh-firewall/           # 公共：SSH / OpenCode Web / 防火墙
│   ├── opencode-config/        # 公共：vimrc / git / OpenCode 目录
│   ├── node-tooling/           # 可选：pnpm + Playwright
│   ├── python-uv/              # 可选：uv + PyPI 镜像
│   ├── golang/                 # 可选：Go 工具链
│   └── git-delta/              # 可选：git-delta
├── test/                       # Feature 测试（devcontainer features test）
├── coding_agent_devcontainer/  # CLI 工具（Python 包）
│   ├── cli.py                  # init / update / list 命令
│   ├── features.py             # Feature 元数据注册
│   ├── render.py               # devcontainer.json 渲染
│   └── constants.py            # 注册表命名空间等常量
├── .github/workflows/          # CI：发布 feature + 构建 base image
├── .devcontainer/              # base image 构建配置（由 CLI 生成）
├── image/                      # 旧版单文件 Dockerfile（迁移参考）
├── gpu/                        # 仓库级 GPU 配置（回退用）
├── nogpu/                      # 仓库级无 GPU 配置（回退用）
└── scripts/                    # 入口脚本
    ├── 02-devcontainer-up.py   # 容器启动 CLI
    └── 03-gpus-from-nogpus.py  # GPU 配置文件生成器
```

### Feature 开发

每个 feature 由 `devcontainer-feature.json`（元数据）和 `install.sh`（安装脚本）组成。feature 的 `install.sh` 以 **root** 运行，需以 `node` 用户执行的命令用 `su -l -s /bin/bash -c "..." node` 切换。

- **公共 feature**（`system-tools`、`shell-setup`、`ssh-firewall`、`opencode-config`）内置于 base image，在 CI 中构建一次。
- **可选 feature**（`node-tooling`、`python-uv`、`golang`、`git-delta`）在容器创建时按需安装。
- 新增 feature 时：在 `src/<feature-id>/` 下创建目录，并同步 `coding_agent_devcontainer/features.py` 中的元数据（`common` 标记）。

### 发布与 CI

`.github/workflows/release.yaml` 完成两步：

1. `publish-features`：使用 `devcontainers/action` 将 `src/` 下所有 feature 打包发布到 GHCR（`ghcr.io/<owner>/<repo>/<feature-id>:<version>`）。
2. `build-base-image`：渲染 base 配置并 `devcontainer build`，推送 base image 到 GHCR。

> 注意：当前仓库 remote 为 Gitee；如需 GHCR 发布，请将仓库镜像到 GitHub 并配置 `GITHUB_TOKEN`。

### 容器配置 (`gpu/` / `nogpu/devcontainer.json`)

仓库级 `gpu/` / `nogpu/` 配置用于**未迁移的项目回退**；迁移后的项目使用 CLI 生成的 `.devcontainer/devcontainer.json`。

两份配置差异仅在两处：

| 配置项 | GPU 版 | 无 GPU 版 |
|--------|--------|-----------|
| `runArgs` | 含 `--gpus=all` | 不含 |
| `containerEnv` | 含 `NVIDIA_VISIBLE_DEVICES`、`NVIDIA_DRIVER_CAPABILITIES` | 不含 |

共同包含：

- **`runArgs`**：`NET_ADMIN` + `NET_RAW` 权限（供 iptables 使用）
- **`mounts`**：挂载 SSH 公钥（`~/.ssh/id_ed25519.pub` → 容器只读）、7 个持久化 Volume（参见上文数据持久化表）
- **`appPort`**：映射两个端口 — `${localEnv:DEVCONTAINER_SSH_PORT}` → 容器 `2222`（SSH），`${localEnv:DEVCONTAINER_OPCD_PORT}` → 容器 `4096`（OpenCode Web UI）
- **`containerEnv`**：`NODE_OPTIONS`（4GB 堆内存）、代理环境变量（大/小写）、`POWERLEVEL9K_DISABLE_GITSTATUS`、`OPENCODE_SERVER_USERNAME` / `OPENCODE_SERVER_PASSWORD`（Web UI 认证）、`DEVCONTAINER_OPCD_PORT`（Web UI 端口）
- **`postStartCommand`**：依次执行 `init-ssh.sh`（启动 SSH）和 `start-opencode-web.py`（启动 opencode serve）
- **`postCreateCommand`**：通过 `pnpm add -g --allow-build=opencode-ai opencode-ai` 安装 OpenCode（首次创建时执行）
- **`waitFor`**：`postStartCommand`（等待启动完成）

### SSH 初始化 (`image/init-ssh.sh`)

- 挂载宿主机公钥到 `authorized_keys`（通过公钥指纹去重）
- 生成/复用 SSH Host Key（通过 Volume `devcontainer-ssh-hostkey` 持久化）
- 在 2222 端口启动 `sshd`

### 防火墙初始化 (`image/init-firewall.sh`)

> **当前状态：TODO**，脚本逻辑已实现但未接入 `postStartCommand`，需要调试和验证。

**已实现的逻辑**：

1. 保存并恢复 Docker DNS NAT 规则（`127.0.0.11`），避免容器内部 DNS 被清空
2. 放行 DNS (UDP 53)、SSH (TCP 22)、localhost 流量
3. 创建 `allowed-domains` ipset 集合
4. 通过 GitHub Meta API 获取官方 IP 范围并添加到白名单
5. 对白名单域名逐一 DNS 解析并加入 ipset：
   - `registry.npmjs.org`, `api.anthropic.com`, `sentry.io`, `statsig.anthropic.com`, `statsig.com`, `marketplace.visualstudio.com`, `vscode.blob.core.windows.net`, `update.code.visualstudio.com`, `yunwu.ai`
6. 检测宿主机 IP 网络段并放行
7. 设置默认策略 DROP，仅允许 ipset 内目标出站
8. 验证规则（example.com 不可达，api.github.com 可达）

**待完成**：验证脚本在容器启动环境中的可用性，将 `init-firewall.sh` 加入 `postStartCommand`（需确认与 ssh 启动顺序及完整网络连通性）。

### 启动 CLI (`scripts/02-devcontainer-up.py`)

- 检测可用的 devcontainer CLI（按优先级：`devcontainer` → `npx` → `pnpx` → `bun` → `bunx`）
- 从指定 SSH 端口开始自动寻找**两个连续**可用端口：第一个用于 SSH，第二个用于 OpenCode Web UI（递增扫描至 65535）
- 根据 `--gpus` 标志选择 `gpu/` 或 `nogpu/` 配置
- 通过 `DEVCONTAINER_SSH_PORT` 和 `DEVCONTAINER_OPCD_PORT` 环境变量注入端口，执行 `devcontainer up`

### GPU 配置生成器 (`scripts/03-gpus-from-nogpus.py`)

从 `nogpu/devcontainer.json` 自动生成 `gpu/devcontainer.json`，添加 `--gpus=all` 参数和 NVIDIA 相关环境变量，确保两个配置保持同步。

### OpenCode Web 启动脚本 (`image/start-opencode-web.py`)

- 检查环境变量，未设置时自动生成随机密码（`secrets.token_urlsafe(32)`）
- 执行 `opencode serve --port 4096 --hostname 0.0.0.0`（守护进程方式，分离会话）
- 输出访问地址和连接命令到标准输出

## 注意事项

1. **代理配置**：`devcontainer.json` 中 `containerEnv` 默认设置了 `http://host.docker.internal:7890` 代理。如果不需要代理，请将对应项设为空字符串。

2. **host.docker.internal**：容器通过 `host.docker.internal` 访问宿主机。该域名在 Docker Desktop / OrbStack 中默认可用；Linux 原生 Docker 需在启动参数中添加 `--add-host=host.docker.internal:host-gateway`。

3. **内存限制**：Node.js 默认堆内存设为 4GB（`NODE_OPTIONS="--max-old-space-size=4096"`），可根据宿主机资源调整。

4. **SSH Host Key**：容器重建时 SSH Host Key 因 Volume 持久化而保留，避免客户端告警。如需重新生成，删除 `devcontainer-ssh-hostkey` Volume 后重建即可。

5. **OpenCode Web UI 认证**：用户名和密码通过 `OPENCODE_SERVER_USERNAME` 和 `OPENCODE_SERVER_PASSWORD` 环境变量控制。未设置时自动生成随机密码，容器启动日志中可查看。密码不会持久化，如需固定密码请在启动前设置环境变量。

## TODO

- [ ] `init-firewall.sh`：脚本逻辑已编写（`image/init-firewall.sh`），需要调试验证并接入 `devcontainer.json` 的 `postStartCommand`。当前容器启动 SSH 与 OpenCode Web UI 服务，未启用防火墙。
- [ ] `proxy` 配置：目前代理地址硬编码在 `devcontainer.json` 中，考虑通过环境变量或 `.env` 文件统一管理。
