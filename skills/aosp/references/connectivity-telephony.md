# 连接与电话：无线链路、IP 连通性和订阅状态

按子系统继续读[Wi-Fi](wifi-connectivity.md)、[电话/运营商/eSIM](telephony-carrier-esim.md)、[蓝牙/NFC/UWB](bluetooth-proximity.md)和[网络栈服务](network-stack-services.md)；本页保留整体协作模型。

本页用于连接建立、网络切换、热点、近场通信、蜂窝与通话变更。核实日期：2026-10-28。
机制判断先落到目标 release/tag、设备 capability、运营商配置、模块版本和 vendor HAL；文档当前路径不是所有分支的事实。
源码搜索起点是定位线索，实际进程、接口定义、状态机与测试以目标树为准。

## 先把用户现象拆成不同状态

- “打开无线开关”“链路关联”“取得地址”“存在路由”“网络已验证”“某 UID 可以访问”是不同完成条件。
- UI 的已连接状态不能证明 DNS、互联网、VPN 路由或应用权限已经正确。
- 同一设备可能同时有多张 SIM、多个 Network、多种传输；不要把默认数据订阅、默认语音订阅和当前调用对象合并成一个全局状态。
- 一次异步操作应关联请求身份、网络/订阅身份及状态代次，旧结果不能覆盖新连接。
- 权限校验、用户限制和硬件能力应在正确入口生效；不能靠隐藏开关替代服务端检查。
- HAL 服务死亡、无线固件复位、SIM 热插拔和用户切换都是正常需要处理的状态变化，不只是日志异常。

## Wi-Fi：先找失败层，再改变策略

主路径是 API/Binder → Wi-Fi 服务/状态机 → supplicant、hostapd 或 vendor HAL → 驱动/固件。[1][]
`wificond` 通过 `nl80211` 与驱动协作；Vendor、Supplicant、Hostapd 三类 HAL 有不同职责。
STA、Soft AP、P2P、Aware、RTT 不是同一连接流程，不能把某模式成功推论成另一模式可用。
服务常见起点为 `packages/modules/Wifi`，`wificond` 常见起点为 `system/connectivity/wificond`。
当前文档描述 AIDL 路径；旧分支还可能采用 HIDL，应检查目标树接口和设备 manifest。

- 关联失败：检查扫描结果、鉴权/关联状态、错误码和固件能力，不先归因 DNS。
- 已关联但无地址：转查 IP provisioning、DHCP、IPv6 RA 与接口生命周期。
- 已有地址但无网络：转查网关、DNS、验证、路由与 UID 策略；不要直接重写 Wi-Fi 状态机。
- 修改候选网络评分、重连或漫游策略前，先定义切换抖动、断流和电量指标。
- 能力声明必须与芯片、HAL 实现和并发组合一致；开资源布尔值不能创造硬件支持。

## IP 网络：分开 provisioning、validation 与选择

Network Stack 承担 `IpClient`、DHCP、NetworkMonitor 和 captive portal 相关能力，通过稳定 IPC 跨模块协作。[2][]
NetworkMonitor 判断可达性及门户状态；一次探测失败不是所有应用流量失败的充分证据。
ConnectivityService 组织 L3 以上网络选择；其所属模块及源码位置随版本变化。[3][]
Network Stack 与 Connectivity/Tethering 不是同一个可随意互相调用内部实现的模块。

- 保留网络身份、LinkProperties、NetworkCapabilities、验证结果的时间关联。
- DNS 正常不代表 HTTP 可达；门户、私有 DNS、代理、VPN 和按 UID 路由需要分别判断。
- 调整验证 URL 或超时必须评估门户误判、弱网恢复、隐私与网络切换行为。
- 断连后取消旧计时器、回调和 provisioning；服务重连后重新建立必要状态。
- 不能通过修改某个 app 的网络显示掩盖实际系统路由或模块接口问题。

## 热点与 tethering：二层接入成功只是第一步

Tethering 协调下游、上游、授权检查和 offload；IPv4 常见 DHCP/NAT，IPv6 使用 SLAAC 等对应路径。[3][]
热点客户端能连上 AP，不代表已获得地址、默认路由、DNS 或可用上游。
Android 11 引入相应 APEX 交付；Android 12 起相关范围扩展到 `packages/modules/Connectivity`，旧路径只能作为迁移线索。

- 分别确认客户端接入、地址配置、上游选择、转发规则和返回流量。
- 硬件或 eBPF offload 可绕过部分 CPU 数据路径；只看普通抓包或单一计数器可能漏掉已转发流量。
- 切上游时需清理旧前缀/规则并建立新状态；不能让旧回调重新启用失效接口。
- 验证 IPv4/IPv6、Wi-Fi/USB/蓝牙下游，以及无上游与上游恢复；不以单次 ping 替代完整路径。

## Bluetooth、NFC 与 UWB 的边界

Bluetooth 主机栈包含 API、profile、JNI/native 与 vendor 控制器接口；profile 已连接不代表音频或 PAN 数据路径已建立。[4][]
配对/bond、链路连接、profile 连接、媒体路由是不同状态；失败证据应带对端、profile 和时间。
当前模块通常从 `packages/modules/Bluetooth` 定位；官方将模块引入记为 Android 13、可更新支持记为 Android 16 起，必须按设备交付核对。
蓝牙音频故障要把蓝牙传输与音频框架路由两侧关联，不能只根据“蓝牙已连接”关闭音频问题。

NFC Services 在 Android 16 成为可选、可更新 Mainline 模块，包含 API、NFC APK、JNI 与 NCI 栈，vendor 仍提供 HAL。[5][]
早期分支的位置和打包方式可能不同；`packages/modules/Nfc` 不是旧树必然存在的目录。
标签发现、读写、卡模拟和安全元件交互的路由与权限不同；不能以 NFC 开关开启证明支付路径已就绪。
检查控制器能力、HAL 状态、路由配置、锁屏/用户策略及具体交易结果；不要把应用 UI 当控制器确认。

Android 13 起提供默认 UWB 框架；服务/原生 UCI 层经 HAL 与芯片通信，系统 API 与第三方 Jetpack API 有不同边界。[6][]
测距要区分带外参数交换、session 配置、启用测距和结果回调；发现设备不等于已完成测距。
身份、会话参数、权限及对端能力需一致；距离精度还受环境与硬件影响，不能只用 API 成功码评价。

## 电话与 RIL：状态由多个异步参与方共同产生

先区分 Telecom 的通话组织、Telephony 的订阅/无线状态、Radio HAL/vendor RIL 和 modem 的实际执行。
查找起点通常涉及 `packages/services/Telecomm`、`packages/services/Telephony`、`frameworks/opt/telephony`、`hardware/interfaces/radio`；先确认目标树存在及所有权。
请求 serial、响应、非请求 indication、错误码及服务重启要能串成同一条时间线。
RIL 重构文档解释 Android 7 的错误分类和 wakelock/ACK 改进，不是现代所有 Radio HAL 的接口模板。[7][]
较新接口是否拆分为稳定 AIDL 服务、具体版本及 fallback 均查目标分支；不要直接照抄旧 `ril.cpp` socket 流程。

- 通话失败可能来自订阅、运营商配置、注册、承载、路由或远端；UI 一条失败码不足以选择修复层。
- 不能无限持有 wakelock 等待 modem；同时不能在应答处理前过早释放导致响应丢失。
- 超时不等于底层操作已取消；处理晚到响应和 modem reset，防止重复通知或旧状态复活。
- 权限、carrier privilege、slot、phone、subscription 的含义不同，不能用数组下标互相代替。

## eSIM、IMS 与紧急呼叫

eSIM 路径是调用方 → EuiccManager/框架 → LPA 的 EuiccService → eUICC；AOSP 提供框架，不包含完整 LPA 产品实现。[8][]
下载、切换、删除是异步事务；处理完成回调、可由用户解决的错误及详细错误码，不把“请求已发出”当完成。
card ID、物理 slot、逻辑订阅需要明确映射；多 eUICC、重启和不可达芯片不能落回未经确认的默认卡。
运营商权限与用户同意共同决定可执行操作；测试不能靠绕过授权实现成功。

Android 9 引入现代 ImsService System API；框架绑定 OEM/运营商实现，并按订阅与 feature 决定服务。[9][]
MMTEL、RCS、IMS 注册、provisioning 与一次实际通话不是同一状态。
SIM 或 carrier config 变化可能换绑 ImsService；服务不在 telephony 进程内，需处理死亡、解绑和重新可用。
框架接口测试只能证明框架交互；不能替代 IMS 协议、modem、网络与运营商端到端验证。

紧急号码来自网络、SIM、数据库、modem 等来源；号码类别、来源与 routing 需要一同保留。[10][]
Android 10 的 Radio HAL 1.4 已把 emergency dial 与普通拨号区分；现代分支应核对对应 AIDL/HIDL 契约。
无 SIM、锁屏、多 SIM、漫游和不同注册状态不能被普通通话路径的前置条件误挡。
号码识别正确不证明真实紧急通话能接通；验证必须使用隔离实验网络、模拟器或约定测试设施，不能随意拨打真实紧急号码。

## 用证据决定实现位置

| 现象 | 至少需要的关联证据 | 优先检查 |
|---|---|---|
| 无线已连但应用离线 | 接口、IP/路由/DNS、Network 身份、验证与 UID 策略 | provisioning/Connectivity，避免只改图标 |
| 热点客户端无网 | 下游租约、上游、IPv4/IPv6、转发与 offload 计数 | tethering 控制面及实际数据路径 |
| 通话或 IMS 抖动 | subscription/slot、服务绑定、注册状态、请求响应与 modem 重启 | 错误是否跨越重绑/状态代次 |
| eSIM 切换卡住 | card/profile 身份、LPA 回调、用户解决流程与错误码 | 事务完成与取消恢复 |

实现前先复现状态转换和失败点；审查时检查 IPC 权限、身份传播、回调代次、资源释放及模块 API 边界。
使用目标分支已有单测/集成测试验证状态机；涉及无线/运营商行为时记录实机、芯片、固件、网络条件及对端版本。
没有匹配硬件或实验网络时，明确哪些只完成静态/框架验证，不推断射频、漫游或紧急呼叫已经验收。

## 已核实的官方深读入口

1. [Wi-Fi 架构与三个 HAL 职责](https://source.android.com/docs/core/connect/wifi-overview)
2. [Network Stack：IpClient、NetworkMonitor 与模块接口](https://source.android.com/docs/core/ota/modular-system/networking)
3. [Tethering：模块边界、双栈与 eBPF offload](https://source.android.com/docs/core/ota/modular-system/tethering)
4. [Bluetooth 模块：版本、组成与依赖](https://source.android.com/docs/core/ota/modular-system/bluetooth)
5. [NFC Services：Android 16 模块与 NCI 栈](https://source.android.com/docs/core/ota/modular-system/nfc-services)
6. [UWB：服务、UCI、HAL 与 API 分界](https://source.android.com/docs/core/connect/uwb)
7. [RIL refactoring：历史 ACK 与 wakelock 机制](https://source.android.com/docs/core/connect/ril)
8. [eSIM：EuiccService、LPA、身份与异步结果](https://source.android.com/docs/core/connect/esim-overview)
9. [IMS：ImsService 绑定、feature 与订阅变化](https://source.android.com/docs/core/connect/ims)
10. [紧急号码与 emergency calling 接口](https://source.android.com/docs/core/connect/emergency-call)

[1]: https://source.android.com/docs/core/connect/wifi-overview
[2]: https://source.android.com/docs/core/ota/modular-system/networking
[3]: https://source.android.com/docs/core/ota/modular-system/tethering
[4]: https://source.android.com/docs/core/ota/modular-system/bluetooth
[5]: https://source.android.com/docs/core/ota/modular-system/nfc-services
[6]: https://source.android.com/docs/core/connect/uwb
[7]: https://source.android.com/docs/core/connect/ril
[8]: https://source.android.com/docs/core/connect/esim-overview
[9]: https://source.android.com/docs/core/connect/ims
[10]: https://source.android.com/docs/core/connect/emergency-call
