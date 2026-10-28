# 音频 Framework、策略、效果与设备状态

本页用于音频路由、音量、并发录音、效果链、空间音频、蓝牙语音及 TV 音频问题。核实日期：2026-10-28。
先固定 Android 分支、launch level、Audio/Effects/Bluetooth HAL 接口版本、实际模块和产品配置；运行在新系统上不代表 vendor 已迁到新接口。
低延迟、PCM/SRC、USB 与 MIDI 另见 [音频性能与 I/O](audio-performance-io.md)。本文描述机制和诊断证据，不替代目标版本 CDD、冻结接口与真实硬件验证。

## 状态所有者：播放成功不是一个布尔值

音频入口经 Framework/native 客户端、Binder 和服务到达 AudioFlinger、Audio Policy 与 HAL；HAL 再对接 DSP、驱动和物理端点。
AudioFlinger 组织混音、流和效果处理，Audio Policy 根据用途、设备能力及运行条件选择路径；AudioService 还管理焦点、音量和相关用户状态。
官方 [音频架构概览][architecture] 保留了历史 mediaserver 名称；定位现代设备应核实 audioserver、system_server 与 vendor 服务的实际进程，不能照目录名推断进程边界。

```text
客户端意图/attributes → 策略与授权 → 设备/port/profile → patch/stream
                    → 混音/效果/音量 → HAL/DSP/驱动 → 物理声音
```

每一箭头都可能失败。focus 获得、设备已连接、patch 建立、write 接受、硬件时钟推进和听到声音需要各自证据。
由此推导：无声时应找相邻状态首次不一致的位置；不能仅因 app 已进入 playing 就改驱动，也不能用反复 open 掩盖旧 patch/stream 未释放。
接口职责依据 [Audio HAL 概览][hal]；当前符号与调用链仍需落到目标源码。

## HAL 代际与配置来源

| 接口与版本 | 应保持的契约 | 易错迁移 |
|---|---|---|
| HIDL Audio HAL，Android 13 及以前的主要接口体系 | policy/effects XML 及其 XSD 属于相应 HAL 版本契约；stream 是单向输入或输出 | 用另一版本 schema 或新设备能力填旧接口，XML 能解析却表达不了真实能力 |
| Android 14 起的 Stable AIDL 开发 | Core 负责端口、路由、stream 与相关控制；Effects 负责效果实例；Common/稳定类型复用结构 | 把 HIDL 方法机械改名，忽略注册、配置、数据结构及生命周期变化 |
| AIDL 的配置与服务发现 | `IModule` 实例直接注册；primary 实例通常名为 `default`；APM 从 HAL 的 AIDL 数据获得相应配置 | 仍假设 framework 必定直接读取 vendor XML，或只安装旧 `audio.primary.*.so` 就宣告新服务可用 |

以上区别见 [HIDL 实施][hidl]、[AIDL 实施][aidl] 和 [逐项对照][comparison]。Framework 可支持未迁移的 HIDL vendor；新系统版本本身不是 AIDL 已部署的证据。
AIDL 参考实现可以从旧 XML 生成 AIDL 配置；“vendor 内仍保存 XML”与“framework 通过何种契约取得配置”是两件事。
`IConfig`、`IModule`、`ITelephony`、`IBluetooth` 和 Effects `IFactory` 有不同责任，通话控制不能靠任意 Effects 参数替代。

AIDL 中端口能力、可用 route、实际 port config、patch 与打开的 stream 是不同对象。
HIDL 的 `create/update/releaseAudioPatch`、stream standby/pause/drain/flush 等操作在 AIDL 中分布于 module、common stream 和 `StreamDescriptor` 命令/响应；实现前按 [接口对照][comparison] 核对语义，不能假定旧方法返回时机与新命令完成时机一致。
诊断至少关联 module、port/config、patch、stream 身份及一次 start/standby/close 的时间线；设备断开后旧对象不得继续代表新连接。

## 策略：attributes、strategy、volume 与拓扑

`AudioAttributes.usage` 表示用途，`contentType` 表示内容；二者帮助系统决定路由、音量和焦点处理。
不能把 `USAGE_MEDIA` 简化成“固定扬声器”，也不能用旧 stream type 代替全部现代策略输入。
[Audio attributes][attributes] 给出其语义及历史 stream 映射；映射表是兼容线索，不是产品策略的完整定义。

[策略配置][policy] 描述 mix port、device port、route、profile 与 policy engine 的关系。
播放通常从 mix source 到 device sink，录音方向相反；profile 必须保留格式、采样率和 channel mask 的组合约束。
分别支持 PCM float、某采样率和某声道布局，不证明任意三者组合都可打开。
策略 engine 决定设备选择和音量规则；拓扑声明只说明可连接关系，不能创造 DSP、驱动或并发能力。

Android 10 的重构将 product strategy、volume group 和曲线等选择从旧硬编码组织中进一步分开。
音量 index 是相对整数；设备类别的 attenuation curve 将 index 转成衰减，不能把同一 index 当作跨扬声器、耳机和 USB DAC 相同的声压。
这一关系见 [策略配置][policy] 和 [音频术语中的 volume index/curve][terminology]。
由此推导：音量不一致应核对 attributes→group→设备类别→曲线→软件/硬件增益，而非只比较 UI 数字。

Configurable Audio Policy（CAP）使用 Parameter Framework，以 criteria 表达通话模式、可用设备等条件，以规则改变路由/音量参数。
Android 16 的 AIDL HAL 完整支持 CAP 配置；vendor 的可变配置通过 AIDL 提供，固定的音频 domain 描述可留在 system。
已有 HIDL CAP 产品可维持 vendor 配置；迁移时还需核对内置 strategy 名称从旧短名到 `STRATEGY_*` 的变化。
依据 [AIDL CAP][cap]，不能把旧 HIDL XML 读取方式或某个历史 build flag 当作所有 Android 版本的配置入口。

## 多设备与动态 profile：连接不意味着立即重开流

[Combined audio routing][combined] 从 Android 12 起扩展同类多设备及每 strategy 的多个 preferred devices。
preferred 是选择意图，active media devices 是当前用于选配置的设备集合，实际 stream/patch 才是执行结果。
优选设备全部可用时可一起选用；否则按文档规则退到最后连接的可移除设备或默认策略。
不能在一个 preferred device 暂不可用时，未经策略确认就把剩余设备当作完整优选集合。

动态 profile 的能力可能在连接后探测。输出需支持目标 active devices 与 dynamic profiles，且尚未路由到它们，才进入相应 reopen 判断。
空闲流可关闭重开；活动流可能延后到 standby，避免破坏仍在播放的 track。
由此推导：“设备回调已到但格式未变”未必是丢回调；先看流是否仍忙、探测是否完成及何时允许重新配置。

`AudioProfile` 将每种格式与其采样率、channel masks 绑定；旧扁平数组不能天然表达这种关系。
HAL、SDK profile 与旧扁平能力查询应保持相应内容一致；不能把扁平能力做全笛卡尔积后误报所有组合可用。
Android 14 起多 USB 同时路由还要求不同音频 device type、内核与 vendor 支持；不是“Android 12 支持多设备”即可推出多张 USB 声卡任意组合可用。
这些条件与相关 CTS/GTS 范围均见 [combined routing][combined]。

Android 11 起 device type 不再可任意当作设备集合的 bitmask；新枚举值会破坏 `device & SOME_GROUP`、OR 聚合等假设。
使用 `DeviceTypeSet`、相应类别 helper 或明确数组表达集合，并通过 audio patch API 路由。
创建 patch 时需生成唯一 handle，更新已有 patch 应遵守传入 handle 语义；device type、设备 address、port handle 与 patch handle 不能混用。
依据 [Device type limit][device-types]，旧 `set_parameters` 路由示例不能无条件用于新类型。

## Focus：竞争协调与用户意图

focus 不提供硬件独占，也不替代设备路由。请求可能被拒绝或延迟，获得后仍可能短暂失去、duck 或永久失去。
播放恢复应同时满足新的 focus 状态与用户仍希望播放；晚到 gain 回调不能撤销用户主动 stop。
Android 12 起系统在特定条件下执行 fade/mute；目标 API 35 及以上应用请求 focus 还受前台 app/foreground service 条件约束。
具体 usage、speech、duck 与通话静音条件见 [官方 audio focus 行为][focus]；不能把某一版本的强制处理套到旧系统或全部内容类型。

## Effects 与预处理：绑定对象决定寿命

效果实例可能绑定 session、stream 或 device；同一个 UUID 说明效果实现身份，不说明它附着在哪条路径。
[设备效果][effects] 从 Android 11 起允许设备被选用时自动启用指定 pre/post processing，甚至控制 entirely below HAL 的 device-to-device 路径。
此类硬件路径要求相应 `HW_ACC_TUNNEL` 能力和 patch 路由支持，不能假定必须先存在 AudioTrack 才能施加效果。
device effect 使用框架分配的 port handle；设备拔出/重连后不能用旧 handle 给新连接增删效果。

HIDL 的 effects XML、`createEffect` 和 AIDL 的 `queryEffects/queryProcessing` 等入口不同；AIDL 的 proxy/offload 协调也可能已移到 framework。
迁移依据 [HAL 对照][comparison]，逐项核对支持能力、创建、参数、START/STOP/RESET 和资源释放，不以“UUID 能枚举到”作为效果已生效的证据。
效果输入输出格式的接受/拒绝与精度另见 [性能与 I/O 的 high-resolution 小节](audio-performance-io.md#pcm格式src与高解析效果)。

[预处理配置][preprocessing] 将 AudioSource 用例映射到 capture device、gain 和预处理，而不是让 app 直接指定一块麦克风硬件。
`VOICE_COMMUNICATION` 若提供 AEC，应能通过 `AcousticEchoCanceler` 被发现和控制；不能在 HAL 偷开一份不可控 AEC 后声称 API 支持正常。
`VOICE_RECOGNITION` 不应默认打开 NS 等预处理；文件未配置 NS 也不足以证明合规，还要核实 HAL 默认处理。
语音识别的频响、线性、失真和近超声要求有专门条件；本文只提炼选择机制，数值验收应回到目标 CDD 和原页测试要求。

## 并发 capture：能开始录音不等于获得非静音样本

Android 10 的 [并发捕获机制][concurrent] 可以让某些客户端继续处于 capture 状态，但由 framework 将其音频静音，以便高优先级用例结束后恢复。
因此 AudioRecord 启动成功、HAL stream 活动及 app 获得实际麦克风数据是三个不同状态。
这不表示任意两个普通 app 都能同时得到原始音频；授权、隐私敏感用例和优先级仍决定实际供数。

- HAL 至少应支持配置中各 input profile 的相应实例；框架可能同时持有多个活动 input stream，即使只有部分客户端收到非静音数据。
- 同一个 HAL input stream 上多个客户端按用例优先级选择设备/预处理；不同 stream 可能选择不同设备。硬件冲突时决策必须可重复，冲突结束后恢复剩余 stream 原先请求的设备。
- 用例交接时效果请求可能短暂重叠。HAL 要跟踪被接受的请求；某实例 remove 后不能误关另一仍需要的 AEC/NS，也不能永久保留被抢占用例的处理。
- 不同 stream 共用物理采集源时，优先考虑在 demux 后分别预处理；若硬件不能做到，按明确优先级解决，不能让一个 app 的处理意图无条件污染全部输入。
- 通话与 AP capture 并发时，冲突设备/预处理由 voice call 优先；通话 RX/TX 捕获还有 `IN_TELEPHONY_RX`、模式和授权条件，不能与普通 MIC 录音混为一谈。

这些是 [concurrent capture][concurrent] 的 HAL 约束。诊断保留 source、UID/授权、silenced 状态、输入 stream、device、effect 请求和 call mode 的同时间线；静音政策命中时，无波形不能推导驱动没有采样。

## Sound Trigger：触发事件与随后音频是两条路径

[Sound Trigger][sound-trigger] 的 STHAL 负责低功耗识别，middleware 负责多客户端、权限与兼容，service 还关联系统状态及 sound model 管理。
模型内容对 framework 不透明；具体算法/数据格式依赖 app 与 vendor HAL 的约定，不能从通用接口推断可互换模型。
触发通知是离散事件，真正的周边音频通常由后续 AudioRecord 通过 Audio HAL 获取；收到 trigger 不证明捕获流已经可读。

状态应跟踪为 load model→handle→start recognition→停止/检测/资源中止→inactive→可重新 start 或 unload。
普通检测或 abort 后不能继续发正常 recognition 回调；`FORCED` 事件是例外，不会自动结束识别。
Android 11 对不成功 HAL 返回采用更严格的编程错误/重启恢复策略；这是对应代际的契约，不能把旧 HAL 文档里列出的错误直接当作可任意重试的业务分支。

声明 concurrent capture 的 STHAL 与 Audio HAL 必须共同兑现能力：热词 input profile 及可同时打开/激活的流数需覆盖相应并发模型/会话要求。
低功耗 DSP 检测、触发后的 `HOTWORD` 捕获和普通 AP capture 都要覆盖；仅“唤醒词偶尔能用”不证明并发资源契约成立。
依据 [Audio HAL 要求][hal] 和 [DSP/AP 并发捕获][concurrent]。

## Spatializer 与 head tracking：内容、设备和姿态处理共同决定可用性

Android 13 的 [空间音频体系][spatial] 将 spatializer 与 decoder 解耦：多声道 mix 进入专用 spatializer thread/effect，再形成输出；传感器栈提供 head tracking。
app 的 API 可用、用户已启用、耳机能力、当前内容与实际 spatializer graph 是否成立需分别判断。
dedicated output/profile、效果能力、设备与动态 `TYPE_HEAD_TRACKER` sensor 的关联缺一不可；一个布尔属性不能替代完整图配置。

[实施指南][spatial-implementation] 规定支持场景的 AAC/PCM 5.1 渲染与用例转换。
普通 stereo 不应仅因总开关开启就默认进入空间化；若产品提供 stereo 空间化，需要对应用户控制。
通知等并发内容、从多声道到 stereo、通话接管与结束恢复，都应保持用户设定并避免长时间重配或无声。
静态 spatial audio 不要求 head tracking；不能把“没有姿态 sensor”当作所有空间音频不可用。

动态 head tracking 的延迟从 IMU 感知运动到换能器输出变化计算，而非一次 Binder 调用或传感器 callback 时长。
该实施指南针对蓝牙耳机的 head tracking 要求不超过 150 ms；姿态推荐约每 20 ms 报告，最大间隔不超过 40 ms，且应说明实际测量方法。
耳机姿态上报受用户 head tracking 开关控制；设置持久化、设备重连及 sensor 绑定也属于功能结果。
codec 选择需区分 spatializer/media stream 与 VoIP 等无关流；低延迟 codec 与 jitter buffer 的 latency mode 调节是不同控制，不能靠一种信号代替另一种。[实施依据][spatial-implementation]

Android 15 的 [LE head tracking][le-head-tracking] 增加 ACL/ISO 传输选择；HAL 报告的 latency modes、vendor transport preference 和 spatializer connection capability 必须有共同可实现的组合。

| 模式/路径 | 姿态计算责任 | 应核对的条件 |
|---|---|---|
| `FRAMEWORK_PROCESSED` | framework 预处理并提供 head-to-stage | 不应在效果中再次重复同一坐标变换 |
| `DIRECT_TO_SENSOR_SW` | 效果经 sensor 软件栈获取数据并自行处理 | framework 仍控制 sensor enabled；实现应明确手机姿态的协调方式 |
| `DIRECT_TO_SENSOR_TUNNEL` | 效果通过硬件 tunnel 直接获取数据并自行处理 | BT、DSP 与效果能力真实连通，不能只宣告 `iso-hw` 偏好 |

无可兼容的 transport/mode 时应定位产品配置，而不是假设所有 ISO 路径都能硬件 tunnel。
BT Classic 的 FREE/LOW_LATENCY 与 LE 新的 software/hardware 动态空间模式并非同一完整枚举集合。

## 蓝牙语音：Android 17 AMSCO 的归属迁移

[Audio Managed SCO][amsco] 描述 Android 17 及以后的新路径：SCO 连接状态变为音频流活动/路由的后果，audio framework 与 AHAL 接管原先 BT framework 的连接控制。
启用仍需相应系统属性与兼容的 Audio/BT Audio HAL；系统升级但 vendor HAL 未升级时可保留 legacy 路径。
因此分析前先确认运行的是 AMSCO 还是旧流程，不能全版本要求 BT stack 停止旧 connect/disconnect 调用。

新路径下重点核对活动 stream 到 SCO 的 patch、audio mode 与相应启动/挂起条件，AHAL 通过 HFP 的 Bluetooth Audio provider/session 协作。
BT profile 已连接不等于 SCO 音频已建立；旧 SCO 广播也不是新路径的唯一真相，应关联 audio device callback、patch 与 provider 状态。
满足对应 SCO 条件时，framework 还协调 A2DP 并发 patch，防止媒体与语音路由状态分裂。

BT 异常/抢先断开需通知 audio framework；codec 重协商、active HFP device 改变和 audio mode 切换都可能重建会话。
若 `HfpTransport::StartRequest` 返回 `PENDING`，AHAL 需要在 HFP 状态就绪后重试；由此推导，重试应绑定当前设备/会话代次，避免晚到结果复活旧 SCO。
额外 hysteresis 不能跨 audio mode 改变继续存活。具体 Telecom、VoIP、语音识别序列与 codec 优选见 [AMSCO 原页][amsco]，不把某个产品的 DSP 路径当作通用实现。

## Sound dose：测量位置与输出路径必须一致

Android 14 引入 [sound dose 支持][sound-dose]，但官方启用计算的完整逻辑从 **Android 14 QPR1** 才成立；不能只因存在接口就给初始 Android 14 打开 CSD 计算。
MEL 表示瞬时暴露量，CSD 在连续滚动七天窗口累积；固定音量上限、某次峰值和七天累计剂量不是同一个指标。
适用法规、认证范围及精确阈值仍需相应规范；这里提炼 AOSP 数据与控制契约。

SoundDoseManager 在 audioserver/AudioFlinger 侧收集 HAL 数据或从可见 PCM 估计，SoundDoseHelper 在系统服务侧持久化、恢复、通知并按条件调整音量。
硬件实际增益、DSP effects 与换能器特性会改变用户听到的声压；读取 API 音量 index 或 DSP 前 PCM 幅值都不足以证明 MEL 准确。
压缩 offload/direct 路径可能只让 framework 看见压缩数据，无法靠内部 PCM fallback 估计真实输出；适用要求下需要 HAL 提供实际 MEL。

注册 HAL sound-dose callback 后 framework 内部计算会关闭，HAL 应在其生命周期内持续供数。
因此不能注册后只覆盖普通 PCM 而漏掉 offload/BT 路径，也不能让 HAL 和 fallback 对同一段输出重复累计。
`MelRecord` 的单调时间与各 port 时间基准需一致；同时间数据会聚合，多设备应分别标识，不能把重启后的时钟直接接到旧时间线。
接口、standalone AIDL 过渡方案、配置条件和 VTS 见 [sound dose 原页][sound-dose]；原页出现相近配置名，实际 overlay 键必须核对目标树资源定义，不能照相近拼写猜测。

## TV 与动态 soundbar：device-to-device 也是实际音频路径

[TV audio][tv] 将 TIF 硬件输入信息关联到 source AudioPort，将输出关联到 sink AudioPort，软件 stream 则是 AudioMixPort。
tuner/HDMI 输入可能通过 device-to-device patch 直接到输出，并与软件音频合流；没有 decoder 或 AudioTrack 活动不能据此断言“没有音频路径”。
切换到 HDMI 输出时，应同时更新软件输出与已有 TV 输入 patch 的 sink，避免直播声与系统声走向不同端点。

TV `DEVICE_IN_LOOPBACK` 表示 TV 输出混合音频的 capture source；它与外接线缆测 round-trip latency 的 loopback 不是同一个概念。
原页还要求该 TV 路径的 DEFAULT input acquisition 使用虚拟 null source；不能照手机经验将任何 DEFAULT AudioRecord 都解释为内置麦克风。
默认 AudioRecord、专用 loopback、授权与选用 patch 的条件需按目标 TV 实现核实。
原页含旧权限、旧 C HAL 和录文件示例；本文保留 port/patch/loopback 机制，不将旧路径、采样率示例或权限组合视为现代完整验收规范。[TV 原页][tv]

Android 14 的 [Dynamic soundbar mode（DSM）][soundbar] 面向具备扬声器和 ARC 能力的 Android TV CEC playback device。
启用时 framework 尝试动态分配 CEC audio-system 逻辑地址 5，并建立 ARC；关闭时释放本地 audio device/连接。
支持的是 ARC 和相应 system audio control；DSM 本身不提供 eARC Rx。

模式默认应保持关闭，以避免网络里已有 audio system 时的竞争；不能通过 RRO 默认打开来替代能力和拓扑判断。
CEC 关闭、连接非 ARC 端口、地址 5 已被占用、扬声器断开和 HDMI 热插拔有不同结果。
设置持久化或显示 enabled 不证明 ARC 建立；诊断同时记录 CEC 设备/逻辑地址、ARC 状态、实际音频 patch 与电视/本机发声。
设备不是 active source 时还应暂停相应本地媒体；UI、驱动 ARC 与音频策略需共同兑现，相关行为和 CTS 场景见 [DSM 实施与验证][soundbar]。

## 用证据选择修复位置

| 现象 | 必须关联的证据 | 可验证的推导 |
|---|---|---|
| 已选设备却仍走旧输出 | preferred/active device、profile 探测、stream busy/standby、patch | 是策略选择错误，还是重开时机尚未满足 |
| 录音启动成功但静音 | UID/source/授权、silenced、并发优先级、HAL input、effects | 政策静音、效果冲突与底层无样本分别处理 |
| 通话结束后声音不恢复 | mode、SCO/A2DP provider、patch 代次、原设备与 focus 意图 | 旧回调或效果请求是否污染新会话 |
| head tracking 卡顿/漂移 | sensor 绑定/时间戳、transport、connection/latency mode、最终声学延迟 | 区分错配传输、重复姿态处理与输出缓冲 |
| dose 为零或突增 | 输出路径、HAL callback、MEL port/时间、fallback 状态、持久化 | 是否漏 offload、重复积分或跨时钟拼接 |
| TV 声与系统声分离 | TIF 输入 port、TV patch、软件输出、CEC/ARC | 是否只迁移一条输出路径 |

CTS/VTS 验证对应接口，CTS Verifier 与真实设备场景补足路由、外设和听感；spatial 算法、声压校准、DSP 处理及供应商内部路径不能仅凭 framework API 通过推定正确。
本文未提炼各 vendor 算法、逐命令 HAL stream 状态机或完整 HDMI-CEC 协议；需要这些细节时从下列已读入口继续定位并切到目标 revision。

## 已读官方依据

[architecture]: https://source.android.com/docs/core/audio
[hal]: https://source.android.com/docs/core/audio/implement
[hidl]: https://source.android.com/docs/core/audio/hidl-implement
[aidl]: https://source.android.com/docs/core/audio/aidl-implement
[comparison]: https://source.android.com/docs/core/audio/aidl-hidl-comp
[attributes]: https://source.android.com/docs/core/audio/attributes
[policy]: https://source.android.com/docs/core/audio/implement-policy
[terminology]: https://source.android.com/docs/core/audio/terminology
[cap]: https://source.android.com/docs/core/audio/aidl-cap
[combined]: https://source.android.com/docs/core/audio/combined-audio-routing
[device-types]: https://source.android.com/docs/core/audio/device-type-limit
[focus]: https://developer.android.com/media/optimize/audio-focus
[effects]: https://source.android.com/docs/core/audio/audio-effects
[preprocessing]: https://source.android.com/docs/core/audio/implement-pre-processing
[concurrent]: https://source.android.com/docs/core/audio/concurrent
[sound-trigger]: https://source.android.com/docs/core/audio/sound-trigger
[spatial]: https://source.android.com/docs/core/audio/spatial
[spatial-implementation]: https://source.android.com/docs/core/audio/implement-spatial-audio
[le-head-tracking]: https://source.android.com/docs/core/audio/ht-leaudio
[amsco]: https://source.android.com/docs/core/audio/sco-audio-mgmt
[sound-dose]: https://source.android.com/docs/core/audio/sound-dose
[tv]: https://source.android.com/docs/core/audio/tv
[soundbar]: https://source.android.com/docs/core/audio/soundbar
