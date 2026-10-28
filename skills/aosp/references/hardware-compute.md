# 设备算力、低功耗计算、触感与 USB 外设

事件/FMQ/flush、输入映射、触觉校准和外设生命周期见[传感器、输入与触觉](sensors-input-haptics.md)。

本页用于算力驱动、CHRE、振动器和 USB 外设变更。核实日期：2026-10-28。
先确认目标 Android 分支、设备声明的接口版本与实际硬件能力；硬件存在、接口可发现、请求受理和任务完成是四种状态。
NNAPI NDK API 从 Android 15 起弃用，但 Neural Networks HAL 继续受支持；不能据此删除既有驱动。[1][]
当前官方 NPU Manager 文档限定 Android 17 及以上；旧分支不能直接套用其服务、权限或调度契约。[3][]

## 不同计算域承担不同工作

NN HAL 抽象模型计算设备，框架根据模型支持度、性能及功耗信息选择执行路径。[1][]
NPU Manager 的版本限定职责是协调 NPU 资源与优先级；它不是模型算子实现，也不能代替底层驱动。[3][]
CHRE 让可信 nanoapp 在低功耗处理器上响应环境事件，减少 AP 参与；它不是任意 Android 应用的后台容器。[4][]
触感和 USB 同样跨越 framework、HAL、驱动与物理设备；软件成功返回不足以证明物理动作达到预期。

| 对象 | 需要区分的状态 | 不能直接推导的结论 |
| --- | --- | --- |
| 计算设备 | 枚举、支持模型、准备、执行完成 | 有 NPU 就加速整个模型 |
| nanoapp | 已加载、已启用、事件送达、回复到达 | 卸载或重启后原会话仍有效 |
| 振动效果 | 能力声明、触发、完成、实际波形 | HAL 返回成功就有同等手感 |
| USB 设备 | 连接、枚举、授权、打开、传输 | 充电成功就能通信 |

## NNAPI 与驱动能力：模型支持是具体契约

官方驱动概览主要以 NN HAL 1.3 描述能力查询、模型准备和执行；方法名不能直接照搬到其他 HAL 版本。[1][]
能力性能信息用于设备选择，应反映标准参考负载；不能靠夸大能力数字强制框架挑选自己的硬件。
算子支持还受类型、形状、参数和内存条件约束；支持卷积不等于支持任意尺寸、量化方式或动态图。
模型切分与跨设备中间结果会产生调度和搬运成本；判断收益要看实际模型端到端时间。
准备模型得到可执行句柄，并不意味着每次执行的输入已经提交或输出已经写完。
异步执行的回调或 fence 才承载相应完成条件；同步与异步 HAL 方法按目标接口处理。
输出尺寸不确定时必须遵守该版本对输出形状及不足 buffer 的报告规则，不能静默截断结果。

Android 10 引入设备发现及指定设备功能，NN HAL 1.2 对应实现包含设备类型和驱动版本查询。[2][]
CPU、GPU、ACCELERATOR 和 OTHER 是执行设备分类；ACCELERATOR 不保证任意模型都优于 CPU。
驱动版本用于区分实现变化；不应只改二进制而保持无法区分的版本信息。
性能定位要保留模型/输入、精度、驱动版本、设备选择、准备耗时、执行耗时和传输耗时。
缓存、burst、QoS 等能力有各自版本条件；确认目标接口与调用路径后再采用，不能把它们当通用默认。

## NPU Manager：只在具备对应版本和实现的设备上讨论

Android 17+ 的官方方案通过 framework 服务和 NPU Scheduling AIDL HAL 协调模型加载及工作优先级。[3][]
客户端先异步请求加载许可，再调用底层库加载；许可是资源协调决定，不是计算完成通知。
模型真正加载后报告已加载；收到卸载请求后释放资源并报告已卸载，才能闭合资源占用生命周期。
排队、开始、暂停、恢复和终止是不同工作状态；暂停不能直接算失败或完成。
客户端声明的优先级需要结合 UID、前后台与设备状态协调，不能由应用字符串自行越权提升。
评估旧设备时先查是否有该服务和 HAL；厂商已有 NPU 路径不能仅因名称相近就视作这一契约的实现。

## CHRE 与 Context Hub：低功耗来自少唤醒和有界工作

Context Hub HAL 连接 Android 服务与 CHRE，负责 hub/nanoapp 发现、加载卸载、消息等操作。[4][]
CHRE 的事件驱动 nanoapp 使用 C/C++；单个 nanoapp 不会由多个线程同时执行，但事件处理仍不能长期阻塞。
源代码可移植不等于二进制通用；处理器 ISA、ABI、API 版本、可选能力与工具链需要匹配。
传感器、GNSS、Wi-Fi 等信号能力存在版本和可选功能边界，必须查询目标实现而非假设全部提供。
CHRE 可以使用传感器框架，但不替代 Android Sensors HAL 的完整职责。

- 只让系统可信客户端经受限接口访问；nanoapp 不是第三方应用绕过后台或权限约束的入口。
- 低功耗方案应把筛选留在 hub、减少 AP 往返；逐样本上传仍可能抵消卸载收益。
- 对消息保存 hub、nanoapp、客户端及事务标识；区分加载应答、事件处理和应用层结果。
- hub 可以独立于 Android 重启；收到重启事件后重新核对 nanoapp 和会话状态。
- 启动时 hub 枚举属于启动路径；慢调用、错误能力声明会影响启动或导致后续请求无法成立。

## 触感：能力、效果语义与完成通知必须一致

`HapticFeedbackConstants` 关联输入/UI 语义，`VibrationEffect` 预定义效果表达振动效果；二者不是同一组标识。[5][]
框架把公共常量、预定义效果与 primitive 映射到 HAL；未原生实现的效果可能走 fallback。
因此“能感觉到震动”不能证明预定义效果、组合 primitive 和幅度控制都已正确实现。
primitive 的强度、持续时间、频率响应和刹车受执行器影响；跨设备一致性需验证物理输出，而非只比较数组。

Android 16 分支的 `IVibrator` 明确用能力位和支持列表描述可调用的接口。[6][]
`on`/`perform` 完成回调分别取决于相应能力；`compose` 有自己的能力及完成回调要求。
该接口中的 `perform` 返回预计时长，不表示效果已经播放完；取消已有振动时也需按契约收敛关联回调。
已有效果运行时直接再次触发可能落入接口未定义行为；框架/HAL 的取消和串行化关系应明确。

- 不宣称硬件无法兑现的幅度、频率、组合或外部控制能力。
- fallback 可以保证有反馈，但不能拿 fallback 成功证明硬件 primitive 合规。
- 对比触感时固定机身放置、测量位置和激励序列；重复短效果可能累积为不同强度。
- 完成回调证明的是接口状态推进；手感和尾振问题仍需波形、持续时间与硬件测量证据。

## USB 与外围设备：连接、角色和授权各有边界

USB host 模式下 Android 枚举设备并作为总线主机；accessory 模式下外部配件充当 host。[8][][9][]
Type-C 的数据角色与电源角色是独立维度；角色交换能力不能由插头外形或充电状态推断。
Android 8.0 的 USB HAL 将端口状态查询及角色交换纳入 HAL；gadget 功能配置还涉及设备实现路径。[7][]
Android 12 增加的 Gadget HAL 功能、速度与版本查询有版本条件，旧设备不能假定拥有同等接口。
端口角色、gadget 功能、内核设备枚举和应用传输接口属于不同层次，失败时不要只改一个属性掩盖问题。

host 应用可通过连接事件或已有设备列表发现设备，再选择 interface/endpoint。[8][]
发现设备不授予无条件访问权：检查用户授权，异步授权返回后重新核对设备仍存在且身份匹配。
VID/PID 或类信息用于匹配用途，并不能证明协议兼容、端点配置正确或数据可信。
打开连接、声明接口与实际传输分别可能失败；长传输不能阻塞 UI 线程。
拔出时停止提交新请求，按接口规则取消/收敛在途请求，释放 interface 并关闭 connection。
重插后重新发现、授权检查和打开；不要让旧句柄或延迟回调写入新的设备会话。
普通 Android API 的 host/accessory 供电描述不能替代具体 Type-C/PD 拓扑、电源预算和硬件验证。

## 诊断证据与实现判断

| 现象 | 优先建立的证据 | 需要排除的误推 |
| --- | --- | --- |
| 模型变慢 | 设备选择、支持报告、准备/执行/传输分段时延、驱动版本 | 总耗时都算在 NPU 内核上 |
| 计算卡住 | 请求标识、回调/fence、资源占用、取消与驱动存活状态 | 受理日志等于完成 |
| CHRE 耗电或丢事件 | AP 唤醒、消息频率、nanoapp 状态、hub 重启时间线 | 在小核执行就必定省电 |
| 触感缺失或尾振 | 能力/支持列表、fallback 路径、回调、实测波形 | API 调用无异常就合格 |
| USB 仅充电或中断 | 端口角色、枚举、授权、端点、HAL 结果、移除事件 | 线缆供电证明数据通路正常 |

修改能力声明时，应能指出由哪个真实实现兑现，以及失效、取消、重启或拔出时谁释放资源。
修改异步路径时，应能按同一请求/会话标识把“受理—开始—完成/取消—回收”连起来。
性能改进需在相同模型/效果/外设条件下解释延迟、能耗和资源变化，避免用单个接口耗时代表用户结果。
厂商固件、执行器校准和 USB-PD 电气细节超出通用文档保证；结论落到目标硬件与对应接口规范。

## 已核实的官方来源

1. [NNAPI drivers：弃用边界、能力、准备与执行](https://source.android.com/docs/core/interaction/neural-networks)
2. [Device discovery and assignment：Android 10 / NN HAL 1.2 条件](https://source.android.com/docs/core/interaction/neural-networks/device-discovery)
3. [NPU Manager：Android 17+ 的加载与调度生命周期](https://source.android.com/docs/core/perf/npu-manager)
4. [CHRE：可信 nanoapp、事件与 hub 重启](https://source.android.com/docs/core/interaction/contexthub)
5. [Haptic constants and primitives：公共语义、fallback 与物理输出](https://source.android.com/docs/core/interaction/haptics/haptics-constants-primitives)
6. [Android 16 IVibrator AIDL：能力位、取消与完成契约](https://android.googlesource.com/platform/hardware/interfaces/+/refs/heads/android16-release/vibrator/aidl/android/hardware/vibrator/IVibrator.aidl)
7. [USB HAL：端口状态、数据/电源角色与版本条件](https://source.android.com/docs/core/permissions/usb-hal)
8. [USB host：发现、授权、端点及断开](https://developer.android.com/develop/connectivity/usb/host)
9. [USB accessory：配件作为 host 的边界](https://developer.android.com/develop/connectivity/usb/accessory)

[1]: https://source.android.com/docs/core/interaction/neural-networks
[2]: https://source.android.com/docs/core/interaction/neural-networks/device-discovery
[3]: https://source.android.com/docs/core/perf/npu-manager
[4]: https://source.android.com/docs/core/interaction/contexthub
[5]: https://source.android.com/docs/core/interaction/haptics/haptics-constants-primitives
[6]: https://android.googlesource.com/platform/hardware/interfaces/+/refs/heads/android16-release/vibrator/aidl/android/hardware/vibrator/IVibrator.aidl
[7]: https://source.android.com/docs/core/permissions/usb-hal
[8]: https://developer.android.com/develop/connectivity/usb/host
[9]: https://developer.android.com/develop/connectivity/usb/accessory
