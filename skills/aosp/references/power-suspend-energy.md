# Suspend、能量观测与设备电源状态

用于待机不休眠、异常唤醒、功耗归属、无电池/TV 设备和能量 trace。核实日期：2026-10-28。
Doze、thermal、Power HAL/ADPF 和 BatteryStats 基础见[电源与性能](power-performance.md)；本页补充控制与观测边界。

## SystemSuspend 的计数与 wakeup 握手

Android 10 的 SystemSuspend 取代旧 libsuspend 的发起 suspend 职责。文档中的 main/Binder 线程管理客户端 wakelock，suspend 线程在受保护计数归零后，通过 kernel wakeup_count 握手再进入 suspend；出现新的 wakeup 事件时握手失败并重新检查。

“所有应用 wakelock 都释放”不是立刻休眠的充分条件：kernel wakeup source、正在到达的事件和底层 suspend 失败仍可能阻止进入。不能通过跳过 wakeup_count 或绕开计数强制休眠来证明无竞态。

每次 acquire 返回独立的 wakelock 对象；debug name 相同不代表它们是同一个引用。显式 release、对象/客户端死亡与 service 重启后的状态应保持一致。旧 sysfs 同名锁行为与 Binder 对象模型不能混用。文档的 HIDL/native 与 SystemServer AIDL 控制接口具有该版本的分工，现代分支核对实际接口定义。[SystemSuspend](https://source.android.com/docs/core/power/systemsuspend)

证据需对齐 Framework wakelock、SystemSuspend 活跃对象/计数、kernel wakeup sources、wakeup_count 失败和 suspend/resume trace。屏幕关掉、CPU idle、SoC suspend 和 app Doze 是不同状态。

## PowerStats 测量、residency 与 hint 不能互换

Power HAL/hints 请求资源策略，PowerStats 提供能量/状态驻留等观测。没有某条 power rail 的物理量测能力，可以与拥有 sleep-state residency 能力并存；不支持字段应按契约报告，不能伪造零值。

累计能量、瞬时/平均功率、驻留时间、唤醒次数和基于 profile 的 UID 归属分别具有单位和时间窗口。做差前验证同一 rail/entity、计数基线、重启/溢出与采样时刻；读取不能破坏累计数据。PowerStats 的定期/事件采样也不保证覆盖每次短负载。

官方页面保留 Android 10 HIDL 的接口与历史 fallback 说明，不能把方法名和 fallback 推广为所有 AIDL 分支。以目标冻结接口的量纲为准；示例文案里的“功率”不能直接当成 energy 字段的单位。[PowerStats](https://source.android.com/docs/core/power/power-stats-hal)

实验室 component/device 测量用于建立模型和校准。屏幕内容、radio 状态、后台负载、温度与电源供给都可能改变结果；模型估算不是对每个 UID 的直接硬件电表读数。[Component measurement](https://source.android.com/docs/core/power/component)、[Device measurement](https://source.android.com/docs/core/power/device)、[Power values](https://source.android.com/docs/core/power/values)

## Wattson：受支持模型上的 trace 估计

Wattson 基于 Perfetto 的 CPU frequency/idle/scheduling 等事件估计硬件块及线程能量。它需要受支持 SoC 的模型，工具通过相应 SoC 标识选择支持；改属性不会给不支持的硬件生成可信模型。

先核对数据源完整性、丢事件、trace 时段、模型/设备及线程归属，再比较同条件负载。CPU/GPU 模型结果不等于整机电池总能量，缺少 modem/display 等观测时应保留范围；软件估计也不能代替产品校准或硬件安全限值。[Wattson](https://source.android.com/docs/core/power/wattson/wattson)、[采集与分析](https://source.android.com/docs/core/power/wattson/how-to-wattson)

## 电池不存在与电池电量为零不同

无电池设备的 present/status/capacity、充电器 online 和 Framework 的“是否视作外接供电”是不同字段。Android 9 的默认值调整不等于无电池设备必须因电量零关机；反过来，也不应为了隐藏 UI 把不存在的电池伪报成健康满电。

产品应由 power_supply/Health HAL 准确表达外部电源，分别验证 BatteryService、充电相关 job 和 UI。HAL、kernel 和产品 policy 各自改变的字段须可追溯。[Batteryless devices](https://source.android.com/docs/core/power/batteryless)

## 用户行为政策不由 wakelock 单独决定

Android 11 的 TV inattentive sleep 可以在没有用户交互一段时间后关闭屏幕，即使存在某些 screen wakelock/keep-screen-on；PARTIAL wakelock 又有不同范围。警告时点、用户活动、HDMI-CEC/cast/语音与实际关屏要分开验证，避免叠加两套政策形成重复警告。[TV standby](https://source.android.com/docs/core/power/tv-standby)

Android 13 的长时间不可见前台服务提醒与 background battery usage tracker 是不同机制，默认启用状态也不同。文档中的阈值/限制和 DeviceConfig 属于相应版本，不能由“有 tracker 类”推定本产品已启用，更不能用自定义全局杀进程替代原有用户控制。[Background trackers](https://source.android.com/docs/core/power/trackers)

Routine Battery Saver 等策略也需区分系统默认、配置覆盖、用户选择与本次实际生效值。诊断时保存状态转移及触发信号，不能只看某次 UI 显示。[Routine Battery Saver](https://source.android.com/docs/core/power/routine-battery-saver)

本页不提供各 SoC rail/PMIC 的完整模型、Wattson 所有 SQL、产品唤醒源配置和历代省电阈值；这些必须按硬件与目标分支读取。
