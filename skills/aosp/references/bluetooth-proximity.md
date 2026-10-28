# 蓝牙与近场：profile、控制器、支付路由和测距会话

适用于 Bluetooth Classic/BLE、音频 offload、NFC/SE/钱包、UWB、跨技术 ranging 与 presence 校准。核实日期：2026-10-28。固定 Android/模块版本、chip/firmware、HAL、对端协议/能力和角色。协议规定、Android 对主机/控制器的扩展契约及某厂商实现分别取证；硬件标准版本不等于该版本全部 profile/API 可用。

## Bluetooth：bond、链路、profile、媒体路由分开

[Bluetooth 架构](https://source.android.com/docs/core/connect/bluetooth) 是应用 API/Binder → Bluetooth app/profile services → JNI → native host stack → vendor HAL/HCI → controller。当前常见目录为 `packages/modules/Bluetooth/{framework,android/app,android/app/jni,system}`。主机实现 profile/策略，controller 执行无线链路，vendor HAL 连接二者；不能把 Java callback 当空口应答。模块从 Android 13 引入，Android 16 起支持相应可更新交付，需核对实际产品包和依赖。[Mainline](https://source.android.com/docs/core/architecture/modular-system/bluetooth)

设备发现、配对/bond、安全链路、profile service 连接、codec/音频数据路径及系统媒体路由有不同所有者。由此可推导：设备列表显示“已配对”不足以证明 profile 可用；A2DP 已连接不足以证明正在播放；一个 profile 断开也不应无条件删除全部 bond。重启 Bluetooth/controller 后，旧 connection handle、advertising instance、callback 与 offload 流均需重新核对，不能套用重启前状态。

## Services 与音频路径

[Bluetooth services](https://source.android.com/docs/core/connect/bluetooth/services) 的 profile 矩阵主要覆盖 Android 6–8，**不是当前完整能力清单**，其“仅 Classic 音频”的历史描述也不能否定 ASHA/后续 LE Audio。读取目标版本 profile service、公开能力及对端支持，避免把所有蓝牙设备当一种流。

| 功能 | 协议/状态边界 |
|---|---|
| A2DP/AVRCP | A2DP codec 协商和编码/传输，AVRCP 控制/绝对音量分别建立；音量反馈应避免本地/对端反复回送，最终路由还需 Audio Framework |
| HFP/HSP | 免提控制、呼叫状态与 SCO/eSCO 媒体通路分开；PBAP 联系人同步成功不证明通话音频成功 |
| MAP/PBAP | 消息/电话簿访问属于对应服务与授权，历史正文的 MAP SMS 范围不应泛化为任意邮件/IM 同步 |
| OPP/OBEX、SPP、HID/HOGP、PAN/BNEP、SAP | 对象交换、串行、输入、IP 共享和 SIM 访问各有 profile 生命周期/数据面；PAN 连上还需 IP provisioning/转发，SAP 连接也不等于本机订阅业务已成功 |

[A2DP offload 的 HCI 契约](https://source.android.com/docs/core/connect/bluetooth/hci_requirements) 将编码与数据流交给音频处理器直接送 controller，主机继续管理会话配置/启停。codec 协商、Audio HAL、controller capability 与实际 offload 版本必须相容；offload 不表示主机已失去 stop/cleanup 责任。新命令按 connection handle、L2CAP channel 和 direction 区分流，不能用旧无实例 stop 模型处理所有并发流。动态 buffer 依据能力上下界调节，用延迟交换抗抖动，不能把增大 buffer 当作射频/调度故障的通用修复。音频路由和延迟另见 [音频框架](audio-framework-policy.md)、[音频 I/O](audio-performance-io.md)。

## BLE：广播、发现、GATT 与 offload

[BLE](https://source.android.com/docs/core/connect/bluetooth/ble) 的 central/peripheral 是发现/连接角色，GATT client/server 是访问属性数据库的角色，二者不能简单绑定，通知方向也不决定永久的 client/server 身份。权限需同时看 OS、target SDK、是否用于位置及附近设备权限；Android 12 的 `BLUETOOTH_SCAN/ADVERTISE/CONNECT` 与旧版本位置授权不同。声明 `neverForLocation` 不是任意后台定位通行证。

[Advertising](https://source.android.com/docs/core/connect/bluetooth/ble_advertising) 先查询 2M/Coded PHY、extended/periodic advertising 等实际能力，再创建 `AdvertisingSet`；启动、数据变更、参数变更、enable/disable、stop 分别由 callback 确认，不能未等启动完成就操作无效 instance。primary 与 secondary PHY 有各自合法组合，旧广播/扩展广播、controller 容量与 payload 大小分别限制。无广播结果可能是权限、scan filter、PHY 不兼容、实例资源或 RF，不能统一归因对端没开机。

[HCI requirements](https://source.android.com/docs/core/connect/bluetooth/hci_requirements) 规定能力查询、batch scan、APCF、能耗/质量报告和 offload；扩展版本与 Bluetooth Core 标准版本不是同一个数字。能力缺失时按接口规定降级，旧厂商 multi-advertising/RPA 命令在新扩展版本已由标准 HCI 路径替代，不应盲目保留双份控制。

扫描 offload 的关键所有权是 host 分配 filter/资源和 controller 执行匹配/存储/OnFound-OnLost：同一报告可命中多个 app/filter 并采用不同 delivery mode；停止一个 app 不得清空其他 app 的 filter。batch buffer、去重键、读取直到无记录、相对时间戳和丢弃策略共同决定结果，callback 时间不是空口接收时间。APCF 不过滤 periodic advertising，不能把它解释为所有 BLE 报告的总开关。

Sniff offload 还区分控制器全局 enabled 与每 ACL 的 pending-parameters/control-started；host 按 profile 活动选参数，controller 决定进入/退出时机。事件抑制也受 host mask 约束，缺少 mode-change callback 不一定代表状态没变。ISO feedback、BIG channel classification 和连接 proximity threshold 是各自需能力门控的后续扩展；它们不证明对端身份或安全测距。完整 opcode/bitmask 表留在原规范，不能照扩展版本号假设每项能力都有实现。

## ASHA：控制用 GATT，音频用 LE CoC

[ASHA](https://source.android.com/docs/core/connect/bluetooth/asha) 把左右助听器看成一个音频 sink，单侧丢失时混成单声道，两侧都失联才丢失整个 sink。此处配对集合由 HiSyncId/左右属性关联，不应与 Bluetooth bond 概念完全合并。ASHA 通过 GATT 读取属性、PSM、codec、render delay 及控制/status，实际音频走 LE credit-based L2CAP CoC；这与标准 LE Audio profile 不是同一协议。

开流次序是查询共同 codec/PSM → 建 CoC/credits → 完成所需连接参数更新 → encoder/sequence 重置 → 写 Start → 等 status 成功 → 送音频；Stop 后重新启动要重建相应流状态，空闲仍可保留 GATT 链路。音频必须加密。序号和连接事件时序用于双耳同步，peripheral 负责最终同步播放；加深弹性 buffer 会增加时延。ASHA 无耳端音频回传，通话输入用 central 麦克风，不能从助听器播放正常推断其麦克风应可录音。

## AIS 与诊断证据

[Android information service](https://source.android.com/docs/core/connect/bluetooth/os-identification) 从 Android 14 提供 GATT API level characteristic，Android 作为 server；可发现状态下与不可发现状态下的读取授权不同。API level 只是能力适配线索，不是设备认证、具体 module/HAL 版本或全部 profile 能力证明。

[Verify/debug](https://source.android.com/docs/core/connect/bluetooth/verifying_debugging) 提供 `dumpsys bluetooth_manager`、bugreport/btsnooz、HCI snoop 及 profile 互通测试。HCI 记录 host-controller 边界，并非完整空口 trace；offload 音频可能不出现在普通 host 数据日志。BQR 的 choppy/LSTO、重传、underflow、coex 与 controller fatal 事件应与 profile、Audio Framework 和同时间 RF 条件关联；计数有按报告/重置清零语义，不能跨 reset 直接相减。全量 snoop 可能含个人数据，选择相应日志模式并按数据作用域处理。

## NFC、SE 和钱包：三种路由状态必须一致

Android 的标签读取、host card emulation、off-host SE card emulation、Reader/poll 与 listen/observe 模式各有控制路径。NFC 开关开启不证明卡路由、安全策略或交易完成。[NFC Services](https://source.android.com/docs/core/ota/modular-system/nfc-services) 在 Android 16 成为可选可更新模块，包含 API、系统 APK、JNI/NCI stack，vendor 仍负责 HAL，SE 另有执行与授权边界。早期树路径/交付方式须另查。

[FeliCa HCE](https://source.android.com/docs/core/connect/felica) 用 NFC-F 硬件、`HostNfcFService` 与对应 feature，实现 host 侧卡模拟；不能把它当作所有 FeliCa 交易都经过 host，更不能用 HCE feature 证明 SE applet 已部署。

[Secure NFC](https://source.android.com/docs/core/connect/secure-nfc) 允许用户要求解锁后才能 off-host 卡模拟，依赖 controller/NCI 2.0 等前提。锁屏、灭屏、设备关机与普通 NFC 路由状态必须分别验证；仅 UI 开关变化不证明 controller 已改变允许交易状态。

[Off-host payment synchronization](https://source.android.com/docs/core/connect/offhost-payment-sync) 对齐默认付款服务、CLF 路由和 SE 中 app-selected 状态。获取 preferred service AID/route/描述受专用权限保护，默认服务变化广播是同步触发，不是交易结果。由此可推导：只改 Tap & pay UI 可能仍使用 SE 内旧 app；同时部署多个 SE app 时要用读卡器结果确认真正执行者。

[Quick Access Wallet](https://source.android.com/docs/core/connect/quick-access-wallet) 的 SystemUI 展示与默认支付 app 的 `QuickAccessWalletService` 交互，绑定受专用 signature 权限约束。Android 11 的 power-menu plugin 与 Android 12+ SystemUI 入口不同。取卡、选卡、dismiss、支付开始事件应形成一致生命周期；选卡回调可能重复，应保持幂等。展示卡片、选择支付方式和 NFC APDU 交易成功各有独立确认，支付 app 需确保所选卡真正用于后续交易。锁屏显示、解锁后重新取卡与可访问性状态也不是 Secure NFC 本身。

## Android NCI 扩展：能力与 RF 状态控制

[Proprietary NCI commands](https://source.android.com/docs/core/connect/android-proprietary-nci-commands) 是 Android 在 NCI vendor 空间的明确协议，不能当作任意厂商私有命令的通用字节表。先 query capabilities，命令或单项能力未支持按各自默认值处理；Android 要求版本、NCI core 版本、controller 的具体能力分开。

Observe mode 阻止 controller 在 listen polling loop 自动响应，先向 host 报 field/polling frame，再由策略放行交易；普通 poll mode 仍按其协议执行。exit-frame table、per-technology observe 控制、suspend/resume notification 与 reader annotation 分别有生效条件，某些修改仅允许 RFST_IDLE。power-saving command 后通信行为也受专门约束，返回全功耗需相应重置/初始化。由此推导：付款延迟/无响应要保留 RF field、polling 通知、observe 状态及 release/exit 条件；不能只靠重发 APDU 或关闭全局 NFC 绕过会话契约。逐字段长度、端序和保留位必须读目标版本表，本文不穷举。

## UWB：framework session 与 UCI/HAL 双重生命周期

[UWB](https://source.android.com/docs/core/connect/uwb) 从 Android 13 提供默认框架：API/support library、UwbService/CSML、native UCI → stable AIDL HAL → vendor driver/chip。系统 `UwbManager` 与第三方 Jetpack API 不同。HAL 的 `open/close/coreInit/sessionInit` 及 `sendUciMessage/onUciMessage` 是控制通道，真正的 UCI response/notification 才表达命令/会话进展；Binder 发送成功不等于已开始测距。

[UWB HAL interface](https://source.android.com/docs/core/connect/uwb-hal-interface) 区分 FiRa UCI version、Android vendor UCI version 与可用 capability/TLV。range diagnostics、power stats、AoA interleaving 只在相应能力支持时启用；历史模块接受的 draft CR 也不能视为永远稳定。session conflict、非法 AoA channel、法规禁用有不同状态码与 notification reason，需关联 sessionId。

国家码来自 framework 多源策略并下发 controller；未知国家码或法规不允许可使 stack DISABLED，获得有效码后才可能 READY。国家码变化、HAL init 成功与 session ACTIVE 是不同条件，不能用强制国家码消除产品真实约束。测距结果还需核对对端地址、session key/config、时序与环境，发现对端或 UI 开关打开均不足以证明测距可用。

## Ranging OOB：交换配置，不替代底层无线与授权

[OOB v1](https://source.android.com/docs/core/connect/ranging-oob-spec)、[v2](https://source.android.com/docs/core/connect/ranging-oob-spec-v2)、[v3](https://source.android.com/docs/core/connect/ranging-oob-spec-v3) 定义 capability request/response、configuration、stop 等消息及 payload。它们不规定特定传输，分片/重组由 OOB channel 实现承担，Ranging module 接受完整消息。共同 header、technology ID、bitfield、块 size、版本协商必须一起解析，不能从系统版本直接猜对端 wire format。

- v1 随 Android 16 Ranging，引入 UWB、BLE CS、Wi-Fi NAN RTT、BLE RSSI；连接型先请求，广播型可由 responder 宣告能力。
- v2 为 Android 16 QPR3，追加 device type 和 technology-transitioning 能力；只有 responder 支持 make-before-break 才能在旧技术停止前启动新技术，否则需先 stop。
- v3 为 Android 17，增加 motion 通知/请求与 Wi-Fi proximity detection，部分 NAN RTT capability 字段弃用；当前 v3 正文以连接型请求链描述，不应原样套用 v1 广播流程。

双方使用共同可理解的版本，新字段追加/超长部分按规范处理；端序是字段级契约（通常 little-endian，但地址及部分字段有例外）。responder 要能处理多次/乱序 capability 请求，不能假设每条连接只初始化一次。configuration 的“设置成功”、底层 session 启动和连续测量有效各自确认；可选 response 是否需要取决于 OOB channel，不宜用等待一个本来可选的响应制造死锁。

UWB config ID 隐含一组参数，必须从共同支持集中选，不能任意拼接 key/channel/interval；每次 UWB session 结束后重查能力，因为对端地址可轮换。BLE CS 需要既有 bond/链路安全前提，OOB 协议不负责建立 bond；CS 由 initiator 通过 Bluetooth 发起，responder 不像 UWB 那样必须额外调用 start/stop API。跨技术 stop bitfield 只停止指定技术，不能意外杀掉 make-before-break 尚在使用的另一条会话。OOB 成功交换不证明认证或距离可信，相关安全前提还需底层和应用契约。

## Presence 校准：分布、偏差与产品几何

[Presence calibration](https://source.android.com/docs/core/connect/presence-requirements) 把 Android 14+ 的 UWB、NAN RTT、BLE RSSI 校准和相应 CDD/CTS 条件联系起来。UWB/RTT 要区分距离偏置与随机分散，BLE 要区分芯片/core/channel 校准和整机天线导致的 Rx/Tx offset。使用相应参考设备、朝向、LOS/反射条件、距离与足量采样；手机、电视等形态的交互几何不同。

单点 RSSI 门槛不能跨设备保证“距离小于一米”，更不能作为身份认证。周期峰值可能来自未校准的天线 core/广告信道，应结合原始样本和切换周期推断；调一个应用阈值不能补偿所有整机差异。规范 KPI 与测试数量是特定版本/设备条件下的合规标准，本文不提供跨版本固定阈值。

本页覆盖 Bluetooth Overview/Services/BLE/Advertising/HCI/ASHA/AIS/Verify-debug，NFC 的 FeliCa/Secure NFC/Offhost sync/Quick Access Wallet/NCI 扩展，UWB/HAL、Presence，以及 Ranging OOB v1–v3。未逐字展开 HCI opcode 与 BQR 全字段、各 profile 互通规范、NCI/UCI TLV 表、Ranging 每字节编解码、FiRa/CCC 密钥建立及厂商射频算法；这些必须使用对应版本原文和目标实现。通用发现/配置/会话/诊断机制已提炼，不表示所有厂商协议细节已核验。
