# SystemUI、通知、Launcher 与应用体验

用于通知/FGS 可见性、会话、媒体控制、桌面数据、主题与文本分类定制。核实日期：2026-10-28。
先固定系统/target SDK、当前用户、包与角色、模块版本及真实状态所有者；显示合成与窗口转场见各自专页，UI 文案不代替服务状态。

## 通知许可、channel、DND 与 FGS 分别生效

Android 13 的通知 runtime permission 是 `android.permission.POST_NOTIFICATIONS`。部分 AOSP 概览中的单数拼写不能用作真实 manifest 常量。许可主要控制非豁免通知；它与通知 channel、DND、用户屏蔽和 FGS 启动资格不同。

拒绝通知权限不等于 app 不能启动 FGS，FGS 仍需提供对应通知并满足其余限制；用户能在哪里看到状态还有 Task Manager 等系统路径。升级/恢复、旧 target 的提示时机与符合条件的预授予，不能套用“所有安装一律同样询问”的简单逻辑。[通知 permission 正式行为](https://developer.android.com/develop/ui/compose/notifications/notification-permission)、[OEM 迁移责任](https://source.android.com/docs/core/display/notification-perm)

DND 管理打扰与自动规则，不等于 app 失去通知权限。历史 Android 7 的规则/闹钟/UI 说明只定义当时行为，后续版本的 policy/规则所有者需读对应接口；系统定制不能只隐藏系统 UI 而保留相反的公开 API 状态。[DND](https://source.android.com/docs/core/display/dnd)

## Conversation 与 history 的身份和留存

Conversation 用稳定的 sharing shortcut/会话身份关联 MessagingStyle、重要会话、bubble、PeopleService 与 widget。换了 conversation ID 或把多个联系人复用为一个 shortcut，可能让设置/展示关联错误；不能只给普通通知换一个布局就认为实现了会话机制。

会话数据的跨界面使用不自动授权跨用户访问；用户/profile、包、shortcut 生命周期和通知可见性应一起验证。Android 11/12 的会话与 widget 演进有对应要求，不能把页面中的 GMS 合作要求说成纯 AOSP 代码依赖 GMS 才能工作。[Conversations](https://source.android.com/docs/core/display/conv-notifications)

Notification history 包含稍后提醒、近期移除及留存期内记录，是独立可选能力。关闭时应停止记录并删除历史，而不是仅隐藏入口。当前通知撤销、history 删除与 AppOps/permission 变化也不是同一动作。[History](https://source.android.com/docs/core/display/notification-history)

## Task Manager 的停止不是普通划掉通知

Android 13 的 Task Manager 从 SystemServer 接收 FGS 状态，再由 SystemUI 提供用户停止入口。它补充通知被关闭后的资源可见性；核心功能 app 有停止入口例外，不能为方便实现把所有运行 app 都列为可任意停止。

状态上报、列表展示、用户点击、服务端停止与后续清理需要对齐。不能只移除卡片或通知来模拟 app 已停止，也不能以没有通知推断没有 FGS。[Task Manager](https://source.android.com/docs/core/display/task-manager)

## 媒体控制读取播放状态

Android 13 对满足条件的媒体控制按 PlaybackState actions 生成按钮，同时保留旧 target/缺少状态信息时的兼容路径。按钮是否出现、是否 enabled、真正执行哪个 session 的操作应一起检查；只改通知 action 可能没有改变当前使用的状态来源。

Remote playback 信息和替换 output switcher 的系统能力需要相应权限。远端设备名/icon/intent 是展示与交互数据，不能因通知长得像媒体面板就允许任意 app 冒充受信的远端控制。[SystemUI media controls](https://source.android.com/docs/core/display/media-control)

## Launcher shortcuts、widgets 与布局模型

App shortcut、pinned shortcut、widget 和图标不是一个对象。稳定 ID、发布/更新/禁用、Launcher pin 状态、包/用户恢复与真正 intent 目标共同决定能否使用。[App shortcuts](https://source.android.com/docs/core/display/app-shortcuts)

Android 8 的 pin flow 要由 Launcher 展示确认并在接受后完成添加；widget 的接受还包含相应 widget ID。发送旧添加广播、收到请求或立即返回 callback，都不能替代用户确认与实际落入桌面模型。[Widget/shortcut pinning](https://source.android.com/docs/core/display/widgets-shortcuts)

LauncherProvider 的布局导出反映数据模型，不是当前屏幕像素。导入会覆盖相应旧模型；官方行为要求方法原子、阻塞且导入后立即可读。需定位实际默认 Launcher 的 provider 能力，不能假设所有第三方 Launcher 实现该 API。

迁移时保留用户、包/组件、shortcut、widget 绑定、folder/app-pair 与网格的关系；XML 能解析不代表目标包存在或 widget 已合法绑定。导入后立即导出可验证模型一致性，真实渲染还需另查。[Home screen data](https://source.android.com/docs/core/display/home-screen-data)

Adaptive icon 的前景/背景与系统 mask 共同决定各系统表面的图形，mask/safe zone 与 round-icon 配置需一致。它不是把任意 app 图标裁成一个圆；主题资源更新也需使 Launcher、Settings 和 Sharesheet 等消费者取得一致结果。[Adaptive icons](https://source.android.com/docs/core/display/adaptive-icons)、[Circular icons](https://source.android.com/docs/core/display/circular-icons)

## 动态色是语义资源，不是面板色域配置

Material You 从颜色源生成按明度/语义分组的系统 tonal palettes，再由资源/overlay 给消费者使用；主题风格、用户选择、浅/深色和对比度影响结果。换一张壁纸、写入 theme setting、overlay 生效和应用重新取得资源，是不同阶段。

不能只更改一个 accent 常量就声称整套动态色工作，也不能把 UI 色板与显示色域/传递函数的 color management 混为一谈。具体角色/算法和风格按目标版本复核，避免硬编码当前生成的所有颜色。[Material You](https://source.android.com/docs/core/display/material)、[Dynamic color](https://source.android.com/docs/core/display/dynamic-color)

## 文本分类服务与模型更新

Android 11 的默认 TextClassifierService 位于可更新 ExtServices，旧 local classifier 返回 NO_OP 的历史变化不能靠继续调用旧入口解决。服务实现、活动模块、模型语言/版本和调用 API 都影响结果。

分类/语言/会话 action 是推断结果，不代替系统权限与用户决定；模型不存在或不支持某语言时应区分无结果、服务错误与策略拒绝。OEM 自定义服务可调用默认实现，但不能把当前 model 路径当成永久 ABI。[Text classifier](https://source.android.com/docs/core/display/textclassifier)

## Retail demo 的历史条件

官方 Retail Mode 页面同时保留“不再支持”的警告与旧实现步骤；只能作为历史集成资料，不能因网页存在就把旧服务当作当前保证支持的功能。其 device owner/demo user、provision 前状态、数据重置和消费者设置边界仍需按目标分支确认，不能只打开一个 setting 就把用户设备安全转换为 demo 产品。[Retail demo](https://source.android.com/docs/core/display/retail-mode)

本页不逐条复制全部 Notification/Launcher/Material API、UI 视觉规范、TextClassifier 模型算法或历史 demo 服务配置；应按具体变更继续读官方 reference 与目标实现。
