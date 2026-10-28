# AAOS 乘员、显示、交互与安全权限

核实日期：2026-10-28。本文把汽车导航中 Users、Displays、HMI、Scalable UI、Voice、Driver distraction、Device management 与 Security 联系起来。
这是平台机制说明；UX 声明、CTS 或权限配置不能单独证明车辆功能安全或地区法规符合性。
跨 VM 仪表安全显示另见 [automotive-sdv.md](automotive-sdv.md)，车辆属性和服务生命期见 [automotive-vehicle-services.md](automotive-vehicle-services.md)。

## 用户身份与座位拓扑

AAOS 从 Android 10 起采用 headless system user 模型：user 0 承载后台系统职责，日常使用者是 regular secondary user，guest 通常是临时身份。
admin 是用户管理角色，不能与 Linux root、Device Owner 或“唯一车主”混为一谈。
regular/guest、临时/持久、前台/后台、running/stopped、locked/unlocked 是不同轴；存储可用性仍受 CE/DE 与解锁状态控制。[多用户][users] [用户状态][user-system]

| 标识 | 所表达的对象 | 集成时应关联的关系 |
|---|---|---|
| Android user ID | 应用数据、账号和用户生命期 | 用户是否 running/unlocked、允许的跨用户调用 |
| occupant zone ID | 司机/乘客所在乘员区域 | 用户、主显示及其它外设的分配 |
| display ID / physical port / stable ID | 逻辑显示或物理连接 | API/配置究竟要求哪种 ID、热插拔后的变化 |
| seat area ID | VHAL 属性的物理座椅区域 | 车辆能力的实际控制范围 |
| audio zone ID | 音频设备、焦点和音量的独立域 | 与 occupant zone 及用户设备 affinity 的映射 |

同一用户可以有多个显示语境，一个 occupant zone 也可以包含主显示和仪表等额外显示。
换人不是简单重画头像：应用账号、输入目标、通知、音区、车辆偏好和异步回调都要归到正确用户。
官方旧 user_system 页中的默认最大运行用户数、仅一个前台用户及服务回收描述有历史版本前提；不能覆盖新分支的多显示并发可见用户配置。
即便某用户的进程还在运行，也不证明它的 Activity 可见、CE 已解锁或允许向当前乘员展示内容。[用户状态][user-system] [乘员通信][comms]

## User HAL 是 ECU 与 Android 的生命周期协议

Android 11 引入 User HAL 属性，需显式启用 `android.car.user_hal_enabled`。
`INITIAL_USER_INFO` 可让车辆按钥匙等身份线索选择默认、既有或新用户；超时/无法执行时有 Android 的回退行为。
启动耗时应区分 ECU 响应等待与用户实际启动，增加 UI 动画不能消除 HAL 超时。[User HAL][user-hal]

Modern `CarUserManager` 切换先询问 HAL，再执行 Android 用户切换，最后发送 `ANDROID_POST_SWITCH` 结果。
外部 ECU 应等最终结果再同步座椅等用户状态，否则 Android 切换失败仍可能造成物理状态改变。
legacy `ActivityManager` 流程是切换后的单向通知，HAL 无法否决；这两种入口不能视作相同安全语义。
创建用户需要处理 HAL 拒绝后的回滚；移除用户是通知，标识关联属性则可独立用于钥匙等身份机制。
请求 ID、目标用户和最终现存用户集合比“回调到过一次”更能证明 ECU/Android 状态一致。[User HAL][user-hal]

## 多显示通信与输入路由

Multi-Display Communications API 面向同一 Android 实例/单 SoC 中、不同可见用户的同包应用。
它分离 discovery、connection 与可选显示电源管理；它不是任意包之间的跨用户消息总线，也不是 SDV 跨 ECU middleware。
receiver 先接受连接，发送方才通过 `CarOccupantConnectionManager` 传递 payload；端点注册、缓存、取消和断开均有自己的生命期。[通信][comms]

receiver service 需由 `BIND_RECEIVER_SERVICE` 保护，确保只有 Framework 能绑定。
连接、发现和电源分别需要对应 privileged 权限与 allowlist，不能只声明 manifest 权限就获得资格。
Android 15 文档明确 screen-unlocked discovery flag 尚未实现，不能把该位当作已经生效的解锁授权。
CarService 死亡后应清除旧 manager/连接状态，再从生命周期回调重新获取；同包名不使旧 Binder token、旧用户或旧授权永久有效。
Control Center 的共享控制和任务镜像也使用这条边界，仍需处理接收方接受、可见用户与生命周期。[通信][comms] [Control Center][control-center]

硬件键经 VHAL/CarInputService 路由，事件的 action、keycode、target display 必须一起成立。
按下/抬起不配对会形成卡键；错误显示目标会把乘客输入送给司机；从 CAN 成功收到消息不证明窗口拥有焦点。
旧 key input 文档使用历史 HIDL/vehicle.h 常量，应在目标属性定义中核对，不能照抄数值。[按键][key-input]

旋钮输入有 rotate、nudge、中心键、返回等不同语义。rotate 可合并多个 detent，但需保留方向、首个事件单调时间及相邻 detent 间隔。
RotaryService 用 `FocusArea` 组织跨区域 nudge，用不可见 `FocusParkingView` 暂存焦点以避免跨窗口恢复失控；二者不是装饰 View。
布局焦点、滚动列表、direct manipulation 和 IME 需协同，不能把旋钮全部变成触摸坐标注入。
调试“旋钮无效”时，依次区分 VHAL 事件、目标显示、RotaryService 焦点区域和具体控件是否可聚焦。[OEM 输入][rotary-oem] [应用焦点][rotary-app]

仪表可接收 metadata 由其它系统绘制，也可由 Android 向物理/虚拟显示输出图形，两种责任不同。
早期文档以 Presentation 实现简单仪表的示例不支持完整后排多用户交互；Presentation 是绑定目标显示的 dialog，不能当成独立用户、音频焦点或输入隔离机制。
关键警示的可用性、合成归属和 Android 故障降级需结合实际安全架构，不能从一个仪表 Activity 正常运行推出。[显示][displays]

## HMI 定制的作用层

| 机制 | 适合承担的职责 | 需要维持的契约 |
|---|---|---|
| Car UI 静态库与 RRO | 颜色、尺寸、drawable、toolbar 等允许覆盖资源 | overlayable、资源版本、目标包及限定符 |
| Car UI plugin | 通过 Plugin API 替换组件实现 | API 兼容、签名/安装/发现、classloader 与回退 |
| CarSettings controller | preference 可用性、状态更新、UXR 响应 | UI 状态与服务端策略一致，搜索索引不绕过限制 |
| CarSystemUI overlay window | keyguard、通知等系统呈现和焦点 | 层次、窗口焦点、insets、遮挡与旋钮焦点 |
| Car App Library host | 代表第三方模板应用呈现 OEM 风格组件 | host/app 都存在、模板 feature 与所需权限 |

RRO 改资源，不会自动改变组件业务逻辑；旧版每目标包生成 overlay 的机制也不能替代 Android 11+ 的库资源覆盖能力。
Car UI plugin 是独立 APK 的运行时代码，通过约定 provider 被发现，可作为 shared library 被使用应用引用；版本不匹配、未启用或发现失败会影响是否采用定制实现。
GAS 兼容的最低 plugin API 版本需要单独复核，不能用 Android SDK 版本代替 Car UI API 兼容关系。[Car UI][car-ui] [Plugin][car-ui-plugin]

CarSettings 的深层 preference 可用性还取决于父级导航路径；只放开叶子键而父级不可达，用户仍无法进入。
更细粒度行为由 `PreferenceController.onApplyUxRestrictions` 等实现；“行驶时仅显示已保存 Wi-Fi”是过滤内容与限制消费共同作用。
SystemUI 的 OverlayViewController/mediator/global state 体系将视图控制、外部事件和全局层次分开；顶层 overlay、HUN、navigation/status insets 与旋钮焦点需保持一致。
把一个 overlay 设置为可见并不保证它应抢走输入焦点。[CarSettings][settings-do] [系统 overlay][overlay-window] [App Host][host]

## Scalable UI 管理的是 root task 与状态转换

Panel 对应独立管理的 root task；TaskPanel 承载应用 task，DecorPanel 承载 view 内容。
Variant 描述 bounds、visibility、layer 等视觉状态；Event 触发 Transition，Action 参与交互，WindowManager 协调转换与动画。
这种配置不是应用内部 View 的替代布局系统：把完整可启动应用放进纯装饰容器，会混淆窗口生命周期与职责。[Scalable UI][scalable]

集成需同时启用 `config_enableScalableUI`、声明 `android.software.car.splitscreen_multitasking` 并清理冲突的旧 root-task/windowing 方案。
`window_states` 引入配置，panel 的 role 连接组件数组，事件到目标 variant 的映射决定 Home、应用打开与焦点变化后的行为。
当前官方总览写明 AAOS 16+ 在禁用 Scalable UI 时无法通过 CTS；Android 17 又增加 HUN panels、system bars、Setup Wizard 与 invariants 相关能力。
这属于当前文档的版本要求，不能反向套到所有旧 AAOS 分支，也不能以“启用一个 flag”替代产品验证。[实现][scalable-implement] [版本][scalable]

窗口不变式给出可推导的故障边界：标准 Activity 启动应一次到达稳定 bounds/density，紧接着二次调整容易造成重复配置变化。
Home 应让标准 Activity 达到预期 stopped 生命周期；持续显示的特殊汽车 UI 需有明确分类。
自定义装饰不能遮住标准应用内容，需通过 SystemOverlay insets/DecorPanel 报告；immersive 请求需清除暂时 overlay/insets，不能靠立刻 resize 应用“补偿”。
任意给标准 Activity surface 裁圆角会改变像素和控件可见区域；display 级圆角与 surface 级裁剪不是同一契约。
这些原则也适用于自定义多窗口实现，不能认为只要静态截图正确就满足兼容性。[WM 不变式][invariants]

Car Display Compat 另处理手机/平板应用的密度、safe bounds 与分类，不等于该应用已经获得驾驶中使用资格。
配置的 scale 是逆比例；per-user 缓存可能使文件改动暂未生效；需同时检查应用 metadata、automotive feature 声明、系统/privileged 分类和目标显示。[显示兼容][compat]

## 驾驶分心限制由服务映射，界面持续消费

CarDrivingState 把 gear/speed 映射为 parked、idling、moving，CarUxRestrictions 再映射为可组合限制及内容长度/深度等参数。
同样的速度，档位、市场、restriction mode 或显示 physical port 配置可能带来不同限制；UI 不应自己用 speed>0 取代规则服务。
Distraction Optimized metadata 是 Activity 的声明，实际控件与内容仍需消费当前 UXR 并处理变化。[规则][uxr] [消费][uxr-consume]

保存的新配置只是 staged；需服务重启且车辆 Park 等条件满足才提升为 production。
因此 setter 成功不能证明当前驾驶中的规则已经改变；多显示缺少映射也不能凭司机屏行为推断乘客屏策略。
官方规则页还描述启动时未收到驾驶状态、配置读取失败等回退行为；目标分支要确认这些阶段是否满足产品安全设计，不能把缺失信号补为“肯定可交互”。
行驶中变化应覆盖已打开界面、返回栈和通知入口，不应只阻止新建 Activity。[规则][uxr]

通知与 voice 也受交互语境影响。HUN 可按类别排队、立即显示、前台应用节流及驾驶/停车过期时间抑制。
过期 HUN 转通知中心与删除通知是不同结果，通话/紧急类别需按配置处理，不能把所有通知统一限流。
`ACCESS_NOTIFICATIONS` 与 default notification listener 可见的内容范围不同；listener 的用户授权也可被撤销。[通知调节][notifications] [通知访问][notification-access]

## Voice：常驻入口、会话与实际执行

系统选择默认 VIA；VoiceInteractionService 是轻量入口，VoiceInteractionSession/SessionService 承担一次交互的 UI、识别及命令业务。
系统将 PTT/TTT 路由给默认 VIA，RecognitionService 对其它应用提供识别能力，SoundTrigger 的 hotword 检测又是不同链路。
所以“SpeechRecognizer 可用”不能证明 PTT、热词或锁屏入口已正确集成。[Voice 架构][voice]

VIA 对 HVAC 等车辆能力仍应通过 CarPropertyManager 和对应权限，识别出命令不使 assistant 获得任意总线访问。
assist data、截图、联系人、通知和媒体操作属于不同敏感数据/执行授权，不可因默认 assistant 身份一并信任。
Tap-to-Read 在 `CarVoiceInteractionSession.onShow` 传入 action/context，并区分 read、reply 与异常；读成功后 mark-as-read、RemoteInput reply 的 PendingIntent 必须关联正确通知及用户。
语音播报完成、发送动作触发与远端消息实际送达也不能混作同一成功状态。[Voice][voice] [Tap-to-Read][ttr]

## Unbundled 应用保持独立版本与平台约束

Dialer、Media、Car UI、Messenger 等可在独立汽车应用分支演进，各自有 minSdk、签名、privileged 与更新分发要求。
Android 13+ 平台不再直接包含这些应用的全部源码；导入 prebuilt 时需匹配目标权限 allowlist、签名和模块覆盖规则。
应用可跨多个平台版本运行，不代表每个平台的新 manager、系统 feature 或 Car API 都自动存在。[集成][unbundled]

AppCard 是 app 的 ContentProvider 产生数据、系统 host 控制样式和展示的结构，context 向 provider 给出 API/刷新频率/图片/交互能力提示。
数据更新、组件 ID 和 host 生命周期需一致；卡片显示成功不意味着其中动作已得到车辆权限。[AppCards][appcards]
App Lock 从 Android 14/API 34 起作为 platform-signed privileged unbundled app 提供独立 PIN，不等于 profile 解锁或底层数据加密边界。
媒体锁定还依赖相应 Car Media App release；恢复 PIN 的流程可能清除私有应用数据，不能把它描述为无损解锁。
Control Center 参考实现最低 SDK 35，通过 user-post-unlocked 启动的后台服务与其它 occupant zone 通信，不能仅依赖用户打开 Activity。[App Lock][app-lock] [Control Center][control-center]

## 车辆权限、安全存储与管理身份

汽车安全至少有应用权限、CarService API 校验、VHAL 消息/速率约束、SELinux/驱动接口以及独立 ECU 的边界。
系统签名、priv-app 位置、privileged permission allowlist 和具体 API 调用资格应逐项核对；同一权限不能推定所有车辆能力均开放。
旧隔离文档的 full-disk encryption 和 `android.support.car` 示例有历史前提，当前 FBE、权限名称和保护级别以分支实现为准。[车辆隔离][isolation]

Vehicle-bound encryption 将独立 ECU 上的 16-byte seed 混入文件密钥封装派生，目的在于 IVI 脱车后不能直接解密用户数据。
启用/禁用需要 factory reset；普通 OTA 不可在保留数据下直接切换。VHAL 必须足够早可用，不能在挂载 data 之前依赖 persist.*。
seed 不匹配会触发 recovery/数据擦除或重试路径；ECU 更换、维修和恢复流程需解释种子身份及数据后果。
独立存储、双向认证和安全通道分别解决取走 ECU、伪造请求和总线窃听，单独暴露一个 VHAL BYTES 不构成完整保护。[Vehicle binding][binding]

Secure developer options 可默认施加 `no_debugging_features` 与未知来源安装限制，再由 DRC 验证 OEM 签名 JWS 令牌后调整限制。
DRC 参考实现还校验受信证书链和 issuer 标识；debugging 授权不能只根据一个 Settings 页面是否可点。
多用户的默认限制、生产 user 与内部 userdebug 行为不同，应检查每类用户实际限制及令牌授权范围。
MACsec 则用 wpa_supplicant 的 MKA 与厂商 HAL 保护 CAK，在 Ethernet 链路认证/加密；它不代替上层服务授权，示例内嵌密钥也不代表生产密钥保护。[开发选项][secure-dev] [DRC][drc] [MACsec][macsec]

AAOS 的 CarDevicePolicyManager/DevicePolicyManager 还要考虑驱动态：例如请求 wipe 可先记录并通知，实际 reset 由停车后的用户流程处理。
各 API 的 create/remove/lock/reset 行为并不一致，不能统一成“车辆 moving 时所有管理调用都失败”。
官方 Automotive 设备管理页明确 Android 13+ 可声明 `android.software.device_admin`，企业模式支持 fully managed device，Automotive 不支持 Work Profile。
因此 [enterprise-device-policy.md](enterprise-device-policy.md) 的通用 profile 模型不能直接当成 AAOS 产品支持声明。[汽车管理][management]

## 失效推导与证据

| 现象 | 需要关联的证据 | 不充分的结论 |
|---|---|---|
| 换用户后座椅改变但 UI 未切换 | User HAL request/post-switch、Android 实际用户、ECU 最终提交 | 先让 ECU 切过去即可 |
| 输入进入错误屏幕 | VHAL target、display/port 映射、焦点、occupant/user | keycode 相同就应全局分发 |
| 共享显示通信被拒绝 | 可见用户、同包、feature、privileged allowlist、receiver 接受 | 同 APK 已装在两边就能连接 |
| 多窗口启动闪烁或 CTS 失败 | root task、首个 transition、最终 density/bounds、insets | 截图布局正确即生命周期正确 |
| 行驶中已打开界面仍可配置 | 当前 UXR、回调时间、display/mode、控件/返回栈 | DO 标签自动处理所有限制 |
| 维修后用户数据不可读 | ECU seed、早期 VHAL、密钥派生与 recovery 结果 | 关闭新限制即可保留旧密文 |

本文展开机制与边界；全部 Car UI 资源、Scalable UI XML 属性、Dialer/Settings/Messenger 每项业务和车型安全认证仍需按目标问题查具体子页与分支。

## 官方依据

[users]: https://source.android.com/docs/automotive/users_accounts/multi_user
[user-system]: https://source.android.com/docs/automotive/users_accounts/user_system
[user-hal]: https://source.android.com/docs/automotive/users_accounts/user_hal
[comms]: https://source.android.com/docs/automotive/displays/multi-display-comms-api
[key-input]: https://source.android.com/docs/automotive/displays/key_input
[displays]: https://source.android.com/docs/automotive/displays
[rotary-oem]: https://source.android.com/docs/automotive/hmi/rotary_controller/oem_integration
[rotary-app]: https://source.android.com/docs/automotive/hmi/rotary_controller/app_developers
[car-ui]: https://source.android.com/docs/automotive/hmi/car_ui
[car-ui-plugin]: https://source.android.com/docs/automotive/hmi/car_ui/plugins
[settings-do]: https://source.android.com/docs/automotive/hmi/car_settings/do_car_settings
[overlay-window]: https://source.android.com/docs/automotive/hmi/system_ui/management_system
[host]: https://source.android.com/docs/automotive/hmi/aosp_host
[scalable]: https://source.android.com/docs/automotive/scalableui
[scalable-implement]: https://source.android.com/docs/automotive/scalableui/implement
[invariants]: https://source.android.com/docs/automotive/scalableui/wm-invariants
[compat]: https://source.android.com/docs/automotive/app_compat/car_display_compat
[uxr]: https://source.android.com/docs/automotive/driver_distraction/car_uxr
[uxr-consume]: https://source.android.com/docs/automotive/driver_distraction/consume
[notifications]: https://source.android.com/docs/automotive/hmi/notifications/throttle-suppress
[notification-access]: https://source.android.com/docs/automotive/hmi/notifications/notification-access
[voice]: https://source.android.com/docs/automotive/voice/voice_interaction_guide
[ttr]: https://source.android.com/docs/automotive/voice/ttr
[unbundled]: https://source.android.com/docs/automotive/unbundled_apps/integration
[appcards]: https://source.android.com/docs/automotive/unbundled_apps/appcards
[app-lock]: https://source.android.com/docs/automotive/unbundled_apps/app-lock
[control-center]: https://source.android.com/docs/automotive/unbundled_apps/control-center/technical-details
[isolation]: https://source.android.com/docs/automotive/security/vehicle_system_isolation
[binding]: https://source.android.com/docs/automotive/security/vehicle-bound
[secure-dev]: https://source.android.com/docs/automotive/security/secure_dev_options
[drc]: https://source.android.com/docs/automotive/security/drc
[macsec]: https://source.android.com/docs/automotive/security/macsec
[management]: https://source.android.com/docs/automotive/device_management
