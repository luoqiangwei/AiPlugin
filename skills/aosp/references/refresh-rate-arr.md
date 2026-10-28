# 刷新率、MRR 与 ARR 的呈现时序

用于刷新率策略、模式切换、panel cadence、显示功耗、帧 deadline 与 HWC 配置变更。核实日期：2026-10-28。
先固定 Android 分支、composer 接口版本、panel/驱动能力、显示 config 与 group、内容 frame rate、用户/电源/温度策略及实际呈现证据。
此页提炼官方 MRR/ARR 正文；旧 HIDL 方法名用于说明历史契约，现代 AIDL 的等价字段与命令按目标接口核实。

## 1. 生成、提交、VSync 与 panel refresh 是不同事件

- 应用 frame rate 是内容生产/意图，提交 cadence 是 buffer 到达频率，VSync 是调度/硬件时基，refresh rate 是 panel 更新节奏。
- 新帧生成、buffer queue、SurfaceFlinger latch、HWC present 和最终 panel 更新不是同一个完成点。
- 显示 overlay 的“120 Hz”不保证每秒 120 个不同内容帧；应用报 24 fps 也不是强制 panel 只能 24 Hz。
- 帧时预算要按当前模式和有效 cadence 计算，不把所有显示都固定成 16.7 ms。

**工程判断**：分析掉帧或功耗时同时记录以上身份和时间线。仅看到 `present` 调用成功或应用 FPS 平均值，不能证明 panel 端时序满足要求。

## 2. MRR：通过切换显示配置改变固定刷新节奏

**事实**：Android 11 的 multiple refresh rate（MRR）支持由 composer HAL、平台策略与应用 frame-rate API 协作。
历史 `graphics.composer@2.4` 加入 config group、受约束切换和 timeline 等契约；不能把旧 API 代码逐字套在新 AIDL HAL。[MRR][mrr]

一个 MRR active config 对应固定 VSync/refresh 周期。不同 config 可同时改变分辨率、扫描方式和其他属性，因此不能只按“频率接近”选择。
`CONFIG_GROUP` 将可在相近条件下切换的配置归组，例如 1080p 的 60/90 Hz 与 1080i 的 48/72 Hz 不能当成同一个纯刷新率候选集合。

### 策略与最终选择分工

- DisplayManager 形成 default config、允许的 min/max 范围和系统策略；SurfaceFlinger 根据活动图层/内容在允许范围和 config group 中选择。
- 用户 peak/min 设置、应用 preferred mode、节电、内容 detection、touch/idle/display-power timers 等会参与决策；某处配置文件写了 120 不证明有效策略允许 120。
- 内容 frame-rate hint 是输入，不是无条件 mode 命令；多个图层的 cadence 可让系统选择共同倍数或误差较小的刷新率。
- `preferredDisplayModeId` 与 frame-rate hint 的作用不同；修改应用一项请求并不能证明其他 policy 已被排除。

官方 MRR 页面中的 overlay 名、sysprop 和低功耗频率规则属于对应实现说明。目标分支需查最终 policy vote、display configuration 和 SurfaceFlinger 的选择，不假设旧默认值永久不变。

### 切换时间是一项协议

历史 `setActiveConfigWithConstraints` 的关键语义是：[MRR][mrr]

| 字段/结果 | 必须保持的关系 | 错误后果 |
|---|---|---|
| `desiredTimeNanos` | CLOCK_MONOTONIC 上“不得早于”的生效时间 | 已排队旧节奏 buffer 与新时序冲突 |
| `seamlessRequired` | 要求无可见 artifact；做不到时不能假装成功 | 黑屏/闪烁或不受控切换 |
| `newVsyncAppliedTimeNanos` | 新周期实际开始生效的预测时间 | 平台按错误节奏提前/延后驱动帧 |
| `refreshRequired` / `refreshTimeNanos` | 需要过渡 refresh frame 时明确提出及其时机 | 切换不能按既定 timeline 完成 |
| `onVsyncPeriodTimingChanged` | 原 timeline 被错过/改变时更新平台 | 双方持续使用不同时间假设 |

**事实**：无法满足 seamless 请求时，旧接口通过 `SEAMLESS_NOT_POSSIBLE` 等结果及后续 `onSeamlessPossible` 协调，而不是强行发生有 artifact 的切换。
`getDisplayVsyncPeriod` 查询实际周期有助于过渡中调度；请求目标 config 与当前实际周期不同步是正常过渡状态，需要时间线解释。

**工程判断**：不能仅将 active mode ID 改正确就结束验证。检查约束接收、生效回报、过渡 frame、late timeline callback 和真实 panel 行为是否一致。

## 3. ARR：一个显示配置内按内容改变刷新 cadence

**事实**：Android 15 引入 adaptive refresh rate（ARR）。它让 display VSync rate 与 refresh rate 解耦，以离散 VSync 步进改变实际刷新节奏，减少为改变内容 cadence 而切换 mode 的需要。
平台支持需要系统/内核/panel 配合和 `android.hardware.graphics.composer3` version 3；仅设备运行 Android 15 不等于具备 ARR。[ARR][arr]

| 维度 | MRR | ARR |
|---|---|---|
| 改变实际刷新节奏 | 切换固定周期的 active config | 在一个 ARR config 内按 VSync 的离散倍数呈现 |
| `vsyncPeriod` 的硬件含义 | 该 config 的显示刷新周期 | panel TE/VSync 时基周期 |
| 最大实际刷新率 | 由 active config 的固定周期描述 | 由 `minFrameIntervalNs` 限制最短帧间隔 |
| config 类型 | `vrrConfig` 为 null 的非 ARR 配置 | 设置非 null `vrrConfig` 的 ARR 配置 |
| 额外协调 | config constraints 与切换 timeline | upcoming cadence 与 expected-present 通知 |

同一 display 可暴露不同类型的配置，但一个配置选择 ARR 或非 ARR/MRR；不能将两套字段意义叠在同一配置上。
Android 源码中某些命名使用 `vrr`，要按实际接口语义识别 ARR，不能只按字符串名判断功能。

### TE 频率不等于最大内容刷新率

**事实**：ARR 的 `DisplayConfiguration.vsyncPeriod` 应填 panel TE 周期；`VrrConfig.minFrameIntervalNs` 是最小允许帧间隔，即最大内容刷新率。
例如 TE 为 240 Hz 时 VSync 间隔约 4.16 ms，而 `minFrameIntervalNs` 为约 8.33 ms 时最大实际刷新率为 120 Hz。
前一帧之后满足最小间隔，才可在后续 TE 步进呈现。[ARR][arr]

**工程判断**：不能把“支持 120 Hz”机械写成 ARR 的 8.33 ms `vsyncPeriod`，否则误报了真正调度时基。
也不能仅缩短 `minFrameIntervalNs` 来宣称 panel 支持更高频率；配置必须与驱动/硬件实现一致。

## 4. Expected present 与 frame interval 是前瞻信息

**事实**：ARR 的 `DisplayCommand.frameIntervalNs` 提示即将到来的帧 cadence；`IComposerClient.notifyExpectedPresent` 提供预期呈现时刻和之后的帧间隔，使显示端提前安排 self-refresh。
其行为由 `NotifyExpectedPresentConfig` 和 timing 条件控制。[ARR][arr]

- 只有相应配置存在，且下一帧偏离此前 cadence，或与先前帧间隔达到配置 timeout 等条件时，才按协议发送通知；不是每次 present 都无条件重复通知。
- `expectedPresentTime=N` 与 `frameIntervalNs=T` 表示 N 后预期沿 T 的 cadence 继续，例如下一时刻是 N+T，直到后续改变。
- expected time 是提示/预测，不是证明该帧已经 scanout。实际 fence/呈现和 panel 反馈仍需验证。
- 旧 cadence 的通知不能在新内容节奏已经建立后无条件覆盖新状态；HAL/驱动与平台要以同一时间基准解释数据。

**工程判断**：丢通知、错误 timeout 或错误 interval 可能造成 panel 过早/过晚刷新、功耗异常或卡顿。先对齐请求、调度、present 与硬件信号，再决定改策略还是改 HAL 实现。

## 5. 验证候选集合、过渡和实际呈现

| 现象 | 至少要取得的证据 | 不能直接采用的结论 |
|---|---|---|
| 一直停在低刷新率 | 最终 min/max/default policy、内容/frame-rate hint、active config、thermal/power state | panel 宣称支持高频，所以只能是 app 错 |
| mode 切换闪烁 | group/约束、seamless 结果、timeline、refresh frame 与实际 panel 状态 | 延长动画能修复契约 |
| ARR cadence 错 | TE/VSync、min interval、frameInterval hint、expected-present 通知与最终帧间隔 | 改 MRR mode table 就能覆盖 ARR |
| overlay 显示高频但有抖动 | distinct frame、latch/present/scanout 时间线与尾部统计 | 平均 FPS 或显示 Hz 已证明流畅 |
| 节电收益不明显 | 内容负载、实际 refresh cadence、GPU/合成、panel 与能量窗口 | 不切 mode 就一定比 MRR 更省电 |

**事实**：ARR 官方提供 `onRefreshRateChangedDebug` 调试信息，并建议用 TouchLatency 调整到 panel 时基约数对应的内容 rate，观察实际刷新变化。[ARR][arr]

**工程判断**：覆盖稳定内容、cadence 改变、长时间 idle 后恢复、touch、显示电源/AOD、节电/thermal，以及支持范围内的 mode/group 切换。
真实硬件测试还应覆盖不同显示器与 panel；截图不能验证 TE、实际 scanout、闪烁和显示功耗。
设备缺少硬件时，可以验证配置和逻辑，但保持时序、功耗和可见 artifact 为待验证。

## 依据与仍需查询的范围

本页已读并提炼 MRR/ARR 的配置与时序契约。完整 composer3 AIDL 接口定义、厂商 panel 自刷新实现、frame-rate override、各版本 DisplayModeDirector vote 及游戏策略尚需按具体问题阅读目标代码。
不将这些只被概览指向的实现细节宣称为已逐版本覆盖。

[mrr]: https://source.android.com/docs/core/graphics/multiple-refresh-rate
[arr]: https://source.android.com/docs/core/graphics/arr
