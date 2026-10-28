# AAOS 车辆服务：属性、健康、远程任务与电源

核实日期：2026-10-28。本文以官方正文缓存中的接口契约为依据；解释工程后果的句子是机制推导。
Android 版本、Car API 版本、VHAL 接口版本与属性版本是不同维度，应映射目标 manifest、VINTF 和产品配置。
基础 AAOS 定位见 [automotive.md](automotive.md)，跨 VM SDV 服务见 [automotive-sdv.md](automotive-sdv.md)。

## 属性配置决定可调用的能力

`VehiclePropConfig` 描述 property ID、类型、area 类型、access、changeMode、配置参数及采样边界。
ID 由 SYSTEM/VENDOR 分组、area 类型、数据类型和低位唯一 ID 组合而成；它不是可以随意重排的应用枚举。
GLOBAL 属性使用 `areaId=0`；分区属性的 area ID 是对应区域位标志的组合，必须出现在支持配置中。
例如同一个 HVAC 温度区域可以覆盖多个座位，不能要求每个座位都对应独立可控执行器。[配置][configuration]

| 契约 | 实现与客户端应保留的语义 | 配错后的典型后果 |
|---|---|---|
| 类型与 payload 字段 | INT32、FLOAT、向量、STRING、BYTES、MIXED 各有指定字段；MIXED 的布局依赖 configArray | 读到默认零、越界或双方解释不同 |
| area 与每区配置 | 按属性的物理影响范围分组；读写能力和支持值可按区不同 | 控制错误座位或暴露不存在的独立控制 |
| STATIC | 启动后不变 | 客户端缓存的“静态”能力在运行中失真 |
| ON_CHANGE | 值或状态改变时上报 | 失联或故障状态永不传播 |
| CONTINUOUS | 按订阅频率/车辆消息频率报告；min/maxSampleRate 必须可实现 | 不可达采样承诺、总线或 Binder 负载失控 |
| 静态范围/枚举 | 描述启动时支持值，不能当成动态能力的唯一来源 | 运行时已不可用的档位、位置或范围仍可选 |

系统属性的 access/changeMode 必须符合官方定义。配置里的 property access 与 area access 也不能凭“权限越多越好”扩大。
`minSampleRate` 到 `maxSampleRate` 之间不保证每个频率都受硬件支持，客户端不能据此假定任意精确周期。
HVAC_POWER_ON 的依赖列表影响哪些属性在 HVAC 断电时不可用；区域映射应让每个受影响座位恰好归入一个控制区域。[特殊属性][special]

Android 14 增加 `supportedEnumValues`，空列表在相应契约下表示支持全部枚举，不能解释成不支持任何值。
Android 15 增加 `supportVariableUpdateRate`：连续属性可对要求可变更新的客户端去除重复值。
只要还有固定频率订阅者，VHAL 仍需按固定模式生产，AAOS 再为可变频率客户端过滤；因此某个客户端回调减少不证明底层采样也减少。
Android 16 / VHAL V4 用 `hasSupportedValueInfo` 声明动态范围/支持列表能力，并通过查询、注册及变化通知更新。
缺少声明或旧版接口时应使用静态信息，不能直接调用新方法并把失败当作车辆不支持属性。[配置][configuration] [接口][interface]

## 状态、时间与异步完成是三个事实

`VehiclePropValue.timestamp` 对齐 `elapsedRealtimeNano()` 的单调时钟，表达事件发生时间；它不是 UTC，也不保证等于客户端收到回调的时间。
`status` 表示读取状态。只有 AVAILABLE 时 payload 才可使用；UNAVAILABLE/ERROR 的 payload 必须忽略。
对于 READ_WRITE 属性，读取 AVAILABLE 不保证此刻允许写入，写入可用性需从实际写操作结果得知。[接口][interface]

`getValues`/`setValues` 提交一批异步操作；Binder 方法返回与属性操作完成必须分开。
结果通过 `onGetValues`/`onSetValues` 回调交付，一次回调可以只包含已经完成的一部分结果。
请求 ID 应关联本次请求和超时/取消状态，避免重连后旧回调完成了新请求。
已知所属请求的写错误通过对应 set result 返回；无法关联原始请求的异步写错误才走 `onPropertySetError`。
HAL 不应在接收请求的 Binder 线程等待车总线操作完成，否则一个慢 ECU 可拖住全部调用。[接口][interface]

由此可以推导：提交成功、VHAL 处理成功、ECU 确认和物理动作完成可能有不同时间点。
是否回读、等待状态变化或使用属性特定确认，取决于具体属性契约，不能给所有车辆操作套统一“setter 成功即完成”。
超时也不能证明 ECU 没有执行；有副作用的重试需结合请求去重、当前状态和车辆协议处理。
订阅应携带 property/area/rate，状态变化也应上报；清理订阅、客户端死亡与服务重连都属于数据正确性的一部分。

LargeParcelable 通过内联 payload 或共享内存 FD 承载大列表，native 端应使用规定的序列化辅助库。
文档中的库内阈值不等于 Binder 的通用硬上限，也不意味着任意大、高频 vendor BYTES 都适合经过车辆属性通道。
配置或事件突然变大时，需区分序列化错误、FD/映射生命周期与车辆侧超时。[接口][interface] [扩展限制][special]

## 版本、扩展与权限边界

| Android 基线 | 官方列出的最新 AIDL VHAL | 重要区别 |
|---|---|---|
| 13 | V1 | AIDL VHAL 起点，属性定义尚未拆成独立接口 |
| 14 | V2 | 属性接口 `android.hardware.automotive.vehicle.property` 与 VHAL 接口分离 |
| 15 | V3 | 支持可变更新频率的配置能力 |
| 16 | V4 | 动态支持值查询与变化通知 |

官方表中 Android 13–16 的最小兼容 AIDL 版本均列 V1；这不使新方法、新属性或新 Car API 自动在旧实现上存在。
VHAL 与属性接口要分别声明依赖；HIDL 分支迁移还涉及产品实例、VINTF、服务和测试，不能只换客户端生成代码。[接口版本][interface] [属性版本][system-properties]

标准属性优先，vendor 属性不能重复已有 SDK 车辆属性来避开生态契约。
扩展默认使用 vendor extension 权限，`SUPPORT_CUSTOMIZE_VENDOR_PERMISSION` 可按 property 分别配置读/写权限。
`PERMISSION_NOT_ACCESSIBLE` 禁止 Android 应用经相应 API 访问，不等于已经阻止所有 native VHAL 客户端；native 域仍需权限、SELinux 与接口约束。
SEAT/STEERING 的位置与移动属性、ADAS 的启用与状态属性应保留各自意义，控制请求不能替代真实状态反馈。[扩展][special] [座椅][seat] [ADAS][adas]

## CarService、可选能力与 Watchdog

Car API/manager 是客户端契约，CarService 承担权限、用户、策略与 HAL 协调；车辆协议适配属于 VHAL/厂商实现。
多数汽车服务是必选，部分能力由 `config_allowed_optional_car_features` 允许，再由 VHAL 的 `DISABLED_OPTIONAL_FEATURES` 阻止。
因此“类存在”“APK 安装”“RRO 中列出功能”都不能证明 manager 可用。
诊断需同时查看当前 enabled、配置默认值、VHAL blocklist 和等待重启的 pending 状态。[功能控制][features]

Watchdog 的健康检查与资源过量使用是两条机制。
服务注册超时等级后，需在本次 session 的健康确认完成后回复；只让独立线程机械回 ping，不能证明工作线程未死锁。
未及时回复的进程可被终止并生成 `/data/anr` 状态，故障分析应关联 session、被测工作队列、调度/锁等待和终止时间。
VHAL 通过 `VHAL_HEARTBEAT` 接受健康监测；没有该属性时不能假定 Watchdog 正在监测 VHAL。
默认心跳检查间隔及 `ro.carwatchdog.vhal_healthcheck.interval` 需按目标版本复核，增大间隔会改变故障发现时限。[系统健康][watchdog-health]

Flash 监控使用内核 per-UID I/O 统计，按 UTC 日聚合，并跨同日的车辆重启保留用量。
前台、后台与 Garage Mode 有不同阈值；包特定、应用类别和组件默认值存在优先关系。
vendor 服务默认被视为关键，只有配置为 safe-to-terminate 的实体才适用对应终止/禁用动作；不能笼统宣称“超额便杀所有应用”。
被设为 DISABLED_UNTIL_USED 的应用需要 Launcher 正确展示与重新启用，否则用户会认为应用被卸载。
重启不能规避当日预算；减少日志、批量写入和缓存策略应针对实际写入来源。[Flash 监控][watchdog-flash]

性能记录是采样证据，user 与 userdebug/eng 的采样频率不同；开机、唤醒、换用户和滚动窗口也不同。
Top UID 的 CPU/I/O 或缺少一次样本不能单独证明根因，应关联事件窗口和线程/总线证据。[性能记录][watchdog-perf]

## AP 电源状态与组件策略

VMCU 发起车辆电源请求，CPMS 协调 AP 状态转换，VHAL 传递 `AP_POWER_STATE_REQ/REPORT`，内核/BSP 实现 STR/STD/关机。
CPPD 是电源策略状态的权威，CPMS 将策略请求委托给它；Android 应用不能以自己的 UI 状态代替车辆电源状态。
WAIT_FOR_VHAL、ON、PRE_SHUTDOWN_PREPARE、SHUTDOWN_PREPARE、最终 suspend/关机有不同含义。
其中熄屏、音频关闭后系统仍可能运行维护任务；STR 时 RAM 保持而 CPU 不执行，STD 则把状态写入非易失存储。[电源状态机][power]

`CAN_SLEEP`、`CAN_HIBERNATE`、`SHUTDOWN_ONLY` 与各 IMMEDIATELY 参数影响允许的目的状态及能否延后。
延后关机需要有界完成条件；listener 的异步 future 只在对应版本允许的状态使用，不能把所有回调都当作无限期异步准备窗口。
最终 ready 报告、外围接口发送完成和内核入睡之间的竞态由集成方负责。
“CPMS 请求 suspend”不足以证明硬件已休眠，证据还需内核结果、唤醒源、外设状态和 VMCU 交互。[电源][power]

策略指定组件的预期 on/off；部分策略可仅更新所列组件，当前生效状态需看累积结果和当前 policy group。
应用/原生服务按 filter 订阅自己关心的组件，硬件驱动仍必须执行实际状态变化。
策略变更和 AP 状态转换相关，但不等价：关闭 AUDIO/DISPLAY 不必关闭 CPU，切换 policy 不等于 VMCU 已断电。[电源策略][power-policy]

Garage Mode 给 `JobScheduler` 的 idle jobs 提供停车维护窗口，应用通过 job 约束参与。
网络、用户解锁和其它约束仍然有效；一个从未在本次启动解锁的用户不能仅因 Garage Mode 获得 CE 数据访问。
允许延后的 SHUTDOWN_PREPARE 与资源不足时允许的立即退出不同；任务必须承受取消、未完成和下次重试。[Garage Mode][garage] [用户生命期][user-system]

## 远程访问的身份、时限与所有权

Android 14 引入的 Remote Access 是显式 opt-in 能力，依赖 Remote Access HAL、TCU/唤醒客户端、车辆电源控制与服务器。
AAOS 提供任务交付和客户端生命期，不提供整个云服务、用户认证、车辆 attestation 或任务数据安全方案。
注册关联 user、vehicle ID 与 CarService 分配的 client ID；server 必须确认车辆身份/所有权，不能信任请求里自报的 VIN 或 ID。[远程访问][remote]

远程任务客户端由 CarService 绑定和管理，运行于 system user，因此不自动获得司机用户的凭据数据。
客户端应尊重 `remainingTimeSec`，完成时报告 task done，关机通知时停止队列并完成对应 future。
Remote Access HAL 的 AP ready 状态与任务回调、VHAL 的 `SHUTDOWN_REQUEST`/`VEHICLE_IN_USE`、silent boot 需要共同集成。
任务结束时车辆可能已有人使用，不能无条件恢复“最初关闭”的状态；silent boot 也应同时约束显示和音频。[远程访问][remote]

factory reset 清除本地 client ID，不会自动删除云端映射。旧映射可能继续唤醒车辆，却无法把任务交给新的 client ID。
所有权转移因此需处理云端 unlink、重新注册与唤醒授权；仅清除 IVI 数据不能证明前车主的全部远程能力已撤销。
网络不一定在 reset 时可用，清理设计不能只依赖当时一次成功 HTTP 请求。

## Automotive 顶层分支的知识归属

以下按官方 Automotive 导航的机制分支归属，入口重定向不另算一种能力；表中“边界”是尚需专题展开的深度，不能当作已穷尽每个子页。

| 官方分支 | 主要承接内容 | 本次后的深度边界 |
|---|---|---|
| Start / releases / IVI | `automotive.md`、`reference-and-evolution.md`、`setup-product-integration.md` | 各季度 release notes 的全部差异未逐条建模 |
| Car framework core / Feature control / VHAL | 本页 | 每个 VehicleProperty、厂商总线协议与全部测试向量仍需按题核对 |
| Watchdog / Flash wear / Performance analysis / System performance tools | 本页及 `memory-resource-management.md`、`performance-optimization.md` | Flash 器件寿命模型、torq 每个参数、硬件基准未穷尽 |
| Power / Remote access / USB reset | 本页 | BSP/TCU/云端实现与 USB 控制器恢复时序依赖产品 |
| Users and accounts / Displays / Custom input / App compatibility | [乘员与 UI](automotive-occupants-ui.md) | 各车型屏幕和外设拓扑需实际映射 |
| Driver distraction / HMI / Scalable UI / Voice | [乘员与 UI](automotive-occupants-ui.md) | Car UI 组件资源、Dialer 每个定制项、各 action/event 属性未逐项列举 |
| Security / Device management | [乘员与 UI](automotive-occupants-ui.md) 及 `enterprise-device-policy.md` | AAOS 管理限制不能从通用手机管理模型直接推断 |
| Audio / Camera / Radio | [媒体与设备集成](automotive-media-integration.md) | SoC 媒体管线、标定、音频矩阵和广播标准认证依赖产品 |
| Connectivity / IVI connectivity / Location bypass | `connectivity-telephony.md`、`network-data-accounting.md`、`permissions-privacy.md`，结合下段 | 车载专属 PANS、Ethernet 管理、蓝牙策略仍需更深专题 |
| Time | `localization-time.md`，结合下段 | 每种车载时间源和休眠漂移的完整产品策略未覆盖 |
| Unbundled apps | [乘员与 UI](automotive-occupants-ui.md) 和 [媒体集成](automotive-media-integration.md) | App Lock、Control Center、Messenger 的全部业务内部结构未穷尽 |
| Virtualization / AVD / Dev tools / Tools | `devices-virtualization.md`、`test-harness-infrastructure.md`、`testing-diagnostics.md`，结合下段 | VirtIO 各后端、Catbox/Spectatio 全 API 与云资源部署未穷尽 |
| Software defined vehicle | `automotive-sdv.md` | 不在本页扩展经典 IVI 契约 |

连接、时间与开发设备的汽车特有边界也需保留。PANS 以包映射 OEM 网络偏好，改变的是应用未显式选择网络时的 default network。
有 fallback、no-fallback、paid-only、private-only 等不同策略，不能把所有 OEM 网络偏好理解为“断网就走用户流量”。
配置跨用户一致但不跨启动持久化，需在开机重新应用；PANS 不会覆写应用通过专用 API 提交的每个 NetworkRequest。
AAOS 13+ EthernetManager 的更新可包含 IP、capabilities 与允许的 UID，异步 completion 与网络真正满足请求要区分，运行时配置同样不跨重启保存。[PANS][pans] [Ethernet][ethernet]

持续热点需产品 capability overlay 和用户 opt-in；启用后若上次关车时热点打开，可在下次开车恢复，并允许无客户端连接时保持。
蓝牙则由 CarBluetoothService 保存当前用户的设备/profile 优先级，默认手机连接策略需避免与汽车策略同时运行。
自定义策略还要分别处理临时为休眠关闭 adapter 与用户持久选择关闭，不能把每次关车都记成用户关闭蓝牙。[热点][hotspot] [汽车蓝牙][bluetooth]

Driver Assistance location bypass 有独立开关、allowlist 与权限：Android 13+ 请求还需相应 LocationRequest bypass 标志和 LOCATION_BYPASS。
GAS allowlist policy 的用途范围另有限定，不能把平台 API 的存在解释为所有汽车应用都可忽略一般定位开关。[定位 API][location-api] [定位边界][location]
时间同步先选择权威方向：ANDROID_EPOCH_TIME 从 Android 向 ECU，EXTERNAL_CAR_TIME 从车辆向 Android 的 TimeDetector 建议。
若同时支持，两者不能形成外部时间依赖 Android 再回灌的反馈环；外部源应在校准/源变化时更新，不能为自然时间流逝持续发更新。
建议源优先级、UTC、时区和单调时间仍需分开；休眠恢复后的新鲜度不能由系统日期看似合理证明。[时间源][time]

Automotive VirtIO guest 的设备后端可能在另一 VM；VHAL、音频、EVS、传感器、GNSS 的 guest 日志不能单独定位后端故障。
AVD/云模拟器能验证 UI、属性和集成路径，不能证明真实总线、ECU 时限或休眠功耗。
USB Port Reset API 从 Android 13+ 提供、要求对应 USB HAL v2.0 与 system-privileged 调用方，重置的是 USB 连接。
它不是总能恢复供电或任意外设的通用电源循环；旧页面同时出现 gadget/HIDL 示例路径，实际接口与 VTS 目标需按分支核对。[虚拟化][virtualization] [USB][usb]

## 有区分力的失效证据

| 现象 | 需关联的证据 | 可以排除的错误推断 |
|---|---|---|
| set 返回后车辆未动作 | request ID、完成回调、area、写入错误、ECU 状态 | Binder 返回就是物理完成 |
| 缓存仍显示可用 | 状态变化事件、单调时间、订阅与重连 | 最后一次 payload 永远有效 |
| manager 为 null | optional feature 默认/禁用/pending、HAL 与服务状态 | 加权限即可解决全部空值 |
| VHAL 被反复重启 | HEARTBEAT、实际工作健康、Watchdog session、ANR | 只延长 timeout 就是修复 |
| 停车后持续耗电 | AP 转换、listener 完成、HAL 资源、内核唤醒源 | 熄屏即 STR |
| reset 后仍能远程唤醒 | 新旧 client ID、server 映射、TCU 授权 | 本地 wipe 会自动撤销云端身份 |

## 官方依据

正文依据为已读取的官方公开内容；旧示例中的 HIDL 路径、枚举及调试命令不固定当前产品接口。

[configuration]: https://source.android.com/docs/automotive/vhal/property-configuration
[interface]: https://source.android.com/docs/automotive/vhal/vhal-interface
[system-properties]: https://source.android.com/docs/automotive/vhal/system-properties
[special]: https://source.android.com/docs/automotive/vhal/special-properties
[seat]: https://source.android.com/docs/automotive/vhal/seat-steering
[adas]: https://source.android.com/docs/automotive/vhal/adas-properties
[features]: https://source.android.com/docs/automotive/feature-control
[watchdog-health]: https://source.android.com/docs/automotive/watchdog/wd_system_health
[watchdog-flash]: https://source.android.com/docs/automotive/watchdog/wd_flash_memory
[watchdog-perf]: https://source.android.com/docs/automotive/watchdog/wd_performance_health
[power]: https://source.android.com/docs/automotive/power/power
[power-policy]: https://source.android.com/docs/automotive/power/power_policy
[garage]: https://source.android.com/docs/automotive/power/garage_mode
[user-system]: https://source.android.com/docs/automotive/users_accounts/user_system
[remote]: https://source.android.com/docs/automotive/remote_access
[pans]: https://source.android.com/docs/automotive/connectivity
[ethernet]: https://source.android.com/docs/automotive/connectivity/ethernet-manage
[hotspot]: https://source.android.com/docs/automotive/connectivity/persist-access-point
[bluetooth]: https://source.android.com/docs/automotive/ivi_connectivity
[location-api]: https://source.android.com/docs/automotive/location_bypass/driver_assistance_location_bypass_api
[location]: https://source.android.com/docs/automotive/location_bypass/location_bypass_policy
[time]: https://source.android.com/docs/automotive/time/extensible_time_management
[virtualization]: https://source.android.com/docs/automotive/virtualization/architecture
[usb]: https://source.android.com/docs/automotive/usb-reset
