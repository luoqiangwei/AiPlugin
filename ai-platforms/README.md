# AI 平台、框架与自动化子项目

`ai-platforms/` 统一收录 AI 应用平台、Agent 开发框架/SDK 和工作流自动化项目，通过下表的类型标注各自用途。各上游以 Git submodule 管理，父仓库记录上游地址与固定提交，用于源码研究、架构对照和按需构建。

## 项目目录

| 类型 | 子项目 | 上游 | 研究方向 |
|---|---|---|---|
| AI 应用开发平台 | [dify](dify) | [langgenius/dify](https://github.com/langgenius/dify) | 可视化工作流、RAG、Agent、模型接入、应用 API 与可观测性 |
| AI 应用开发平台 | [coze-studio](coze-studio) | [coze-dev/coze-studio](https://github.com/coze-dev/coze-studio) | Agent 与应用的可视化开发、调试、发布，知识库和插件集成 |
| AI 应用开发平台 | [langflow](langflow) | [langflow-ai/langflow](https://github.com/langflow-ai/langflow) | 可视化构建 Agent/工作流，API、MCP 与组件编排 |
| AI 应用开发平台 | [fastgpt](fastgpt) | [labring/FastGPT](https://github.com/labring/FastGPT) | 知识库、模型调用、Flow 工作流与 Agent 应用构建 |
| Agent 开发框架/SDK | [langchain](langchain) | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) | Agent/LLM 应用开发、模型、工具与第三方组件集成 |
| Agent 开发框架/SDK | [langgraph](langgraph) | [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | 有状态、长时运行 Agent 的编排、持久执行、记忆与人工介入 |
| Agent 开发框架/SDK | [crewai](crewai) | [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI) | Crews 多角色协作与 Flows 事件驱动工作流 |
| Agent 开发框架/SDK | [metagpt](metagpt) | [FoundationAgents/MetaGPT](https://github.com/FoundationAgents/MetaGPT) | 角色、SOP 与多 Agent 软件开发协作 |
| Agent 开发框架/SDK | [openai-agents-sdk](openai-agents-sdk) | [openai/openai-agents-python](https://github.com/openai/openai-agents-python) | Python Agent 循环、工具调用与多 Agent 工作流 SDK |
| Agent 开发框架/SDK | [google-adk](google-adk) | [google/adk-python](https://github.com/google/adk-python) | 代码优先的 Python Agent 构建、评估、部署与编排 |
| Agent 开发框架/SDK | [microsoft-agent-framework](microsoft-agent-framework) | [microsoft/agent-framework](https://github.com/microsoft/agent-framework) | Python/.NET Agent、多 Agent 工作流、检查点与人工介入 |
| Agent 框架与运行平台 | [agno](agno) | [agno-agi/agno](https://github.com/agno-agi/agno) | Agent SDK、团队与工作流，以及 AgentOS 持久服务和编排 |
| 历史框架参考 | [autogen](autogen) | [microsoft/autogen](https://github.com/microsoft/autogen) | 多 Agent 对话与协作实现；上游 README 已宣布停止维护 |
| 工作流自动化平台 | [n8n](n8n) | [n8n-io/n8n](https://github.com/n8n-io/n8n) | 可视化与代码工作流、业务系统连接及 AI Agent 自动化 |

## 上游说明

以下说明基于 2026-10-31 核对的上游信息：

- 所有上述项目统一放在本目录；类型标签用于说明研究方向。同一仓库兼有 SDK、平台或自动化能力时，只挂载一次。
- AutoGen 的 README 已宣布归档、停止维护，并推荐新用户使用 Microsoft Agent Framework；本目录同时保留历史实现和后继框架。该声明不等同于 GitHub 仓库已设置为只读。
- MetaGPT 使用当前上游 `FoundationAgents/MetaGPT`，旧 `geekan/MetaGPT` 按同一仓库去重。
- Agno 使用当前上游 `agno-agi/agno`，旧 `phidatahq/phidata` 与 `agno-agi/phidata` 按同一仓库去重。
- Dify、FastGPT 的许可包含自定义附加条件；n8n 为 fair-code/source-available，使用 Sustainable Use License 及企业许可。各项目的使用条件以其 LICENSE 和组件说明为准。

## 拉取与维护

在 AiPlugin 项目根目录拉取本目录全部子模块：

```sh
GIT_LFS_SKIP_SMUDGE=1 git submodule update --init --depth 1 -- \
  ai-platforms/dify ai-platforms/coze-studio ai-platforms/langflow ai-platforms/fastgpt \
  ai-platforms/langchain ai-platforms/langgraph ai-platforms/crewai ai-platforms/metagpt \
  ai-platforms/openai-agents-sdk ai-platforms/google-adk ai-platforms/microsoft-agent-framework \
  ai-platforms/agno ai-platforms/autogen ai-platforms/n8n
```

首次收录使用浅克隆并固定提交；Git LFS 大文件按需获取，工作区可能保留相应指针。需要这些资源时，在对应子模块中执行 `git lfs pull`。嵌套子模块、运行环境、模型服务及外部系统连接按各上游文档配置。

后续更新应明确选择目标提交，再提交父仓库的子模块指针。添加新项目时，先检查 `.gitmodules` 和已有仓库的 `origin`，按迁移后的上游地址跨 `skills/`、`agents/`、`ai-platforms/`、`model-training/`、`model-serving/` 去重。
