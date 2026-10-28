# 媒体、相机与音频：请求、缓冲区和受控输出

相机组合与会话细节见[相机流与会话](camera-stream-sessions.md)。音频的策略、效果、录音仲裁和空间音频见[音频策略与 Framework](audio-framework-policy.md)，FAST/MMAP、USB/MIDI 与延迟量测见[音频性能与 I/O](audio-performance-io.md)。

成像/扩展/外接相机见[相机扩展](camera-advanced-features.md)，Codec2/转码/编码/安全媒体见[媒体管线](media-pipeline-codecs.md)。

本页用于拍照/录像、编解码、DRM、播放/录音和音频路由问题。核实日期：2026-10-28。
先确认目标分支、HAL 版本、芯片/驱动、媒体模块版本、具体内容及输出设备；能力表与日志必须对应同一组合。
源码位置是定位起点；供应商组件、APEX 更新和旧接口共存时，实际加载的实现比目录名更有判断价值。

## 跨领域共同机制

- 控制 API 配置一条异步数据管线；请求已接受，不代表帧已生成、声音已输出或受保护内容已可播放。
- 每个 buffer 都有当前所有者、使用条件和归还责任；引用存在不等于可以立即读写。
- buffer handle、像素/采样格式、stride、dataspace、时间戳和 fence 的含义不能互相替代。
- 延迟来自排队、调度、硬件执行、转换及消费；优化单次函数耗时未必改善端到端延迟。
- session 重建、设备断开、服务死亡及 flush 后的晚到回调必须有可判定的生命周期。
- 权限、隐私开关、录制归属和保护内容要求属于管线契约，不能用“先让画面/声音出来”绕过。

## Camera HAL3：一个请求对应一组结果

主要路径为 Camera2/API → CameraService → provider/device/session HAL → sensor/ISP → metadata 与目标 surface 的图像 buffer。[1][][2][]
HAL3 将拍摄参数封装在请求中，管线可同时承载多个请求；结果包含捕获事实和对应输出，不只是一个 JPEG 回调。
3A 会依据模式控制曝光、对焦和白平衡；请求中的手动参数是否生效必须结合模式与结果 metadata 判断。
静态 characteristics 描述能力，request 表达意图，result 描述本次实际结果；不能用静态声明证明执行正确。

- 枚举/open、configure streams、提交请求、接收结果、flush/close 是不同状态转换。
- frame/request 身份、stream 身份和时间戳需足以关联结果；核对接口对 partial metadata、顺序及错误通知的精确约束。
- 不要求 metadata 和所有图像在同一次 callback 到齐；但每个接受的请求与其 buffer 必须按契约收敛。
- 分辨率、格式、usage、并发组合和带宽共同决定可配置性；分别支持两个 stream 不证明同时支持该组合。
- reconfigure 时旧 stream/buffer 的引用寿命要清楚，不能因 ID 复用误归还到新会话。
- close/flush 不应留下永久在途请求、悬空 fence 或未归还 buffer；错误帧也需完成对应错误契约。

Android 8 将 Camera HAL 转为 HIDL 稳定接口；Android 13 起框架支持 AIDL，新相机 HAL 接口功能开发转向 AIDL。[1][]
升级设备可能仍使用 HIDL；不要把“运行 Android 13+”误读为所有设备已迁移 AIDL。
常见源码起点是 `frameworks/av/services/camera`、`hardware/interfaces/camera` 和产品 provider；名称与冻结接口查目标树。

## Buffer 管理：容量、吞吐和内存的取舍

Android 10 引入可选的 HAL3 buffer management API，使请求排队与输出 buffer 分配解耦。[3][]
实现可在接近使用时请求 buffer 节约内存，也可缓存少量 buffer 降低分配抖动；没有对所有场景最优的单一策略。
达到 `maxBuffers`、消费者长持有、流断开与 reconfigure 都会改变 buffer 获取结果。

- 异步请求多不代表可以无限接受；HAL 需要与实际管线容量匹配的背压。
- `requestStreamBuffers` 的等待可能来自消费端持有，不应立即归因为 sensor 或 ISP 卡死。
- 正常 result 归还和多余 buffer 归还有不同接口语义；核对归属，防止重复归还或泄漏。
- `signalStreamFlush` 与配置计数/代次要配合，避免 flush 旧流错误地清空新会话。
- 等待 acquire fence 后才访问，按接口传递 release fence；不能用固定 sleep 代替同步完成条件。
- 预览流畅不证明 JPEG、RAW、录像、多摄、后台退出和错误恢复都满足契约。

## Media/Codec2：拆开容器、码流和呈现

解复用/解析提供压缩样本，codec 处理码流，渲染端消费音频或图像；容器能打开不证明 codec 支持内部 profile/level。[4][]
Media 与软件 Codec2 组件可独立更新；软件 codec、vendor 硬件 codec 和旧 OMX 组件不能视为同一个实现。
确定实际选中的 component、媒体类型、profile/level、分辨率、色彩和安全要求后再定位失败层。

Codec2 的 component 接口管理状态、配置及 `C2Work` 队列，完成与错误通过 listener 返回。[5][]
`queue_nb` 成功只说明排队成功，后续 work 仍可能失败；`drain_nb` 的提交也不表示全部输出已返回。
`start/stop/reset/release` 有各自状态和资源契约；不能在回调与调用线程间无序切换生命周期。

- EOS、flush、seek、格式变化和取消都应有明确边界，旧输出不能混入新时间线。
- buffer pool、图形内存映射和格式转换可能造成“codec慢”；先查队列深度与消费速度。
- 零拷贝减少某些复制，不免除所有权、同步或像素布局协商。
- 支持列表与真实实现必须一致；不通过仅调整 XML/排名把不支持的编码能力报告为可用。
- 测试包含截断/损坏码流、动态格式、资源不足和重复重建，不只播放单个标准样本。

## DRM：授权、解密与安全输出必须连起来

MediaDrm 管理 DRM session/许可证，MediaCrypto 关联解密；框架通过已注册厂商 plugin 的 Drm/Crypto HAL 处理对应方案。[6][]
UUID 支持、MIME 支持、安全级别、密钥可用、解密成功和最终安全显示是不同判断。
Android 13 及以后首发设备的 DRM binderized HAL 要使用 AIDL；升级设备和具体 plugin 仍查产品契约。

- DRM session 需要关闭与服务死亡恢复；密钥过期、provisioning 和输出限制分别处理。
- 许可证获得成功不能推出 secure decoder、受保护 buffer、显示链或内容策略已满足。
- 不能把受保护内容复制到普通内存或截图来“验证画面”；应使用允许的受保护链路和状态证据。
- 定位时记录错误阶段、scheme、安全级别、component 和输出路径，不记录密钥或敏感许可内容。
- ClearKey 测试或框架 CTS 不能证明某商业 DRM/内容服务认证与硬件安全级别已经通过。

## Audio：数据面、策略和焦点各有职责

播放/录音客户端经服务与 AudioFlinger、Audio Policy 等协作，再通过 Audio HAL 到 DSP/驱动/设备。
AudioFlinger 处理相应的流、混音及数据面；策略决定适合的设备、profile、路由和音量规则，HAL 提供硬件能力与实际端口。
旧概览中的 mediaserver 描述不能当现代进程事实；以 audioserver、vendor 服务及产品进程图为准。

Android 14 起 Audio HAL 采用 Stable AIDL 开发；Core、Effects、Common 有不同职责，不能用 Effects 解决路由选择。[7][]
AIDL 模式下 APM 从 HAL 获取相应策略配置，旧 vendor XML 配置流程不可无条件套用。
传统配置中的 mix port、device port、route 与 profile 描述可连接拓扑和格式约束；声明路径必须有实际实现。[8][]

- 设备连接、策略选中、patch/stream 建立、样本写入与实际发声应分别验证。
- 蓝牙、USB、HDMI、听筒/扬声器和通话模式的热切换可能改变 profile、采样与缓冲条件。
- “write 返回成功”不保证 speaker 输出非静音；还需检查音量、mute、route、HAL 数据推进及硬件。
- underrun、过大 buffer、重采样、效果链和调度都会影响时延，不能一律靠缩小 buffer 或提高线程优先级。
- 录音需检查输入选择、格式、权限、隐私状态与并发捕获规则；无波形不等于麦克风驱动坏。

AudioAttributes 的 usage 表示用途、content type 表示内容类型；它们参与 focus、routing、volume 与处理策略。[9][]
audio focus 协调播放竞争，不是独占硬件锁，也不是选择某个输出设备的等价操作。[10][]
Android 12 起存在有条件的系统淡出/静音；目标 Android 15+ 应用请求 focus 还有前台/前台服务限制，不能套用旧行为。
处理 focus 拒绝、延迟获得、短暂/永久失去与 duck；异步恢复不能覆盖用户已经停止的播放意图。

## 诊断证据与实施选择

| 现象 | 必须关联的证据 | 先检查的机制 |
|---|---|---|
| 相机黑屏/卡住 | session/stream/frame、在途请求、metadata、buffer/fence 与消费者 | 配置、背压、同步和错误收敛 |
| 播放卡顿/花屏 | 内容参数、选中 codec、work/输出时间线、surface 消费 | 解析、解码、布局与呈现的实际边界 |
| 受保护内容失败 | DRM 阶段、安全级别、secure codec、输出限制 | 授权与安全数据链是否匹配 |
| 无声/路由错误 | attributes/focus、策略设备、patch、stream、HAL 与音量 | 控制面与数据面何处首次分歧 |

修复放在拥有错误状态或资源的层，不靠 app 重试掩盖 HAL 资源泄漏，不靠延长超时掩盖永不完成的请求。
审查回调线程、跨进程锁、buffer/fd 生命周期和服务重启；避免持关键锁同步回调未知客户端。
单测证明状态和转换，CTS/VTS 证明相应契约，真实设备与内容/对端才能补足 ISP、DSP、时延及安全输出证据。
报告设备、HAL、模块、内容和路由组合；没有匹配硬件时不能把“编译通过”写成画质、音质或 DRM 端到端验收。

## 已核实的官方深读入口

1. [Camera HAL：HAL3 与 AIDL/HIDL 版本](https://source.android.com/docs/core/camera/camera3)
2. [Camera HAL subsystem：请求、3A、结果与时序](https://source.android.com/docs/core/camera/camera3_requests_hal)
3. [Camera HAL3 buffer management API](https://source.android.com/docs/core/camera/buffer-management-api)
4. [Media modules：软件 Codec2 与更新边界](https://source.android.com/docs/core/media/media-modules)
5. [Codec2 component 官方接口契约；读取时为 master，实施需切目标分支](https://android.googlesource.com/platform/frameworks/av/+/master/media/codec2/core/include/C2Component.h)
6. [DRM：plugin、DrmHal/CryptoHal 与 AIDL](https://source.android.com/docs/core/media/drm)
7. [AIDL Audio HAL：端口、stream 与策略来源](https://source.android.com/docs/core/audio/aidl-implement)
8. [Audio policy：传统配置拓扑与 profile](https://source.android.com/docs/core/audio/implement-policy)
9. [AudioAttributes：usage、内容与策略](https://source.android.com/docs/core/audio/attributes)
10. [Android 官方 audio focus 行为及版本条件](https://developer.android.com/media/optimize/audio-focus)

[1]: https://source.android.com/docs/core/camera/camera3
[2]: https://source.android.com/docs/core/camera/camera3_requests_hal
[3]: https://source.android.com/docs/core/camera/buffer-management-api
[4]: https://source.android.com/docs/core/media/media-modules
[5]: https://android.googlesource.com/platform/frameworks/av/+/master/media/codec2/core/include/C2Component.h
[6]: https://source.android.com/docs/core/media/drm
[7]: https://source.android.com/docs/core/audio/aidl-implement
[8]: https://source.android.com/docs/core/audio/implement-policy
[9]: https://source.android.com/docs/core/audio/attributes
[10]: https://developer.android.com/media/optimize/audio-focus
