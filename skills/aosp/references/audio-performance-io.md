# 音频性能与 I/O：实时路径、采样转换、USB 和 MIDI

本页用于低延迟、爆音/断音、AAudio/MMAP、格式精度、USB 音频和 MIDI 问题。核实日期：2026-10-28。
先记录 Android/内核/HAL revision、音频设备、实际采样格式和 stream 路径；同一 API 可以落到不同实现，不能只按 API 名称判断延迟或精度。
路由、效果归属、并发录音、空间音频和蓝牙通话见 [音频 Framework 与策略](audio-framework-policy.md)。

## 先定义测量对象和时间边界

[Audio latency][latency] 指信号穿过系统产生的时间差，输入、输出、round trip、启动 warmup 与 head-tracking motion-to-sound 不是同一个量。
纯 buffer 推算只能描述部分排队：`frames / sampleRate` 得到该段音频时长，不能自动包含客户端等待、HAL/DSP、USB/BT、转换与换能器延迟。
frame 包含同一采样时刻的全部声道；byte 数需再乘 frame size，不能用声道数或采样位深代替 container size。
单位和术语依据 [Audio terminology][terminology]、[数据格式][formats]。

buffer 数量/长度经常是调度不稳后的补偿，而非问题起点。增大 buffer 可减少 underrun，却增加时延；缩小 buffer 会暴露原有最坏调度延迟。
[延迟贡献因素][contributors] 还包括 DSP、长中断、调频/电源转换及安全执行等造成的停顿。
由此推导：先关联 underrun/xrun 与 CPU 可运行等待、HAL write 周期、硬件推进，再评估 buffer；不能把所有爆音都交给一个 buffer 常量修复。

## FAST Mixer：请求、准入与实际执行分开

[Reduced-latency design][fast-design] 描述 normal mixer 与 fast mixer 协作：normal mixer 提供普通轨道的子混音，fast mixer 周期性混入准入的 fast tracks 后交给 HAL。
FAST 路径减少处理能力以换取稳定的短周期；其设计不承担普通 mixer 的逐轨 SRC、逐轨效果和混音效果等完整功能。
因此新增效果、采样率转换或改变配置后，必须重新核实实际路径，不能一边要求所有处理、一边假定 FAST 永不降级。

`AUDIO_OUTPUT_FLAG_FAST` 只是请求；客户端及 AudioFlinger 都可拒绝。
准入受 fast mixer 是否存在、采样率、callback 线程、buffer 大小和可用 fast-track slots 等影响；旧设计文档中的具体 slot 数与周期不是所有 release 的常量。
确认请求位、服务端接受状态和实际 mixer thread 三者，才足以声称测到了 fast track。

fast mixer 使用实时调度并以低 jitter 高频运行；过晚会缺数据，过早也可能在客户端尚未供数时拉取。
normal mixer、fast mixer 和客户端 callback 不同调度级别的协作见 [FAST 设计][fast-design]；不能用“提高优先级”替代整个生产/消费时序。
HAL write 是该设计中预期的等待点；向 fast mixer 加普通锁、同步 Binder 或可阻塞日志会破坏其时间预算。

## 实时线程与 priority inversion

高优先级线程等待低优先级线程释放共享状态，会产生 priority inversion；爆音、重复环形 buffer 或控制命令迟到都可能由此引发。
[Avoid priority inversion][priority-inversion] 建议在适合的边界使用单读者/单写者 FIFO、复制状态、atomic 单字状态和 state queue，而非让实时线程同步等复杂共享对象。
这不是“任何 mutex 都错”；普通线程仍可使用正确加锁，关键是不能把无界等待带入周期性音频路径。

- 音频 callback 要短且工作量有界；避免 I/O、内存分配抖动、同步 IPC 和等待 UI/业务线程。app 侧建议见 [低延迟 app 指南][latency-app]。
- non-blocking 不自动等于有界；无限 CAS 重试或长队列遍历仍可超过 deadline。数据队列与控制状态应分别设计。
- 单读写者结构的正确性依赖真实 producer/consumer 数量与 memory ordering；新增第二个生产者后不能继续假设旧 FIFO 安全。
- 跨进程共享 control state 不能因“音频性能”而免校验，索引和容量仍需边界检查；不可信客户端可破坏的状态不能决定任意内存访问。
- 固定实时优先级应结合周期、最坏执行量及其他实时任务分配；不可建模的无界任务不应仅因“重要”就抢占音频线程。[延迟因素][contributors]

由上述机制推导，可靠优化应同时减少平均耗时与最坏停顿；只看总体 CPU 占用低，不能证明一个 2 ms 级周期不会错过 deadline。
观察 scheduling、频率/idle 转换、IRQ、HAL write 与 xrun 的同一时间线，避免只截一张线程优先级截图作结论。

## AAudio 与 MMAP：低延迟 API 不保证使用低延迟路径

AAudio API 从 Android 8.0 提供，MMAP 相关增强从 Android 8.1 才具备对应框架支持。
[AAudio/MMAP][aaudio] 的路径分为：

| 路径 | 谁向硬件共享 buffer 供数/取数 | 核心约束 |
|---|---|---|
| MMAP EXCLUSIVE | 客户端直接访问与 ALSA/硬件共享的映射区 | 绕开服务端 mixer，但资源分配、授权和关闭仍由服务协调 |
| MMAP SHARED | audioserver 内的 mixer 使用 MMAP buffer | 多客户端共享，不等于原有 AudioFlinger legacy 路径 |
| Legacy fallback | AAudio 通过原有 AudioFlinger 数据路径 | API 仍可正常工作，但不能算 MMAP 验证通过 |

MMAP NOIRQ 路径不是靠普通共享读写计数器管理每次消费；服务周期性获取硬件 frame position 与 `CLOCK_MONOTONIC` 时间，客户端或服务 timing model 据此预测硬件进度。
采样位置、时间单位、时钟来源或速率错误，会表现为供数预测偏移、xrun 或不稳定延迟，即使 mmap 系统调用本身成功。
输入路径的数据方向相反，但也依赖可靠的硬件位置/时间模型；不能用 write 调用耗时推导真实 presentation position。[机制依据][aaudio]

HAL 需兑现 MMAP buffer 创建、start/stop、position 查询及相应能力，policy 需有可选择的 MMAP/NOIRQ profile，硬件前端还需能与原 AudioFlinger 路径共存。
仅设置 `aaudio.mmap_policy` 不会补齐这些能力。
AUTO 允许 MMAP 失败时退到 legacy；ALWAYS 可用于区分是否真能打开，但具体属性/测试接口及重启要求应核对目标版本，本文不默认改运行设备。
验收必须记录 stream 实际是否使用 MMAP、sharing mode 和实际格式，而非只记录请求的 LOW_LATENCY/EXCLUSIVE。

EXCLUSIVE 的共享 fd 还承担安全边界：原始 `/dev/snd` fd 可能暴露过多驱动访问，不能任意传给 app。
原页描述可分享的 `anon_inode:dmabuf` 路径和历史 ION 实现；Android 10 起可用 `AUDIO_MMAP_APPLICATION_SHAREABLE` 标志表达能力。
不能照搬旧“负 buffer size 表示可共享”约定到所有接口，也不能靠放宽 SELinux 直接交出原始声卡 fd。
现代 allocator、AIDL 类型与映射寿命应核对目标树；安全语义与历史分配器实现不是同一层要求。[MMAP fd 契约][aaudio]

app 侧 Oboe/AAudio 的 low-latency、exclusive 请求、原生 sample rate/buffer 建议及 callback 约束见 [app 指南][latency-app]。
请求值与最终协商值要分别保存，路由切换或设备断开后要按新 stream 重新验证；不能把首次打开的 mode 缓存成设备永久能力。

## Round trip、warmup 与证据有效范围

[测量指南][latency-measure] 通过全双工播放/录制、回送信号和相关性算法找输出/输入信号的时间偏移。
内置 speaker→mic、模拟耳机线缆回环及 USB audio interface 回环走不同物理路径，测量结果不可混比。
结果是总的输入加输出时延；没有独立测量或模型，不能简单除以二后声称得到精确单向时延。
测试还需区分排队配置、采样率、路由、负载、冷启动/持续播放和实际 fast/MMAP 状态。

[Loopback dongle][loopback] 的电路用于将耳机输出衰减到麦克风输入范围，并满足相应插头识别条件。
错误接线、过载、声学回授或接口极性会破坏相关性测量；“软件未找到峰值”不必然是系统延迟无限大。
OboeTester 与 CTS Verifier 使用这类 round-trip 思路；符合目标 CDD 的判断还需匹配版本、设备能力与实际测量条件。

[Audio warmup][warmup] 是放大器/时钟/去爆音等电路从关闭到可稳定工作的启动过程，与稳定态 FIFO 延迟不同。
FastMixer 的 `measuredWarmup/warmupCycles` 根据多次 HAL write 周期稳定情况估计输出 warmup，是重要线索，但不能替代所有物理换能器的端到端测量。
测量前的静音间隔、刚开机与稳定运行、speaker 与有线耳机都可能改变结果；硬件没充分休眠会得到偏低样本。
优化去爆音延时、并行启动和时钟保持需同时评价 popping 与 idle power，不以持续供电掩盖启动流程缺陷。

## PCM格式、SRC与高解析效果

[Audio data formats][formats] 区分 bit depth、container size、packed/unpacked、对齐、符号与定点/浮点表示。
24-bit 数据放在 32-bit word 中时，不能从“32-bit buffer”推断 32 位有效精度；MSB/LSB 对齐错误会变成音量、失真或噪声问题。
channel position mask 表示空间位置，channel index mask 表示索引集合；不能对所有多声道输入强行赋予相同扬声器语义。

float 常用 ±1.0 作为外部标称范围，中间运算可有更大 headroom；转换到外部定点时需按规则钳位。
转换降低整数范围要防溢出，降低小数精度涉及截断/舍入/dither；不能通过简单重新解释字节实现不同 Q 格式转换。
单精度 float 可以无损表示至多 25 个有效位的相应定点值，但 float→常用定点一般有损；NaN/Inf 等异常值也不能假定全栈自动以相同方式消毒。
因此“先转 int16 再转 float”无法恢复丢掉的精度。[转换边界][formats]

[Sample rate conversion][src] 在源与 sink 的 sample rate 不一致时改变离散采样序列。
质量评估同时看带宽/幅度保持、phase/group delay、转换比、CPU/功耗与内部延迟；更高复杂度不总适合交互路径。
Android 的 linear/cubic/sinc 等实现及选择可随版本、负载、用途和 vendor 修改，`af.resampler.quality` 是定位线索，不能作为跨产品稳定接口承诺。
由此推导：回放变慢/音调变化要先查 sample-rate 契约，固定噪声或混叠再查转换质量；不能把任何格式问题都交给“更高 quality”。

[High-resolution audio][highres] 说明 Android 9/10 对 multichannel float、较高采样率和效果处理的改进。
precision 必须沿 decoder→mix→effect→HAL→设备逐段保留；文件支持 192 kHz/float 不证明最终 output 没有降采样或转 int16。
vendor insert effect 的输入/输出声道约束、aux effect 的 mono 输入，以及 position/index masks 均需显式验证。
旧效果若只支持 int16 stereo，应在配置阶段拒绝不支持的组合，而非成功返回后按错误 stride/布局处理内存。
旧 adapter 可兼容功能，但可能损失精度；报告“高解析”时应记录实际效果链和每个边界的格式。
原页的并发轨道数与内存上限是对应历史实现改进，不应当作所有分支固定容量。

## USB audio：传输角色、能力协商与实际时钟

[USB digital audio][usb] 区分 Android 为 host、peripheral/accessory 及 adb development mode 的不同角色。
host 枚举外设 descriptors，按 audio class/interface/endpoint 获得能力；一个物理外设可同时包含多个功能，设备被枚举不等于 audio streaming interface 已可用。
文件传输的 MTP/MSC 与实时 USB audio class 不同；可拷贝音乐文件不证明实时采集或播放支持。

USB audio 常用 isochronous transfer：传输检测错误但不靠逐包重传恢复。
带宽由速率、声道、sample container 和 endpoint/SOF 条件共同限制，不能只提高 HAL profile 的 sample rate。
adaptive、asynchronous、synchronous 模式的采样时钟来源不同；时钟漂移、反馈或错误的每周期数据量可产生断续音，即使 USB 控制传输看起来正常。
ALSA/tinyalsa 层通常抽象掉等时传输细节，故障仍可能需下钻 USB/驱动，而非只改上层 mixer。[传输依据][usb]

USB 支持需串联 host 硬件/供电、内核 USB audio/isochronous、framework host feature、HAL 模块与 policy route。
能力应在热插拔后重新协商；外设供电不足、quirk、format/profile 不匹配和路由未更新要分开定位。
原 USB 文档包含 Android 5.0 UAC1 最小支持集及旧 `audio_policy.conf` 示例；它们不是现代 UAC2、AIDL 或高解析设备能力的完整上限。
accessory audio 还有历史固定格式和 host 配合条件；不建议从旧例子推导新产品应实现何种音频角色。

## Android 14 USB preferred mixer 与 bit-perfect

[Preferred mixer attributes][preferred-mixer] 允许 app 在受支持 USB 设备上配置 format、sample rate、channel mask 与 mixer behavior；不适用于任意内置或蓝牙设备。
framework 可能为新 attributes reopen output stream，vendor 需提供可路由到 USB 的 dynamic mix port。
若 USB 功能并入 primary HAL，相应 dynamic port/route 也需由该模块提供，不能继续只检查独立 usb 模块配置。
Android 14 要求相应 preferred attributes 支持；`BIT_PERFECT` 是可选、仅 AIDL Audio HAL 提供的额外能力。

bit-perfect 的不变式是 **API 到 USB 端点整个路径保持数据不变**：不能软件缩放、SRC、混音或施加 effects，DSP 也受此约束。
对 MQA/DSD-over-PCM 等承载有意义的编码数据，哪怕一次“无害的”增益/混音也会破坏其含义。
硬件负责相应音量控制；仅添加 `AUDIO_OUTPUT_FLAG_BIT_PERFECT` 或绕开 AudioFlinger 某个处理步骤不能证明整条链满足条件。
验证需要实际兼容 DAC、端到端格式/字节保持及用户路径，相关 CTS activity 只能覆盖其断言范围。[bit-perfect 契约][preferred-mixer]

## MIDI：带时序的事件流与端口生命周期

[MIDI][midi] 传递乐器等控制事件，不传送 PCM 波形；MIDI device 可用、NoteOn 到达与 synth 发声是不同层结果。
Android 从 6.0 起可选声明 MIDI feature，直接支持 USB、BLE 和 virtual/interapp；AMidi NDK API 从 Android 10 提供。
MIDI 2.0 USB transport 从 Android 13 提供，virtual transport 从 Android 15 提供；不能把 MIDI 1.0 的 ALSA 启用条件无差别套给所有 MIDI 2.0 路径。

[MIDI architecture][midi-architecture] 的 message 是事件边界，transport 负责封装/交付；read 得到的 chunk 不应被随意当作完整消息，长 SysEx 与多个短消息需正确处理。
时间戳可能来自 transport 或平台，MIDI 1.0 协议本身并不携带通用 timestamp；BLE 包内消息的时间信息不能被丢掉后仍声称时序等价。
message 顺序与事件时间影响 synth 调度；不能用“总字节数相等”证明音乐节奏正确。

IN/OUT 是相对于端口的方向；USB host/peripheral 是总线角色，二者不能仅按相同英文单词相配。
一个 USB endpoint 可含多个 virtual cable/port，每条消息流又有 channel，不能把 cable number、port 和 MIDI channel 当作同一标识。
MidiManager 用于发现/open/close device，再通过 ports 收发；input port 的独占连接限制意味着打开失败也可能只是被另一 app 占用。
解绑、热拔插、取消选择和 app 退出后应关闭端口，使新连接可用，并阻止旧回调继续向新设备发送事件。[体系依据][midi]；[端口测试依据][midi-tests]

USB MIDI 1.0 的 host/peripheral 与 BLE/virtual 使用不同底层；USB host 需要相关内核与 host 能力，BLE/virtual 不走同一 ALSA 路径。
旧文档中的 3.10 gadget patch 只说明历史背景，现代 ConfigFS、USB function 与 kernel 配置应核对目标实现。
声明 `android.software.midi` 不会实现 transport 或消除供电限制；[MIDI test procedure][midi-tests] 要覆盖已有连接、运行中插拔、断开后枚举、virtual、host/peripheral 与 BLE 实际事件。
无声时先用事件接收证据分开 transport/port 与 synth/audio output，不把所有 MIDI 问题归为音频驱动。

## 库、服务与产品能力声明

[Configure a shared library][shared-library] 描述历史 `audio.primary.<device>.so`、a2dp/usb 模块名、安装位置、policy 与产品 feature 配套。
其本质是 loader 约定、产品打包和能力声明必须匹配实际实现；它不是现代 Stable AIDL 服务注册/VINTF 配置的通用模板。
实施时核对目标分支 build definition、安装 ABI/分区、服务实例和产品选择，不能因一个 `.so` 编译成功就认定 audioserver 会加载它。
`android.hardware.audio.low_latency`、MIDI 等 feature 声明应有实际能力与对应测试，XML 文件存在不是测量结果。
本文仅提炼打包/声明的边界，未把 Galaxy Nexus Android.mk/旧 CONF 步骤升级为当前构建教程。

## 调试：观察不能破坏被观察的实时路径

[Audio debugging][debugging] 的 tee sink 可保存音频片段用于比较，但默认在编译期/运行期关闭，属于受控调试构建功能。
captured PCM 可能含用户声音；采集范围、保存寿命与关闭清理是诊断方案的一部分，不应把 tee sink 常开进生产版本。
fast、normal、deep-buffer、每 track 等路径并不天然都有同等 tee 覆盖；某 dump 没有声音不能直接推导硬件没有输出。

ALOG 类日志可能阻塞、丢失或改变时序；NBLOG 使用独立 timeline 和共享环形 buffer 降低干扰。
无锁 writer 的正确性依赖每个 timeline 的写者模型，多线程共享要额外同步，而同步又可能损失实时优势。
官方原页包含旧 media.log 进程与开关流程；在现代分支应确认设施仍存在，不直接照旧命令改系统。
优先保留 stream/mixer/HAL 时间线、xrun、实际路由和精确配置，再选择最小必要数据采集。

| 现象 | 关键证据 | 先排除的错误结论 |
|---|---|---|
| AAudio 延迟仍高 | 实际 MMAP/legacy、sharing mode、协商格式、hardware timestamps | API 名为 AAudio 就已走 MMAP |
| 小 buffer 爆音 | deadline、调度等待、IRQ、HAL write、xrun、效果/SRC | buffer 越小必然越好 |
| 高解析内容精度下降 | 每段格式/container/有效位、effect 配置、最终端口 | 文件头格式等于硬件输出格式 |
| USB 能枚举却无声 | role、descriptor、供电、profile、stream/patch、时钟反馈 | USB 连接成功等于 audio class streaming 成功 |
| MIDI NoteOn 有但无声 | 消息时间/port、synth、实际 AudioTrack/output | MIDI 消息就是音频样本 |

未在此处给出完整 USB/UAC 协议、MIDI 2.0 UMP/property exchange、DSP resampler 算法或所有 AAudio stream API 的状态表；这些应按实际问题继续查接口与目标源码。
已提炼的边界应由相应 CTS/VTS、CTS Verifier、loopback 和真实外设证据分别验证，不能以一次正常播放替代所有路径。

## 已读官方依据

[latency]: https://source.android.com/docs/core/audio/latency
[terminology]: https://source.android.com/docs/core/audio/terminology
[formats]: https://source.android.com/docs/core/audio/data_formats
[contributors]: https://source.android.com/docs/core/audio/latency/contrib
[fast-design]: https://source.android.com/docs/core/audio/latency/design
[priority-inversion]: https://source.android.com/docs/core/audio/avoiding_pi
[latency-app]: https://source.android.com/docs/core/audio/latency/app
[aaudio]: https://source.android.com/docs/core/audio/aaudio
[latency-measure]: https://source.android.com/docs/core/audio/latency/measure
[loopback]: https://source.android.com/docs/core/audio/latency/loopback
[warmup]: https://source.android.com/docs/core/audio/warmup
[src]: https://source.android.com/docs/core/audio/src
[highres]: https://source.android.com/docs/core/audio/highres-effects
[usb]: https://source.android.com/docs/core/audio/usb
[preferred-mixer]: https://source.android.com/docs/core/audio/preferred-mixer-attr
[midi]: https://source.android.com/docs/core/audio/midi
[midi-architecture]: https://source.android.com/docs/core/audio/midi_arch
[midi-tests]: https://source.android.com/docs/core/audio/midi_test
[shared-library]: https://source.android.com/docs/core/audio/implement-shared-library
[debugging]: https://source.android.com/docs/core/audio/debugging
