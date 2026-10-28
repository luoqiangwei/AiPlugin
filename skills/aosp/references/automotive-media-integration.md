# AAOS 媒体集成：音区、车辆相机与广播收音机

核实日期：2026-10-28。音频、Camera/EVS 与 Radio 都跨应用、Framework、HAL 和硬件，但使用不同的状态与资源所有权。
通用音频与相机管线分别见 [audio-framework-policy.md](audio-framework-policy.md)、[camera-stream-sessions.md](camera-stream-sessions.md)。
汽车用户/显示关系见 [automotive-occupants-ui.md](automotive-occupants-ui.md)，电源与 VHAL 见 [automotive-vehicle-services.md](automotive-vehicle-services.md)。

## 音区是路由、焦点与音量的共同作用域

CarAudioService 使用动态 AudioPolicy，把某用户和 AudioAttributes 对应到音区内的 bus 输出设备。
`car_audio_configuration.xml` 定义 zone、zone config、volume group、设备 address 和 context；这些地址要与核心 `audio_policy_configuration.xml` 和 Audio HAL 端口一致。
occupant zone 到用户的分配改变时，旧用户的 device affinity 需移除，再赋给新用户相应设备。
因此乘客换用户后声音仍在原座位，可能是 affinity 生命期错误，不只是媒体应用没有刷新。[多音区][zones]

| 对象 | 控制范围 | 不能据此推断 |
|---|---|---|
| audio zone | 独立输出、焦点、音量管理 | 必然与某一个扬声器一一对应 |
| zone config | 同一乘员区的一组可选设备 | 所有配置可同时作为该用户默认输出 |
| volume group | 同组设备一起调 gain | 所有设备有相同硬件增益范围 |
| CarAudioContext/AudioAttributes | 声音用途与路由/交互分类 | App 包名本身决定安全优先级 |
| audio device affinity | 用户可路由的设备集合 | 可绕过 Audio HAL 的并发硬件限制 |

Android 14 的动态 zone config 支持后排在头枕扬声器/耳机等配置之间切换，一次只为该用户选择一个配置。
primary zone audio cast 与 passenger audio mirror 则是其它机制：向主舱播放需相应请求/接受流程；mirror 使用专用 mirror 设备和 HAL 复制，同时协调参与者焦点。
任意把两用户输出连接到同一 sink，不能获得这些机制的授权、焦点与回收语义。
无线耳机/USB 输出能否独立并发仍由底层设备与硬件路由支持决定。[音区路由][zones]

## Focus 决定交互，实际混音与 ducking 依赖路径

焦点请求应使用与真实播放一致的 AudioAttributes。AAOS 按新请求与已有 holder 的 context 矩阵决定 exclusive、reject 或 concurrent。
有多个 holder 时，以最保守的交互结果决定；不能只比较最近一个 holder。
并发通常要求新请求为 `GAIN_TRANSIENT_MAY_DUCK`，已有 holder 不要求 pause-on-duck，也不选择接收 duck 事件；具体条件按分支核实。[焦点][focus]

焦点是逻辑协调，不保证任意应用都请求/遵守焦点，也不应被当成安全声音的唯一硬件控制。
若媒体与导航已经在 Android 混成同一物理流，HAL 不能再分别降低媒体而保留导航。
独立 bus 输出使 HAL 可以在混音前 duck 某一路，或把导航路由到司机扬声器；因此焦点授予正确但导航听不清，仍可能是 bus/混音层设计错误。
Audio Control HAL 接收 duck/mute 设备列表，实际增益和硬件执行需能关联到同一设备地址。[焦点][focus] [Audio Control HAL][control-hal]

Android 11 加入 delayable focus，适合非 transient 请求：返回 DELAYED 时应等待 callback，不能立即播放；放弃/被替换需终止等待。
瞬时提示若在很久以后才获焦点可能已经失去语义，所以不能把延迟焦点当作所有音效的默认重试队列。
HAL 外部声音可通过 Audio Control HAL 请求/释放焦点；这与 Android 活跃 AudioTrack 的检测不同。
HAL 焦点在返回异步结果前后的播放约束还要看接口契约，不能用应用焦点规则简单推断车辆外部警示的停止条件。[焦点][focus] [HAL 焦点][control-hal]

## 音量、增益回报与 OEM 插件

AAOS 常将音量应用在 HAL 以下硬件放大器，`config_useFixedVolume` 用来避免普通 stream 软件音量破坏该模型。
Car volume group 的步长要一致；组范围由设备增益配置构造，单设备超出自身范围时会截到自身 min/max。
所以 UI index 改变不保证每个设备产生同样幅度变化，音量 index、毫贝 gain 与硬件感知响度也不是同一量。
group ID 是每个 zone 内按配置顺序产生的局部标识，不能只用 groupId 全局缓存；未带 zone 的旧 API 常默认主音区。[音量][volume]

音量按关联用户/音区持久化；换 zone、换用户、动态 config 与硬件回报都可能更新当前有效值。
Android 12 的 volume-group muting 需配置开关与 AIDL Audio Control HAL 配套，否则静音可能仍是 master mute。
硬件增益变化回调可反映限制/静音等原因，不能收到一个回报就假定用户主动改了音量并永久覆盖偏好。
Android 15 增加最小/最大 activation volume，需启用对应 flag、配置触发类型与范围；它限制指定激活时机，不是所有时间强制把用户音量夹回同一默认值。[音量][volume] [HAL][control-hal]

Android 14 起 OEM car audio plugin 可定制 focus、ducking、volume/mute，并在独立进程运行。
CarService 将当前 holder/loser 等必要状态交给插件做判断；插件不会自动继承 CarService 的权限。
评估是阻塞 IPC，应避免插件反向同步调用 CarAudioService 形成等待环，插件超时/不可用也应有明确结果。
若另注册一套焦点策略绕过 CarAudioService，插件拿到的状态会不完整；这比“插件返回值正确”更早破坏一致性。[OEM 插件][plugin]

CAP engine 与 OEM plugin 是不同层：CAP 用策略/criteria 管核心路由与音量，plugin 提供汽车服务决策钩子。
Android 14 CAP 主要用于 primary zone，Android 16 扩展至所有 zone；`useCoreAudioRouting` 与 `useCoreAudioVolume` 可分别控制。
Android 16 的 Audio HAL AIDL 可直接提供 CAP 配置；不能假设 Framework 仍一定从旧 vendor XML 路径解析全部内容。
迁移需同时核对 product strategy、volume group、criteria、settings 和 car audio flags，不能混合两代 schema 后只看 XML 可解析。[CAP][cap]

## 音频电源与输入资源

电源策略禁用 AUDIO 时，CarAudioService 保留 critical EMERGENCY/SAFETY 的焦点，放弃/拒绝其它焦点，并按启用的 group muting 能力静音非关键组。
关键与非关键 context 若共组，会影响选择性静音的效果，因此 volume group 结构本身也是电源行为的一部分。[音频电源][audio-power]

应用未释放输入/输出流时，活跃硬件可阻止 STR/STD。
官方建议 Audio HAL 在 suspend 准备阶段释放硬件输出并丢弃输入到 HAL 的播放数据，释放硬件输入并向 Framework 返回静音，resume 后恢复。
这里的“静音数据”描述转换期间和流接口的行为；CPU 实际 suspend 后不会继续执行应用代码。
焦点清理、逻辑 mute 与硬件真正 idle 应分别验证；仅在 Settings 把音量设为零不能证明音频不再阻止休眠。[HAL suspend][suspend]

多通道麦克风使用 channel index mask，普通 positional mask 的语义与数量不同；同时设置时不应假定 index mask 会优先。
AudioSource 影响处理链，VOICE_RECOGNITION 与通话/普通录音不能随意互换；并发采集还受隐私限制。
BUS/FM_TUNER 输入可能需要显式 preferred device；硬件 patch 绕过软件 mixer 时也绕过部分媒体键/软件混音能力。
`HwAudioSource` 通过 device-to-mixer 软件 patch 将输入纳入 Android 播放/路由，但仍需匹配 HAL patch 与输入流实现。[麦克风][microphone] [输入播放][hw-source]

## EVS：采集、渲染与 buffer 所有权

EVS 原为早期倒车/环视等车辆相机设计，最小化对完整 Android 启动服务的依赖。
EVS app 向 manager 请求帧、完成变换/拼接/渲染，再提交显示；manager/HAL/驱动负责设备与资源。
倒车摄像头、surround view 多相机和普通 Camera2 视频会议有不同启动/权限/显示责任，不能只按“都是 camera”互相替换。[相机总览][camera] [EVS HAL][evs-hal]

采集帧来自 HAL 所有的有限 buffer 池。客户端借用后要 `doneWithFrame`/对应版本方法归还；达到 frames-in-flight 上限而未归还时可跳帧。
增加 buffer 数量只能增加可同时持有的数量，不能修复没有归还的泄漏，也会增加延迟/内存。
显示 buffer 则由 `getTargetBuffer` 取得，必须通过 `returnTargetBufferForDisplay` 返回；提交后客户端不应继续写入。
camera buffer 与 display buffer 有不同来源和归还 API，不能因为都可导入 EGLImage 就交换句柄归属。[EVS HAL][evs-hal]

EVS 1.1 用 HardwareBuffer/BufferDesc 对齐 graphics 元数据，包含 bufferId、physical deviceId、timestamp 与 frame metadata。
EGL/Gralloc 的 handle、format、stride、usage 以及实际 GPU 完成时机需一致；bufferId 是不透明标识，不能当成永久地址或跨设备唯一身份。
`stopVideoStream` 后流水线仍可交付尾帧，这些帧仍要归还；收到 STREAM_STOPPED 后才不应有后续帧。
FRAME_DROPPED、TIMEOUT、PARAMETER_CHANGED 等事件能区分无新画面、采集超时与控制变化，不能只凭最后一帧截图判断流还活着。[事件与帧][events]

HAL 直接设备接口中的重新 open 可使旧实例失去所有权，旧句柄收到 OWNERSHIP_LOST 后不能再改变设备状态。
实际多客户端策略可能由 manager 仲裁；不能把一次 native open 的成功推广为所有 client 同时拥有控制权。
显示可见请求与实际 display state 不同，关闭前仍需归还尚未提交的 target buffer。
Automotive Display Proxy 通过 producer/ANativeWindow 让 vendor 侧使用 SurfaceFlinger/EGL；它依赖相应服务就绪，不能单靠样例路径证明任意早期启动显示都满足时限。[所有权][evs-hal] [Display Proxy][proxy]

逻辑多相机需枚举 physical IDs、逻辑多相机 capability 与同步类型。
APPROXIMATE 与 CALIBRATED 表示不同传感器同步条件；把几张相近时间戳图片拼起来不等于硬件曝光同步。
环视还涉及标定、畸变、帧时序与降级显示，官方 logical camera 枚举支持不能单独证明拼接质量或安全要求。[多相机][multi-camera]

## Camera2 迁移改变资源与权限模型

当前官方文档计划淘汰 EVS 相机 API；其中 EVS HIDL 1.0/1.1 已在 Android 14 废弃。
“计划淘汰”不能写成所有 EVS AIDL/CarEvsService 已在所有产品移除，也不能假定承诺中的兼容 shim 已可在目标分支使用。[迁移范围][camera-overview]

| EVS 习惯 | Camera2 对应判断 | 迁移风险 |
|---|---|---|
| open 同时配置单流 | open device 后建立 capture session 与输出 surface | 设备开了但 session/stream 尚未成立 |
| 动态 setMaxFramesInFlight | ImageReader 的 maxImages 在初始化/session 设计时确定 | 继续持有 Image 导致生产者耗尽 |
| pause/resume stream | stopRepeating / 重新提交 repeating request | 在途结果仍需处理 |
| 设参数/主控角色 | CaptureRequest；shared primary 由服务优先级决定 | 旧 master 假设继续越权修改 |
| EVS display | Surface/Display API 或早期硬件 buffer 显示集成 | 相机早可用而 UI/合成尚未就绪 |

Camera2 shared mode 在 Android 16+ 提供 system camera 多客户端访问：最高优先级为 primary，可创建请求和改参数；secondary 只启停指定 surface 的 streaming。
`shared_session_config.xml` 及传入 session 配置必须匹配，shared mode 不等于所有第三方应用可无限共享相机。
更高优先级的 exclusive 客户端可能驱逐 shared 客户端；断开、优先级变化和重建不能留着旧 capture request。[Shared camera][shared] [迁移][migration]

常规 Camera2 需要 CAMERA；system camera 额外需要 SYSTEM_CAMERA。
跨前台用户切换运行的 user 0 相机服务还涉及 CAMERA_HEADLESS_SYSTEM_USER；隐私开关例外有 CAMERA_PRIVACY_ALLOWLIST 的专门范围。
早期外部 system camera 访问是特权 EVS UID 等条件下的路径，不是任意持有 CAMERA 的 APK 可在开机前访问所有摄像头。
迁移的启动、用户切换、遮挡和隐私行为应分别确认，不能把旧 EVS 独立显示的保证自动带到普通 Activity。[迁移权限与早期相机][migration]

Dashcam 还分 Service（流/录制/触发）、Manager API 与参考 App，需相应 system/Camera2 权限、存储空间和生命周期。
倒车预览可用不能证明持续录制可用；录制权限、容量耗尽、文件保留、换用户和 Flash 写入预算属于额外机制。[Dashcam][dashcam]

## Broadcast Radio：调谐控制与音频传输分开

Broadcast radio HAL 提供 AM/FM、DAB 等模块能力和 tune/seek/step、program list、announcement 的控制/回调。
HIDL 2.0 用 tuner session，新的 AIDL 将这些方法移到 `IBroadcastRadio` 并使用 tuner callback；迁移不是逐字替换 `scan` 方法名。
tune 接受请求和异步成功/失败不同；节目列表以 chunk 更新，应保留 purge/complete 与项标识语义，不能把一个增量 chunk 当成全量目录。[广播 HAL][radio-hal]

ProgramSelector 表达调谐身份，频率、节目 ID 和可见名称不是同一主键。
收藏项可能离开接收范围仍存在，band channels 是当前地区物理可调频点，programs 是扫描/硬件提供的可用节目；三种列表不能互相代替。
antenna 状态、tune result、program metadata 与实际音频听得到应分别观察。
Radio HAL 的控制链不负责替代 Audio HAL 的流、patch、音量和 focus 集成。[广播 HAL][radio-hal] [控制][radio-control]

Radio App 用 MediaSession/MediaBrowser 暴露统一控制，play/stop 常映射 unmute/mute；只有确有缓存/time-shift 能力时 pause 才能模拟广播暂停。
`mediaId` 在会话中需要稳定唯一，URI 可表达 ProgramSelector，但频率变化可能改变 URI。
next/previous 的语义取决于当前 favorites/programs/band 上下文；不能统一当作“频率加一个步长”。
通用搜索由客户端选择 MediaBrowser 结果再发明确播放目标，不能假定 reference Radio 用自由字符串搜索即可满足所有语音命令。[Radio 媒体契约][radio-control]

汽车 Media UI 通过 MediaSession/Browser 选择与展示媒体源；登录/设置可由来源应用提供，同时要响应 UXR。
deep link 需来源 app trampoline 解码，再把 component/mediaId/query 交给支持相应 intent 版本的 CarMediaApp；不能只添加 URL filter 就认为目的页面已打开。
CAL 模板媒体是另一种 UI 集成：Car-apps-release-17、templates_host.media、后台音频 feature、Launcher PACKAGE_CHANGED 与系统媒体卡需协同，不能由 Android SDK 数字推断支持。[Media 组件][media] [深链][media-links] [CAL 媒体][cal-media]

## 失效证据与剩余深度

| 现象 | 需对齐的证据 | 常见误推 |
|---|---|---|
| 导航压不低媒体 | context/focus、bus 地址、混音位置、duck 回调/实际 gain | 请求 MAY_DUCK 就一定硬件 duck |
| 某座位音量 UI 正常但无声 | user affinity、zone config、group mute、HAL port/amp | 修播放器音量即可 |
| 熄屏后不能 suspend | 活跃 input/output、HAL deactivation、内核唤醒源 | 没有可听声音就没有音频资源 |
| EVS 几帧后冻结 | buffer 借还、frames-in-flight、STREAM_STOPPED/timeout、GPU 完成 | 多分配 buffer 即可修复 |
| Camera2 多客户端突然断开 | shared config、primary/secondary、exclusive 抢占、权限 | shared camera 永不被抢占 |
| Radio 显示正确但无声音 | tune callback、program、Audio HAL patch、focus/mute | metadata 正确即 RF/音频链正常 |

本文不枚举每个 CarAudioContext 交互格、HAL gain reason、广播地区标准或 EVS/Camera2 全参数。
芯片混音拓扑、镜头标定、法规启动时限和产品安全降级需结合目标硬件论证；模拟图像和合成音频只证明相应软件路径。

## 官方依据

[zones]: https://source.android.com/docs/automotive/audio/audio-multizone-routing
[focus]: https://source.android.com/docs/automotive/audio/audio-focus
[volume]: https://source.android.com/docs/automotive/audio/volume-management
[control-hal]: https://source.android.com/docs/automotive/audio/audio-control-hal
[plugin]: https://source.android.com/docs/automotive/audio/car-audio-plugin
[cap]: https://source.android.com/docs/automotive/audio/configurable-audio-policy-engine
[audio-power]: https://source.android.com/docs/automotive/audio/audio-power-management
[suspend]: https://source.android.com/docs/automotive/audio/hal-suspend
[microphone]: https://source.android.com/docs/automotive/audio/microphone-input
[hw-source]: https://source.android.com/docs/automotive/audio/optional-player
[camera]: https://source.android.com/docs/automotive/camera
[evs-hal]: https://source.android.com/docs/automotive/camera/evs/camera-hal
[events]: https://source.android.com/docs/automotive/camera/evs/event_frame
[proxy]: https://source.android.com/docs/automotive/camera/evs/display_proxy
[multi-camera]: https://source.android.com/docs/automotive/camera/evs/multi_camera
[camera-overview]: https://source.android.com/docs/automotive/camera/acs/overview
[shared]: https://source.android.com/docs/automotive/camera/acs/multi-client-cameras
[migration]: https://source.android.com/docs/automotive/camera/acs/camera2-migration
[dashcam]: https://source.android.com/docs/automotive/hmi/dashcam
[radio-hal]: https://source.android.com/docs/automotive/radio/broadcast-radio-hal
[radio-control]: https://source.android.com/docs/automotive/radio/radio-control-implementation
[media]: https://source.android.com/docs/automotive/hmi/media/technical_details
[media-links]: https://source.android.com/docs/automotive/hmi/media/media-deep-links
[cal-media]: https://source.android.com/docs/automotive/hmi/aosp_host/media-cal
