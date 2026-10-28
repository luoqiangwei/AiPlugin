# 相机高级特性：逐帧控制、图像语义与扩展生命周期

用于3A、裁剪/变焦、reprocess、HDR/色域/HEIF、vendor extensions、特殊相机与USB视频。核实日期：2026-10-28。请求/结果基础见 [媒体与相机](media-camera-audio.md)，组合/多摄/并发/session/buffer管理见 [相机流与会话](camera-stream-sessions.md)。先固定 camera ID、physical ID、HAL版本、硬件级别、capabilities、模块/库版本、会话及实际输出，避免仅依据产品相机app可用便宣称公开API具备相同能力。

## Characteristics、request、result 有不同事实等级

[Metadata and controls](https://source.android.com/docs/core/camera/camera3_metadata) 要求静态metadata描述传感器/镜头/色彩等能力，动态result报告本次硬件实际使用的曝光、帧时长、感光度及统计等。硬件限幅/取整后必须回报实际值，不能回显请求冒充执行。RAW解释还依赖sensor特性、黑电平、lens shading和色彩标定，不能仅凭像素文件证明RAW正确。

一个参数出现在available keys中、可在当前模式设置、确实逐帧应用，是不同判断。高代价切换应使用对应session机制而不伪装成无停顿逐帧参数；帧号/时间戳/partial-final metadata与输出buffer需保持关联。[Request submission](https://source.android.com/docs/core/camera/camera3_requests_methods)、[HAL subsystem](https://source.android.com/docs/core/camera/camera3_requests_hal) 定义请求管线，完整错误/缓冲归还在既有会话页。

## 3A是HAL算法对外状态机

[3A modes](https://source.android.com/docs/core/camera/camera3_3Amodes) 中，设备open使AF/AE/AWB初始为INACTIVE；configure streams本身不应重置已锁定的3A。`CONTROL_MODE_OFF`关闭自动覆盖，AUTO让三套算法分别运行，scene mode可按其契约覆盖个别模式。不是所有写入的手动曝光/对焦值在自动模式都有效。

| 控制 | 完成条件与关键区别 | 易错推导 |
|---|---|---|
| AF | OFF手动镜头；AUTO/MACRO由trigger启动单次扫描；continuous-picture/video的trigger/lock时机不同；EDOF不进行普通扫描 | START在每个请求中都非IDLE会被当作多次独立触发；不能在repeating request永久留下START |
| AE | searching/converged/flash-required/precapture/locked分别表示不同事实；precapture是测光过程，可能涉及闪光 | “进入PRECAPTURE”不是高质量拍照已就绪；AE控制会覆盖曝光/感光度/帧时长等，需看result |
| AWB | 自动/固定场景/手动及lock共同控制实际色彩变换 | CONVERGED可因场景变化再次SEARCHING，不是永久白平衡承诺；锁定也不等于取消所有颜色处理 |

trigger是事件、mode是持续策略、state是观察结果。调用方须按帧观察状态变化，考虑pipeline延迟、取消和切换模式；不能用固定sleep代替收敛。HAL须保持状态与真实镜头/曝光算法一致，不能为了app快拍把未完成扫描报告成locked。Low Light Boost等后续模式要按目标capability和帧率契约判断，不能与普通AE或长曝光夜景扩展混用。

## 裁剪、zoom、稳定与重处理共用坐标语义

[Crop/reprocess](https://source.android.com/docs/core/camera/camera3_crop_reprocess) 中传统crop region以sensor active array坐标表示；HAL为对齐或防抖作取整/调整，要回报实际region。不同aspect ratio的输出会在共同crop之内进一步居中裁剪，不能预期所有stream得到完全相同FOV。

Android 11起的`CONTROL_ZOOM_RATIO`可表达超广角缩小及多镜头光学/数字变焦；zoom后的crop、AE/AWB/AF regions与faces坐标语义随之改变，RAW及其标定metadata不跟随普通处理图像一概变换。由此可推导：触摸对焦偏移先核对preview crop/rotation/zoom坐标，再改3A；不能把UI点击坐标直接传作sensor region。数值相同的crop在不同zoom模式可能不是相同视野。

Reprocessing使用已捕获图像及其metadata产生新的输出，不是重新曝光。先查设备实际支持的输入/输出格式与reprocessing capability，保证输入buffer、来源帧和metadata一致；不要把历史RAW示意当所有HAL都支持RAW重处理的保证。错误复用后拍帧的3A/时间戳，会导致颜色、降噪和曝光解释错误。

[Preview stabilization](https://source.android.com/docs/core/camera/camera-preview-stabilization) 从Android13在preview及其他非RAW输出上提供相应模式，让预览与录像一致；模式声明、有效组合、FOV和实际稳定质量需分别核实。防抖增加裁剪或延迟不能只通过把result crop保留旧值掩盖，检验应包含运动输入、preview/record对齐和metadata。

[Bokeh](https://source.android.com/docs/core/camera/bokeh) 的extended scene mode公开最大尺寸和zoom range，调用方还需选择对应CONTROL mode；代价可能涉及多帧/立体计算和内存。不能以“支持bokeh”推导所有分辨率/zoom/组合皆可用；需要session级切换的模式应按session keys与无副作用重配置查询实现，勿让enable隐含未上报停顿。

## 位深、动态范围、色域与编码文件不是一个开关

| 路径 | 公共能力和管线契约 |
|---|---|
| [10-bit output](https://source.android.com/docs/core/camera/10-bit-camera-output) | Android13起通过DynamicRangeProfiles选择，支持该能力的设备需相应sensor/ISP和HLG10基线；profile map约束流间组合，P010/PRIVATE输出及Gralloc静态/动态metadata须匹配 |
| [HDR modes](https://source.android.com/docs/core/camera/hdr-modes) | 多曝光融合输出SDR与真正10-bit HDR视频/图像分别理解，不能从场景模式名推出文件传递函数 |
| [Wide gamut](https://source.android.com/docs/core/camera/wide-gamut) | Android14起`ColorSpaceProfiles`/session color space表达Display-P3等支持；8-bit JPEG也可广色域，广色域不等于HDR；ICC和实际超出sRGB像素都应验证 |
| [Ultra HDR](https://source.android.com/docs/core/camera/ultra-hdr) | JPEG_R包含SDR基图与重建HDR所需信息，HAL直接输出与framework合成有不同资源代价；gainmap关联和SDR兼容显示各自检查 |
| [HEIF/HEIC](https://source.android.com/docs/core/camera/heif) | framework把HAL未压缩图和JPEG APP/Exif段送媒体编码器，要求对应HEIC或HEVC CQ硬件编码；公开一条HEIC流可能内部占两路HAL流，不能仅按公开流数量估资源 |

HEIC的thumbnail不应再次按`jpeg.orientation`旋转，framework写Exif/container方向，避免主图/缩略图双重旋转。APP1、capture result与码流可派生字段的来源需一致；JPEG质量/方向控制延续到对应HEIC语义，原文不允许JPEG与HEIC流同时配置，目标组合按接口核对。

HDR结果需一路确认capture → codec → container → decoder → dataspace/metadata → display，详见 [媒体管线](media-pipeline-codecs.md) 和 [显示色彩](display-color-transitions.md)。Android17 [HAGC](https://source.android.com/docs/core/display/hagc) 还需Camera HAL宣告相应dynamic-range profile与逐帧metadata，单纯升到10-bit并不自动生成ST2094-50 metadata。

## Vendor extensions：库版本、会话与图像引用

[Camera extensions](https://source.android.com/docs/core/camera/camerax-vendor-extensions) 用OEM library向Camera2/CameraX暴露Night/HDR/Bokeh等。该库运行在第三方app进程，不能要求系统特权。`checkApiVersion`协商major/minor，availability按camera ID查询；app API版本、extension接口版本和HAL版本相互独立。

Basic Extender让Camera2/X控制请求并在固定preview/still管线插入参数/processor；Advanced Extender可自定义session输出和请求序列，通过RequestProcessor与SessionProcessor协作。整套extensions选择相应实现类型，不能同一设备随意混用两类后还宣称接口一致。重初始化可能多次发生，重资源应在真正session初始化分配而不是构造/查询时分配。

生命周期至少包含版本/初始化完成 → availability/支持尺寸与keys → initSession或onInit → capture-session start → repeating/still processing → end/deInit。中间RAW/YUV ImageReader、ImageReference、capture result及最终surface的引用/释放按接口收尾；capture失败/取消不能让processor永久持有Image造成背压。先看框架允许哪些request/result keys，再谈“extension忽略了某个Camera2参数”。

当前正文的extension架构以preview/still为支持范围，不能因为app录下预览就宣称MediaCodec/MediaRecorder surface获得同等扩展保证。Android14增加extension strength/current type metadata也不等于任意算法都有相同强度曲线。extended scene mode与extensions可实现相似bokeh，但前者在普通会话的正交控制/组合责任更广。

[Validation tool](https://source.android.com/docs/core/camera/camerax-vendor-extensions-validation-tool) 的自动检查验证接口与capture stages，人工检查验证预览/成片效果；接口通过不能替代夜景曝光、虚化分割、HDR或延迟质量。本文提炼架构和生命周期，长篇所有processor方法/版本表未逐项展开。

## 特殊设备能力和权限

[System cameras](https://source.android.com/docs/core/camera/system-cameras) 从Android11将设备可发现/可访问性限制在SYSTEM_CAMERA与普通CAMERA权限的交集；普通CAMERA仍可被用户撤销，不能用system capability绕过用户控制。只隐藏Camera UI不等于服务端已阻止枚举/访问。

[Monochrome](https://source.android.com/docs/core/camera/monochrome) 的MONO/NIR、Y8及DNG metadata有专门规则，不应伪装Bayer RGB色彩校准；Y8可减少内存，但支持Y8并不证明任意彩色算法仍适用。[Motion tracking](https://source.android.com/docs/core/camera/motion-tracking) capability表示适合图像/其他sensor联合分析的曝光和标定要求，相机本身不直接产出运动轨迹，不能把capture intent当完整SLAM输出。

[Torch strength](https://source.android.com/docs/core/camera/torch-strength-control) 从Android13公开多级亮度和默认/最大level，属于独立camera device控制，不要求先open一个capture session；未支持多级时不应编造level。camera占用、热状态、torch mode/strength与实际闪光单元状态需一致；无camera权限要求不等于可绕过所有设备可用性限制。

## USB外接相机与手机作为webcam方向相反

[External USB cameras](https://source.android.com/docs/core/camera/external-usb-cameras) 是Android作为USB host，经UVC/V4L2、external provider枚举相机并提供Camera2 EXTERNAL设备；hotplug、provider、视频节点、权限/SELinux、格式/帧率与CPU转换成本各自确认。通用实现不承诺手机内置ISP的复杂控制/高速能力，外接摄像头也可能没有camcorder profile。

[Device as webcam](https://source.android.com/docs/core/camera/webcam) 是Android14 QPR1起将手机作为USB gadget：选择UVC function → UsbManager/system_server → gadget HAL/ConfigFS → DeviceAsWebcam服务 → host协商并经V4L2传输。ConfigFS宣告的MJPEG/YUYV尺寸/帧率必须同时满足camera、编码/转换、USB带宽；“host识别到UVC”不证明已开流。USB断开、host重配、camera切换/zoom/preview退出要收敛数据和资源，不能保留旧host配置继续写已销毁节点。

## 诊断及分支范围

[Camera debugging](https://source.android.com/docs/core/camera/debugging) 的Android13+ `cmd media.camera watch`可在复现前按client/tags启监视，保留关闭客户端的缓存；`dumpsys media.camera`主要提供当前客户端状态。问题发生后才开启watch不能补回此前逐帧3A证据。对齐request/result差值、frame number、实际crop、时间戳、buffer/fence、session及消费者，不以相机app的一张截图推断HAL执行事实。

[HAL版本](https://source.android.com/docs/core/camera/versioning) 需区分Camera1/Camera2 app API、HAL设备版本、HIDL/AIDL及硬件等级，旧兼容适配存在不等于Camera2所有手动特性都有硬件支持。Camera入口、HAL、requests、metadata、3A和上述高级分支在本页有机制归属；stream config、buffer management、multi-camera、concurrent streaming、single-producer、多session参数及error-stream由既有 [流与会话](camera-stream-sessions.md) 承接。

未逐项展开3A所有状态转移表、完整extension processor API、各HAL版本兼容表、ISP调优/画质算法及USB gadget配置表；这些须目标接口、真实sensor/镜头/host和相应ITS/CTS/VTS条件。本文不把功能声明当作这些实现与画质均已验证。
