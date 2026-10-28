# AAOS SDV：跨 VM 服务、身份与可用性

发现/topic/channel、跨 VM I/O、部署/更新和诊断的专门机制见[SDV 服务协议](sdv-service-protocols.md)。本页保留架构与责任边界。

核实日期：2026-10-28。当前官方架构将 Android 17 / 26Q2 作为公开基线；旧 AAOS 分支不自动包含这些能力。
本页描述文档中的机制与工程推导，不能证明某辆车已集成、量产或获得安全认证。
使用前复核目标 manifest、`system/software_defined_vehicle`、产品 VM 拓扑、agent/APEX 与硬件支持。

## 与既有 AAOS 的关系

SDV 将 Android 的能力扩展到信息娱乐之外，以轻量 headless Android 和多 VM 组织车辆服务。
既有 AAOS IVI 仍承载应用及信息娱乐；SDV Core、SDV Media 与 IVI 拥有不同运行职责。[系统架构][architecture]
文档中的低启动时延和资源目标是特定设计能力，不能直接当成产品实测值。

| 运行范围 | 主要职责 | 必须另行确认 |
|---|---|---|
| SDV Core | headless 服务、通信、管理 agent | 可用库/运行时、VM 配置、车辆集成 |
| SDV Media | HAR 等早期图形/媒体能力 | 显示管线、PAL、硬件及安全设计 |
| SDV IVI | 完整 AAOS 体验、DriverUI 与应用 | Gateway、权限和服务接口组合 |
| 外部 ECU | 车辆功能及已有协议栈 | SOME/IP 映射、时序与安全责任 |

SDV Core 不能被当成任意 Android APK 都可运行的完整手机系统。
VirtIO VM 隔离也不能自动等同于 AVF protected VM 的信任保证。
云端 Cuttlefish 可提供集成反馈，但不证明物理 ECU、总线、显示或安全反应时限已经满足。

## VSIDL、service unit 与 service bundle

VSIDL 在 protobuf 数据类型之上定义服务交互；生成器处理注册及中间件绑定。
service unit 表达接口能力，service bundle 组织可部署服务，实例才是实际运行对象。[VSIDL][vsidl]
RPC、流和发布订阅是不同交互契约；同一业务事实不应因传输改变而悄然改变语义。

服务接口与具体传输解耦，使同一架构可以映射进程、跨 VM 或外部 ECU 通信。
这种解耦不消除延迟、断线、队列、重试和版本差异，客户端仍需定义不确定执行结果。
调用超时后，不能推断远端没有执行；重新提交有副作用的操作需要相应幂等或状态查询语义。
SOME/IP 或既有 ECU 映射需核对类型、实例、单位与错误表示，而不只是让生成代码编译。

## 服务实例身份不能用 PID 替代

服务实例有车辆范围的 FQIN 与 SID：FQIN 跨进程重启和系统重启保持身份，SID 绑定某次进程生命期。
服务重启后 SID 改变，旧 SID 不能继续指向新的运行实例。[实例身份][identity]
本地 Service Discovery Agent 识别进程并分配身份，远端通过相应证书链建立可信身份。

配置和持久引用一般应表达稳定名称，而运行中的连接、回调与缓存还需绑定本次实例。
同名实例重新上线不代表旧请求、订阅和授权缓存仍可继续使用。
仅在 payload 中声称自己的 FQIN，不能替代可信注册或证书验证。

## 发现、通信授权与 VM 信任

通信策略区分 client、server、publisher 和 subscriber，并绑定接口/channel 或消息类型/topic。
能发现服务、能调用服务、能提供服务和能发布数据是不同权限。[通信授权][authorization]
VM 级策略补充服务级授权，不能用一个“内部车辆网络可信”判断替代两层约束。

Service Discovery 会同步并缓存 mesh 节点的策略；节点离线会使相应缓存失效。
重连或策略变化后的调用，必须重新收敛到当前授权和当前实例状态。
权限失败、服务不存在、对端未就绪和通信中断应保持可区分，避免用统一重试掩盖拒绝访问。

SDV VM 通过 DICE 链及车辆配置确认对端身份，`vvmconfig` 与 `vvmtruststore` 承担不同配置职责。
证书链存在不等于已受信任；还需要 ECU 信任、测量校验和期望 VM 拓扑。[VM 身份][attestation]
镜像、密钥、启动测量或 provision 状态不匹配时，关闭验证只提供诊断条件，不能证明正式 mesh 可用。

## Orchestrator 与电源驱动的生命期

每个 VM 的 Orchestrator 根据车辆、电源及自定义模式控制服务实例的创建、启动、停止和销毁。
配置来自服务包与 VM 级规则，声明的依赖和状态必须与实际就绪条件一致。[Orchestrator][orchestrator]
配置文件已存在不代表它是当前生效文件；持久配置可能覆盖 boot-time 默认选择。

模式转换应解释正在处理的请求、资源释放及重复启动，而不只定义“运行/停止”两个结果。
一个服务启动了不代表其依赖已经可用；一个进程退出也不代表外部物理动作已撤销。
自定义 mode 的发布授权需要保持明确，否则普通服务可间接改变其它服务的生存状态。

## Health Monitor、恢复与更新

Health Monitor 监测存活心跳、QoS、实例恢复与关键 agent 状态，形成 VM 健康报告。
服务需按配置产生信号；集成方提供的 listener 决定怎样恢复，HM 本身不包办车辆恢复策略。[健康机制][health]
心跳说明被观测实体满足某种存活条件，不单独证明输出正确或所有请求均满足时限。

重启策略需防止无限恢复循环；稳定名称与新的运行 SID、订阅和外部动作要一起收敛。
局部 VM 的恢复可能影响其它 VM 的依赖，不能假设局部进程恢复等于整车能力恢复。

Update Manager 管理本 VM 的系统或 service bundle 更新，车辆级组合由系统集成客户端协调。
Prepare、Activate、Commit 表达不同持久状态，激活后还存在需确认或回退的阶段。[更新状态机][update]
APEX 暂存成功与所有 VM 已运行兼容版本不是同一结论。
中断、重启、回退以及共享协议/数据兼容需按车辆更新方案验证，不能从单 VM 成功推导跨 VM 原子更新。

## IVI Gateway 保留平台边界

SDV Gateway 让 IVI Java 应用及 native 服务通过注册、发现与 RPC 访问 SDV 服务。
VHAL proxy 是一种集成模型，不意味着 SDV topic 可以绕过车辆属性权限和状态契约。[Gateway][gateway]
native client 的 Binder 回调依赖正确线程池与 client 生命周期，销毁前需收敛订阅和回调。
服务重连时同时核对权限、接口与实例身份，避免把旧远端句柄或旧车辆缓存视为有效。

## Display Safety 的安全与可用性责任

DriverUI 提供丰富 Android 界面，HAR 负责需快速出现及 Android 不可用时的关键/占位呈现。
两路输出的组合与心跳决定显示归属，不只是“两个应用画到同一屏幕”。[Display Safety][display-safety]
Safety design toolchain 生成工件，Safety Monitor 验证相应显示；其参考实现不是已获 ASIL 认证的产品方案。
OEM 必须结合硬件、PAL、设计、监控和失效处理完成自身安全论证与认证。

“有安全设计工具”“心跳正常”“页面提到 ASIL 目标”均不能单独证明产品达到该安全等级。
显示输出一致、早期启动可用、IVI 故障后占位/警示正确及超时反应，需各自有实际证据。

## 故障归因的证据

| 现象 | 有区分力的证据 | 常见误推 |
|---|---|---|
| 发现后调用被拒绝 | service/channel、bundle 策略、VM 策略及对端身份 | 发现成功意味着已授权 |
| 重启后错误实例收到请求 | FQIN、旧新 SID、注册与连接时间线 | 服务名相同即可复用旧状态 |
| 电源变化后功能丢失 | mode、实例期望状态、依赖就绪和配置来源 | 改成永不停止即可修复 |
| 更新一部分后通信异常 | 每 VM 版本、APEX、状态机与接口组合 | 某次 Commit 成功证明整车一致 |
| 仪表缺少关键内容 | HAR/DriverUI/监控状态、实际合成及硬件路径 | Android UI 正常等于安全显示正确 |

## 已读官方依据

资料来自公开官方正文缓存；缓存提取日期不代表产品发布或认证日期。下列当前架构需逐项映射目标分支。

[architecture]: https://source.android.com/docs/automotive/sdv/sdv-system-architecture
[vsidl]: https://source.android.com/docs/automotive/sdv/core-areas/vsidl
[identity]: https://source.android.com/docs/automotive/sdv/core-areas/service-identity
[authorization]: https://source.android.com/docs/automotive/sdv/workstreams/core/comms-authorization/overview
[attestation]: https://source.android.com/docs/automotive/sdv/workstreams/core/vm-attestation/overview
[orchestrator]: https://source.android.com/docs/automotive/sdv/core-areas/orchestrator
[health]: https://source.android.com/docs/automotive/sdv/core-areas/health-monitor
[update]: https://source.android.com/docs/automotive/sdv/core-areas/sdv-update-manager
[gateway]: https://source.android.com/docs/automotive/sdv/sdv-gateway-on-ivi
[display-safety]: https://source.android.com/docs/automotive/sdv/display-safety
