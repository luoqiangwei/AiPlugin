# 媒体管线、Codec2 与受控输出

用于容器解析、codec 选择/资源、编码控制、DRM、转码和 Mainline 媒体组件。核实日期：2026-10-28。固定系统与模块版本、实际 component/driver、内容的容器/MIME/profile/level/位深/色彩、输入输出 surface 与安全级别。音频和 Camera 请求基础见 [媒体概览](media-camera-audio.md)，图形内存见 [合成与内存](graphics-composer-memory.md)。

## 一段视频有多个独立契约

容器 sniffer/extractor 选择 → track/sample/CSD → codec 配置和 work → 解码/编码 buffer → 渲染或 mux → 最终消费。容器可识别不表示内部码流可解，codec 注册不证明资源可获得，输出 buffer 回调也不证明已显示。每次 seek、flush、format change、EOS、session 重建都要保持 sample 时间戳、work/frame 身份与配置代次一致。

[Media 首页](https://source.android.com/docs/core/media) 主要说明历史 Stagefright/OMX/plugin 路径，列出的旧设备目录及 `libstagefrighthw.so` 不是所有现代设备的模板。现代软件 Codec2、vendor C2、遗留 OMX 与具体硬件 offload 可以共存，先由 MediaCodecList/日志确认实际选择者，再定位目标实现。

## Extractor 和可更新组件

[Media modules](https://source.android.com/docs/core/media/media-modules) 区分 Media（extractors、MediaSession2、MediaParser）、Media Codecs（可更新软件 Codec2）和 MediaProvider（索引/访问）。系统、APEX、vendor codec 服务有不同版本和依赖边界；更新模块不能假设改变 vendor 硬件能力。

[自定义媒体组件](https://source.android.com/docs/core/media/updatable-media) 中 extractor 有独立 `.so`、sniffer/factory、名称/UUID/版本；framework 加载可用插件，sniff confidence 影响同格式候选的选择。Extractor 的 API version、plugin version 与媒体模块版本分别确认；不要靠提高 confidence 让不完整 parser 抢占全部文件。`dumpsys media.extractor` 可核实实际加载的名称、版本与路径。

Extractor 输出 MIME 必须与 decoder 约定匹配；新增容器可能复用已有 codec，新增码流才需要相应 decoder。媒体扫描的扩展名↔MIME、元数据提取和播放 parser 是不同环节。ModernMediaScanner 不因 extractor 导出扩展名列表就自动完成注册。跨模块插件依赖稳定 API，不能把某版 framework 私有符号当成永久 ABI。

## Codec2：work 归属、配置与状态

`C2ComponentStore` 发现/创建 component，component interface 处理参数能力与配置，`C2Work` 承载异步输入、输出与结果。`queue_nb` 接受 work 不是解码完成；listener 的 work done、错误与格式/配置更新才组成输出事实。`drain`/EOS、flush、stop/reset/release 必须按目标接口状态收敛，不能让旧输出混入新 seek。基础定义见 [Codec2 官方接口](https://android.googlesource.com/platform/frameworks/av/+/master/media/codec2/core/include/C2Component.h)；该链接是移动分支，实施时切目标 revision。

配置 query、supported-values 与 config 返回的修正/拒绝需要保留。输出 format 改变后，消费者必须按新的尺寸、crop、位深/色彩和 buffer layout 解释；像素格式不是 dataspace，CSD 也不是普通展示帧。Surface/graphic block 的 handle、fence、pool 与生命周期不能因“零拷贝”而省略。

`drain_nb`只是记录“处理到此处”的信号，不等待work完成；带EOS与不带EOS的drain对后续输入语义不同。`flush_sm`可立即返回已丢弃work，暂不能立即放弃的work仍须在后续done回调按丢弃语义收回。flush方法返回不能解释为所有引用与回调已消失，客户端需保持相应代次和收尾接收能力。

由这些边界可推导：无输出先区分无输入、码流等待依赖、资源不足、work 未完成、pool/consumer 背压、surface 失效，不能直接增大超时或把所有 work 丢弃。重建能暂时恢复也不排除旧实例/图形内存泄漏。

## 资源管理：能力上限与当下可用资源不同

[OEM resource manager](https://source.android.com/docs/core/media/oem) 要求公开并发实例、可达到的 frame rate 和 secure/nonsecure coexistence 等能力真实；`getMaxSupportedInstances` 是能力信息，不保证任意分辨率、帧率、安全级别混合都可同时获得资源。

[SoC resource manager](https://source.android.com/docs/core/media/soc) 的 legacy OMX 说明强调准确的 insufficient-resources 错误，供资源管理器考虑回收低优先级使用者；priority 是资源规划提示，operating rate 与目标播放帧率不同，例如慢动作输入吞吐远高于成片播放率。对应 C2 参数/错误按目标实现确认，不能把 OMX index 原样塞给 C2。假报一般错误会阻断正确回收，假报成功则使后续 work 挂住。

证据包括申请/回收的 PID/UID、codec 实例、priority/operating rate、分辨率、分配失败与服务死亡；“单实例能播”不足以证明多应用、secure+nonsecure 或相机编码共存。

## 编码统计、低延迟与 RoI

| 机制 | 版本与帧级契约 | 诊断推导 |
|---|---|---|
| [编码统计](https://source.android.com/docs/core/media/encoding-stats) | Android 13 起可输出逐帧 picture type、平均 block QP；QP 按 luma block 统计/取整，全部 skip 时使用规定的无有效 QP 哨兵值 | 不能把哨兵当超低画质，也不能只按输入顺序关联存在重排的输出帧；开启的 statistics level 要与输出字段一致 |
| [低延迟解码](https://source.android.com/docs/core/media/low-latency-media) | Android 11 起 framework 传达模式，decoder 按标准尽快输出而非为额外输入等待，并保持对应唤醒策略 | 不能改变码流固有依赖；不承诺网络、queue 或显示端都低延迟，需测输入到输出和最终呈现，同时看功耗 |
| [RoI](https://source.android.com/docs/core/media/roi) | Android 15 标准化 QP offset map/rect，配置在输入帧入队前生效，未新配时可沿用上一配置；map 与实际编码块间有映射 | 坐标/尺寸、sticky 状态与 frame 关联错误会把质量预算用到错误区域；负 offset 提升目标区域质量，不是无代价增加全帧码率 |

RoI 的标准化 rect/map 与 vendor 配置共存时有明确优先级：标准 rect、标准 map、vendor rect、vendor map；同类多配置不能无序叠加。SoC 不支持的 offset 由契约限幅/尽力处理。启用 feature、当前配置、实际码率/画质结果分别观察；不要把样例 offset 范围当所有编码器支持范围。

## DRM 与媒体硬化

[DRM](https://source.android.com/docs/core/media/drm) 区分 factory 的 scheme UUID/MIME/security-level 支持、DrmPlugin 的 session/license/provisioning、CryptoPlugin 解密和安全输出链。Android 13+ 首发 DRM binderized HAL 采用 AIDL，旧设备/服务仍按 VINTF 和实际实例判断。许可证可用、secure codec 分配成功、受保护 graphic buffer 与输出保护缺一不可；ClearKey/框架测试不等于商业方案 robustness/compliance 通过。

[Media hardening](https://source.android.com/docs/core/media/framework-hardening) 的 Android 7 重构把旧单体 mediaserver 的 parser、codec、DRM、camera/audio 等职责拆到权限更小的进程，借 SELinux/seccomp 限制影响面。文档中的具体哪些 codec 留在 mediaserver 是当时事实，不能作为当前进程布局。跨进程 transport 使用有意义的 native handle/FD，裸指针不能代表远端 buffer；导入、dup、关闭和引用收尾按接口规定，不通过扩大 parser 权限解决共享问题。

损坏容器/码流是跨信任边界输入，sniffer 的长度/偏移/分配、decoder 输出尺寸、受保护内存访问都需要保持边界。诊断用内容参数、错误阶段、匿名事务及 component，不记录密钥/许可敏感数据；不得把 protected 帧复制到普通 CPU 内存来验证黑屏。

## Compatible transcoding 与 MediaProvider

[Compatible media transcoding](https://source.android.com/docs/core/media/media-transcoding) 从 Android 12 在 MediaProvider/FUSE 访问层依据 app capabilities 选择原文件、缓存结果或转码；它不是任意文件/路径的全局转换器。原文支持范围针对相应短视频、本机 camera/DCIM 和主存储等条件，旁路传输、次级卷或资源限制时可能仍返回原始 FD，调用方必须识别实际格式。

`MediaTranscodingService` 管客户端/session/调度，transcoder 用 decoder→可选 HDR-to-SDR filter→encoder；过滤器 query/config、start/stop/reset/release 与 pool 要协作。client 需要最终 filter 的输出 buffer/format，不能返回 decoder 的旧 metadata 冒充已 tone-map 内容。HDR filter 不存在时不会凭请求自动产生正确 SDR。

转码请求、正在执行、完成/取消/失败及缓存命中分别取证，`dumpsys media.transcoding` 能查看当前/历史 session。打开文件耗时可能是首次转码而非存储读慢；重复读取耗时降低也可能来自缓存，不能直接宣称 encoder 加速。原文的时长/并发预算是对应实现的资源策略，测试 override 不应当作出货通用配置。

[MediaProvider](https://source.android.com/docs/core/media/media-provider) 的 MediaStore 索引、文件访问/scoped storage 和敏感 Exif 处理与播放管线不同。扩展名/MIME 注册、audio/video 的 metadata retriever、image 的 Exif、卷是否可索引各有职责；数据库有条目不证明 codec 支持。generation 适用于增量同步，不把文件时间戳当唯一变化证据。更完整存储授权见 [存储与数据](storage-data.md)。

## 新格式及跨域 metadata

[VVC](https://source.android.com/docs/core/media/vvc) 在 Android 17 提供 `video/vvc`、MP4 parser/extractor 与 C2/MediaCodec 解码支持，当前官方说明无 AOSP 软件 decoder、无 VVC 编码，依赖 vendor C2 decoder。声明 XML 是发布已有能力，不能替代实现；移除声明和移除库也是两个动作。

HDR static/dynamic metadata 必须与对应帧传递，不能仅在 codec 创建时读一次。Android 17 的 [HAGC](https://source.android.com/docs/core/display/hagc) 还要求 codec 提取相应 T.35/C2 dynamic metadata，Gralloc 可保存读取，最终 HWC/LUT 消费；单独支持 AV1/HEVC 解码不等于该 HDR metadata 链完整。色彩与 tone map 见 [显示色彩](display-color-transitions.md)。

本页为 core/media 的全部13分支提供机制归属。未逐条展开 C2/OMX 状态表、所有 parser/容器格式、商业 DRM 安全规范、SoC rate-control、转码 filter 全接口、MediaStore 全权限矩阵及 VVC 标准；这些需对应目标接口和协议。已提炼组件、身份、资源/错误与诊断边界，不将未阅读的完整标准宣称为已核验。
