# 传感器、输入、触感与外围计算的交付语义

核实日期：2026-10-28。采样、事件到达、输入分发、执行器完成与物理输出是不同事实。
本页细化 Core/Interaction 中 Sensors、Input、Haptics、Accessories、CHRE 与 NNAPI 的接口和生命期；通用算力/USB 概览见 [hardware-compute.md](hardware-compute.md)。
相机/音频另有独立 HAL，不能因为包含传感芯片就套用 Sensors HAL 的报告语义。

## Sensors：先识别报告模式，再解释频率

| 模式 | 事件生成语义 | 错误实现的后果 |
|---|---|---|
| continuous | 按 sampling period 持续产生事件 | 用 callback 间隔误代实际采样时序 |
| on-change | 激活立即报告；之后仅在变化时报告，并受最短事件间隔约束 | 值未变化时仍不断上报，或激活后没有初始状态 |
| one-shot | 检测后先自行 deactivate，再发送一次事件 | 回调中重新激活与旧状态产生竞态 |
| special | 按具体 sensor type 的专门契约 | 把所有 sensor 强行当加速度计 |

one-shot 忽略 batch 的采样周期/最大报告延迟，不能把触发事件攒在 FIFO 等下一批再交付。
sampling period 对 continuous 是生产周期，对 on-change 是最短事件间隔；SDK 客户端又可能因 Framework 复用不同速率请求而得到不同回调节奏。
数据应同时保留 sensor handle/type、事件时间与交付时间，不能把一批 100 个旧样本当成同一时刻的 100 次测量。[报告模式][modes] [batching][batching]

## Batching、wake-up 与 flush

batching 在 hub/硬件 FIFO 暂存事件，`max_report_latency_ns` 给的是事件到 HAL 的最大延迟，不能改变事件自身 timestamp。
`fifoMaxEventCount` 是可用最大容量，`fifoReservedEventCount` 是共享 FIFO 中保证的保留量；所有 sensor 的最大值不能简单相加为硬件容量。
AP 休眠时 non-wake-up sensor 不应为交付数据自行唤醒 AP；wake-up sensor 则需按时唤醒，并为实际唤醒/排空的耗时留 FIFO 余量。
共享 FIFO 的 non-wake-up on-change sensor 还需保留最后状态，防止被连续采样数据覆盖后，恢复时应用永远看不到新的状态。[batching][batching]

flush 是异步排空屏障，不是“重新开始采样”。返回后仍要按序发送指定 sensor 的既有事件，最后给 flush-complete。
空 FIFO 或不支持缓存的非 one-shot sensor 也要成功并报告 complete；one-shot flush 返回 BAD_VALUE 且不发 complete。
共享 FIFO 被一起排空时，也只对本次请求的 sensor 生成相应 complete，不能把所有 sensor 都当收到过 flush 请求。
客户端在 complete 前不能宣称“此前样本全已处理”，HAL 则不能用方法成功返回代替 complete 事件。[AIDL HAL][aidl]

## FMQ、handle 稳定性与动态设备

Sensors HAL 2.0 从 Android 10、2.1 从 Android 11 提供；AIDL HAL 从 Android 13 提供并基于 2.1 演进。
这些接口不是与旧 HAL 1.0 任意互换；实际声明、head-tracker/limited-axis 等类型和 Multi-HAL 组合需按版本核对。[HAL 2][hal2] [AIDL][aidl]

初始化时 Framework 提供 Event FMQ、Wake Lock FMQ 与 callback。
Event FMQ 写成功后还要用 EventFlag 通知读者；同步队列空间不足时写会失败，不能丢弃返回值再当成事件已送达。
wake-up 事件写队列前要持有 wake lock；Framework 接管并在 Wake Lock FMQ 确认处理数量，HAL 才按未确认计数归零释放。
过早释放会在消费前睡下，漏读确认则会一直耗电；一个“FMQ 有数据”的 dump 不能区分这两种故障。[AIDL 队列][aidl]

静态 sensor 的 handle 必须跨 HAL 进程重启稳定；启动枚举顺序抖动不该使同一个 handle 指向另一颗芯片。
列表显著改变会破坏应用生命期内静态 sensor 不变的契约，Framework 可能触发 runtime 重启。
动态外设则走 connected/disconnected callback，断开后不应继续沿旧 handle 注入事件。
direct channel 将事件写入注册的共享内存，客户端自己读取；它不同时保证通过普通 Framework callback 再收到一份。
direct channel 的注册、配置与撤销、HAL 重启后的重新建立均有单独资源生命期。[AIDL][aidl]

Android 10 引入的 Sensors off 控制经过 SensorService/CameraService/AudioPolicyService 的应用访问，不能从其名称推出所有硬件电路均断电。
电话通话等不经对应 AudioPolicyService 路径的麦克风访问有专门例外；suspend 则涉及 AP 与 wake-up 交付，二者不能以“都不回调”混为一类。[Sensors off][off]
功耗应计入 sensor/hub 与 AP 唤醒成本；把每个样本从 hub 立即转交 AP，可能抵消低功耗处理器的收益。
传感器融合与复合类型仍需满足声明的 sensor type、坐标系、精度和报告模式，不能只测试某个静态值合理。

## Input：驱动事实、映射、校准与窗口目标

Linux evdev → EventHub/InputReader → InputDispatcher → 目标窗口，是不同处理层。
`.kl` 把 Linux key/axis 或 HID usage 映射为 Android key/axis 与策略标志；`.kcm` 再把 Android keycode+modifier 映射到 Unicode/键盘行为。
改 `.kcm` 不能修驱动没有产生的按键，改 `.kl` 也不能单独改变大小写、死键或字符组合。[key layout][kl] [key character map][kcm]

设备专用文件按 vendor/product/version 或设备名匹配，再使用 Generic 回退；设备名规范化、文件所在分区和匹配顺序都会影响最终选中项。
系统 Generic/Virtual 映射用于广泛外设与合成输入，不应为修单个硬件而修改全局默认。
SPECIAL_FUNCTION 键盘与 FULL 文本键盘不同；错误分类可能造成输入法或硬键盘配置异常。
应以实际设备身份和 InputReader 选中的配置判断，不能从文件存在推断已加载。[布局][kl] [字符][kcm]

多触点由 ABS_MT_POSITION_X/Y 等能力分类，并通过 tracking ID 区分持续接触的工具；Protocol B 的 slot 是报告存储槽，不等于应用的 pointer index。
tracking ID 在接触期间需稳定，离开后可再使用；重复 ID、缺少离开或错误 slot 状态会表现为跳点/幽灵触摸。
同时声明单触点与多触点轴时采用多触点路径，不能指望改 ABS_X/Y 一定影响多点位置。[触摸][touch]

INPUT_PROP_DIRECT、INPUT_PROP_POINTER 与 `.idc` 的 `touch.deviceType` 帮助区分 touchscreen、touchpad、pointer。
设备原始轴范围通过校准映射到显示像素；pressure、touch size、orientation、distance 与 stylus tool type 有独立语义。
仅调应用坐标偏移会隐藏驱动范围或显示绑定错误，并让旋转、外屏或其它应用继续出错。
InputDispatcher 的焦点、窗口可触区域和安全权限仍在后续层；getevent 能看到正确 raw event 只证明驱动侧，不能证明已分发给预期窗口。[触摸分类与校准][touch] [IDC][idc]

getevent 用于 raw 能力/事件时间线，validatekeymaps 用于映射文件语法，dumpsys input 连接设备分类、映射、校准与目标分发。[事件工具][getevent] [映射校验][validate]
“按下有 DOWN 没 UP”“字符错误”“方向反了”“触点进入别的显示”分别优先检查事件配对、KCM、axis mapping、显示/窗口目标，不应统一改 UI 手势代码。

## Haptics：语义映射、primitive 与物理校准

HapticFeedbackConstants 表达输入/UI 语义，VibrationEffect 的预定义效果表达能量/形状，Composition primitive 是可组合的基础效果。
Framework 映射到 Vibrator HAL；未原生支持的预定义效果可能走 fallback，因此“有振动”不能证明指定 primitive 已实现。
能力位、支持列表、幅度控制、composition size/delay/duration 与 completion callback 必须被真实 HAL 兑现。[常量和 primitive][primitives]

校准既看单次 click/tick，也看连续 composition：许多弱 tick 累积后可能比单个 tick 的主观强度大。
执行器共振频率、机身耦合、测量加速度计位置与设备放置会影响波形，跨设备比较必须保持测量条件一致。
主脉冲与尾振的 PRR、峰值幅度和持续时间分别描述清脆度、强度与拖尾；提高最大幅度不能自动修复刹车或尾振问题。[primitive 校准][primitives] [评估][assessment] [波形][analyze]

Android 16 的 basic/advanced PWLE API 以 envelope 描述变化，要求相应共振频率、FOAM 与 compose PWLE HAL 能力。
感知 intensity/sharpness 与物理 amplitude/frequency 不线性等同，不能直接把 0.5 intensity 当成一半电压。
envelope 需平滑起止，点数、最短/最长 segment 等限制应来自能力查询；FOAM 报告的是各频率可达最大加速度，失真表会使 Framework 请求硬件无法兑现的轨迹。[PWLE][pwle]

取消、覆盖与完成回调是接口生命周期；真实执行器可能还有尾振，需用波形判断。
若 callback 到了而感觉很弱，先区分 fallback、硬件能力/校准与执行器输出；若效果完成后服务仍忙，则检查回调和状态回收。

## Accessories、CHRE、NNAPI 的专门边界

AOA accessory 由外部配件做 USB host，Android 切入 accessory 模式；版本协商与重枚举会改变设备会话。
AOAv2 可在 endpoint 0 注册 HID，ID 仅在本次连接/注销前有效，报告描述符与发送的 report 必须匹配。
AOAv2 audio 在 Android 8 已废弃，不能以旧协议音频示例设计新的通用 USB 音频能力；USB Audio Class、headset 按键与 Type-C adapter 另有规范。[AOAv2][aoa]
Android 12 的 USB data signaling 管理可保留充电而禁用数据，需 DPM 调用资格、设备 capability 与 USB HAL 支持；充电正常不能排除策略阻止数据。[USB data policy][usb-policy]

CHRE API 版本不必与 Android 版本一致，nanoapp 需查询实际版本/可选能力；同 ISA/ABI 条件下的兼容不能推成任意处理器二进制通用。
nanoapp 事件处理不并行调用同一 nanoapp，但阻塞 handler 仍会拖住后续事件。hub 的 RESTARTED 通知必须在恢复到可接新请求之后发送。
收到 restart 后应重查已加载 nanoapp、事务和订阅，不能把 Android 进程未重启当成 hub 会话仍存活。[CHRE][chre]

NNAPI NDK 在 Android 15 弃用不代表 NN HAL 被移除。模型支持需按 operand/type/shape、控制流、memory pool 与 QoS 能力判断。
Android 10/NN HAL 1.2 的可选 compilation cache 包含 token 和文件句柄；token 冲突可能产生错误结果，compiled model cache 还需完整性校验，不能盲信可写缓存。
burst FMQ 减少 IPC，但 FMQ 本身不保证对端进程存活；死亡、结束 burst 与 memory mapping 回收需绑定上层对象。
准备/缓存命中、请求提交、异步 callback/fence 和输出可读分别有不同完成点。[驱动][nn] [编译缓存][nn-cache] [burst][burst]

## 主要分支归属与深度边界

| 官方 Interaction 分支 | 承接内容 | 未逐项展开 |
|---|---|---|
| Sensors：types/stack/HAL/Multi-HAL/reporting/batching/suspend/off/head tracker | 本页；通用测量见 `devices-virtualization.md` | 全 sensor type 数值规范、HID head-tracker 字段、全部 Sub-HAL 调度细节 |
| Input：keyboard/keylayout/keychar/touch/config/tools | 本页；窗口分发见 `graphics-input.md` | 全 KCM 语法、每种触控校准公式与旧版迁移差异 |
| Haptics：UX/实现/constants/PWLE/assessment | 本页与 `hardware-compute.md` | 每效果目标波形、全部设备性能图及测量工具操作 |
| Accessories：AOA/audio/headset/stylus/custom/data policy | 本页与 `hardware-compute.md`、`media-camera-audio.md` | USB/3.5mm 电气表、所有 headset/stylus report 位与认证 |
| CHRE | 本页与 `hardware-compute.md` | 每版 API 和芯片 firmware 实现 |
| NNAPI drivers：discovery/cache/burst/memory/control flow/QoS/extensions | 本页与 `hardware-compute.md` | 各 operation 支持矩阵、vendor extension schema、所有 deadline 规则 |

## 官方依据

[modes]: https://source.android.com/docs/core/interaction/sensors/report-modes
[batching]: https://source.android.com/docs/core/interaction/sensors/batching
[aidl]: https://source.android.com/docs/core/interaction/sensors/sensors-aidl-hal
[hal2]: https://source.android.com/docs/core/interaction/sensors/sensors-hal2
[off]: https://source.android.com/docs/core/interaction/sensors/sensors-off
[kl]: https://source.android.com/docs/core/interaction/input/key-layout-files
[kcm]: https://source.android.com/docs/core/interaction/input/key-character-map-files
[touch]: https://source.android.com/docs/core/interaction/input/touch-devices
[idc]: https://source.android.com/docs/core/interaction/input/input-device-configuration-files
[getevent]: https://source.android.com/docs/core/interaction/input/getevent
[validate]: https://source.android.com/docs/core/interaction/input/validate-keymaps
[primitives]: https://source.android.com/docs/core/interaction/haptics/haptics-constants-primitives
[assessment]: https://source.android.com/docs/core/interaction/haptics/haptics-assess-hardware
[analyze]: https://source.android.com/docs/core/interaction/haptics/analyze
[pwle]: https://source.android.com/docs/core/interaction/haptics/haptics-pwle
[aoa]: https://source.android.com/docs/core/interaction/accessories/aoa2
[usb-policy]: https://source.android.com/docs/core/interaction/accessories/disable-signaling
[chre]: https://source.android.com/docs/core/interaction/contexthub
[nn]: https://source.android.com/docs/core/interaction/neural-networks
[nn-cache]: https://source.android.com/docs/core/interaction/neural-networks/compilation-caching
[burst]: https://source.android.com/docs/core/interaction/neural-networks/burst-executions
