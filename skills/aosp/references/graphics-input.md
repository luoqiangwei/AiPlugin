# 图形、显示与输入：从事件到真正呈现的一帧

窗口/任务落屏、multi-resume、IME 与显示信任见[窗口与多显示](window-display-management.md)；ARR 时序与模式配置见[刷新率与 ARR](refresh-rate-arr.md)。本页解释缓冲、合成、输入与传感器的基础边界。

Mapper/DMA-BUF、GPU/Composer 和 Winscope 见[图形内存与合成](graphics-composer-memory.md)，HDR/色彩/亮度与转场见[显示色彩](display-color-transitions.md)，通知/Launcher 等见[SystemUI](systemui-app-experience.md)。

本页用于图层、显示合成、帧延迟、色彩、触摸和传感器变更。核实日期：2026-10-28。
先确认目标分支、composer/allocator/mapper 接口、GPU 驱动、panel、显示连接和传感器 HAL；当前文档的旧图与接口示例必须带版本理解。
帧是否生成、排队、被合成、交付显示硬件以及用户是否看到，是不同的完成条件。

## 总体路径与边界

典型显示路径：应用渲染 → Surface/图形 buffer → SurfaceFlinger 图层合成 → HWC/显示硬件 → panel。[1][][2][]
WindowManager 决定窗口及其相应布局/可见性关系，SurfaceFlinger 消费图层状态与 buffer；二者不是一个可互换的服务。
典型触摸路径：控制器/内核 evdev → EventHub → InputReader → InputDispatcher → 目标窗口；绘制结果再走显示路径。[8][]
触摸延迟应沿整条时间线测量，不能从应用单个 callback 快推出“触摸响应已经改善”。

- 标识证据时保留 display、layer/window、buffer/frame、input device/pointer 和时间基准。
- 逻辑显示、物理显示、窗口坐标、buffer 像素和触摸原始坐标不能直接混用。
- 旋转、折叠、热插拔、显示模式切换和窗口迁移都可能改变变换或生命周期。
- 屏幕截图只是某种捕获路径的结果，不能证明真实 panel、HDR、安全图层和输入映射都正确。

## BufferQueue 与 Gralloc：传 handle，按协议移交所有权

BufferQueue 连接 producer/consumer：dequeue → producer 写入 → queue → consumer acquire → release。[1][]
buffer 内容由 handle 传递；BufferQueue 本身不逐像素复制数据，但管线其他环节仍可能转换或复制。
buffer 个数和配置由双方条件共同约束，消费端慢会产生背压；增加队列深度可能增加内存和输入到显示延迟。
Gralloc 根据尺寸、格式和双方 usage 分配适合的内存；allocator、mapper 与具体内存布局需要匹配。
旧文档中的 C/HIDL 接口是历史说明，现代 AIDL/mapper 版本以目标树 `hardware/interfaces/graphics` 和设备 manifest 为准。

- 不把 RGBA 格式名直接当 CPU 线性布局保证；核对 stride、plane、压缩/tiling 与访问方式。
- buffer 可跨 Binder 传递，不表示任意进程拥有读取权限或硬件支持任意 usage 组合。
- CPU lock/unlock、cache 同步和 GPU/DPU 使用的边界需明确，不靠重复 memcpy 隐藏格式错误。
- consumer 断开、surface 重建或尺寸变化后，旧 buffer 的生命周期仍需收敛。
- protected usage 需要真正受保护的内存与输出路径；不能清标志或普通 CPU 映射来修复黑屏。

## SurfaceFlinger、HWC 与 fence

SurfaceFlinger 汇总可见图层，与 HWC 协商哪些走设备合成、哪些需要 client 合成。[2][][3][]
HWC 不是永远直接合成所有图层；GPU client composition 也是正常路径，不能仅凭其发生认定性能故障。
传统 HWC2 文档的 validate/accept/present 描述协商与呈现关系；实际命令缓存、接口传输及优化路径查目标版本。
修改 layer 属性、client target 或显示状态后，需要满足该版本对重新验证与提交的契约。

fence 表示异步工作依赖，不是普通互斥锁，也不是“buffer 已分配”的标志。[4][]
acquire fence 保护尚未完成的生产写入；release fence 表示消费端不再使用，可按契约归还 producer 复用。
调用提交成功与 fence signal 的时间不同；不能在 fence 未满足时覆盖下一帧数据。

- 追查卡住的 fence 应找到生产者、等待者及硬件任务，不先把 timeout 加大或跳过 wait。
- fence fd 的所有权/转移/dup/close 按具体接口定义处理；避免重复关闭和泄漏。
- 不在关键全局锁内等待 GPU、HWC 或未知客户端，防止跨线程/跨进程等待环。
- 局部画面正确不能证明 blend、crop、transform、z-order、保护内容或多显示一致性正确。
- “关闭 HWC 后好了”只是缩小故障范围的实验，不是证明永久改用 GPU 已满足功耗与性能要求。

## Vulkan：应用 API、loader 和 driver 的协作

Android Vulkan loader 位于 `frameworks/native/vulkan`，连接应用与驱动，并提供 Android WSI 相关能力。[5][]
系统 feature 声明应反映真实驱动版本与能力，不通过修改 feature XML 宣称不存在的 Vulkan 支持。
WSI 将 swapchain 图像与 Gralloc buffer、usage 及 native fence 关联；它仍遵守图形缓冲区的使用与归还条件。

- API 调用成功不代表工作已完成；检查实际队列执行、同步、buffer 访问和呈现结果。
- shader/管线编译、GPU 执行、CPU 提交和显示等待是不同瓶颈，不能统一归为“GPU性能差”。
- 先确认实际加载的驱动、ABI、扩展和 layer，再分析某应用的兼容性回归。
- 驱动更新需验证相应 CTS/dEQP 及真实场景，不从单个游戏或 benchmark 成功推出全面兼容。

## 显示模式、刷新率与 HDR

显示刷新率是硬件模式与平台策略的结果；DisplayManager 提供范围/策略，SurfaceFlinger 结合内容选择。[6][]
应用帧率、显示刷新率、提交频率与呈现节奏不同；120 Hz 模式不保证应用每秒生成 120 个不同帧。
切换可能受 mode group、seamless 能力、电量、温度和应用请求影响；不能忽略产品策略强制保持最高模式。

- 记录当前 active mode、候选模式、约束、内容帧率及实际帧时间分布。
- 优化关注掉帧、长尾、切换黑屏和功耗；平均 FPS 正常不排除抖动。
- 多显示/折叠场景需分别核对尺寸、旋转、模式与路由，不复用未验证的内屏假设。

HDR 不是一个“10-bit”开关；内容 profile、传递函数、色域、metadata、codec、合成与显示能力必须连通。[7][]
静态和逐帧动态 metadata 需要正确关联输出；错误传播会出现亮度或色彩异常，即使画面仍可见。
HDR 与 SDR 混合需要合适的色彩空间及 tone mapping，不能把普通 sRGB 截图与肉眼 panel 当同一种验证。
官方 HDR 页面包含 Android 7～10 与 OMX 的历史步骤，现代 Codec2/新 composer 实施需映射目标契约，勿复制旧 index。

- 检查 dataspace 与实际像素含义一致；仅改 metadata 不能把 SDR 内容变成正确 HDR。
- 保留 panel/外接设备报告、选中模式、内容类型和实际合成路径，比较同一亮度与环境条件。
- 安全输出与 HDR 支持是不同能力，不能因其一成立就推断另一项满足。

## 输入与触摸：正确设备、正确坐标、正确窗口

EventHub 读内核事件，InputReader 依据设备类别、映射与配置转换，InputDispatcher 选择窗口并等待消费。[8][]
驱动事件正确不保证窗口路由正确；窗口能绘制也不保证具有触摸区域、焦点或能及时处理输入。
key layout/character map、`.idc` 与固件校准有不同职责，不通过修改全局分发逻辑修复单型号坐标范围。

触摸设备报告原始轴范围、接触身份及工具状态，再映射到显示坐标；touchscreen、touchpad 和 pointer 行为不同。[9][]
旋转与显示关联决定变换；校准参数来自具体硬件，不能复制样例常数或用界面尺寸直接替换原始范围。

- 多指事件保持 pointer 身份与 down/move/up/cancel 语义；不能用每帧数组位置代替稳定身份。
- 触摸从屏内滑出可能产生超出显示范围的坐标，强制 clamp 会破坏连续手势，不能一律当作异常数据。
- display hotplug、旋转、fold 和设备移除时，要防止旧映射继续投递到新窗口。
- 输入卡顿分查内核到达、reader 解码、dispatcher 等待及应用响应；ANR 不自动等于驱动丢中断。
- 修改过滤、掌压/手写笔或手势策略时验证误触与漏触，不能仅靠输出事件数变少评价改善。

## 传感器：不走触摸分发，但会影响交互与功耗

SensorService/框架经 Sensors HAL 取得传感器事件；它与 evdev/InputDispatcher 是不同数据路径。[10][]
Android 13 起提供 AIDL Sensors HAL，基于 HAL 2.1 的能力；旧 poll/HIDL 与 FMQ 模型不能混用。
AIDL 初始化建立 Event FMQ 和 Wake Lock FMQ，事件必须被正确发布并通知框架，写入内存本身不足以交付。
WAKE_UP 事件需要在框架接手前保持对应 wakelock，数量确认与释放错误会导致事件丢失或耗电。

- sensor handle/描述在契约要求的生命周期内稳定，重启 HAL 后不能随意改变静态列表。
- batch/flush 控制采样交付，不等于停止采样；flush complete 要对应请求传感器和正确事件顺序。
- 事件时间戳、单位、坐标系及精度必须符合类型契约；“有数值”不等于物理测量正确。
- 验证激活/停用、频率、FIFO、休眠唤醒及 HAL 重启；数值精度需要已知输入或人工/硬件测试。

## 用证据约束修复

| 现象 | 需要关联的证据 | 应避免的修复跳跃 |
|---|---|---|
| 黑屏/残影 | layer/buffer/fence、合成类型、display 状态 | 直接跳过同步或关闭保护 |
| 帧抖动 | 应用生产、队列、GPU、SF/HWC、实际呈现 | 只提高刷新率或加 buffer |
| 触摸偏移/不响应 | 原始轴、设备映射、display/window 变换、分发等待 | 复制校准值或改全局坐标 |
| 旋转/唤醒异常 | sensor 类型、时间线、FMQ 与 wakelock 状态 | 把传感器当输入驱动处理 |

优先对齐同一时间基准的系统 trace、图层/窗口状态和驱动证据；选择目标分支可用的 Perfetto/Winscope/系统 dump，不假设固定命令全版本有效。
测试覆盖实际 panel、外显、方向、刷新率和硬件组合；没有对应设备时只报告已验证的逻辑与接口，不宣称物理显示或传感器精度通过。

## 已核实的官方深读入口

1. [BufferQueue、Gralloc 与 usage](https://source.android.com/docs/core/graphics/arch-bq-gralloc)
2. [SurfaceFlinger 与 WindowManager 的职责](https://source.android.com/docs/core/graphics/surfaceflinger-windowmanager)
3. [HWC：合成协商与呈现；留意历史 HWC2 示例](https://source.android.com/docs/core/graphics/implement-hwc)
4. [同步框架与 acquire/release fence](https://source.android.com/docs/core/graphics/sync)
5. [Android Vulkan loader、WSI 与 Gralloc](https://source.android.com/docs/core/graphics/implement-vulkan)
6. [多刷新率策略与配置组](https://source.android.com/docs/core/graphics/multiple-refresh-rate)
7. [HDR 内容、metadata 与显示管线](https://source.android.com/docs/core/display/hdr)
8. [输入管线与配置控制点](https://source.android.com/docs/core/interaction/input)
9. [触摸设备轴、校准和坐标映射](https://source.android.com/docs/core/interaction/input/touch-devices)
10. [Sensors AIDL HAL：FMQ、batch、flush 与 wakeup](https://source.android.com/docs/core/interaction/sensors/sensors-aidl-hal)

[1]: https://source.android.com/docs/core/graphics/arch-bq-gralloc
[2]: https://source.android.com/docs/core/graphics/surfaceflinger-windowmanager
[3]: https://source.android.com/docs/core/graphics/implement-hwc
[4]: https://source.android.com/docs/core/graphics/sync
[5]: https://source.android.com/docs/core/graphics/implement-vulkan
[6]: https://source.android.com/docs/core/graphics/multiple-refresh-rate
[7]: https://source.android.com/docs/core/display/hdr
[8]: https://source.android.com/docs/core/interaction/input
[9]: https://source.android.com/docs/core/interaction/input/touch-devices
[10]: https://source.android.com/docs/core/interaction/sensors/sensors-aidl-hal
