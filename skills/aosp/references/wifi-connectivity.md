# Wi-Fi：扫描、选择、并发与无线会话

适用于 STA、热点、P2P、Aware、RTT、企业认证和 Wi-Fi 7。核实日期：2026-10-28。先固定 Android release、Wi-Fi 模块版本、首次出厂版本、芯片/固件及三类 HAL 版本；文档中的资源值、扫描周期、分数与阻断时间是对应实现的策略，不能当作所有设备的常量。IP provisioning、互联网验证和默认网络选择见 [网络栈与连接服务](network-stack-services.md)，计量与 tethering offload 见 [网络数据计量与控制](network-data-accounting.md)。

## 所有者和完成条件

应用经 Binder 调用 Wi-Fi 服务；主服务控制 STA/Soft AP，P2P、Aware、RTT 有各自服务。常见源码起点为 `packages/modules/Wifi`；独立进程 `wificond` 位于 `system/connectivity/wificond`，通过 `nl80211` 与驱动通信。Vendor HAL 提供 Android 特有芯片命令，Supplicant HAL 控制 `wpa_supplicant`，Hostapd HAL 控制 AP；三者不能互相代替。Vendor HAL 对基础 STA/Soft AP 并非一概必需，官方 HAL 概览将 Aware/RTT 列为必需场景；Android 17 的 Aware 控制面迁移见后文，不能据旧概览认定所有功能始终都经 vendor Aware 命令。[架构](https://source.android.com/docs/core/connect/wifi-overview)、[HAL](https://source.android.com/docs/core/connect/wifi-hal)

Supplicant/Hostapd 从 Android 13 提供 AIDL，Vendor HAL 从 Android 14 提供 AIDL；旧分支存在 HIDL 及 legacy shim。AIDL 接口存在、manifest 声明、固件支持和实际能力上报分别核对。一次连接至少有：模式/接口创建 → 扫描与候选选择 → 认证/关联 → IP 配置 → 网络验证 → 按请求可用。由这些边界可推导：关联成功不应清除尚未成功的 DHCP/验证故障记录，接口销毁后的旧回调不能修改新接口状态；定位需保存接口、网络配置、BSSID、请求及会话代次。

## 扫描与候选选择是两层反馈

[Infrastructure](https://source.android.com/docs/core/connect/wifi-infrastructure) 的自动开启 Wi-Fi 依赖保存过的网络、足够信号和位置扫描能力，同时保留用户刚关闭 Wi-Fi 的意图；开放网络通知则在 Wi-Fi 已开启、尚未连接且存在合适开放网络时提示。扫描开关、Wi-Fi 开关、自动加入和通知是不同状态，不能用一种开关解释全部行为。

[PNO](https://source.android.com/docs/core/connect/wifi-scan) 在屏幕关闭且断开时把偏好网络扫描交给固件，框架通过 `NL80211_CMD_START_SCHED_SCAN` 安排扫描，发现匹配项后唤醒主机。移动状态由系统侧提供，用来调节发现速度与功耗；缺少移动状态更新不能假设为静止。屏幕关闭且已连接时，漫游扫描通常由固件负责；其他组件触发的扫描仍可能进入选择流程。

[网络选择正文](https://source.android.com/docs/core/connect/wifi-network-selection) 以 Android 12 算法为基线，并包含后续版本变化，实际实现仍以目标树为准：

1. 根据连接质量、流量、最近用户选择、OSU 等条件决定是否扫描或跳过选择；“有扫描结果”并不必然触发重连。
2. 过滤低信号、被阻断、不满足凭据或 AP 限制的 BSSID；saved/suggestion nominators 产生 `WifiConfiguration` 候选。
3. 候选 scorer 综合链路/吞吐预测、计费属性、保存/建议来源、当前网络及用户偏好选择候选；用户连接选择还可改变结果。
4. 比较当前连接与获胜候选。在固件支持漫游及 BSSID 阻断时，同 SSID/安全类型可能交给固件选 BSSID；否则框架发起连接。
5. 已连接网络另有质量评价，用 RSSI、链路统计及可选外部 scorer 报告可用性。外部 scorer 的 `sessionId` 必须对应当前会话，状态更新、NUD 请求和当前 BSSID 阻断各有不同效果。

SSID 级禁用与 BSSID blocklist 的粒度、失败计数和恢复条件不同。密码错误、EAP、关联、DHCP 和互联网验证分别增加相应故障记录；恢复也应由相应成功事件证明。由此可推导：把整个 SSID 反复删建会抹掉故障证据；只提高 RSSI 奖励不能修复错误凭据；任意缩短 blocklist 会形成反复连接失败与耗电。Scorecard 是持久化质量记录，不能仅凭存在该记录就推断目标版本用它决策。

## 并发是接口组合、无线资源和用途的共同契约

HAL 报告支持的 interface combinations；组合可表达多 STA、AP、`AP_BRIDGED`、P2P/NAN 之间的数量与互斥。构建声明和 RRO 用于向框架暴露/启用已有能力，不能创造独立射频资源。功能宣称必须与芯片、固件、HAL、框架用途和允许频段组合一致。[并发定义](https://source.android.com/docs/core/connect/wifi-hal)

| 场景 | 状态与责任 | 失效推导 |
|---|---|---|
| [STA/AP](https://source.android.com/docs/core/connect/wifi-sta-ap-concurrency)，Android 9 起 | STA 上网与 AP 接入分别启停；不同信道可能在固件中时分调度，也可能使用 DBS | 同频段多信道时分会损失吞吐；STA/下游子网冲突会造成路由问题；接口都存在不证明同时可用 |
| [STA/STA](https://source.android.com/docs/core/connect/wifi-sta-sta-concurrency)，Android 12 起 | 分别支持自动 make-before-break、local-only+internet、restricted+internet；多 internet 为 Android 13 起可选用途，各自有能力查询与开关 | 第二网络不能占用第一网络的身份/统计；新网络验证失败应保留旧主网络；手动切换、MAC 冲突等可能走 break-before-make |
| [AP/AP](https://source.android.com/docs/core/connect/wifi-ap-ap-concurrency)，Android 12 起 | HAL 建立桥接接口，向上暴露多个 AP 实例的 BSSID、信道、客户端；未使用实例可因空闲策略关闭 | 桥接整体状态不代替每个实例状态；某频段消失需区分空闲关闭、法规、coex 和固件错误 |

双 STA 时框架通过 `setMultiStaPrimaryConnection` 和 `setMultiStaUseCase` 告诉芯片当前主接口和用途；漫游/APF 等至少需在主接口成立，链路统计按接口记录。主连接偏好与两条长期连接均衡是不同资源目标，具体无线调度由 vendor 决定。应用用 `NetworkCallback.onCapabilitiesChanged()` 获取对应 Network 的 `WifiInfo`，单一 `getConnectionInfo()` 无法表达两条连接。并发两条互联网连接也不自动等于应用流量聚合。

## Soft AP：能力、配置、运行态与下游 IP

[Soft AP](https://source.android.com/docs/core/connect/wifi-softap) 有 tethered 与 local-only 两种用途。`SoftApCapability` 描述可支持的安全、ACS、客户端上限等；`SoftApConfiguration` 表达请求；`SoftApInfo` 与回调描述真正运行的频段/信道/标准；这些对象不可混作结果。tethered 启动由 `TetheringManager` 协调，local-only 不承诺互联网转发。

允许/阻断列表需要强制断开客户端的实际能力。客户端上限受硬件与 carrier 约束，允许列表并不绕过上限；未知客户端在启用用户控制时可能通过 blocked 回调触发用户决定。Wi-Fi 客户端回调给出 MAC，IP 信息从 `TetheringEventCallback.onClientsChanged` 获取。配置跨设备恢复时需按新设备能力重置或降级频段/信道等，不能照搬旧设备上限。

诊断热点至少关联：AP 启动结果/每实例信息 → 客户端 L2 关联 → DHCP/IPv6 配置 → 上游及转发状态。只见到客户端 MAC 不能证明客户端拿到 IP，看到 IP 也不能证明上游可用。MAC 随机化、自动关闭和桥接实例关闭应在状态变化时重新核对，避免 UI 保留已销毁实例。

## coex 与低延迟分别控制频率冲突和时延功耗

[蜂窝共存避让](https://source.android.com/docs/core/connect/wifi-coex-channel-avoidance) 从 Android 12 根据 modem 的物理信道报告、设备专用干扰表推导 unsafe Wi-Fi channels；邻频、谐波/互调及显式 override 是不同输入。unsafe 建议、功率上限和对 Soft AP/P2P/NAN 的强制限制必须区分。表的系数取决于天线与产品布局，不能复制一组通用数值。

框架向 HAL 下发 unsafe 集合：Soft AP 有强制限制时从 ACS 候选中排除，候选耗尽会停止热点；P2P 可经 supplicant 禁用频率；NAN 的具体信道避让由固件负责。无强制限制时常由固件尽力避让或限功率。由此推导，热点因蜂窝频率变化而关闭，可能是约束正确生效，需先查看物理信道、coex 集合、限制位和 ACS 结果。

[低延迟锁](https://source.android.com/docs/core/connect/wifi-low-latency) 的有效期取决于前台、亮屏、Wi-Fi/互联网状态与持锁；框架关闭 Wi-Fi power save，额外扫描/漫游优化由 HAL/驱动/固件能力决定。它与旧 high-performance lock 不同，也不承诺端到端时延。验证要对齐锁有效状态、驱动省电状态、上下行分布和能耗，不能从“锁 acquire 成功”直接推出固件切换成功。

## 认证、订阅和身份

| 机制 | 平台契约与易混边界 |
|---|---|
| [WPA3/OWE](https://source.android.com/docs/core/connect/wifi-wpa3-owe) | Android 10 起支持 SAE、企业安全增强和 OWE；OWE 提供无线加密而不认证 AP。过渡模式、Transition Disable 与 H2E 依赖对应版本和能力。STA 与 Soft AP 的支持分别查询，旧 client 文档不能当作新热点能力上限 |
| [TOFU](https://source.android.com/docs/core/connect/wifi-tofu) | Android 13 起可在首次 EAP 连接由用户接受 CA/域信息，后续保存信任。首次获得的公钥未经预置信任；接受、拒绝和无效/过期证书分支不同，不能将 TOFU 实现成永久跳过服务器验证 |
| [Passpoint](https://source.android.com/docs/core/connect/wifi-passpoint) | GAS/ANQP 用于发现/匹配，PPS 配置与 EAP 凭据用于认证；HomeSP FQDN、AAA trusted names、realm、PLMN 是不同字段。R1 文件、R2 OSU 与 R3 条款/venue URL 分开；官方指出 WFA 已弃用 OSU，旧实现存在不代表推荐新部署。profile 过期、deauthentication-imminent 会禁止自动重试；多 profile 可以有相同 FQDN |
| [Carrier Wi-Fi](https://source.android.com/docs/core/connect/carrier-wifi) | SIM 身份认证、carrier suggestion 与 IMSI 隐私密钥共同工作；Android 11 起用 suggestion 提供 profile。证书下载依赖可达网络和计费策略，密钥过期/替换与 EAP 拒绝需要串联；不能为了自动连接退回明文永久身份 |
| [Easy Connect/DPP](https://source.android.com/docs/core/connect/wifi-easy-connect) | URI/QR 或其他带外渠道提供引导，DPP 交换凭据；引导成功不证明网络认证/IP 成功。Android 10 文档描述 initiator/configurator、initiator/enrollee 和 client 模式，后续模式需另核能力 |

[MAC 实现](https://source.android.com/docs/core/connect/wifi-mac-randomization) 与 [行为](https://source.android.com/docs/core/connect/wifi-mac-randomization-behavior) 还需区分：扫描 MAC、关联 MAC、P2P device/group、Aware NMI/NDP、RTT 事务 MAC。持久随机地址按网络 profile 参数生成，忘记后重加不保证换地址；非持久策略在新连接开始时判定，不应为换地址主动切断现有连接。MAC 随机化可能改变门户、DHCP 租约和基于 MAC 的接入策略，不能作为稳定硬件身份使用。

## P2P、Aware 与 RTT 各有独立会话

[Wi-Fi Direct](https://source.android.com/docs/core/connect/wifi-direct) 通过发现、组建和组内连接实现离线直连；Vendor/Supplicant 支持与 feature 声明须一致。device address 与 group/interface address 的随机化生命周期不同，持久组可能保留 device address。

[Aware](https://source.android.com/docs/core/connect/wifi-aware) 的 publish/subscribe 发现与 NDP 数据通路分别完成；发现对端不代表已建立数据连接。Aware ranging 还需要 RTT 能力。Android 14 起可选 suspend/resume 包含关联 NDP，暂停时不收发该 session 的帧；跨设备恢复可由带外通信协同。NMI/NDP 必须随机化，存在 NDP 时暂停重随机化并不允许改用工厂地址。

官网链接的 [Android 17 Aware 架构 PDF](https://source.android.com/static/docs/core/connect/wifi-aware-architecture.pdf) 开头明确新边界：服务发现、安全和数据通路建立等控制移到 mainline supplicant，framework 管 NIK/NPKSA、MAC 随机化和高层调度协商；firmware 保留 cluster/beacon、帧收发/加解密及 RTT 执行。Vendor HAL 的 NAN 接口创建/删除仍参与资源管理，supplicant 经 nl80211 与驱动协作。因此“控制转到 supplicant”不等于不需要 vendor 接口或固件支持。已提炼该 PDF 的架构与初始化边界，后续详细 pairing/security/调度流程未逐项深入。

[RTT](https://source.android.com/docs/core/connect/wifi-rtt) 测量支持的 AP/Aware peer 距离；802.11mc 与 Android 15 起的 802.11az 需相应能力。成功回调、有效距离和产品校准是三件事；精度与带宽、天线、LOS/多径、采样分布有关。近场跨技术切换与 presence 校准见 [蓝牙与近场](bluetooth-proximity.md)。

## Wi-Fi 7：MLD 连接包含多个链路

[Wi-Fi 7](https://source.android.com/docs/core/connect/wifi-7) 的基线支持从 Android 13 起，Android 14 起增加 MLO 评分、链路统计与 TID 映射通知。设备支持、扫描 AP 支持、实际连接使用 11be 分别来自芯片/驱动、EHT IE、supplicant 的关联能力，不能互相证明。

MLD MAC 标识设备，BSSID/STA MAC 标识每链路；affiliated、associated、idle、active 不是同义词。active 表示有 TID 映射，不证明该链路一直唤醒。框架管理 STA MLD MAC；vendor 由它和 link ID 可重复地生成 per-link MAC。vendor 只能上报实际空口收到的扫描结果，不能根据 RNR 宣告伪造未收到的 AP 结果。

芯片暴露最大 STR 链路数、最大关联链路数及同时频段组合；多关联不等于全部同时传输。框架选择候选网络，vendor 决定具体关联链路、流量分发及省电；额外接口并发优先于同一接口多链路占用无线资源。MLO 下行进入 APF 前需把 per-link MAC 换成 MLD MAC，所有链路共用一份 APF；否则基于 MLD 地址的过滤会失配。诊断应同时看 `MloLink`、TID 映射及逐链路统计，单个合并 RSSI 可能掩盖弱链路。

## 可观察证据与覆盖边界

[调试正文](https://source.android.com/docs/core/connect/wifi-debug) 提供 framework/manager 测试、HAL 测试、固件 ring buffer 与 bugreport 入口。AIDL 与 HIDL 的固件日志位置不同；仅有 Java 日志不能排除 firmware reset。`dumpsys wifi`、supplicant/hostapd 状态、wificond/驱动事件和同时间的 `network_stack`/Connectivity 记录应对应同一接口与网络，保留断连前日志以定位第一次失败。

本页覆盖 Wi-Fi 侧边栏 Overview、HAL、Infrastructure、Scan、Network selection、三类 Concurrency、Soft AP、Coex、Low latency、WPA3/OWE、Passpoint、TOFU、DPP、MAC 两页、Direct、Aware、RTT、Wi-Fi 7、Test/debug。未逐项展开芯片私有漫游/调度、coex XML 全字段、Passpoint 示例证书/XML、每个 scorer 数值及 MLO PHY 参数；这些分别需目标固件、原文 schema、目标分支算法与对应无线规范。本文的失败推导是依据上述状态所有权进行的分析方法，不是对任意厂商实现的已验证结论。
