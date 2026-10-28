# Android TV 设备集成：输入、调谐、CAS、CEC 与验证

核实日期：2026-10-28。本文承接 Devices/TV 侧边栏的全部机制分支，并区分内容应用、TV 系统能力和硬件实现。
官方 TV 文档包含较早 Android/API/HIDL 示例，产品声明应以目标版本 CDD、接口、VINTF 与权限定义复核。
TV Input Framework 不实现全部地区广播规范；Android TV 开源平台能力也不等于某个 Google TV、运营商或内容授权产品要求。

## TIF 将输入身份、会话与节目数据分开

TV App 提供直播交互，经 TvInputManager/TvInputManagerService 创建每个 TV Input 的会话，TV Input Service 再处理具体源。
TV Provider 保存 channel/program 与访问约束；可选 TV Input HAL 连接内建输入硬件。
物理 tuner、HDMI passthrough、网络 TV Input 和独立 OTT 播放不是同一条路径。[TIF][tif]

| 组件/对象 | 所有的事实 | 不能据此推断 |
|---|---|---|
| TV Input ID / session | 某个输入及其使用实例 | 同一节目换台后仍能复用任意旧 decoder/Surface |
| TvProvider channel/program | 节目与频道元数据、包归属、标志 | 已经调谐成功或已经获得解密授权 |
| TvInputService | tune、Surface、内容可用/阻止等会话行为 | 可以直接访问任何其它输入的数据 |
| TV Input HAL | 系统输入的硬件端口/流 | 第三方应用自动获得硬件访问 |
| passthrough input | HDMI 等外部输入展示 | 像 tuner 一样必须有节目频道数据库 |

第三方输入对 Provider 通常仅能读写属于自己包的行；系统/特权访问和跨包访问要按实际权限核对。
`TV_INPUT_HARDWARE` 等能力使系统硬件输入可以动态添加/移除输入，并非安装普通 TV Input APK 即获得。
输入断开、Surface 更换和 session release 需收敛资源与回调；旧会话回调不能更新新会话的“当前频道”。
数据库里的 INTERNAL_PROVIDER_DATA 可保存源特定字段，但不是不受信任边界检查的通用 IPC 通道。[TIF][tif]

display name/number、broadcast identifiers、源私有数据与 searchable/browsable/locked 标志承担不同语义。
`COLUMN_SEARCHABLE=0` 影响搜索，`COLUMN_BROWSABLE=0` 影响列表，`COLUMN_LOCKED=1` 才涉及频道 PIN 锁定；隐藏条目不能代替播放授权。
broadcast genre 到 canonical genre 的转换也不等于完整节目内容评级或访问控制。
EPG 正确、频道可见、画面开始、音频开始与内容被正确保护应分别观察。[Provider][tif]

## Tuner Framework 的资源与数据通道

Android 11 起的 Tuner Framework 提供 SDK API、JNI/native bridge、Tuner HAL 与 Tuner Resource Manager（TRM）。
Frontend 负责标准相关调谐/扫描，Demux/Filter 拆流和产生事件，Descrambler 与 CAS 配合，DVR 支持录制/播放，LNB 服务卫星输入。
MediaCodec/AudioTrack 消费 A/V；Tuner 并不是一个自行完成 UI、解密、解码和显示的播放器。[Tuner][tuner]

先检查硬件/HAL capability 与版本，再选 FrontendSettings、filter 类型和数据路径。
Android 12 的 Tuner HAL 1.1 增加部分能力，例如 DTMB；SDK 方法存在不证明设备 HAL 支持。
`TunerVersionChecker.getTunerVersion()` 与具体 API 的最低版本条件应配对，不能只用 Android 版本选择标准。
标准名被枚举也不证明产品具备对应射频前端、解调器或地区认证。[版本][tuner]

| 数据路径 | 需要处理的资源/协议 | 常见失效 |
|---|---|---|
| section/一般 filter 数据 | 事件通知、FMQ/MQ、Filter.read、实际长度 | 只收事件不读数据导致 overflow |
| clear A/V payload | buffer/linear block、Codec 生命周期 | 回调后过早回收或重复使用 |
| secure A/V payload | 安全内存 handle、descrambler、Codec 安全路径 | 意外映射成普通应用明文 buffer |
| passthrough | 硬件数据路径、同步标识、下游配置 | 软件 buffer 正常但硬件路由未成立 |
| DVR | filter attachment、FD、buffer 水位与停止/flush | 容量不足、回放停止后仍占资源 |

MediaEvent 交付的 A/V handle 在消费完成后才释放；callback 发生不等于 Codec 已消费完数据。
DATA_READY、DATA_OVERFLOW、LOW_WATER/HIGH_WATER 等状态有不同含义，overflow 不是可忽略的 UI 提示。
增加 callback executor 数量不能修复无人消费的 FMQ，也不能解除安全句柄的生命周期要求。[数据流][tuner]

TRM 仲裁有限的 frontend、LNB、CAS session 和输入设备，按 use case、前台状态、priority/nice 等规则决定回收。
resource-lost callback 表示客户端要停止依赖旧资源并释放/重建，不能继续拿旧 frontend handle tune。
扫描、直播、录制并发是否可行取决于可共享 frontend/demux、节目复用与产品硬件；一个电视应用创建了两个 Tuner 对象并不等于有两个物理 tuner。
厂商可配置 use-case 优先级，但这不自动允许所有应用覆盖资源所有者。[资源管理][tuner]

## CAS：授权、会话与安全媒体路径

Media CAS 通过公共 Java API/native plugin 框架连接不同 CA 系统；TIS 从广播 PSI/CA descriptor 获得 CA system ID、ECM/EMM 等信息。
CAS plugin 处理授权材料并向 descrambler 提供控制密钥或 token；Tuner 再把解扰结果交给后续媒体链。
CAS session、调谐频道、A/V PID、密钥与安全策略要关联，换台后的旧 ECM、旧 session 或过期 key 不应继续作用于新内容。[CAS][cas]

CA descriptor 指出系统与私有信息；ECM 包含控制字相关材料，EMM 提供相应授权/密钥信息。
EMM 可在带内到达，也可由 plugin 通过自身网络协议获得；“没有网络请求”不一定表示 CAS 没工作。
Media CAS 统一接口但不标准化每家 TEE/key ladder 的实现，支持某个 CA system ID 也不证明完成内容商的认证。
TEE、secure memory、secure decoder、secure display/输出保护属于连续路径，不能只由 `MediaCas` 对象创建成功推导。[CAS 架构][cas]

旧软件 extractor 路径需特别注意明文边界：为解析 PES header 可能请求少量 clear data，plugin 必须检查负载确实是允许的 header/stream type。
视频要求 secure decoder、音频允许非安全解码时，若共享可被音频路径调用的密钥会话，可能泄漏视频内容。
官方因此不推荐相应软件配置；不能通过“为了兼容”把全部 secure stream 解扰成普通 buffer。[CAS 软件限制][cas]

调谐成功而画面黑屏时，应分开验证 RF lock、demux PID/filter、CAS session/entitlement、descrambler、Codec 与输出保护。
无权内容应保持权限失败或受保护状态，不能把授权失败悄悄降为明文输出以证明播放链通畅。
这里的 CAS 与 OTT 常见的 DRM/license 流程有不同接口与数据来源，不能把一个 DRM demo 的成功当作 CAS 集成证据。

## HDMI-CEC 控制路径与电源

HdmiControlService 与 TV Input、Audio、Power 服务协作，经 HDMI-CEC HAL 收发控制消息、hotplug 和地址/版本信息。
HDMI 视频数据、CEC 控制总线与 ARC 音频有不同链路；HDMI 有画面不能证明遥控转发或系统音频控制正常。
logical device type 与 physical address 也不同；电视 sink、playback source、audio system 承担不同角色。[CEC][cec]

产品需声明 HDMI-CEC feature、正确 device type，并让厂商独立 CEC controller 与 HdmiControlService 避免同时争夺协议状态。
厂商命令扩展仍需保持标准命令行为，不能因为需要私有功能就让两个 controller 并行响应。
对服务的 privileged API 访问与 TV 遥控按键的应用输入权限不同；普通应用不能据“可播放视频”推定可以控制所有 HDMI 设备。[CEC 集成][cec]

Android 12 起播放设备的唤醒通常尝试 One Touch Play，使 TV 唤醒并成为 active source；休眠时是否请求关 TV 还与当前 active source/配置相关。
不能把任何 source 的睡眠都当作必须关闭整套家庭影院，也不能把 CEC wake 消息回调等同于面板已经亮屏。
standby 时可能由底层微处理器接管 CEC，切换与恢复需保留逻辑地址和设备状态，不能只测 Android 完全启动后的情形。
CEC 2.0 需要设备和用户配置以及 HAL 报告共同支持，版本字段为 2.0 不单独证明互操作成功。[CEC 版本与电源][cec]

## Multimedia tunneling 的同步基准

tunnel mode 让压缩视频经硬件 decoder 直接到 display，呈现时机由底层比较 PTS 与同步时钟决定。
点播 Android 5+ 常用同一 audioSessionId 关联 AudioTrack/MediaCodec；Android 11+ 直播可用 Tuner 的 avSyncHwId 关联 PCR/STC。
这两个 ID 和时钟来源不能混用，墙上 UTC 更不能作为逐帧同步基准。[Tunneling][tunnel]

音频时钟驱动的视频可能在 AudioTrack 未开始或 underrun 时停住；静音音量不代表可以停止送音频 buffer。
seek、flush、首帧 peek、速度变化和 PTS 不连续都有对应行为，画面停顿未必是 decoder 性能问题。
反过来，视频平滑而声音滞后也可能是错误的同步 ID、时钟不前进或音频管线 delay。
tunneling 绕过部分 Android 图形路径，因此 GPU blur、任意圆角/PiP 效果能力可能受限，不能假定普通 GPU 合成效果完全保留。[Tunneling 行为][tunnel]

## TV 安全、家长控制与参考应用

家长控制由 TV App、TV Input Manager、Provider 与 TV Input 共同执行。
program 的 `COLUMN_CONTENT_RATING` 主要用于展示，不会自行阻止播放；TV Input 需在节目/频道/评级设置改变时向 manager 检查阻止状态并通知 content blocked/allowed。
频道 COLUMN_LOCKED 和评级规则要分别处理，PIN 临时解锁也不能无意变成永久全局解除。
官方 TIF 把家长控制列为必需并由 CTS Verifier 覆盖，实际产品还需按对应版本 CDD 的设备类型和功能条件复核。[家长控制][tif]

TV Provider 包隔离、TV Input hardware 权限、CEC privileged 访问与 CAS secure path 保护不同资产。
Verified Boot/OTA、应用权限、SELinux、debug 暴露与系统组件更新仍适用通用 Android 安全机制；“大屏固定在家中”不使网络输入、广播数据或 HDMI 设备成为可信输入。
EPG、私有 CA 数据和 vendor command 都需格式/长度/状态检查；某个广播源或外接设备断开时应回收会话与受保护资源。
安全基础机制见 [security.md](security.md)，兼容条件见 [compatibility.md](compatibility.md)。

Reference Live TV 是系统 TV App 的样例，需要其它 TIF 组件，不能独立安装后宣称完成 TV 设备集成。
定制包需为持有 CUSTOMIZE_TV_APP 权限的预装系统应用，reference TV app 只选择一个定制包。
资源可控制 time-shifting 等选项，Activity 的指定 manifest intent category 可增加选项行/自定义行；扩展 Activity 承担具体画质等业务。
这类 UI 定制不改变硬件和访问控制职责。
官方 reference app 表中的 target/min API 反映所列历史分支，不能作为当前 TV 产品 target SDK 的一般建议。
直接运行旧示例中的 provider clear、remount 或安装命令也不是理解机制的前提。[参考应用][reference] [定制][customize]

## 验证证据应覆盖每条实际链路

| 要证明的机制 | 有区分力的证据 | 单独不足的证据 |
|---|---|---|
| TIF 会话与 Provider 隔离 | input/session、包归属、换台/Surface/断开、第三方输入权限 | EPG 能显示 |
| Tuner 硬件及仲裁 | frontend lock、filter 状态、资源 owner/reclaim、录制并发 | 一个直播频道能播放 |
| CAS 与安全媒体 | CA ID/session、ECM/EMM、secure handle、decoder/输出保护 | plugin 能被枚举 |
| CEC 互操作 | 拓扑/地址/角色、active source、standby/wake、音频系统与拔插 | HAL send 返回成功 |
| tunneling A/V sync | session/avSync ID、PTS/时钟、underrun/seek/速度变化 | 短视频视觉上同步 |
| 家长控制 | 动态评级改变、设置改变、PIN/解锁、受阻内容不泄漏 | UI 中显示一个锁图标 |

CTS 与 CTS Verifier 提供兼容行为证据，HAL/VTS 测试提供接口行为证据，reference TV app 的功能/jank 测试提供特定 UI/性能证据。
测试集合应匹配目标分支和已声明 feature；不能用某个历史参考应用的单元测试代替设备兼容要求。
地区广播、CEC/内容商认证、真实 RF 接收质量、硬件 secure path 与长时间录制仍需要对应设备/标准证据，模拟输入只覆盖模拟路径。

## Devices 其它入口的归属

官方 Devices 的 Enterprise、Cuttlefish、TV 是三个独立导航 book，不能把 TV 一页或虚拟设备概览算作全部 Devices 已深入覆盖。

| 导航入口 | 已有知识归属 | 仍需按具体问题展开的深度 |
|---|---|---|
| Enterprise / Device management | [enterprise-device-policy.md](enterprise-device-policy.md) | custom user types、enterprise telephony、OTA 与完整多用户测试细节 |
| Cuttlefish | [devices-virtualization.md](devices-virtualization.md)、[test-harness-infrastructure.md](test-harness-infrastructure.md) | snapshot/reset 状态语义、GPU/WebRTC 后端、multi-tenancy、hybrid/on-prem 部署与虚拟外设细节 |
| TV | 本页 | 每种 broadcast frontend/filter 配置、CA 私有协议、CEC 全消息状态机与产品认证 |

AVF 属于 Core/Virtualization 的隔离执行主题，Automotive virtualization 有自己的 VirtIO 车载集成主题，两者不能仅因包含 VM 字样合并为 Cuttlefish 能力。
Watch 等形态的兼容要求可从对应 CDD 判断，本次 Devices 侧边栏快照没有独立 Watch 导航 book，不能凭名称补造已读官方栏目。

## 官方依据

[tif]: https://source.android.com/docs/devices/tv
[tuner]: https://source.android.com/docs/devices/tv/tuner-framework
[cas]: https://source.android.com/docs/devices/tv/media-cas
[cec]: https://source.android.com/docs/devices/tv/hdmi-cec
[tunnel]: https://source.android.com/docs/devices/tv/multimedia-tunneling
[reference]: https://source.android.com/docs/devices/tv/reference-tv-app
[customize]: https://source.android.com/docs/devices/tv/customize-tv-app
