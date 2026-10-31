# AiPlugin

用于软件设计、开发和审查的独立技能集合。

| Skill | 职责 | 入口 |
|---|---|---|
| DDD | 通用需求分析、建模、架构、实现与验证方法 | [skills/ddd/SKILL.md](skills/ddd/SKILL.md) |
| Code Review | 按语言、运行环境和具体风险审查代码 | [skills/code-review/SKILL.md](skills/code-review/SKILL.md) |
| AOSP | Android 平台机制、接口契约、版本条件与诊断知识 | [skills/aosp/SKILL.md](skills/aosp/SKILL.md) |

三个 skill 独立维护，不互相调用或要求安装彼此。各目录中的引用、脚本和 UI 元数据随相应 skill 使用。

## 外部技能子项目

`skills/` 下除自有 skill 外，还以 git submodule 方式挂载了上游技能仓库，用于对照、取材和按需安装。它们不属于本仓库内容，不在本仓库维护，各自的许可与更新节奏以上游为准。

| 子项目 | 上游 | 用途 |
|---|---|---|
| `skills/android` | android/skills | Android 应用开发官方技能 |
| `skills/superpowers` | obra/superpowers | 开发流程骨架：头脑风暴、计划、TDD、验证 |
| `skills/mattpocock` | mattpocock/skills | 工程实战：建模、架构、TDD、排错 |
| `skills/anthropics` | anthropics/skills | 标准参考实现与 docx/pptx/xlsx/pdf 产物 |
| `skills/addyosmani` | addyosmani/agent-skills | 全流程阶段覆盖：规格、实现、审查、CI、发布 |
| `skills/vercel` | vercel-labs/agent-skills | React / Next.js 性能与设计规范 |
| `skills/openai` | openai/skills | Codex 目录：部署、Figma、CI 修复 |
| `skills/ui-ux-pro-max` | nextlevelbuilder/ui-ux-pro-max-skill | 设计系统生成 |
| `skills/impeccable` | pbakaus/impeccable | 前端设计语汇，防 AI 味界面 |
| `skills/awesome-agent-skills` | VoltAgent/awesome-agent-skills | 社区技能索引，用于检索 |
| `skills/context-engineering` | muratcankoylan/Agent-Skills-for-Context-Engineering | 多智能体与上下文工程 |

克隆本仓库后需要显式拉取子模块内容：

```sh
git submodule update --init --recursive
```

`skills/impeccable` 为浅克隆并启用稀疏检出，只保留 `skill/`、`plugin/`、`docs/`（全量约 104 MB，其中大部分是测试与 Rust crate）。该配置写在本地 `.git/modules/skills/impeccable/` 下，不会随提交传播；新克隆需要重新执行：

```sh
git submodule update --init skills/impeccable
git -C skills/impeccable sparse-checkout init --cone
git -C skills/impeccable sparse-checkout set skill plugin docs
```

## AOSP 资料与覆盖

AOSP 知识以官方文档和公开源码为依据，正文采用原创机制归纳，不分发整站手册副本。它需要结合目标分支、产品配置、运行产物和设备证据使用。

- [主题深度](skills/aosp/references/sources/topic-coverage.md)：区分机制、概览、检索入口及已知深度边界。
- [实际侧边栏](skills/aosp/references/sources/sidebar.json)：跟随官方顶部栏目标签，保留可折叠标题和后代节点；本地知识归属与直接出处分别记录。
- [侧边栏归属规则](skills/aosp/references/sources/sidebar-routes.json)：维护主题到知识文件的路由。路由存在不代表每个叶子页面的所有内容都已提炼。
- [文档目录](skills/aosp/references/sources/catalog.jsonl)与[采集状态](skills/aosp/references/sources/coverage.json)：区分正文提取、失败、待处理与范围外资料。正文抓取成功不等于语义核实完成。

PDF 规范、发布数据、生成式 API reference、外部源码及厂商实现分别承担不同证据职责；精确条款、结构和行为应按适用版本复核。工具的公开网页读取不会自动修改平台代码、设备或知识规则。

## 维护脚本

使用 Python 3 标准库，在项目根目录运行：

```sh
python3 -B skills/aosp/scripts/docs_catalog.py search "virtual ab snapshot"
python3 -B skills/aosp/scripts/docs_catalog.py sync --resume
python3 -B skills/aosp/scripts/sidebar_inventory.py --html-dir /tmp/aosp-sidebar-cache
python3 -B skills/aosp/scripts/test_docs_catalog.py
python3 -B skills/aosp/scripts/test_sidebar_inventory.py
```

`sync --resume --refresh` 重新获取正文目录；`--retry-failed` 重试失败项。侧边栏临时 HTML 缓存应位于项目外；省略 `--html-dir` 会直接重新读取导航。新增资料需核实后写入对应机制文件，并更新主题深度和导航归属。

各既有引用和上游资料的许可、出处说明保持在相应文件中。
