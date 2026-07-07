# OpenCode Dev Container

基于 `node:20-slim` 构建的全栈 AI 开发容器，集成 [OpenCode](https://opencode.ai) 编程助手，适用于 Python + Node.js + TypeScript 项目开发。

## 容器能力

### 语言与运行时

| 组件 | 版本/说明 |
|------|----------|
| Node.js | 20 (slim) |
| Python | 可通过 uv 安装指定版本 |
| OpenCode | `opencode` CLI，最新版 |

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

## 使用方法

### 构建镜像

```bash
./scripts/01-build-image.sh [镜像名称]
```

默认镜像名称为 `opencode-sandbox-ribom:latest`。首次构建约需 5–10 分钟。

### 启动容器

> 使用 `scripts/02-devcontainer-up.py`：

```bash
# 无 GPU
python scripts/02-devcontainer-up.py -w /path/to/your/workspace

# 启用 GPU
python scripts/02-devcontainer-up.py -w /path/to/your/workspace --gpus

# 指定 SSH 起始端口（默认 50022，自动寻找第一个可用端口）
python scripts/02-devcontainer-up.py -w /path/to/your/workspace -p 2222
```

### VSCode

将对应的 devcontainer 配置复制到项目的 `.devcontainer` 目录：

```bash
# 无 GPU
mkdir -p /path/to/your/workspace/.devcontainer
cp nogpu/devcontainer.json /path/to/your/workspace/.devcontainer/

# 或启用 GPU
cp gpu/devcontainer.json /path/to/your/workspace/.devcontainer/
```

然后在 VSCode 中打开项目，按 `F1` → 选择 **"Dev Containers: Reopen in Container"**。

### Zed / 其他编辑器（SSH 连接）

容器启动后，SSH 服务监听在容器内 2222 端口，宿主机映射端口由脚本自动分配并输出。通过 SSH 远程开发：

```bash
ssh -p <宿主机映射端口> -o StrictHostKeyChecking=no node@localhost
```

在 Zed 中，添加 SSH 远程服务器即可连接开发。

### 数据持久化

以下目录通过 Docker Volume 持久化，容器重建后数据不丢失：

| Volume | 挂载路径 | 用途 |
|--------|---------|------|
| `opencode-bashhistory-*` | `/commandhistory` | Bash/Zsh 历史 |
| `opencode-config` | `/home/node/.config/opencode` | OpenCode 配置 |
| `opencode-local-share` | `/home/node/.local/share/opencode` | OpenCode 本地数据 |
| `devcontainer-ssh-hostkey` | `/home/node/.ssh/host_ssh_key` | SSH Host Key |

## 开发

### 项目结构

```
.
├── image/                     # Docker 镜像构建
│   ├── Dockerfile             # 镜像定义
│   ├── build-image.sh         # 构建脚本
│   ├── debian-tuna.sources    # APT 清华镜像源
│   ├── init-firewall.sh       # 防火墙初始化（TODO）
│   └── init-ssh.sh            # SSH 服务初始化
├── gpu/                       # GPU 容器配置
│   └── devcontainer.json
├── nogpu/                     # 无 GPU 容器配置
│   └── devcontainer.json
└── scripts/                   # 入口脚本
    ├── 01-build-image.sh      # 镜像构建快捷入口
    └── 02-devcontainer-up.py  # 容器启动 CLI
```

### 镜像构建 (`image/Dockerfile`)

- **基础镜像**：`node:20-slim`
- **安装流程**：
  1. 替换 APT 源为清华镜像并安装系统依赖（`iptables`, `ipset`, `openssh-server` 等）
  2. 安装 Playwright Chromium 系统依赖（仅运行时库，不含浏览器二进制）
  3. 安装 `git-delta`（deb 包）
  4. 以 `node` 用户安装：pnpm、OpenCode（`curl -fsSL https://opencode.ai/install | bash`）、uv
  5. 配置 zsh + powerlevel10k 主题
  6. 复制 `init-firewall.sh` → `/usr/local/bin/`（配置 sudoers 白名单），`init-ssh.sh` → `~/.local/bin/`
- **构建参数**：`TZ`（时区）、`GIT_DELTA_VERSION`、`ZSH_IN_DOCKER_VERSION`、`PLAYWRIGHT_VERSION`、`HTTP_PROXY` / `HTTPS_PROXY`（代理）
- **镜像源配置**：`NPM_MIRROR`（默认 npmmirror.com），`PYPI_MIRROR`（默认 TUNA）

### 容器配置 (`gpu/` / `nogpu/devcontainer.json`)

两份配置差异仅在两处：

| 配置项 | GPU 版 | 无 GPU 版 |
|--------|--------|-----------|
| `runArgs` | 含 `--gpus=all` | 不含 |
| `containerEnv` | 含 `NVIDIA_VISIBLE_DEVICES`、`NVIDIA_DRIVER_CAPABILITIES` | 不含 |

共同包含：

- **`runArgs`**：`NET_ADMIN` + `NET_RAW` 权限（供 iptables 使用）
- **`mounts`**：挂载 SSH 公钥（`~/.ssh/id_ed25519.pub` → 容器只读）、4 个持久化 Volume
- **`appPort`**：`${localEnv:DEVCONTAINER_SSH_PORT}` 映射到容器 2222 端口
- **`containerEnv`**：`NODE_OPTIONS`（4GB 堆内存）、代理环境变量（大/小写）、`POWERLEVEL9K_DISABLE_GITSTATUS`
- **`postStartCommand`**：`init-ssh.sh`（挂载公钥、生成/复用 Host Key、启动 sshd）

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
- 从指定 SSH 端口开始自动寻找第一个可用端口（递增扫描至 65535）
- 根据 `--gpus` 标志选择 `gpu/` 或 `nogpu/` 配置
- 通过 `DEVCONTAINER_SSH_PORT` 环境变量注入端口，执行 `devcontainer up`

## 注意事项

1. **代理配置**：`devcontainer.json` 中 `containerEnv` 默认设置了 `http://host.docker.internal:7890` 代理。如果不需要代理，请将对应项设为空字符串。

2. **host.docker.internal**：容器通过 `host.docker.internal` 访问宿主机。该域名在 Docker Desktop / OrbStack 中默认可用；Linux 原生 Docker 需在启动参数中添加 `--add-host=host.docker.internal:host-gateway`。

3. **内存限制**：Node.js 默认堆内存设为 4GB（`NODE_OPTIONS="--max-old-space-size=4096"`），可根据宿主机资源调整。

4. **SSH Host Key**：容器重建时 SSH Host Key 因 Volume 持久化而保留，避免客户端告警。如需重新生成，删除 `devcontainer-ssh-hostkey` Volume 后重建即可。

## TODO

- [ ] `init-firewall.sh`：脚本逻辑已编写（`image/init-firewall.sh`），需要调试验证并接入 `devcontainer.json` 的 `postStartCommand`。当前容器仅启动 SSH 服务，未启用防火墙。
- [ ] `proxy` 配置：目前代理地址硬编码在 `devcontainer.json` 中，考虑通过环境变量或 `.env` 文件统一管理。
