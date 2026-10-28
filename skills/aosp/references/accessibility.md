# 无障碍：语义树、服务能力与交互变换

本页用于读屏、焦点、节点动作、系统放大、字体和无障碍服务变更。核实日期：2026-10-28。
先确定目标 API/分支、用户、display、已启用服务及能力声明；最新 SDK 页面同时包含新 API，不等于旧平台具备这些能力。
平台定位通常从 `frameworks/base/services/accessibility`、`AccessibilityManager`、View/节点提供端及 SystemUI 开始，实际职责查目标树。

## 系统提供的是语义与受控动作，不是另一张截图

应用 View 或自定义 provider 描述可理解的节点与动作，框架组织窗口、事件与服务连接，服务再提供语音、触觉或其他交互反馈。
AccessibilityEvent 表示某类变化；AccessibilityNodeInfo 是可查询的语义节点；AccessibilityWindowInfo 描述交互窗口，三者不能互相替代。[2][][3][][4][]
像素可见不代表节点存在，节点存在也不保证正在显示或支持任意 action。
自绘内容可通过虚拟子节点暴露逻辑结构；不应要求每个语义对象对应一个真实 View，也不靠重复 contentDescription 代替结构。[3][]

- 标签、角色、状态、层次、可执行动作和遍历关系共同决定可用性，不能只检查“读出文字”。
- 输入焦点和无障碍焦点用途不同；改变一个焦点不应无条件抢走另一个。
- 事件应对应实际变化和适当类型，避免大量无意义 announcement 淹没状态或打断用户。
- 完整窗口变化、窗口中的 pane 变化和内容变化有不同事件语义，不能统一伪装成应用切换。

## 服务启用与能力边界

AccessibilityService 需要声明系统绑定入口，以 `BIND_ACCESSIBILITY_SERVICE` 限制由系统绑定；它不是普通 app 请求一次运行时权限就能得到的授权。[1][]
服务已安装、由系统绑定、被当前用户启用，以及声明了某项 capability，是不同条件。
读取窗口内容、请求触摸探索、执行手势及控制放大有各自能力/flag；不要通过给 APK 提权一并打开所有功能。
多用户/工作资料与服务死亡后的重绑定应遵循目标平台策略，不能把一个用户的服务连接、节点或反馈带到另一个用户。

- 查询交互窗口需要对应内容检索能力与 opt-in；窗口列表不是系统所有窗口的无条件完整枚举。
- active window 不等同于所有情况下的视觉最上层；它与用户触摸和输入焦点有关。[4][]
- 多 display 下保留 display/window 身份，不能把 active root 默认解释为主屏当前 Activity。
- 关闭服务或撤销能力后及时停止相应访问与输入，不能仅移除 Settings 中的开关。
- 平台预装服务、用户启用界面和 Direct Boot 等兼容责任按目标版本 CDD 核查；[8][]仅给出 Android 15 的具体入口。

## 节点与事件是会过期的观察

收到事件后 UI 可能已经变化；事件来源可能不再可查询，不能假设每个事件都携带一棵完整、最新的节点树。[2][]
节点属于某个窗口与节点提供者的当时状态；重新布局、窗口销毁、列表复用和远端进程死亡都会使缓存过期。
`refresh()` 可以失败，表示原节点已不在树中；反复点击旧引用不是可靠的恢复策略。[3][]
跨线程使用事件要遵守回调对象寿命；服务回调返回后继续使用时需按该 API 契约复制，不能无条件持有调用方对象。[1][]

- 动作前验证窗口/节点身份及当前状态，动作后观察实际结果；返回成功不证明用户目标已经完成。
- 自定义控件需真实实现其声明的 action，并同步状态和事件；不能只增加“可点击”标记。
- 修复缺失语义优先落在节点提供端，修复事件过滤落在相应过滤/分发层，避免全局扩大数据访问。
- 异步结果到达时检查当前用户、display 和窗口代次，防止过期结果改变新界面焦点。

## Window magnification 与坐标

Android 12 引入局部窗口放大，与全屏放大可按用户选择切换；Android 14 增加对应尺寸选项。[5][]
放大不是简单增大某个应用 View 的布局尺寸；显示区域、放大源区域、控制窗口和触摸变换需要协同。
服务控制放大需声明对应 capability；系统放大状态不能被单个 app 或一次手势随意重置。

- 区分原始触摸、逻辑显示、窗口、节点 bounds 与放大后坐标；不要把截图像素直接当动作坐标。
- 手势派发会进入触摸交互路径，并可能取消已有手势；不能把它当独立、不干扰用户的点击 RPC。[1][]
- 验证放大区域移动、模式切换、旋转、多显示和触摸探索的组合，不只检查放大图像清晰。
- 功能开关、用户偏好与运行态分别维护，不能用修改资源默认值覆盖用户选择。

## 读屏语义与屏幕捕获授权分别判断

节点内容检索、截图/录屏、输入注入与安全图层访问是不同授权通路，不因“无障碍已开启”而自动等价。
restricted screen reading 页面描述 Android 10 起限制 privileged app 静默捕获屏幕 buffer；它不是“禁止所有语义读屏”的规则。[6][]
不具备相应 signature 权限的捕获使用 MediaProjection 等用户同意路径；不能用普通预装身份绕过。
敏感节点、密码文本、安全内容及服务能力限制按目标分支规则处理；无障碍支持不能成为扩大敏感数据日志的理由。

- 诊断只记录必要的事件类型、窗口/节点身份、状态及错误，避免批量输出用户文本、密码或屏幕内容。
- 某节点不可读、capture 失败和 action 被拒绝应分别定位，不能把所有失败都修成扩大权限。
- 测试用户拒绝、服务关闭、锁屏与用户切换，确认功能退化有清晰状态而不是继续使用旧缓存。

## 字体缩放与布局语义

Android 14 起支持最高 200% 非线性字体缩放，大字号与小字号的倍率并不相同。[7][]
字体大小、display density、显示尺寸和屏幕放大是不同设置；不能统一用一个 scale 乘全部坐标。
文字使用平台支持的 sp 转换；不要手算 `fontScale × px` 或把非线性的 sp 当 padding/固定 View 高度单位。
布局需允许换行、重新测量与可达操作，避免文本被截断、覆盖按钮或使节点 bounds 与实际触摸区域分离。
语义树完整不代表大字体可用；大字体界面可见也不证明读屏顺序和焦点恢复正确。

## 用机制与证据判断修复

| 现象 | 先关联的证据 | 判断方向 |
|---|---|---|
| 能看到但读不到 | 提供端节点、服务能力、事件过滤、窗口身份 | 缺语义还是访问边界，不先放宽全局权限 |
| 读错/动作错位 | 事件时间、缓存刷新、窗口代次、bounds/变换 | 过期节点或坐标空间混用 |
| 放大后无法操作 | 放大模式、source/display区域、输入路由、焦点 | 显示与触摸是否使用同一变换 |
| 大字体内容丢失 | OS、字体/密度设置、布局与节点区域 | 重新测量与非线性转换，不缩小用户字体 |

实现时同时维护节点状态、事件和实际动作；回归包含读屏/键盘/触摸探索、窗口切换、最大字体及服务重连。
自动节点检查补充语义契约，真实交互验证反馈、顺序和操作可达性；无匹配设备/服务时明确未验证组合。

## 已核实的官方深读入口

1. [AccessibilityService：绑定、能力、窗口与手势](https://developer.android.com/reference/android/accessibilityservice/AccessibilityService)
2. [AccessibilityEvent：窗口、内容与来源语义](https://developer.android.com/reference/android/view/accessibility/AccessibilityEvent)
3. [AccessibilityNodeInfo：虚拟节点、动作与刷新](https://developer.android.com/reference/android/view/accessibility/AccessibilityNodeInfo)
4. [AccessibilityWindowInfo：active/focused 窗口](https://developer.android.com/reference/android/view/accessibility/AccessibilityWindowInfo)
5. [Window magnification：版本、模式与交互](https://source.android.com/docs/core/display/window-magnifier)
6. [Restricted screen reading：屏幕 buffer 捕获授权](https://source.android.com/docs/core/permissions/restricted-screen-reading)
7. [Android 14 非线性字体缩放](https://developer.android.com/about/versions/14/features#non-linear-font-scaling)
8. [Android 15 CDD 无障碍责任；实施时切目标 CDD](https://source.android.com/docs/compatibility/15/android-15-cdd#3_10_accessibility)

[1]: https://developer.android.com/reference/android/accessibilityservice/AccessibilityService
[2]: https://developer.android.com/reference/android/view/accessibility/AccessibilityEvent
[3]: https://developer.android.com/reference/android/view/accessibility/AccessibilityNodeInfo
[4]: https://developer.android.com/reference/android/view/accessibility/AccessibilityWindowInfo
[5]: https://source.android.com/docs/core/display/window-magnifier
[6]: https://source.android.com/docs/core/permissions/restricted-screen-reading
[7]: https://developer.android.com/about/versions/14/features#non-linear-font-scaling
[8]: https://source.android.com/docs/compatibility/15/android-15-cdd#3_10_accessibility
