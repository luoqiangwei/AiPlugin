# Camera：能力、组合与会话

相机问题先区分设备枚举、会话配置、逐帧请求、结果元数据和缓冲归还。一个层次接受某个值，不表示其余层次具备相应资源。基础请求/结果与 fence 所有权见[相机与音视频](media-camera-audio.md)。

## 能力声明不是任意组合的承诺

单路 `StreamConfigurationMap` 中的格式、尺寸、帧时长，不能通过排列组合推导多路会话一定可用。ISP 带宽、传感器读出模式、缩放器、编码器和内存共享资源；每路单独成功，组合仍可能失败。

分析配置失败时，同时保留 camera ID、硬件等级/capabilities、每路格式/尺寸/用途、动态范围、物理 ID、会话类型和查询结果。按目标版本的 mandatory stream combinations 核对保证范围；组合查询 API 与设备支持情况也须按版本确认。

推荐流配置是公开配置集的子集，用于表达较有效率的选择。它不能广告公开 map 中不存在的隐藏格式/尺寸，也不降低原有兼容性要求。YUV 格式虽然可用，可能需要额外转换；尺寸/纵横比也会影响功耗和吞吐。推荐配置不是新增硬件能力，更不是所有客户端必须遵守的白名单。[官方流配置说明](https://source.android.com/docs/core/camera/stream-config)

## 逻辑多摄与独立相机并发

| 情况 | 控制关系 | 应验证的边界 |
|---|---|---|
| 逻辑多摄 | 一个逻辑 CameraDevice/会话协调多个物理传感器 | 逻辑能力、物理 ID、同步/标定信息、物理请求键、逻辑与物理流组合 |
| 独立相机并发 | 多个 CameraDevice 分别建立会话，共享平台资源 | 被声明可并发的 ID 集合，以及这些设备各自配置共同组成的组合 |

逻辑多摄通过 capability 和 physical ID 元数据公开关系。客户端通过 `getPhysicalCameraIds()` 定位成员，按物理 ID 配置输出或请求并读取对应结果；可单独控制的参数受 `getAvailablePhysicalCameraRequestKeys()` 限制。一个逻辑请求中的通用控制不自动等于所有物理传感器接受同样的曝光/焦距语义。物理流支持条件、同步类型和标定质量会影响融合或深度算法，不能只看两张图是否出现。

对支持 RAW 的逻辑相机，如果成员传感器尺寸不同，已配置的逻辑 RAW 流不能任意切换到不同尺寸的成员。这保持 RAW 数据与其传感器解释的一致性。需要利用不同成员采集 RAW 时，按物理流及对应元数据处理。文档中的 Android 9 流替换保证有明确版本条件，不能把历史表无条件套到任意新旧设备。[逻辑多摄](https://source.android.com/docs/core/camera/multi-camera)

Android 11 引入独立相机并发能力的标准查询：先查 `getConcurrentCameraIds()`，再用 `isConcurrentSessionConfigurationSupported()` 核对整个配置集合。两个 ID 都能单独打开，或某个逻辑设备拥有两个成员，都不能替代此查询。保证组合与格式替代规则依硬件能力和版本而定；文档中 HIDL provider 版本是对应实现入口，迁移到 AIDL 后应检查对应契约。[并发流](https://source.android.com/docs/core/camera/concurrent-streaming)

## Session parameters 与无副作用的重配置查询

通常请求参数可逐帧变化；有些参数会改变硬件或内部管线，频繁变更会造成停顿。HAL 将这类参数列入 `ANDROID_REQUEST_AVAILABLE_SESSION_KEYS`，它必须是 available request keys 的子集。客户端可以通过初始 session parameters 让 HAL 在配置管线时准备正确状态。没有声明任何 session key 时，不应假定此机制正在发挥作用。

后续 request 仍可能更改这些参数，Framework 会按实现决定重配置。把常用参数随意列为 session key，可能引入本来没有的停顿；漏列高代价参数，也可能把昂贵切换隐藏在逐帧路径中。依据实际硬件切换代价选择，而不是依据“这个参数很重要”。

Android 10 的可选重配置查询用于进一步减少不必要的重配置。以文档中的 HIDL `ICameraDeviceSession@3.5::isReconfigurationRequired` 为例：查询可能提前发生，后续请求还可能被取消。因此 **查询不能改变硬件、当前管线或可见输出**，也不能阻塞正在运行的捕获。返回 false 表示该参数变化不需要完整重配置，不表示可以提前应用该变化。AIDL 分支核对对应方法定义与测试，保留这一查询/执行边界。[会话参数与查询契约](https://source.android.com/docs/core/camera/session-parameters)

可观察证据应包含参数变化前后的请求 frame number、配置序列、查询返回、丢帧/帧时长及实际应用结果。只看查询返回 false，无法证明新参数已经正确生效。

## 动态输出与缓冲共享

共享相机流允许在符合配置约束的情况下动态加入/移除输出 surface。多个消费者共享同一流的缓冲，需要在所有消费者完成后才能复用；慢消费者可能延长缓冲占用，进而造成回压。增加 surface 不等于复制出一条不消耗资源的独立硬件流。

检查共享输出问题时，区分 stream 与 surface，记录消费者的加入/移除时刻、引用/归还状态、fence 与 producer 队列阻塞。消费者断开不能丢失其他消费者尚持有的所有权，移除后的迟到回调也不能使用已释放对象。[单 producer 多 consumer](https://source.android.com/docs/core/camera/singleprod-multiconsum)

## HDR 的像素、传递函数与容器

“支持 HDR”需要拆开：传感器/算法的动态范围、输出像素位深及传递函数、编码格式、文件容器，以及最终显示的 tone mapping。多曝光融合后压成普通 8-bit SDR，与真正输出 10-bit HDR 的管线不同。

Android 13 起的 10-bit camera output 与 `DynamicRangeProfiles` 允许配置相应位深和传递函数；配置支持、流间约束及消费者能力仍须核对。不能只把 buffer format 改成 P010 就宣称预览、录制和播放的端到端 HDR 已完成。[HDR 模式](https://source.android.com/docs/core/camera/hdr-modes)

Android 14 的 Ultra HDR `JPEG_R` 面向兼容 SDR JPEG 的 HDR 静态图，包含用于恢复 HDR 的附加信息。其 HAL 原生输出与 Framework 合成路径有不同代价；软件合成可能增加延迟和资源消耗。它与 HDR 视频的输出/编码契约不同。验证时保留输出文件、元数据、实际走过的 HAL/合成路径及 SDR/HDR 查看结果，不能仅凭文件扩展名判断。[Ultra HDR 实现](https://source.android.com/docs/core/camera/ultra-hdr)

## 错误仍有收尾义务

区分设备级终止错误与单次请求/结果/缓冲错误。文档中的 HIDL 契约明确：通知 `ERROR_DEVICE` 后仅 close 可成功；暂态捕获错误仍须通知相应错误，并通过 capture result 路径完成该完成的结果/缓冲交接。不能因为“已报错”而让缓冲或请求永久悬挂。AIDL 分支应按其状态码和结果契约核对，不照搬 HIDL 枚举。

故障定位应能对齐 request frame number、notify、partial/final metadata、每个 buffer 的返回与 fence，以及 close/flush 的结束状态。图像偶尔恢复不能证明没有遗留请求和队列泄漏。[错误与流管理](https://source.android.com/docs/core/camera/camera3_error_stream)
