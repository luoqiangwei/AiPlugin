# 网络数据：计量归属、历史统计、配额与 Data Saver

本页用于流量统计不一致、UID/tag 归属、VPN、共享网络/offload、Data Saver、移动数据限额及计费周期问题。核实日期：2026-10-28。
先固定 Android/Connectivity 模块/内核 revision、设备首发版本、Network/接口/订阅、UID/用户与统计区间；当前系统版本不能代替 eBPF、HAL 或模块的实际部署状态。
这是网络字节的计量和政策，**不是磁盘 filesystem quota、应用目录容量或存储缓存配额**；磁盘机制见 [存储与数据](storage-data.md)。

## 三种责任：测得多少、历史如何归属、现在允许什么

[Android data use][overview] 同时提供整体/应用历史用量、warning/limit 与后台数据限制；这些功能依赖不同状态所有者。

| 层次 | 主要对象 | 可证明什么 | 不能直接证明什么 |
|---|---|---|---|
| 内核/数据路径计量 | interface、socket UID/tag、counter set、offload 统计 | 某路径某区间观测到多少字节/包 | 用户应看到哪个订阅/账期、某 UID 此刻是否可联网 |
| 用户态统计与历史 | NetworkStatsService 等的快照、差分、归属修正、时间桶 | 查询条件下的历史用量 | 计数器已立即持久化、控制规则已下发 |
| 网络政策执行 | NetworkPolicy 等决定的限额、metered/UID/后台规则，及相应内核/HAL 实施 | 满足条件的流量是否应允许/拦截 | 历史图表必须即时归零或与运营商逐字节相同 |

角色区分依据 [eBPF traffic monitoring][ebpf] 和 [旧内核计量/配额概览][legacy-kernel]。
由此推导：显示错归属应先修统计链；如果 drop/firewall rule 未执行，改 Settings 图表不会修好限制；更不能为了让图表对齐而悄悄放开联网策略。

## eBPF 与历史 xt_qtaguid 的版本边界

[eBPF 原页][ebpf] 规定 Android 9 首发、相应 4.9 及以上内核条件下采用 eBPF accounting，并说明从 xt_qtaguid/xt_owner 迁移。
这是首发版本与内核共同限定的要求，不是“运行 Android 9+ 就可假定所有设备实现和 map 名相同”。
原页介绍的 netd/TrafficController/bpfloader 目录、map 创建和 hook 是当时实现；现代逻辑可能已进入 Connectivity 模块，应查实际 map/program 所有者与加载器。
app 不应直接读取旧 `/proc/net/xt_qtaguid` 来绕过 framework API；历史 proc 文件存在与现代公共 API 是否正确也不是一回事。

该设计在 transport/cgroup 层按 socket 所有者/设置计 UID，在相应 netfilter hook 计 interface，用户态通过 map 读写维护 tag、counter set 与限制状态。
因此 interface 总量和 UID 明细具有不同计数位置，网络封装、转发及归属修正也可能不同；不能要求每个采样瞬间直接相加完全一致。
UID 防火墙的 power-save/standby/doze 等 map 与流量统计 map 责任不同；某 UID 有历史流量不能证明其当前仍被允许联网。[eBPF 结构依据][ebpf]

旧 [kernel changes][legacy-changes] 记录 xt_qtaguid、quota2 和 netfilter 修改，是历史移植资料。
其中依赖、SIP/conntrack 提醒或某个旧 kernel config 不能无条件用于现代内核；当前 offload 本身可能依赖 conntrack。
在新分支排错时，不应照旧文档关闭 conntrack 或加回已淘汰模块来“恢复流量统计”。

## UID、tag 与 counter set：总计和分类不能重复相加

socket UID 是计量与政策的重要身份；tag 进一步划分该 UID 的业务类别，counter set 可区分前后台等状态。
它们是不同维度，tag 不是新的安全主体，不能用一个新 accounting tag 逃离原 UID 的限制。
[Tags explained][tags] 的历史模型中，`acct_tag=0` 的 default/UID total 包含该 UID 的全部流量，非零 tag 是另外保留的分类统计。

例如同一区间 UID total 为 100 MiB，其中 tag A 为 30 MiB、tag B 为 20 MiB，不能算成 `100+30+20=150 MiB`。
“untagged = total - 各分类”也必须先确认查询语义、tag 是否互斥、同一 counter set/接口/时间区间及底层是否提供完整分类，不能看到 `tag=0` 就当作纯未标记流量。
这些求和约束来自 [tag 总计定义][tags]；现代实现与 API 的 `TAG_NONE/TAG_ALL` 查询应回查目标代码，不能仅按历史名称猜口径。

线程 tag API 最终关联到 socket；eBPF 可通过 socket cookie/tag map 更新归属。
由此推导：复用连接、socket 从何时被 tag/untag、连接池与异步工作切换会影响观测，不能把“这段代码当前在某线程”当作现有所有 socket 已重新分类。
要比较相同 socket 生命周期、UID、tag 和采样点，不能只比较两次线程局部 tag 值。[Socket tagging 依据][ebpf]

下载/媒体等代表其他 app 传输的系统服务可以在授权下将计量归属到请求 UID；这与任意 app 自报一个 UID 不同。
旧实现通过 `TrafficStats.setThreadStatsUid()` 并要求 `MODIFY_NETWORK_ACCOUNTING`；具体入口、权限和代理身份应核对目标分支。
审查时分开真实 socket 所有者、计量归属 UID、调用方用户与政策主体，避免用“system 发起”吞掉所有调用者的用量。[委托归属依据][legacy-kernel]

## Interface 统计：单调性、生命周期和字节层次

[Network interface statistics][interfaces] 要求驱动在 interface 活动期返回单调统计，只有完成 unregister 并产生相应生命周期事件后才可重置。
因此随手清零驱动计数器、复用同名接口却漏生命周期事件，会让 framework 差分负值、丢量或重复归属。
interface name 不是永恒身份：还需关联创建/销毁、Network、底层传输和订阅映射。

原文以 Android 4.0 的 `dev_get_stats` 和 NetworkStateTracker 描述；NetworkStateTracker 不是现代所有分支的接口名，但“统计要绑定可识别网络及生命周期”的约束仍是定位起点。
IP 字节与 Ethernet/USB/无线链路封装字节不同；原页要求相关驱动的 `rx_bytes/tx_bytes` 反映相应 Internet-layer 口径，而非任意底层全部流量。
用户态处理、VPN/464xlat 或 modem/offload 又可能引入其他修正；运营商账单的采样点/计费规则不同，不能靠一组接口计数要求逐字节对账。

由此推导，出现负差分时应先找设备重启、接口重建、native 读取语义或 map swap/清理边界；不能先用绝对值把负数变成“合理流量”。
丢弃负数可隐藏严重错配，重叠累加也会虚增用量。保留旧/新快照、时间与接口生命周期，才能决定应重新建基线还是修复读取/归属。

## 统计读写与 VPN：一个已核实 revision 的具体例子

以下细节只描述 [Connectivity revision `0cc8d81…` 的 NetworkStatsFactory][vpn-sample]；它证明一种实际实现，**不定义全部 Android 版本必有的调用顺序、map 名或接口**。
该实现维护累计原始快照与经过 TUN/464xlat 修正的快照，读取时保留当前 VPN/underlying network 信息的快照，并在保护持久状态的锁下操作。

1. 请求切换 active stats map，随后从 inactive map 读取，避免读与清理同活动写入相互竞态。
2. 将该读取语义下的增量合并进原始累计快照，与上次原始快照做差，得到本次 delta。
3. **该 revision 先应用 464xlat 修正，再按 VPN 的 owner UID、TUN interface、underlying interfaces 执行 `migrateTun`。**
4. 去掉 VPN debug entries，避免它们被当作正式用量重复计入，再将修正后的 delta 累计到修正快照。
5. 最后按查询 UID/interface/tag 过滤返回；不能先丢掉迁移所需的其他参与方，再期待归属修正得到同样结果。

这些次序来自 [该文件的实际实现][vpn-sample]，切换 release 或模块 revision 时应重新验证。
特别是“BPF 读取值是增量还是累计”必须看实际 native reader/map 交换语义，不能把上面的 merge 逻辑复制给另一个累计型接口。

TUN VPN 的外层传输在底层看起来主要属于 VPN app 的 UID，但用户历史用量需要识别实际使用隧道的 app。
因此简单把 TUN 与 underlying 两份统计相加会重复计数，把全部 underlying 字节留给 VPN app 又会错归属。
此例在 delta 上修正，避免 VPN owner/底层网络随时间变化时，将新关系反复作用于全部旧历史；不是修改应用真实 UID，也不是更改网络授权。
464xlat 与 VPN 封装各自有开销，不能假定 TUN 与物理接口字节逐字节相等。[VPN 源码依据][vpn-sample]

诊断需要 VPN owner、TUN/underlying interface 集合、其变化时刻、修正前 delta、修正后记录与 debug entries 的筛除状态。
多网络切换、VPN 自身业务、其他隧道实现及具体迁移分摊算法需继续查目标 `NetworkStats.migrateTun` 与测试；本文未将该 revision 的内部算法推广成所有 VPN 的通用公式。

## Tethering 与 offload：普通 app 统计不能替代转发用量

[Tethering data][tethering-data] 描述 interface pair 之间的转发计量；它与本机 app socket 的用量不同。
原页的 `ConnectivityService.getTetheredIfacePairs()` 是历史实现线索；现代 pair/上游映射与统计入口应核对 Connectivity/Tethering 版本。
下游连上 AP、取得 DHCP 地址和流量成功跨上下游转发是不同条件，不能以单个 socket UID 的统计代替所有 tethering traffic。

[Tethering hardware offload][offload] 从 Android 8.1 提供相应 HAL 路径，让 modem 与 Wi-Fi/USB 之间部分转发绕开主处理器。
普通 CPU 抓包/计数可能看不到已 offload 的数据；看不到包不是没有用量，更不是免计费。
offload 也不必处理所有包，framework 能保留软件路径；IPv4 建立/拆除流的控制包需经过软件以建立/维护 NAT/conntrack 状态。

该硬件方案由 framework 提供已打开的 conntrack netlink sockets，HAL 观察流，无需为此自行取得全套 `CAP_NET_*`。
只有 forwarded flows 应被加速；本机通信和被排除的本地/IPv6 prefixes 不能误纳入。
硬件应周期性报告活跃 IPv4 NAT 的 timeout 更新，使 kernel 不会在真实流仍有流量时过早回收连接。
上游、下游、prefix 或流状态改变时，应撤销旧配置并建立新配置；仅 data plane 仍能收包不证明控制面没残留。[Offload 控制契约][offload]

计量与配额也需跨越这条旁路：NetworkStatsService poll 会使 framework 请求硬件的 forwarded stats，framework 再通过 HAL 下发 data limit。
`getForwardedStats` 与 `setDataLimit` 对应不同责任；只实现前者会留下限额执行空洞，只实现后者会让历史图表漏量。
停启 offload、软件 fallback、切上游和 HAL 重启时，需对齐计数基线、最后一次读数与新实例；不能把同一段软件/硬件转发重复相加。
这些恢复检查是根据 [硬件 offload 统计与限制接口][offload] 推导的实现不变式，精确 counter reset 语义仍查目标 HAL。

## Network quota：报警与强制限制分开

[Data use 概览][overview] 的 warning 表示提醒，limit 可触发禁用移动数据等限制；计费周期图表是历史查询视角。
这与 filesystem quota 对磁盘容量的限制无关，也不等同于 Data Saver 的 metered-background 规则。
判断“到限还在跑流量”时，先确定超的是哪种 quota、匹配哪个 Network/订阅/接口、哪个周期，及政策是否已传给实际软件/硬件路径。

旧 [kernel overview][legacy-kernel] 的 quota2 支持命名配额、到限通知 userspace 并丢弃随后流量；[kernel changes][legacy-changes] 还说明 NFLOG 通知机制。
这些是历史执行方式，不能要求现代内核必须加载 quota2 才算支持网络限额。
现代分支应从 policy 的目标值一路追到 kernel/HAL 执行及回调；任何旁路（尤其 offload）都需兑现同一限制。
由此推导，UI 发出 warning、netpolicy 持有配置和实际后续包被限制是三份证据，不应互相替代。

## Data Saver：metered、UID 状态和用户例外共同决定行为

Android 7.0 起 [Data Saver][data-saver] 提供设备级开关与用户控制；在 metered 网络上限制后台数据，并要求 app 尽量减少前台用量。
metered 不等于 cellular，也不是网络图标：Wi-Fi 也可能被标为 metered，移动网络政策也需看具体能力/配置。
后台 app 的限制与前台少用数据是不同机制，不能把后者写成所有前台包都会被强制丢弃。

[官方 app 行为][data-saver-app] 的 `getRestrictBackgroundStatus()` 区分 disabled、enabled 和允许绕过的状态；app 应结合当前网络是否 metered 判断。
用户可以给特定 app 例外；例外不是无限带宽许可，也不表示其他 doze、standby、VPN、企业或权限规则全部失效。
预装/OEM app 不应自行把所有 app 加到 allowlist；例外需要尊重用户选择，不能用隐藏豁免掩盖后台任务设计问题。[平台实施要求][data-saver]

状态改变通知需要动态注册相应广播，再重新查询当前状态；不能只在进程启动时缓存一次，也不能依赖 manifest 静态 receiver 一定收到。
Android TV 的官方行为有节流而非相同阻断的例外，故不能把手机的完全阻断断言直接套到 TV；具体速率/版本回查 [app 指南][data-saver-app]。
这里的 foreground/background 也应以目标政策使用的 UID/process 状态为准，不能以用户眼前是否看到一个 Activity 猜测全部网络规则。

验证矩阵应至少区分 metered/unmetered、前后台、开关变化、用户例外添加/撤销和其他同时有效的 UID 规则。
检查实际新传输/已复用连接的结果及 app 状态处理，而不只看 Settings 开关；相关 CTS 为 `HostsideRestrictBackgroundNetworkTests`，准确模块/过滤条件查目标树。[验证依据][data-saver]

## APN 类型排除：接口拓扑限制可实现性

[Exclude network types][exclude-types] 的 `config_data_usage_network_types` 是构建时控制纳入总量的 network types 的资源。
若 modem 为不同 APN 提供独立 Linux interface，framework 有条件按这种映射排除相应类型，例如零费率 MMS APN。
若多个 APN 共用同一个 interface，仅修改这个资源不能从聚合 counter 里拆出某 APN 字节。
因此“资源已 overlay，MMS 仍计入”先核对 APN→interface 关系；不能为了逼近账单而任意按比例扣流量。
这也不是任意 URL、应用或业务内容的流量识别/零费率引擎。

## 周期边界：周期规则不是清零内核计数器

[Usage cycle reset dates][cycles] 页面描述以 **UTC 00:00** 为月度边界，短月没有指定日号时使用次月 1 日的规则。
这是该文档的规则与示例，不能推广为所有分支和所有政策的硬编码时区：已核实的 [main 分支 NetworkPolicy][cycle-policy-sample] 使用 `RecurrenceRule`，`buildRule` 接收 `ZoneId`，构造/恢复政策也保存周期的时区。
因此应读取实际政策的 recurrence rule、起点/周期/时区及其生成来源，再核对目标 `RecurrenceRule` 的短月处理与边界精度。设备当前时区、政策保存的时区和 UTC 的表示方式可能不同；不能仅凭这张概览页把合法的非 UTC 政策判为缺陷。
由此推导，账期切换应更新查询/政策窗口，而不是为“从零开始显示”破坏底层单调计数器。
本地日期、时区变化、统计时间桶与用户重置日要分开处理；不能每次时区改变就把旧累计当新流量再记一次。

比较 UI、API、内核和账单时，先统一区间开闭边界、UTC/local 表示、订阅/网络身份、数据层次及更新时间。
周期结束、统计 poll、历史桶持久化与 UI refresh 并非同一时刻；原始值变动暂未显示，不自动证明丢量。
这类判断应保留相邻周期与 reboot/interface reset 证据，不能通过改本地时钟或清库来替代根因定位。

## 失败推导与定位证据

| 现象 | 同时保留的证据 | 先检验的不变式 |
|---|---|---|
| 总量大于所有 app 的直觉总和 | interface/IP 层统计、UID total/tag 分类、tether/offload、VPN | 是否混加总计和分类、转发或隧道双份数据 |
| 某 UID 量突然变负/突增 | 两份原始快照、poll/map swap、reboot、iface 生命周期 | 差分基线、重置及增量/累计读语义是否匹配 |
| VPN app “吃掉”全部流量 | owner/TUN/underlying 集合、修正前后 delta、模块 revision | 是否执行正确归属迁移、是否重复计 debug 记录 |
| 只在热点/offload 时漏量或不限额 | upstream/downstream、HAL stats/limit、NAT callbacks、软硬切换 | 统计和限制是否同时覆盖旁路 |
| Data Saver 开启仍有流量 | metered、UID 前后台、例外与其他规则、真实包结果 | 规则适用条件是否满足，而非仅看全局开关 |
| APN 排除无效 | APN→Linux iface、overlay 实际值、总量查询 | 聚合接口是否本来就无法区分 APN |
| 月初用量不符预期 | 实际 recurrence rule/时区、选定日号、短月、history buckets | 是否用文档示例覆盖了政策规则，或错误重置累计值 |

根据 [eBPF 验证入口][ebpf] 选择匹配分支的 TrafficStats/NetworkUsageStats CTS、netd/Connectivity 单测和内核/VTS 测试；硬件 offload 还需对应 HAL VTS 及真实转发。
旧 `dumpsys netd trafficcontroller`、现代 netstats/netpolicy 等工具输出应按目标实现解释；没有某 map 名不能证明功能不存在。
本页未提炼完整现代 `NetworkPolicyManagerService` 规则优先级、历史时间桶插值算法、各 VPN 协议封装及运营商计费规范；这些仍需目标源码/产品规范。
已给出的源码样本与历史文档不得替代当前分支复核，也不能以 CTS 某一流量测试通过推断真实 modem/offload 全部归属与限额正确。

## 已读官方依据

[overview]: https://source.android.com/docs/core/data
[ebpf]: https://source.android.com/docs/core/data/ebpf-traffic-monitor
[legacy-kernel]: https://source.android.com/docs/core/data/kernel-overview
[legacy-changes]: https://source.android.com/docs/core/data/kernel-changes
[tags]: https://source.android.com/docs/core/data/tags-explained
[interfaces]: https://source.android.com/docs/core/data/iface-overview
[vpn-sample]: https://android.googlesource.com/platform/packages/modules/Connectivity/+/0cc8d81cc79a18a50ac4aa8833725c5be048cc70/service-t/src/com/android/server/net/NetworkStatsFactory.java
[tethering-data]: https://source.android.com/docs/core/data/tethering-data
[offload]: https://source.android.com/docs/core/data/tethering-offload
[data-saver]: https://source.android.com/docs/core/data/data-saver
[data-saver-app]: https://developer.android.com/develop/connectivity/network-ops/data-saver
[exclude-types]: https://source.android.com/docs/core/data/excluding-network-types
[cycles]: https://source.android.com/docs/core/data/usage-cycle-resets-dates
[cycle-policy-sample]: https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/core/java/android/net/NetworkPolicy.java
