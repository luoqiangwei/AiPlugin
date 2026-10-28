# AAOS SDV 服务协议、跨 VM 协作与恢复责任

核实日期：2026-10-28。当前官方系统架构把 Android 17 / 26Q2+ 作为 VSIDL 声明 RPC/topic 的公开基线。
本文在 [automotive-sdv.md](automotive-sdv.md) 的身份、安全与架构概览上补充协议、部署和状态责任；不宣称参考实现已量产、具备硬实时保证或取得 ASIL 认证。
部分旧 IVI 集成页涉及 Android 15，字段/代理/属性不应脱离目标分支照用。[系统架构][architecture]

## Topic/channel 与运行实例

topic 是按消息类型和名称发布/订阅的数据域，可有多个 publisher；channel 是按服务类型和名称发 RPC 的交互域。
客户端关注 topic/channel 时可由 middleware 找端点，不必把进程地址硬编码为业务配置。
底层 service unit 仍用于 endpoint 注册/发现，会出现在调试工具中；“业务无需选 publisher”不等于没有实例身份与授权。[逻辑模型][logical]

service bundle 是授权单元，运行实例映射到一个 Linux 进程；SDV package/APEX 是更新单元，可含多个 bundle，包内来自同一软件信任来源。
bundle、package、instance 与 RPC service type 不能用同一个名字替代；同一 package 的不同 VM 也可能运行不同版本。
FQIN 稳定标识实例，SID 绑定一次进程生命期；重启后 SID 不同，缓存的 remote handle、request 状态和授权关联都需重新收敛。[逻辑模型][logical] [实例身份][identity]

## Service Discovery 是具有生命期的 mesh 状态

本地 SD Agent 识别和注册 bundle，再参与跨 VM 发现；身份与证书的信任链必须成立，不能只信 payload 自报的 FQIN。
mesh 共享各 VM 的授权策略，本地 cache 参与远端 service unit 的发现/许可判断；节点丢失连接时，其缓存策略被删除。
所以“昨天发现过”“进程同名重启”“网络已 ping 通”都不足以复用旧的可用性与权限结论。[身份][identity] [Mesh 授权][authz]

| 状态 | 能证明的事实 | 后续仍需判断 |
|---|---|---|
| 端点注册/Available | 某时刻发现了服务单元 | 当前实例、授权、业务依赖和请求是否成功 |
| topic 暂无消息 | 本次没有可消费消息 | publisher 仍在、尚未发布，还是已 deregister |
| RPC 创建 Unavailable | 端点不存在/尚未注册等 | 服务是否在正确 VM/channel、Orchestrator 是否应启动 |
| 请求已提交 | 传输接受工作 | 远端是否执行、结果是否回来、副作用是否完成 |
| 节点恢复 | 连接重新建立 | 身份、策略 cache、注册、订阅和业务状态是否重建 |

应订阅 availability stream，将 Available/Unavailable 与 reader/RPC 生命周期连接。
publisher deregister 后，Subscriber 可能返回空列表，History 仍有旧消息，Observer/InstantReader 也可能报错；空队列在 publisher 活着但尚无数据时也可能出现。
不能仅凭 read 返回空就判为通信故障，或凭读到历史值就判为远端在线。[middleware 失效][troubleshoot] [可用性监听][suspend]

## 数据流的溢出与请求的不确定结果

publisher 快于 reader 时，Subscriber/Observer 的第一次后续读取可报告 DataLoss，表示队列历史不再完整。
选择降低生产速率、采样或只读最新值应由数据语义决定：InstantReader 适合最新状态，不能替代需要每次事件的审计/控制序列。
放大队列只是增加可容忍暂时积压，也可能增加延迟/内存，并不修复长期消费能力不足。[DataLoss][troubleshoot]

RPC 支持 unary 与流式交互，终止流、取消客户端、remote death 和完成业务操作是不同事件。
超时后远端可能已经执行，重试有副作用的命令需幂等标识、去重或状态查询；middleware 不能替应用决定物理执行是否应再次发生。
跨 VM 的 payload 仍需类型、单位、范围、时间与错误语义，protobuf 可解码只说明格式兼容，不证明双方理解一致。[VSIDL][vsidl]

## Transport 与 VirtIO 的作用范围

SDV middleware 可抽象 vsock、Ethernet、Binder、gRPC、FMQ 等路径，实际选用受运行域、配置和接口能力影响。
本地共享内存/FMQ 的优化不等于默认存在跨所有 VM 的共享内存数据网；旧 Core integration guide 把共享内存限定在 VM 内 IPC 等语境，跨 VM 首选直接 vsock，跨 SoC 用 Ethernet。
serial 在该指南中用于调试，不能把串口接通作为生产服务网络已建立的证据。[架构][architecture] [Core 集成][core]

当前 guest requirements 列出 GKI 6.6/6.12，旧 integration guide 仍出现 6.1；应按目标 release 的 requirements/manifest 核对，不能选看方便的一条。
guest/host 要匹配 virtio-blk、console、net、PCI、rng、vsock 等能力及路由；host↔guest 与 guest↔guest 的可达条件不同。
vsock CID/port、Ethernet/VLAN/IP、VM identity 和 SDV service name 是不同标识，替换 VM 镜像后需核对整个对应关系。[系统要求][requirements]

SDV Core 是原生系统，不包含完整 JVM/Java 系统服务；某 IVI APK 能运行不能推导在 Core 可运行。
Core 的 KeyMint/DICE/网络等仍依赖硬件或虚拟设备后端；只看 guest adbd 正常无法证明安全硬件或车辆网络可用。[Core][core]
SDV Media 包含 Core 加图形/媒体能力，参考路径有 virtio-gpu/media/snd/input；也可在约定 userspace library 接口处集成厂商方案。
后一方式可能让云与真实硬件使用不同驱动，模拟环境性能与可用性必须保留该差异。[Media 集成][media]

## SOME/IP broker 负责协议映射而非业务等价证明

broker 将 SDV RPC/data tunnel 与外部 SOME/IP 对接；本地 stack 实现由 AIDL 接口隔离，可使用厂商栈或 vsomeip 参考实现。
VSIDL provider 提供 runtime type information 与 mapping，service/instance/method/event/eventgroup ID、版本与 SDV type/channel/topic 需一起匹配。
SDV 的 SID（运行实例身份）和 SOME/IP service ID 不同，不能因为缩写相同把它们当同一值。[SOME/IP 总览][someip] [映射][mapping]

每个 broker 实例需要对应本地 stack，provider 要位于 broker 同一 VM，schema/mapping 的可见位置也要符合当前部署能力。
多 broker 可按域/子网拆分，但端点集合应互不重叠；没有自动 cross-agent 同步替它们消除重复发布与发现冲突。
配置文件已打包而 agent 因 boot property、Orchestrator ready 或 stack 未就绪未启动时，不应误判为 ECU 不提供服务。
序列化、类型转换、报文大小与错误码等仍需按 mapping/type definition 和外部 ECU 协议核对。[部署][someip-deploy]

## 部署元数据、配置来源与版本兼容

bundle metadata 至少含 name、整数/字符串版本、相对 APEX 根的 native library path。
orchestration、authorization、VSIDL schema、diagnostics 与 external protocol mapping 路径各自有用途，不是随意可互换的配置路径。
APEX 被安装、registry 发现 metadata、library 可加载、bundle created、on_start 完成与服务端点可用，是六类不同证据。[Metadata][metadata]

Orchestrator 综合 bundle 配置与 per-VM 配置，按 vehicle/power/custom modes 决定 created/started/stopped/destroyed。
persist 配置路径可覆盖 boot 默认且跨启动保留；改 bootconfig 后行为不变应先核对有效来源，不能不断修改未被读取的文件。
声明依赖或设置 started 也不自动证明远端服务已经注册/业务可用，调用方仍需处理 availability。[Orchestrator][orchestrator]

VSIDL 的兼容性同时要求能连接并能理解数据，不能只用 protobuf wire compatibility 判断。
重命名 channel/topic/type、改 RPC 输入输出或消息 field number/type 可能破坏既有端点；新增字段/enum 也可能要求默认/未知值处理。
语言生成、运行时 RTTI、授权文件与 SOME/IP mapping 都可能消费名称，因此“字段名不影响 protobuf 编码”不足以保证 SDV 组合兼容。
工具生成与编译成功只证明该组合能构建，混版本更新后还需观察运行协议语义。[兼容指南][compatibility]

## 授权 enforcement 与身份配置分开

bundle policy、VM policy、VM attestation/truststore、进程 UID/SELinux 保护不同边界。
Core APEX 内通过 metadata 定位 policy，IVI APK/agent 的部署位置又可能不同；把 policy 放错域会表现为有文件却不授权。
agent 没有 APEX 时可由 companion config APEX 承载策略，不能因为它是系统进程就跳过授权建模。[部署差异][authz-deploy]

user build 强制授权且不能通过调试 property 关闭；非 user 可配置 enforcement，设置仅影响本 VM，且运行时值不跨重启保存。
部分 VM 关闭 enforcement、部分开启会形成 split enforcement，不能把这种环境的成功调用视为正常安全组合证明。
Android 15 legacy IVI 的 property 名称还有差异；错误属性未生效与授权策略错误应分开定位。[Enforcement][enforcement]

## VPM、调度与时间共同约束在途工作

车辆 mode 对各服务描述共同车辆状态，power state 则按 VM 独立；OEM power service 请求 VPM，VPM 等待 agents 按 OEM timeout 完成转换后再通知 OEM。
某 VM 已准备睡眠不证明整车全部 VM 已就绪，单 agent timeout 也不自动说明应该直接切断硬件电源。[VPM][power]

bundle 在 on_stop 停止 publisher/subscriber/RPC 工作线程，resume 的 on_start 再按配置创建；created 但不销毁可降低恢复成本。
WAIT_FOR_FINISH 是仍应预期 agents 可响应的最后阶段，不应拖到 SUSPEND_TO_RAM_POST_FINISH/POWER_OFF_POST_FINISH 才依赖它们收尾。
从旧线程收到晚到结果时，要判断属于停止前还是新的实例/订阅，防止恢复后重复物理动作。[Suspend/resume][suspend]

QoS 由 bundle 声明 preset、OEM 映射 Linux scheduling attributes、Lifecycle Manager 在继续执行前应用。
NORMAL/ELEVATED/IDLE 等名称不是跨车型固定 nice/实时性能承诺；privileged preset 的 CAP_SYS_NICE 扩大调度能力，需与 SELinux domain/授权组合解释。
即使使用实时 policy，CPU 预算、阻塞 I/O、跨 VM 调度与优先级反转仍能破坏端到端时限，不能从 preset 名字推导硬实时完成。[Scheduling][scheduling]

UTC 用于日期/证书等，network monotonic clock 用于车辆事件协调，经相应 PTP/dynamic clock 暴露；各 VM 必须能对应共同的时间来源。
clock_gettime 失败需保留 errno/未就绪状态，不能用本地 wall clock 替代为“差不多”的顺序。
官方 time-sync 不将 userland clock/alarm API 用于 >100Hz 或 <10ms 事件时限，这类要求需适合的 kernel/硬件实现。
trace 时间对齐与可信时间状态也分别需要证据。[Time sync][time]

## Update Manager 的 VM 状态与车辆组合责任

Update Manager 只执行其 VM 的 system/bundle update；整车更新客户端提供 payload 并协调所有 VM。
PREPARE 写入/暂存而未生效，ACTIVATE 设置下次启动激活，COMMIT 才使其永久；包内 bundles 同 APEX 更新，不表示其它 VM 同时更新。
客户端先提供 listener RPC 再订阅 status，并在重连后 GetStatus，不应只依赖一次可能丢失的进度回调。[Update Manager][update]

ACTIVATE_PRE_REBOOT_COMPLETE 表示可重启，ACTIVATE_POST_REBOOT_COMPLETE 表示新版本已起但仍待 commit/rollback。
userdata checkpoint 支持失败回退，boot-attempt 限制与 BootControl/APEX session 状态会影响回退；进度 100% 不是已 commit。
跨 VM 接口、持久 schema、共享配置与外部 ECU 组合兼容由整车协调者负责，某 VM READY 不能证明整车原子一致。
故障需保留 UpdateEngine/ApexService/BootControl/Vold 等 failure reason，而不统一写成“下载失败”。[更新状态机][update]

## ConCal、用户偏好、Diagnostics 与 Telemetry

ConCal 让 bundle 注册 schema/default，再按车辆条件得到配置/校准；配置 ID、owner 与 override 的有效范围决定哪份配置作用于哪个实例。
文档存在 26Q2 前后的 ID 差异，不能持久化旧结构后默认跨版本解释相同；多个 ConCal server 也有配置所有权/转发责任。
应用配置成功与物理传感器/执行器校准有效不同，服务仍应验证当前可接受范围。[ConCal][concal]

User Preferences agent 管 per-user/shared 设置的存储、路由与通知，domain 服务保留安全规则与实际应用的自主决定权。
RequestSettingsChange 返回应反映实际接受、拒绝或 clamp 的值，不能先持久化 HMI 期望值再当成硬件状态。
换用户时应用偏好同样可能受当前车辆状态限制，不能把一个旧用户的异步应答提交给新用户。[User preferences][preferences]

Diagnostics Manager 由 OEM 实现，可通过标准 SDV API 将 UDS 请求委派给 bundle。
Authentication/SecurityAccess、DID 读写、routine、IO control、file transfer 与 fault event 有各自状态和授权；普通日志不等同 DTC/故障生命期。
VSIDL diagnostics declaration 描述实体不代替 OEM tester 协议、session/security-level 与 ECU reset 的车辆责任。[Diagnostics][diagnostics]

Telemetry metrics config 定义数据源、stateful aggregator、trigger、report 和生命期。
report 在内存生成并通知 client 获取，不自动证明已上传/持久保存；配置被激活也不证明 source 已存在、有权限或 schema 一致。
Configurable Publisher Registry 让非 SDV middleware 的组件经 Binder 注册，需显式提交 descriptor/type、支持 get/subscribe 与正确 serialized payload；其 SDK 文档明确仍有 experimental 部分。[Metrics][metrics] [Registry][registry]

## 测试与故障的可观察边界

SDV Test Framework 基于 Mobly，区分 sample、E2E、long-running、performance 与只适用物理设备的 hardware tests。
多 VM template 的 device1/device2/device3 绑定、版本组合、授权状态与 setup/teardown 都是测试语境；单 VM sample 成功不能替代真实跨 VM/ECU 组合。
失败/中断后的清理要覆盖会话、配置 override、agent 与资源；残留 persist 状态可能令后续用例测试另一种系统。[测试框架][tests] [系统测试][test-creation]

trace 缺事件可来自未初始化 tracing、未插桩、category 未开或该路径没执行；不能从空轨迹直接判为零耗时。
应关联 FQIN/新旧 SID、VM、request/channel/topic、power/update 状态与统一时钟；guest、host、broker/stack、外部 ECU 日志承担不同证据。
官方仍将部分 Data Tunnel tracing 写为计划能力，不能假定所有路径都有完整内建 trace。[Tracing][tracing]

## SDV 导航主要分支归属与剩余深度

| 导航分支 | 承接机制 | 未逐项展开的边界 |
|---|---|---|
| Get started / local/cloud/org / code/IDE/tooling | `setup-product-integration.md`、`devices-virtualization.md`，本页部署模型 | 云账号/网络/组织资源和每个 IDE 插件配置 |
| System architecture / logical/identity/naming | `automotive-sdv.md` 与本页 | 全命名 grammar、所有 registry 内部结构 |
| Orchestrator / health / power / time / scheduling | 两页共同承接 | 全 mode 规则、Health listener schema、每个调度/恢复参数 |
| Authorization / attestation / bootloader/CDI/truststore/provisioning | `automotive-sdv.md`，本页 enforcement/deployment | 各证书 extension、DICE 字段与 OEM provisioning 全状态 |
| VSIDL / generated middleware / catalog/LSP / reflection / async Rust | 本页 | 语言语法、生成器 CLI、Rust 每个异步接口及 reflection API 全表 |
| Metadata / APEX signing / system/bundle/OEM AB updates | 本页与 `updates-boot.md`、`automotive-sdv.md` | 密钥交付、各分区 payload、完整整车回退协调 |
| Automotive services / ConCal / Diagnostics / User preferences | 本页 | 全 UDS 映射、override 合并算法与每种 preference schema |
| Core / Media / QNX/QVM / requirements / kernel/partitions | 本页与 `kernel-native.md`、`devices-virtualization.md` | QVM 样例全部字段、每个 VirtIO 后端和 PAL 驱动实现 |
| SOME/IP / mapping/type/stack/deploy/optimization / IVI Gateway | 本页与 `automotive-sdv.md` | 每种 AUTOSAR 类型编码、性能调优参数及 Gateway 全 API |
| Test/debug/security violation/SELinux/tracing | 本页与 `testing-diagnostics.md`、`selinux-compatibility.md` | 全测试模块、工具参数与车型故障注入矩阵 |
| Display Safety / DriverUI / HAR graphics/camera/PAL/chimes/toolchain | `automotive-sdv.md`；媒体边界见 `automotive-media-integration.md` | 安全工具链全格式、硬件时限和功能安全论证 |
| Telemetry / SDK/generator/API/data sources/cloud simulation | 本页 | generator 请求全 schema、SDK 全 API、云模拟部署与隐私产品策略 |

导航有归属不等于所有叶子规范均已提炼；尚未展开的内容按上表定位，不能以 114 个导航 URL 或文档读取数量作为机制完成证明。

## 官方依据

[architecture]: https://source.android.com/docs/automotive/sdv/sdv-system-architecture
[logical]: https://source.android.com/docs/automotive/sdv/core-areas/what-service
[identity]: https://source.android.com/docs/automotive/sdv/core-areas/service-identity
[authz]: https://source.android.com/docs/automotive/sdv/workstreams/core/comms-authorization/overview
[vsidl]: https://source.android.com/docs/automotive/sdv/core-areas/vsidl
[troubleshoot]: https://source.android.com/docs/automotive/sdv/core-areas/vsidl/troubleshoot
[suspend]: https://source.android.com/docs/automotive/sdv/core-areas/vsidl/handle-suspend-resume
[core]: https://source.android.com/docs/automotive/sdv/workstreams/core/integration-guide
[requirements]: https://source.android.com/docs/automotive/sdv/workstreams/core/requirements
[media]: https://source.android.com/docs/automotive/sdv/workstreams/media/integration-guide
[someip]: https://source.android.com/docs/automotive/sdv/some-ip-integration
[mapping]: https://source.android.com/docs/automotive/sdv/some-ip-integration/some-ip-mapping
[someip-deploy]: https://source.android.com/docs/automotive/sdv/some-ip-integration/deployment
[metadata]: https://source.android.com/docs/automotive/sdv/workstreams/core/service-bundle-metadata
[orchestrator]: https://source.android.com/docs/automotive/sdv/core-areas/orchestrator
[compatibility]: https://source.android.com/docs/automotive/sdv/core-areas/vsidl/vsidl
[authz-deploy]: https://source.android.com/docs/automotive/sdv/workstreams/core/comms-authorization/deployment
[enforcement]: https://source.android.com/docs/automotive/sdv/workstreams/core/comms-authorization/enforcement
[power]: https://source.android.com/docs/automotive/sdv/core-areas/power-management
[scheduling]: https://source.android.com/docs/automotive/sdv/core-areas/scheduling
[time]: https://source.android.com/docs/automotive/sdv/core-areas/time-sync
[update]: https://source.android.com/docs/automotive/sdv/core-areas/sdv-update-manager
[concal]: https://source.android.com/docs/automotive/sdv/core-areas/automotive-services/concal
[preferences]: https://source.android.com/docs/automotive/sdv/core-areas/automotive-services/user-preferences
[diagnostics]: https://source.android.com/docs/automotive/sdv/core-areas/automotive-services/diagnostics
[metrics]: https://source.android.com/docs/automotive/sdv/workstreams/telemetry/metrics-configuration
[registry]: https://source.android.com/docs/automotive/sdv/workstreams/telemetry/configurable_publisher_registry
[tests]: https://source.android.com/docs/automotive/sdv/testing/sdv-test-framework
[test-creation]: https://source.android.com/docs/automotive/sdv/testing/sdv-system-tests-creation
[tracing]: https://source.android.com/docs/automotive/sdv/workstreams/core/tracing
