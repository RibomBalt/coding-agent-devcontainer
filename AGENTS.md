# 开发规范

## 实现

- coding agent 必须作为可选 feature 安装，不得烘焙进 base image；agent 更新频繁，保持可选可避免每次更新都重建并影响所有消费项目。
- 新增 feature 时，以 `src/<id>/devcontainer-feature.json` 作为唯一元数据来源，并在同目录提供 `install.sh`；CLI 和发布流程都扫描该元数据，避免维护重复清单。
- 只有需要向生成的 `devcontainer.json` 注入环境变量、挂载或端口等配置时，才在 `coding_agent_devcontainer/render.py` 增加对应逻辑；feature 元数据应继续作为发现和发布依据。
- feature 的 `install.sh` 以 root 运行；需要以 `node` 执行的操作用 `su -l -s /bin/bash -c "..." node`，不得依赖 `sudo`；安装阶段由 root 切换用户，而 node 没有 sudo 权限。
- feature 的 `test.sh` 以远程用户 `node` 运行，直接执行用户级配置命令，不得在脚本里再用 `su`；这样测试环境与 feature 实际消费环境一致。
- `installsAfter` 仅表示软依赖，feature 单测不会因此自动安装依赖；测试所需依赖必须由 base image 提供或由被测 feature 明确安装，避免测试依赖隐式成立。
- pnpm 全局可执行文件路径必须使用 `$PNPM_HOME/bin`；只把 `$PNPM_HOME` 加入 PATH 会导致 `pnpm add -g` 找不到全局 bin 目录。
- `${localEnv:...}` 不得放入 feature 的 `containerEnv`；宿主机环境变量应通过 `render.py` 生成到 `remoteEnv`，因为 feature 的 `containerEnv` 会写入 Dockerfile `ENV`，无法解析该表达式。
- 本地测试代理地址必须按当前环境动态获取，不得写死宿主机 IP；WSL2 等环境的宿主机地址可能变化。
- Node.js 项目按仓库现有锁文件选择包管理器；存在多个锁文件时遵循项目已有约定，避免混用工具导致依赖状态分叉。
- Python 依赖使用 `uv` 管理，代码使用 `ruff` 检查和格式化；统一工具可避免依赖与格式配置分散。

## 测试与发布

- feature 测试脚本放在仓库根目录 `test/<feature-id>/test.sh`，Python CLI 单测放在 `test/cli/`；统一目录便于现有测试入口发现和执行测试。
- 发布 GHCR 时，owner/repository 名称必须转为小写；GHCR 要求镜像仓库名称为小写。
- 发布流程以 GitHub remote 为目标，由推送 `v*` tag 触发 GHCR 发布。
- 需要发布 feature 改动时，只 bump 对应 `src/<id>/devcontainer-feature.json` 顶层的 `version`，按语义化版本递增（兼容性修复 bump patch，向后兼容的功能 bump minor，破坏性改动 bump major）；不要顺带 bump 未改动的 feature。然后创建并推送新的 `v*` Git tag 触发发布。注意发布工作流每次都会扫描并发布 `src/` 下的所有 feature。
- base image 没有单独维护的版本字段；其发布版本使用仓库的 `v*` Git tag。需要发布新的 base image 时，创建并推送下一个 `vX.Y.Z` tag；工作流检测到 `image/` 内容变化时构建新镜像并发布该 tag 与 `latest`，内容未变化时则将 `latest` 重新标记为该 tag。不要为此在 Dockerfile 另加镜像版本字段。

## 禁止事项

- 不得删除 `scripts/02-devcontainer-up.py` 兼容入口；现有调用方仍可能依赖该入口。
- 不得恢复已删除的 `gpu/`、`nogpu/`、`scripts/03-gpus-from-nogpus.py`、`image/Dockerfile` 或 `image/start-opencode-web.py`；这些旧实现已由当前 feature/base image 结构取代。
- 不得改变各层约定的 Git 身份：base image 使用 `devcontainer@localhost`，opencode feature 使用 `opencode`，codex feature 使用 `codex@openai.com`；身份用于区分基础环境与各 coding agent 的提交来源。
