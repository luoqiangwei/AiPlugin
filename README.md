# AiPlugin

用于软件设计、开发和审查的独立技能集合。

| Skill | 职责 | 入口 |
|---|---|---|
| DDD | 通用需求分析、建模、架构、实现与验证方法 | [skills/ddd/SKILL.md](skills/ddd/SKILL.md) |
| Code Review | 按语言、运行环境和具体风险审查代码 | [skills/code-review/SKILL.md](skills/code-review/SKILL.md) |
| AOSP | Android 平台机制、接口契约、版本条件与诊断知识 | [skills/aosp/SKILL.md](skills/aosp/SKILL.md) |

三个 skill 独立维护，不互相调用或要求安装彼此。各目录中的引用、脚本和 UI 元数据随相应 skill 使用。

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
