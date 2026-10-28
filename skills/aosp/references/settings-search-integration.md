# Settings 的控制器、动态入口与索引

用于系统设置定制、菜单/搜索不一致、用户切换后可见性错误与建议状态。核实日期：2026-10-28。
官方 Settings 专题主要描述 Android 8/9 的架构及组件，源路径、类名与样式可能已迁移；机制应落到目标分支，不直接复制旧示例。

## Preference、Controller 与实际系统状态

DashboardFragment 组织页面，Preference 表达项目，Controller 负责可用性、显示/更新、点击和实际状态交互。静态 XML 负责结构，不能独立决定权限或底层操作成功。

移动一个菜单项还需要移动/复用其 Controller 及生命周期，不应同时保留两份相互竞争的监听或状态副本。开关状态应反映真实操作结果，包括拒绝、异步进行、后台变更和用户切换；不能在点击时只改变 UI 值就宣称设置生效。[Information architecture](https://source.android.com/docs/core/settings/info-architecture)

动态 tile 用 intent/manifest/category 把外部或内部 Activity 接入 Settings。显示 label/summary 不意味着目标具备同等权限；验证实际解析目标、组件可用性、用户、exported/权限与返回行为。只有需要动态组织时采用该入口，不能把任意 OEM 页面暴露为受信的系统设置。[架构与动态入口](https://source.android.com/docs/core/settings/info-architecture)

## 页面可见、可操作与可搜索是三种状态

文档中的 `SearchIndexProvider` 分别提供 XML、raw data、non-indexable keys 和 Controller。非 XML 动态条目也需要对应索引数据；原页面被替代后，旧 provider 未撤销可能产生重复或失效结果。

Non-indexable keys 要与索引键一致，并根据设备能力、当前用户和配置过滤。页面隐藏后仍能通过搜索进入，通常说明索引/入口的可用性与 Controller 不一致；删除搜索结果也不能替代目标 Activity 的授权检查。

标题、同义词、screen title 和稳定 key 承担不同职责。locale、用户、feature 和策略变化后，需核对索引重建/动态过滤与实际入口；不能把开发环境清除 Settings 全部数据当作产品更新机制。[Universal search](https://source.android.com/docs/core/settings/universal-search)

## 组件交互语义与可访问性

双点击目标的主开关，一部分进入子页，另一部分改变功能状态；点击区域、摘要、启用/禁用状态与实际操作应一致。默认 app picker 的选择还受 role/权限/可用候选限制，不能把 list selection 等同系统授权已经完成。

布局、主题、分组和 summary 应延续系统组件语义，同时覆盖无障碍、长文本和本地化。官方旧组件名或主题不是所有版本的强制实现，精确替代以目标资源和 Controller 为准。[Patterns/components](https://source.android.com/docs/core/settings/patterns-components)、[Design guidelines](https://source.android.com/docs/core/settings/settings-guidelines)

## 建议排序不改变能力与授权

Android 8 的个性化建议参考实现按显示/点击/忽略及时间信号排序，并存在默认关闭的开关。排序模型与候选的可用性、intent 有效性不同；高分不能把受限项目变成可执行项。

产品扩展需要保持 tile 与 suggestion ID 的对应，避免排序后文案和跳转错位；记录用户选择/忽略时也应遵循对应用户与状态生命周期。不能把历史默认 ranker 说成当前所有产品都运行的统一智能服务。[Personalized settings](https://source.android.com/docs/core/settings/personalized)

诊断对齐最终资源、Controller availability、实际 setting/service 值、索引记录、解析目标与当前用户，分别验证菜单进入、搜索进入和状态恢复。本页不穷举全部页面的产品信息架构、每个版本的 Search API 或 UI 视觉规范。
