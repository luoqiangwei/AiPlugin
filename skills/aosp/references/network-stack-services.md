# 网络栈与连接服务：网络身份、验证、路由和会话

用于“已连接但无互联网”、默认网络错误、门户登录、VPN、APF、跨设备权限及网络诊断。核实日期：2026-10-28。链路建立见 [Wi-Fi](wifi-connectivity.md) 和 [电话/运营商](telephony-carrier-esim.md)。UID/tag 统计、配额、Data Saver、VPN/464xlat 计量归属和 tethering offload 计数详见 [网络数据计量与控制](network-data-accounting.md)，本页不重复其数据平面核算机制。

## 对外的 Network 是身份，连接图标是观察结果

把以下状态分别记录：传输接口存在、L2 建立、L3 provisioning、DNS/路由、互联网验证、满足某个 `NetworkRequest`、成为某 UID 默认网络。一个设备可同时有多个 transport 和同 transport 的多个 Network；默认数据订阅、Wi-Fi 主 STA、系统默认网络及 VPN 的 underlying network 也不相等。

`LinkProperties` 描述接口、地址、路由、DNS/代理等链路配置；`NetworkCapabilities` 描述传输、能力与策略状态；`NetworkScore` 传达网络选择策略。三者发生更新时必须与同一个 Network、请求和时间相联系。由此可推导：旧 Network 已丢失后，它的验证结果或旧 `IpClient` 回调不能使新网络变成“已验证”；某 UID 不可达也不能直接把所有 UID 的网络标为失败。

## 模块和所有者

| 组件 | 所拥有的机制 | 接口边界 |
|---|---|---|
| ConnectivityService/Connectivity 模块 | L3 以上的请求匹配、网络排序、默认网络及路由协作 | NetworkAgent 报告状态，ConnectivityManager 向调用方提供按请求的回调 |
| Network Stack | `IpClient` provisioning/维护、`DhcpClient`、APF 生成、`NetworkMonitor` 验证 | Mainline 场景跨进程使用稳定 AIDL；不是把内部类当任意平台私有库 |
| CaptivePortalLogin | 门户登录与用户选择 | 与 NetworkMonitor 协作，登录窗口关闭不等于网络验证通过 |
| DNS Resolver | DNS stub、缓存、查询与配置 | Java/native 解析调用、配置 Binder 与 resolver 自身版本分别核对 |
| Tethering | 下游服务、上游、entitlement、IpServer 和 offload 协作 | 下游接入、IP 与转发完成条件不同；DHCP server 来自 Network Stack |
| netd/内核 | 按系统请求实施路由、接口/防火墙等数据面操作 | 不能从单条框架日志推断所有内核规则已安装 |

[Network Stack](https://source.android.com/docs/core/architecture/modular-system/networking)、[DNS Resolver](https://source.android.com/docs/core/architecture/modular-system/dns-resolver)、[Tethering/Connectivity](https://source.android.com/docs/core/architecture/modular-system/tethering) 描述模块边界。Android 11 的 Tethering APEX 与 Android 12 起包含 ConnectivityService 的扩大范围需区分；目标源码常见于 `packages/modules/Connectivity`、`NetworkStack`、`CaptivePortalLogin`、`DnsResolver`。旧文档列出的 `frameworks/base` 路径可能是迁移前位置。Mainline 包、平台 API 与 vendor HAL 独立演进，当前 OS 版本不能代替模块版本。

## 网络选择：先能满足请求，再比较策略

[Network selection](https://source.android.com/docs/core/connect/network-selection) 区分 Android 11 及以下的整数分数，与 Android 12 起的 `NetworkScore` 策略。后者由 NetworkAgent 传达属性，Connectivity 模块内的 `NetworkRanker` 决策：

- `POLICY_TRANSPORT_PRIMARY` 表示同 transport 内的主网络偏好，不等同所有 transport 的最高优先级。
- `POLICY_EXITING` 表示 agent 判断网络正退出，允许存在其他候选时提前避开；阈值来自对应传输实现。
- `KEEP_CONNECTED_FOR_HANDOVER` 保持待验证/待切换的网络，避免它因尚不满足任何活跃请求被立刻销毁。
- 可服务同一请求且策略相同的网络，优先保留当前服务者，减少无谓切换。请求能力、受限访问等前提仍必须满足。

由此可推导：只把 legacy integer 调大不能改变 Android 12 的策略；新建 agent 若未表达 handover 生命周期，可能“建立—无人使用—销毁—再建立”并耗电。`NetworkFactory` 的 filter 表达其能创建的最强网络，用错会漏掉请求或造成多余工作。Wi-Fi 内部选 AP、蜂窝选订阅/承载和 Connectivity 在多个网络间选路分别归属不同决策，修改其中一处不会自动重写其他两处。

双 STA make-before-break 的第二网络先连接并验证，再晋升主网络；local-only/restricted 网络则只服务相应请求。应用应追踪具体 `NetworkCallback` 的 capability/link-property/lost 变化，避免把某次 `onAvailable` 当作以后永不变化的网络承诺。[Wi-Fi 并发](https://source.android.com/docs/core/connect/wifi-sta-sta-concurrency)

## IP、DNS、验证与门户

`IpClient` 管 IP 配置和维护，`DhcpClient` 获取 DHCP 地址，IPv6 地址/路由还与 RA/邻居状态有关；`NetworkMonitor` 则检查互联网与门户。先检查对应接口的地址、路由、DNS，再检查探测的网络、URL/响应、私有 DNS 与 VPN/代理路径。DNS 解析成功不能证明应用服务器可达，ping 成功也不证明 HTTPS/门户处理正确。

DNS Resolver 的缓存、`.local` mDNS 与普通 DNS 不是同一发现路径；官方描述 `.local` 查询对 VPN/蜂窝不采用相同 mDNS 路径。解析异常需带域名、网络身份、DNS 配置与时间，不能仅从全局 resolver 一条成功记录推断特定 Network 成功。[解析机制](https://source.android.com/docs/core/architecture/modular-system/dns-resolver)

[门户 Custom Tabs 正文](https://source.android.com/docs/core/connect/android-custom-tabs-captive-portal) 说明新的发现链：DHCP option 114 给出 HTTPS API → 读取 RFC 8908 JSON 的 `captive`、portal/venue URL 等 → 决定登录界面。API 证书无效时回退旧方式；`captive=false` 还需常规验证，不能让网络自报“无门户”直接成为可信互联网。HTTP/HTTPS 探测不一致会形成 partial connectivity，登录应用可能不会自动弹出。

Custom Tabs 路径有独立的设备/Mainline 与网络 opt-in 条件：官方当前要求 Android 12+ 且支持相应更新，`x-android-use-custom-tabs` 指向 CaptivePortalLogin 模块版本门槛（正文例为 2026-01 的 `361335020`）。这是模块版本协商，不能只按系统 API level 开启。判断登录故障时分别保留 DHCP option、API TLS/JSON、探测和 UI 启动证据；不能通过关私有 DNS/VPN 或统一改探测 URL 掩盖实际路径问题。

## APF：主机生成规则，固件执行过滤/应答

[Android Packet Filter](https://source.android.com/docs/core/connect/android-packet-filter) 把可更新 bytecode 下发到网络硬件解释器，以减少主机被无关流量唤醒。生成器属于 Network Stack；Wi-Fi HAL 负责安装和读取专用内存；解释器应在固件而非主机驱动运行。v2 提供过滤，Android 10 的 v4 增加计数，Android 15 的 v6 还可发包，例如替主机回应 ARP/NS。v6 的“未送主机”可能表示已由固件应答，不能一律解释为网络丢包。

关键契约：

- 传入完整包，不能只给包头；报告的 interpreter version、packet format 和最大内存须真实，生成器才能选用正确指令与布局。
- 内存同时放程序与数据/计数，只能经规定路径修改，不能被芯片其他任务清空；安装短程序不能破坏规定保留的数据区。
- 包龄参数与实际时间对应；RA 等带时效过滤如果使用错误 age，会过早放行或过久压制有效配置。
- vendor 前置过滤会使包根本不到 APF；单看 APF 无计数不能排除此前已丢弃。漫游、双 STA 晋升、接口重建后要重新核对程序绑定与计数连续性。

证据入口是 `dumpsys network_stack` 中的 `IpClient.<iface>`、`ApfCapabilities`、Last program 与 reason counters；用 `apf_disassembler` 看实际规则，用对应版本的 `apf_run` 加 packet/pcap、data、age 离线复现。原文的内存要求与测试条件按目标 APF 版本采用，本页不提供通用“省电阈值”。抓包在 APF 之后，缺包现象需要与空口/firmware 计数关联。

## VPN、共享网络及运营商受限网络

[VPN UX](https://source.android.com/docs/core/connect/vpn-ux) 主要是承载网络对 IPsec 的互通约束：IPv6 原生 ESP 的可达性/快路径、IPv4 UDP 封装的 NAT/firewall 状态寿命会改变可靠性与 keepalive 功耗。缩短心跳可能临时保活，却增加唤醒及信令；应先用上下行/空闲恢复的包证据确认状态在哪一端超时。运营商推荐超时不是 Android 内部通用常量。

VPN 网络、underlying network、UID 适用范围和目的路由必须分别观察。Android 13 增加 `VpnService.Builder.excludeRoute`，可表达包含默认路由后排除某些前缀的 split tunnel；被排除流量及 DNS 实际路径仍需按 UID/目的地确认。VPN 连接标志不保证所有目的地都走隧道，隧道不可达也不自动证明 Wi-Fi 验证失败。[Tethering/分流](https://source.android.com/docs/core/architecture/modular-system/tethering)

Tethering 要跟踪下游 L2、地址分配、上游选择、转发规则及回程；local-only hotspot 本来就不提供该上游。IPv4 NAT/DHCP 与 IPv6 SLAAC/前缀的行为不同，切上游时旧路由/前缀和 offload 状态应相应失效。具体硬件/eBPF offload 与数据核算在另页，不能只看 CPU 抓包得出“没有流量”。

[余额不足](https://source.android.com/docs/core/connect/oob-users) 使用 carrier signal → 配置的 action → 限制 APN/通知/充值网络的链路。重定向、请求失败、用户配额和真实数据余额不是同一个信号；需要保留 subId、carrier 配置和恢复条件。SIM 替换、重启、充值、Wi-Fi 可用会改变相应状态，不能通过反复重置 radio 丢掉限制语义。套餐权威数据来自具备管理权限的 app 的 `SubscriptionPlan`，有提供者归属与访问保护；套餐的计费/拥塞覆盖及其超时是策略输入，不等于内核逐包计数。[Data plans](https://source.android.com/docs/core/connect/data-plans)

## Companion 与连接 UI 的授权边界

[Companion device profiles](https://source.android.com/docs/core/connect/companion-device-profile) 把设备关联、Android role 和一组权限联系起来：用户批准关联后 CDM 授予对应 profile role；用户仍可单独撤销权限而保留关联。清数据/移除全部设备会按生命周期条件撤销 profile 及其权限。由此可推导：关联存在不证明电话/联系人/麦克风权限仍在，Bluetooth bond 存在也不代替 CDM association。watch、glasses 权限集合随版本变化，按目标 role 定义读取，不能用一个 profile 获得无关权限。

同厂 companion 的免提示配置依赖包名与证书成对匹配，仍存在频率等条件；不能把资源数组误当任意应用跳过用户授权的入口。CrossDevice 提供发现与认证连接相关能力，它和 CDM 角色授权、蓝牙配对均不相等；模块文档中的计划项也不证明某个产品已交付。[CrossDevice](https://source.android.com/docs/core/architecture/modular-system/tethering)

[Connectivity UI](https://source.android.com/docs/core/connect/connectivity-ui) 将 Internet panel、Calls & SMS、无线恢复入口及 carrier-merged Wi-Fi 展示联系起来。Wi-Fi 合并进运营商图标、呼叫强度指示和默认数据选择不等于物理 transport 改变；限制 autojoin 到某 subId 也不等于关闭全部 Wi-Fi 硬件。恢复按钮会重启相应子系统，先保留 reset 前的故障证据；多 SIM 混用不同 carrier UI 配置时需明确展示与操作所针对的订阅。

## 诊断报告能证明什么

[Connectivity Diagnostics API](https://source.android.com/docs/core/connect/connectivity-diagnostics-api) 向拥有/管理网络的 app 提供验证报告、疑似 data stall 和 app 主动报告：carrier privilege 受 subId 约束，suggestion app 受其建议网络约束，VPN app 只有在其 VPN 活跃时管理相应网络。该 API 不是观察任意网络的权限。注册/注销使用同 UID，并核对位置等权限与实际版本要求。

`ConnectivityReport`/`DataStallReport` 携带 Network、时间、LinkProperties、Capabilities 与额外结果；data stall 是怀疑而非已证实根因，app 的 `reportNetworkConnectivity` 是一次观察输入。形成有用证据要把报告与 `dumpsys connectivity`、`dumpsys network_stack`、resolver、netd/路由及传输日志在同一时间窗对齐，记录 app UID 和请求。不要只保存最后一张“无互联网”截图。

本页承接 Network selection、APF、Custom Tabs captive portal、VPN UX、Connectivity diagnostics/UI、Companion profile，并连接 data plans/out-of-balance 到既有计量页。未深入 VPN IKE 协商/具体密码套件、所有 RFC 8908 扩展、APF 指令逐条编码、CrossDevice 完整认证协议及芯片私有过滤器；这些需要相应协议正文和目标实现。网络路由机制已提炼，不能据此宣称任何厂商网络或运营商部署已验证互通。
