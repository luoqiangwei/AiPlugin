# CTS、CTS-V、Camera ITS 与物理验证

用于兼容测试集成、未执行模块、人工/仪器测试、Camera ITS、音频/传感器/多设备环境。核实日期：2026-10-28。
CDD 的适用性见[兼容性](compatibility.md)，harness 事件和分片见[测试基础设施](test-harness-infrastructure.md)。本页解释真实设备测量和结果的边界，不固定某个版本的测试数量、下载地址或所有命令。

## 套件、设备、环境与声明共同确定预期集合

CTS/CTS-V/ITS 与 Android release、suite revision、ABI、设备类型和已声明能力匹配。Release notes 可能改变 test plan、参数、rig、依赖和适用性；新套件不只是旧套件“多几个 case”。

静态 feature、runtime capability、首发 API/vendor 条件和表单形态影响选择。对于 skipped/assumption failure，应解释前置条件为何不满足及设备声明是否正确；不能以报告聚合成 Pass 为由宣称相关能力已测试。[CTS 结果解释](https://source.android.com/docs/compatibility/cts/interpret)、[套件下载/版本](https://source.android.com/docs/compatibility/cts/downloads)

环境也是测试输入：host 工具/语言/资源、ADB、网络/DNS/IPv6、无线对端、GNSS、光照、音频与其他外设。能启动 harness 不代表这些前置条件满足。每台 DUT 都需要它自己的有效物理环境；共享 AP/USB hub/对端还可能引入争用。[自动测试 setup](https://source.android.com/docs/compatibility/cts/setup)

## 结果不只看失败数

保留 suite/build/device 标识、计划/过滤、原始 XML/日志、module completion、case 状态及 session/attempt。`done` 表示模块执行完整性，与该模块用例是否都通过不同；失败数为零但模块不完整，仍缺少执行证据。

原始结果可以区分 pass/fail/timeout/not executed，harness 还可能把 ignored/assumption failure 纳入聚合 Pass。截图或 HTML 总数不能代替原始状态、条件和堆栈。Retry 用于补执行/区分环境与稳定失败，不应删除首次失败；重复失败数量一致也不是性能或所有功能的正确性证明。[执行与重试](https://source.android.com/docs/compatibility/cts/run)、[结果格式](https://source.android.com/docs/compatibility/cts/interpret)

多屏/折叠模式有版本对应的 test plan 或结果后缀，不能把同一 case 在展开态通过当成折叠态也通过。旧 v1 console 与新 v2 console 不是同一套命令契约。[CTS v2](https://source.android.com/docs/compatibility/cts/command-console-v2)

## CTS Verifier：人工操作也要有可复核记录

CTS-V 补充需要位置、动作、感知或外部硬件的测试。测试 app 的权限/AppOps、设备时间、对端配置和 export 位置有各 Android 版本条件；不应把一组旧 `adb` 授权命令直接用于新套件。

人工点击 Pass 不是自动断言的替代品。记录使用的 DUT/对端/外设、模式和观察结果，再导出对应报告。折叠/展开的测试结果需保持可区分；设置按钮切到 folded 模式也不自动证明设备已处于物理折叠状态。[运行 CTS-V](https://source.android.com/docs/compatibility/cts/verifier)、[测试指导](https://source.android.com/docs/compatibility/cts/cts-verifier)

## Camera ITS：metadata、成像与场景共同构成断言

ITS 配置 camera、采集图像/metadata，再针对已广告能力检查成像行为。它不是普通拍照 app 冒烟测试，也不只检查 Camera HAL 方法能返回。

先核对 camera ID、逻辑/物理成员、镜头姿态/焦距、scene、照明、距离、DUT方向、图卡/rig、对端/controller 与 suite 版本。错误 chart、曝光环境或不匹配 rig 可能使正确设备失败；错误 feature/metadata 又可能使测试错误跳过。两种原因都不能靠放宽阈值掩盖。[Camera ITS](https://source.android.com/docs/compatibility/cts/camera-its)

多摄、foldable、FoV 与 sensor fusion 有专门装置和姿态条件。测试图片、capture request/result、分析图、脚本配置和校准结果应一起保存；只保存最终 Pass 页无法分析成像或时序根因。整套 ITS 中单个场景通过不证明所有 camera/scene 组合已执行。[Foldables](https://source.android.com/docs/compatibility/cts/camera-its-foldables)、[Sensor fusion](https://source.android.com/docs/compatibility/cts/sensor-fusion-quick-start)、[ITS test reference](https://source.android.com/docs/compatibility/cts/camera-its-tests)

Camera HAL tests、ITS 的图像断言和用户图像质量调优分别覆盖不同层次。对 vendor extensions，公开能力声明及专门 validation 也需一致；不以隐藏能力规避本应适用的验证。[Camera HAL testing](https://source.android.com/docs/compatibility/cts/camera-hal)

## 音频：信号路径、测量装置和单位要可比

音频 CTS-V 包含基础功能、频率/电平、路径、loopback/latency、USB、多声道、MIDI、近超声与 workload 等。它们测不同对象：有声不证明频响，多声道枚举不证明通道映射，round-trip 不等于单向输出延迟。

输入/输出设备、路由、采样格式/rate、效果、音量、loopback 设备与校准决定真实路径。外设自动切换、USB hub/供电和线缆也会改变观测；先记录连接拓扑与有效输入/输出，再对比误差/延迟。[Audio tests](https://source.android.com/docs/compatibility/cts/audio-tests)、[Data paths](https://source.android.com/docs/compatibility/cts/audio-data-path-tests)、[Latency compliance](https://source.android.com/docs/compatibility/cts/audio-latency-compliance-tests)、[USB audio](https://source.android.com/docs/compatibility/cts/usb-audio)

音频测量阈值、校准操作和器材型号按对应版本原文执行；本页不把示例线缆、基准声压或单台 loopback 延迟当作所有设备要求。实时机制见[音频性能与 I/O](audio-performance-io.md)。

## 传感器、SE 与多设备：可信对端属于 fixture

旋转矢量/传感器融合要区分坐标系、运动轨迹、时间戳和参考测量；barometer 检查也受真实物理条件约束。随机手动晃动或伪造事件不等于满足校准装置要求。[Rotation vector](https://source.android.com/docs/compatibility/cts/rotation-vector)、[Barometer](https://source.android.com/docs/compatibility/cts/cts-barometer)

SE/NFC、Bluetooth、Wi-Fi Aware、UWB 等测试需要能力与访问规则匹配的对端、UICC/SE 测试数据、射频距离和控制链。测试 APDU 失败不能直接归为 OMAPI Java 层，设备可配对也不证明测距/交易语义正确。[SE testing](https://source.android.com/docs/compatibility/cts/secure-element)、[CTS-V multidevice](https://source.android.com/docs/compatibility/cts/ctsv-multidevice-bt)

Media performance class、播放验证、NPU Mobly 等另有声明/负载/设备前提。与通用 CTS 共享 harness，不表示可用同一环境替代其输入文件、对端或资源条件。[Media performance class](https://source.android.com/docs/compatibility/cts/media-cts)、[Media playback](https://source.android.com/docs/compatibility/cts/media-tests)、[NPU Mobly](https://source.android.com/docs/compatibility/cts/npu-cts)

## 深度边界

本文提供选择、环境、测量与结果契约。历代 CDD 的逐条要求、每种 rig 的机械装配/BOM、每个 ITS 算法/阈值、全部 CTS-V 人工步骤和安全芯片测试 profile 仍应读取对应原文；不能根据导航已经有本地归属就宣称这些细节全部完成验证。
