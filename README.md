# OpenCode Dev Container

基于 `node:20-slim` 构建的全栈开发容器，适用于 Python + Node.js + TypeScript 项目开发，集成 [OpenCode](https://opencode.ai) AI 编程助手。

## 容器能力

### 语言与运行时

| 组件 | 版本/说明 |
|------|----------|
| Node.js | 20 (slim) |
| Python | 3.13（通过 uv 管理） |
| OpenCode | `opencode` CLI，最新版 |

### 包管理器与镜像

| 工具 | 镜像源 |
|------|--------|
| npm | `npmmirror.com` |
| pnpm | `npmmirror.com` |
| uv / pip | TUNA (清华大学) |
| apt | TUNA (清华大学) |

### 预装工具

- **Shell**: zsh + powerlevel10k 主题 + fzf
- **Git 增强**: git-delta（语法高亮 diff）
- **编辑器默认**: vim，VSCode 集成 Prettier + Ruff + ESLint
- **浏览器测试**: Playwright + Chromium（`$PLAYWRIGHT_BROWSERS_PATH=/ms-playwright`）
- **网络工具**: iptables, ipset, dnsutils, curl, wget
- **其他**: gh (GitHub CLI), jq, ripgrep (fd-find), man-db, ssh server

### VSCode 插件（自动安装）

- ESLint, Prettier, GitLens
- Python, Pylance, Ruff
- 默认启用 format-on-save

### 安全特性

- **网络防火墙**：容器默认白名单模式出站网络，仅允许 GitHub、npm、Anthropic API、VSCode Marketplace 等必要域名通过（脚本：`init-firewall.sh`）
- **SSH 访问**：自动挂载宿主机 `~/.ssh/id_ed25519.pub` 并配置免密登录（端口 2222）
- **非 root 运行**：以 `node` 用户运行，安全命令通过 sudoers 白名单控制

## 配置方法

### 前置条件

1. 安装 [Docker](https://docs.docker.com/get-docker/)
2. 安装 [VS Code](https://code.visualstudio.com/) + [Dev Containers 扩展](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
3. 宿主机需存在 `~/.ssh/id_ed25519.pub`（用于容器 SSH 免密登录）

### 环境变量

在 `.devcontainer/devcontainer.env` 中配置：

```env
TZ=Asia/Shanghai                  # 时区
HTTP_PROXY=http://host.docker.internal:7890   # 代理（可选）
HTTPS_PROXY=http://host.docker.internal:7890
NO_PROXY=localhost,127.0.0.1
```

- 若无需代理，请将 `HTTP_PROXY` / `HTTPS_PROXY` 设为空字符串或删除

### 镜像源

如需更改镜像源，修改以下文件：

| 组件 | 文件 | 配置项 |
|------|------|--------|
| apt | `.devcontainer/debian-tuna.sources` | `URIs` 字段 |
| npm / pnpm | `.devcontainer/Dockerfile` | `ARG NPM_MIRROR` |
| uv / pip | `.devcontainer/Dockerfile` | `PYPI_MIRROR` 和 uv.toml 内容 |

## 部署方法

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd <project-directory>
```

### 2. 启动 Dev Container

在 VS Code 中打开项目，按 `F1` → 选择 **"Dev Containers: Reopen in Container"**。

首次构建约需 5-10 分钟（含镜像下载和工具安装）。

### 3. 通过 SSH 连接（可选）

构建完成后，可通过 SSH 直接进入容器：

```bash
ssh -p 2222 -o StrictHostKeyChecking=no node@localhost
```

### 4. 网络代理（可选）

若需通过宿主代理访问网络，确保 `devcontainer.env` 中已配置 `HTTP_PROXY` / `HTTPS_PROXY`，且宿主机代理监听在 `host.docker.internal:7890`。

## 数据持久化

以下目录通过 Docker Volume 持久化，容器重建后数据不丢失：

| Volume | 挂载路径 | 用途 |
|--------|---------|------|
| `opencode-bashhistory-*` | `/commandhistory` | Bash/Zsh 历史 |
| `opencode-config` | `/home/node/.config/opencode` | OpenCode 配置 |
| `opencode-local-share` | `/home/node/.local/share/opencode` | OpenCode 本地数据 |
| `devcontainer-ssh-hostkey` | `/home/node/.ssh/host_ssh_key` | SSH Host Key |

另外，宿主机 `~/.ssh/id_ed25519.pub` 以只读方式挂载至 `/ssh-auth-key.pub`，用于自动配置容器内 SSH 授权。

## 注意事项

1. **防火墙白名单**：出站网络默认被拒绝，仅 GitHub、npm、Anthropic、VSCode Marketplace 等列入白名单。如需访问其他域名，请在 `init-firewall.sh` 的域名列表中添加。当前防火墙脚本默认未启用，可取消 `devcontainer.json` 中 `postStartCommand` 的注释来启用。

2. **proxy 配置**：Docker 构建参数中的 `HTTP_PROXY` / `HTTPS_PROXY` 用于构建阶段，`containerEnv` 中的同名变量用于运行阶段。若不需要代理，两处均需清理。

3. **内存限制**：Node.js 默认堆内存设置为 4GB（`NODE_OPTIONS="--max-old-space-size=4096"`），可根据宿主机资源调整。

4. **SSH Host Key**：容器重建时 SSH Host Key 会因 Volume 持久化而保留，避免客户端告警。如确需重新生成，删除 `devcontainer-ssh-hostkey` volume 后重建即可。

5. **Playwright**：Chromium 安装在 `/ms-playwright` 而非默认用户目录，通过 `PLAYWRIGHT_BROWSERS_PATH` 环境变量指定。

6. **host.docker.internal 解析**：容器通过 `host.docker.internal` 访问宿主机（用于代理转发等），该域名在 Docker Desktop / OrbStack 中默认可用。Linux 原生 Docker 需在启动参数中添加 `--add-host=host.docker.internal:host-gateway`。
