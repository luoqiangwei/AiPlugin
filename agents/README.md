# 开源 Agent 子项目

收录用于源码研究、架构对照和二次开发的开源 Agent。各仓库以 Git submodule 管理，父仓库记录上游地址与固定提交；使用、构建与许可要求以各子项目文档为准。

## 项目目录

| 子项目 | 上游 | 研究方向 |
|---|---|---|
| [pi](pi) | [earendil-works/pi](https://github.com/earendil-works/pi) | 可扩展终端编码 Agent、Agent runtime、统一模型 API、TUI 与 TypeScript SDK |
| [opencode](opencode) | [anomalyco/opencode](https://github.com/anomalyco/opencode) | 终端和桌面编码 Agent、计划与构建模式、子 Agent |
| [codex](codex) | [openai/codex](https://github.com/openai/codex) | 本地编码 Agent 与终端交互实现 |
| [gemini-cli](gemini-cli) | [google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli) | Google 终端编码 Agent、工具调用与开发工作流 |
| [cline](cline) | [cline/cline](https://github.com/cline/cline) | 编码 Agent 共享核心、CLI、VS Code 扩展、工具与交互审批 |
| [aider](aider) | [Aider-AI/aider](https://github.com/Aider-AI/aider) | 终端结对编程、代码库映射、补丁编辑、Git 与测试闭环 |
| [goose](goose) | [aaif-goose/goose](https://github.com/aaif-goose/goose) | 本地通用 Agent、Rust 核心、桌面与 CLI、MCP 扩展 |
| [openclaw](openclaw) | [openclaw/openclaw](https://github.com/openclaw/openclaw) | 个人与团队助手、Gateway、多聊天渠道、工具和插件系统 |
| [openhands](openhands) | [OpenHands/OpenHands](https://github.com/OpenHands/OpenHands) | Agent Canvas 开发控制台、会话界面与多后端编排 |
| [openhands-sdk](openhands-sdk) | [OpenHands/software-agent-sdk](https://github.com/OpenHands/software-agent-sdk) | OpenHands 核心 Agent、工具、会话、工作区与 Agent Server |

以上来源于 2026-10-31 核对的上游仓库信息：

- Pi 原仓库 `badlogic/pi-mono` 已迁至 `earendil-works/pi`，两者按同一仓库去重。
- Goose 原仓库 `block/goose` 已迁至 `aaif-goose/goose`，两者按同一仓库去重。
- OpenHands 主仓当前负责 Agent Canvas；核心 Agent 实现在独立的 `software-agent-sdk` 仓库中，因此分别收录。
- Gemini CLI 当前上游 README 面向企业 Code Assist 工作流；具体运行方式以其最新文档为准。
- Cline 此仓库包含开源 Agent 实现；其 JetBrains 插件当前未包含在开源范围内。

## 拉取与维护

在 AiPlugin 项目根目录拉取全部 Agent 子模块：

```sh
git submodule update --init --depth 1 -- agents/pi agents/opencode agents/codex agents/gemini-cli agents/cline agents/aider agents/goose agents/openclaw agents/openhands agents/openhands-sdk
```

首次收录使用浅克隆，保留完整的当前提交源码。后续更新上游时应明确选择目标提交，再提交父仓库中的子模块指针。上游的嵌套子模块、构建依赖和模型服务按实际研究需求配置。

添加其他项目时，先检查根目录 `.gitmodules` 和已有仓库的 `origin`，按迁移后的上游地址跨 `skills/`、`agents/`、`ai-platforms/`、`model-training/`、`model-serving/` 去重。
