# 功耗与性能：约束、归因和稳定工作点

编译优化、ART class-loader context 与启动归因见[性能优化](performance-optimization.md)；freezer、hibernation、内存压力和新内存服务见[内存与资源管理](memory-resource-management.md)。两者都需要按目标版本确认启用路径。

SystemSuspend、能量/驻留计数、Wattson 和无电池/TV 状态见[Suspend 与能量观测](power-suspend-energy.md)。

本页用于待机耗电、卡顿、发热、调度、低内存和 ART 相关变更。核实日期：2026-10-28。
先确认目标 release、首发条件、内核、SoC、Power/Thermal HAL 和产品策略；旧文档默认值不能直接成为新设备配置。
所有优化都需要负载、时长、温度、供电、网络和编译状态可比较，单次峰值不足以证明产品改善。

## 几类状态不能混成“省电模式”

- 屏幕关闭、设备 Doze、应用 App Standby、电量节省、CPU idle 和系统 suspend 是不同机制。
- CPU 空闲不保证 SoC/外设进入低功耗；屏幕关闭也不证明系统真正睡眠。
- 设备变慢可能来自 CPU/GPU 资源不足、等待锁/IPC/I/O、内存回收或温度限制，不先归因“频率不够”。
- 优化目标应同时说明用户可见时延/吞吐、能量、内存、温度和后台功能的允许变化。
- 资源暂时提升要有退出和恢复条件；取消、服务死亡及 session 结束不能留下永久 boost 或 wakelock。

## Doze 与 App Standby：推迟工作，不是随意杀进程

Doze 根据设备空闲条件限制部分后台 CPU/网络活动，并通过维护窗口让延迟工作推进。[1][]
Android 7 起增加屏幕关闭时的轻量模式；完整/轻量模式的进入条件和可用传感器有区别。
现代版本的具体时间、配额和例外以目标源码为准，不把旧文档的分钟数或开关默认值当跨版本契约。
App Standby 根据单个应用的使用情况限制后台活动，与整个设备是否 idle 独立。[2][]
较新版本的 bucket、restricted 状态和用户限制应查对应版本；不能把早期“每天一次”概括套到所有应用。

- 定位延迟任务时记录设备 idle 状态、应用 standby 状态、充电、网络、job/alarm 约束及临时豁免。
- 有通知、运行进程或持有 wakelock，不自动意味着获得所有后台网络与调度权限。
- 白名单/豁免不是通用修复；先证明必要性及作用范围，避免绕过平台限制掩盖错误的任务设计。
- 延迟执行需保持业务的超时、去重及取消语义；维护窗口关闭不应丢失应持久化的工作。
- 测试进入、维护、退出、充电切换和用户活跃恢复，而不只用一次强制 idle 成功判断真实待机行为。

## Power HAL、hint 与调度反馈

框架/应用表达工作需求，Power HAL 和 vendor 策略结合芯片、功耗及温度约束执行；hint 不是硬件频率的无条件命令。
Power 与 PowerStats 的职责不同：前者参与提示/模式控制，后者报告能量或驻留信息；历史上部分统计接口由前者拆到后者。[5][]
HAL 的具体 AIDL/HIDL 版本、mode/boost/session 及支持查询需查目标 `hardware/interfaces/power` 和实际服务，不能复制旧 IPower 1.0 例子。

PerformanceHintManager 自 Android 12 提供，NDK API 自 Android 13 提供；应用向同一负载的线程组报告目标和实际工作信息。[3][]
系统据此选择适合该 SoC 的资源分配；API 存在不等于当前设备提供相同的 vendor 行为或固定频率。

- session 绑定正确线程与生命周期，报告真实工作时长；不要把睡眠/等待任意包装成 CPU 工作来持续索要资源。
- 帧 deadline 不是“永远跑满”的理由；测量完成工作所需能量和持续性能，而不是仅比较首秒 FPS。
- 重复 boost、并发请求及 mode 退出要有定义；异步旧请求不能在新场景结束后重新拉高资源。
- Busy loop、固定绑大核和长期性能模式可能改变热稳态；不能把短时提速直接当净收益。

## Thermal：功率与温度是性能的真实约束

Thermal HAL/服务把硬件信号转成 severity，并向框架和应用提供相应反馈；severity 比“某个温度数字”更接近动作语义。[4][]
Android 10～13 文档采用 Thermal HAL 2.0 HIDL，Android 14 起对应 AIDL；实施仍核对首发/升级与产品契约。
皮肤温度、电池、USB、SoC 等限制来源不同；一个传感器不高不能证明没有 throttling。

- severity 应准确反映已实施的限制，状态变化应通知，不能为了 benchmark 隐藏限频或伪报正常。
- 设计阈值、滞回及恢复行为时避免抖动；不能移除 thermal mitigation 作为卡顿修复。
- 记录温度/状态、频率、工作负载、冷却动作及时间，区分热限制和其他调度原因。
- 验证冷机、预热、持续负载、恢复与充电状态；不同环境温度的数据不能直接作回归对比。
- 应用可根据 thermal 反馈降低需求，框架/vendor 限制负责保底；两个层面不能相互替代。

## 电池统计：模型、硬件读数与单位

BatteryStats 记录组件状态持续时间与归属，结合 power profile 估算消耗；并非直接给每个 app 接一个电流表。[6][]
并发使用共享资源时，归因有分摊规则；各应用显示比例不是硬件瞬时功率的逐项测量。
PowerStats 可提供 rail 能量、power entity 驻留等读数，实际支持由硬件和实现决定；不能从 HAL 存在推出所有 rail 都可测。[5][]

- 分清电流 mA、功率 mW、累计能量、容量 mAh 和驻留时间；转换需要电压与时间口径。
- 累计计数器要处理启动/重置、采样间隔和单位，差分不能因重启变成负消耗。
- 统计采集本身不能频繁唤醒 AP/子系统破坏被测待机；优先利用现有缓存和机会性读取。
- 电量百分比下降有分辨率与电池状态影响，不能用几分钟不掉电证明零功耗。
- 先关联 wakelock、唤醒源、CPU/外设驻留、无线活动和耗能，再决定修复持锁者、触发源还是模型。

## CPU 调度与 cgroups：控制可获得的资源

Android 10 起以 cgroups/task profiles 抽象资源约束；新版本上层应使用对应抽象，避免硬编码某个 cgroup 文件路径。[7][]
Android 12 起 init 的 `task_profiles` 命令取代对应的旧 `writepid` 迁移模式；vendor/API 级覆盖可能改变 profile 实际动作。
CPU affinity/cpuset 决定可运行位置，优先级/权重影响竞争，uclamp 等机制影响容量请求；这些不是同一个旋钮。

- 先区分 runnable 但未运行、实际 CPU 执行、锁/IPC 等待和 I/O 等待，调度提高优先级不能消除所有等待。
- 优先级继承、关键线程依赖与后台线程被限制需一起分析；只提升 UI 可能把瓶颈转移到被依赖服务。
- 资源策略必须针对正确 process/thread 及其生命周期；新线程或重启后策略是否延续需验证。
- 不把所有线程移到 top-app，不靠永久实时优先级解决普通工作负载，避免饥饿与系统功能回归。

## 内存、LMKD 与 ART

LMKD 监控内存压力并回收/终止相对不重要的进程，目标是维持系统响应，而不是让“空闲内存”始终最大。[8][]
Android 10 引入 PSI 压力监控支持，Android 11 的策略进一步考虑 thrashing 等信号；具体算法/属性仍随分支演进。
PSI 反映资源短缺造成的停顿；free、cache、swap、匿名页和 GPU/共享 buffer 必须结合看，单个 RSS 不能解释系统压力。

- 进程消失应区分 LMKD、内核 OOM、crash、ANR 处理及其他平台机制，先查真正退出原因。
- 调高 kill 阈值或把进程设为不可杀不能修复内存泄漏；可能把可恢复的后台重启变成前台卡顿或系统失效。
- 验证 foreground/background 切换、重载、回收停顿、swap 和多任务体验，不仅统计被杀次数。
- Java heap、native heap、图形 buffer、共享页与内核内存分开归因，避免重复计量共享分配。

ART 使用解释/JIT/AOT 与 profile 等机制，编译策略会改变启动、存储、CPU 和内存成本。[9][]
Android 14 起应用 dexopt 由 ART Service 管理，Android 13 及以前由 Package Manager 管理；不要盲改旧属性推断新行为。
`speed-profile` 依赖可用 profile 与具体编译原因；`quicken` 等旧 filter 有版本范围，不能当永久有效配置。

- 比较冷启动、热启动与已编译/未编译条件，先固定 app 数据、profile、代码版本和系统后台编译状态。
- 区分 GC 停顿、分配速率、JIT/编译、缺页、锁和 I/O；“Java慢”不是可实施的根因。
- 增大 heap 可能延缓 GC 却加重系统压力；扩大 dex2oat 并发可能争抢 CPU/内存/I/O，均需全机证据。
- 性能试验不能破坏 runtime 正确性、JNI 约束和应用兼容，不用去掉校验或任意 GC 开关完成指标。

## Trace 与实验：让时间线能解释结果

Perfetto 通过配置的数据源记录系统事件、调度与计数器；未启用的数据不会因打开 trace 而自动出现。[10][]
选择覆盖假设的最小数据源，检查 buffer 大小、丢事件、采样窗口与权限；字段缺失不等于事件从未发生。
沿用户操作标记对齐线程、Binder、CPU 运行/等待、频率/idle、内存和所需硬件信息，避免仅凭两个时间重合宣称因果。
常规日志补充错误与状态，trace 解释时序；符号和构建版本须匹配，繁重诊断可能改变调度与功耗。

| 现象 | 先形成的证据链 | 常见错误结论 |
|---|---|---|
| 待机耗电 | idle/suspend、唤醒源、wakelock、外设驻留、能量区间 | 屏幕灭了所以已经休眠 |
| 长时间卡顿 | 关键路径运行/等待、thermal、内存压力及硬件时序 | 只需要加频或锁定大核 |
| 后台反复重启 | 退出原因、进程重要性、PSI/回收、工作重建 | 全局放宽 LMKD 就是修复 |
| 启动性能变化 | 相同编译/profile/缓存、GC/缺页/调度 | 单次首启动代表正常稳态 |

实现选择应解释“改变了哪个资源或触发条件、为何改善目标、代价落在哪里”；保留正常负载与压力负载的对照。
没有匹配硬件、稳定供电/温度或足够长观察窗口时，报告机制与逻辑验证结果，功耗和持续性能保持待验证。

## 已核实的官方深读入口

1. [Doze：设备级限制与维护窗口；注意历史参数](https://source.android.com/docs/core/power/platform_mgmt)
2. [App power management：应用级后台约束](https://source.android.com/docs/core/power/app_mgmt)
3. [Performance Hint API：deadline 与负载反馈](https://source.android.com/docs/core/perf/performance-hint-api)
4. [Thermal mitigation：HAL、severity 与限制语义](https://source.android.com/docs/core/power/thermal-mitigation)
5. [PowerStats：测量、驻留与历史 Power HAL 职责拆分](https://source.android.com/docs/core/power/power-stats-hal)
6. [BatteryStats 与 power profile 的估算/归因](https://source.android.com/docs/core/power)
7. [Cgroup abstraction 与 task profiles](https://source.android.com/docs/core/perf/cgroups)
8. [LMKD：PSI、压力和终止策略](https://source.android.com/docs/core/perf/lmkd)
9. [ART 配置：编译模式、资源与版本条件](https://source.android.com/docs/core/runtime/configure)
10. [Perfetto 官方 system tracing：数据源、缓冲与分析](https://perfetto.dev/docs/getting-started/system-tracing)

[1]: https://source.android.com/docs/core/power/platform_mgmt
[2]: https://source.android.com/docs/core/power/app_mgmt
[3]: https://source.android.com/docs/core/perf/performance-hint-api
[4]: https://source.android.com/docs/core/power/thermal-mitigation
[5]: https://source.android.com/docs/core/power/power-stats-hal
[6]: https://source.android.com/docs/core/power
[7]: https://source.android.com/docs/core/perf/cgroups
[8]: https://source.android.com/docs/core/perf/lmkd
[9]: https://source.android.com/docs/core/runtime/configure
[10]: https://perfetto.dev/docs/getting-started/system-tracing
