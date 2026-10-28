# 图形合成与内存：buffer、驱动、fence和呈现证据

用于Gralloc/mapper、GPU、EGL/GLES/Vulkan/ANGLE、HWC、内存回收、frame pacing及Winscope。核实日期：2026-10-28。基础路径见 [图形概览](graphics-input.md)，模式策略/ARR见 [刷新率](refresh-rate-arr.md)，窗口归属见 [窗口与多显示](window-display-management.md)，色彩见 [显示色彩](display-color-transitions.md)。先固定release、allocator/mapper/composer版本、GPU/显示driver、实际loaded library、display/layer/buffer身份和时间基准。

## 分配、共享与可访问性是三件事

[BufferQueue/Gralloc](https://source.android.com/docs/core/graphics/arch-bq-gralloc) 中consumer拥有队列，producer按尺寸/format/usage dequeue并queue，consumer acquire/release；队列传handle而不复制像素，不表示整条管线无转换/复制。buffer数量与最小undequeued/acquired限制形成背压，增加buffer可能把卡顿变成更长延迟和更高内存。

Gralloc allocator决定内存分配，mapper导入handle、查询布局/metadata及CPU lock/unlock。旧概览HIDL allocator/mapper与现代接口分别确认；当前 [Stable-C mapper接口](https://android.googlesource.com/platform/hardware/interfaces/+/refs/heads/main/graphics/mapper/stable-c/include/android/hardware/graphics/mapper/IMapper.h) 明确mapper 2–4为HIDL，AIMapper从v5开始，由AIDL allocator提供相应vendor实现线索；不是“所有graphics HAL改成同一种Binder服务”。该源码是main，具体设备用冻结版本。

导入handle有进程内资源/映射寿命，结束时free；CPU地址不能跨进程传递。CPU访问还受usage、accessRegion、planes/offset/stride及acquire fence约束，unlock可能返回release fence；支持format不等于任意CPU usage可映射。protected或压缩/tiling buffer不能按普通线性RGBA裸读，重解释像素不应清除安全/usage约束。

[DMA-BUF](https://www.kernel.org/doc/html/v5.15/driver-api/dma-buf.html) 由exporter管理存储和ops，importer attach/map供设备访问，完成后unmap/detach/put。FD表示共享对象，不等于物理地址、永久pin或独占所有权。CPU缓存一致性与设备异步互斥分开：CPU access bracketing不代替等待GPU/display完成，fence已满足也不自动保证所有CPU缓存维护已完成。具体规则与目标内核/mapper一致，不绕过mapper在app侧任意发IOCTL。

[ION到DMA-BUF heap](https://source.android.com/docs/core/architecture/kernel/dma-buf-heaps) 是特定GKI迁移历史：不同heap设备节点可独立授权，heap name替代ION mask/private flags，纯importer不应依赖exporter类型。该文已标deprecated/5.4历史，不能推断所有当前vendor仍有相同fallback或私有heap名称。

## 生产端的连接与线程生命周期

| 入口 | 实际所有权/同步 | 常见失效推导 |
|---|---|---|
| [Surface/SurfaceHolder](https://source.android.com/docs/core/graphics/arch-sh) | Surface是producer交换接口，holder提供surface生命周期/参数；CPU Canvas、hardware Canvas及EGL/codec producer连接不同 | 调过CPU lockCanvas的producer连接不能随意再交GLES/decoder；Activity存活不证明surface仍可写 |
| [EGLSurface/GLES](https://source.android.com/docs/core/graphics/arch-egl-opengl) | EGLContext/current状态属线程；window EGLSurface连接ANativeWindow，swap提交而非完成显示 | 同一surface只能有相应唯一producer，销毁/换线程须正确解除current/连接；swap阻塞可能是queue背压 |
| [SurfaceTexture](https://source.android.com/docs/core/graphics/arch-st) | app为consumer，updateTexImage取得external texture并更新timestamp/transform；需正确current EGL context | onFrameAvailable不是图像已处理；丢transform会出现旋转/crop错误，用callback时刻替capture timestamp会抖动 |
| [SurfaceView/GLSurfaceView](https://source.android.com/docs/core/graphics/arch-sv-glsv) | 独立合成layer，surface created/changed/destroyed与Activity是相关但独立状态机 | onPause不能证明surface已销毁，surfaceCreated也可能晚到；render线程不能使用旧surface |
| [TextureView](https://source.android.com/docs/core/graphics/arch-tv) | SurfaceTexture内容进入View绘制与app UI合成，再由SF合成 | 不能把它当独立overlay，CPU/GPU路径与secure/HDR支持需实际核对；同线程producer/consumer可能背压 |

SurfaceView/TextureView历史文档中的性能/DRM绝对叙述要结合现代受保护GPU路径与产品能力理解；不能靠简单替换View保证安全输出或消除所有复制。[Layers/displays](https://source.android.com/docs/core/graphics/arch-layers-display) 将position、crop/transform、blend、visible/damage等属性区分；visible region和damage是优化输入，不能改变真实像素语义。virtual display输出到buffer并遵守consumer usage/fence，不是一个无需安全约束的屏幕副本。

## fence依赖与buffer归还

[同步框架](https://source.android.com/docs/core/graphics/sync) 允许CPU提前提交、GPU/DPU按依赖执行。旧文的sync_timeline/sync_pt名称需映射目标内核的dma_fence/sync_file等实现，不能复制旧内核路径当现代接口。关键是依赖、错误、FD所有权及signal的物理含义：

- acquire fence代表输入写入尚未完成，消费硬件必须等其满足后读；允许提前处理控制信息，不允许提前覆盖/采样未完成像素。
- release fence代表该consumer不再使用相应旧buffer，producer才能重写；多consumer依赖合并后需全部完成。
- present fence依物理/虚拟display契约描述呈现或输出可消费边界，不能把函数返回时刻当实际signal/scanout。
- FD转移、dup、close和错误路径按每个API定义执行；不能把某个接口“callee关闭”规则推广到所有接口。

信号卡住需查producer任务、GPU队列、HWC等待、内核driver与复位；先增加timeout或传空fence会把依赖错误变成花屏/跨帧污染。拿到handle、提交成功、fence signal与最后释放引用是四种完成条件。

## HWC协商、状态缓存与内存释放

[HWC实现](https://source.android.com/docs/core/graphics/implement-hwc) 的历史HWC2流程是layer状态/buffer → validate → changed composition types → accept → client target（需要时GPU合成）→ present。GPU fallback是正常资源选择，但HWC接受的crop/transform/blend/protected/dataspace必须真实实现；不能宣称device composition后实际忽略层属性。[HWC概览](https://source.android.com/docs/core/graphics/hwc)

[AIDL HWC](https://source.android.com/docs/core/graphics/aidl-hwc) 从Android13使用`composer3`，强类型parcelable commands替代HIDL FMQ；包含brightness/dimming、display decoration、expectedPresentTime、boot config和idle timer等新增契约。Android13并非所有设备强制迁移；HIDL数字版本与composer3 AIDL接口版本不能直接比较。command返回成功不表示全部状态自动生效，错误/changed composition及cache按目标契约处理。

[Client framebuffer管理](https://source.android.com/docs/core/graphics/framebuffer-mgmt) 描述Android13起分辨率改变时重分配client target：hotplug前/模式切换相应时点须释放旧HWC handle，否则旧新分配同时存在造成峰值、碎片或泄漏。需要继续使用旧framebuffer的硬件必须拥有足够过渡资源，不能希望framework回收其仍持有的引用。

[Graphics memory reduction](https://source.android.com/docs/core/graphics/reduce-consumption) 处理producer断开后SF↔Composer per-layer buffer cache；Android14的新`bufferSlotsToClear`路径与旧接口用placeholder清slot路径有不同支持条件。slot移除、当前active buffer与真实硬件读完成分别确认；旧HAL若不能处理同present周期同layer多次setBuffer，强开兼容开关可能崩溃。内存应观察queue、SF cache、HWC import、driver及DMA-BUF引用，app释放Surface不足以证明最后引用消失。

[Hotplug](https://source.android.com/docs/core/graphics/hotplug) 可刷新EDID/modes/HDR等能力而非仅传插拔。更新mode列表时新config IDs应避免复用导致并发setActiveConfig指向不同语义；保留旧能力代次和新ID映射。外接主屏/placeholder规则有目标版本约束，不应照历史“内屏绝不能断开”代码推断所有现代多显示形态。

## GPU API、loader与驱动能力

[GLES/EGL实现](https://source.android.com/docs/core/graphics/implement-opengl-es) 的loader发现真实driver，EGL config、YUV/external texture、native buffer与同步扩展共同决定跨camera/codec使用。GL API版本、EGL扩展、buffer usage和GPU硬件支持分开；不要仅改feature XML/属性宣称能力。HWUI [renderer属性](https://source.android.com/docs/core/graphics/renderer) 含大量Android8及以下cache调优，当前Skia/renderer先查实际backend；[SF sysprop](https://source.android.com/docs/core/graphics/surfaceflinger-props) 还可能有旧ConfigStore fallback，属性存在不等于新分支仍消费。

[Vulkan架构](https://source.android.com/docs/core/graphics/arch-vulkan) 和 [实现](https://source.android.com/docs/core/graphics/implement-vulkan) 区分platform loader/WSI、layer和SoC driver。swapchain/ANativeWindow由平台WSI协调，driver提供usage、native-buffer及acquire/release同步；内部`VK_ANDROID_native_buffer`不是app可随意使用的公开扩展。image acquire导入native fence，queue present必须返回等待依赖及准备工作完成后的native fence。仅vkQueuePresent返回成功不证明屏幕呈现。

当前文档列Android16/Vulkan1.4、Android13/1.3及ABP条件；实施时还核对首次出厂版本、64位/low-memory条件和对应CDD，不将当前运行版本表当所有设备升级后的必需driver能力。feature、枚举结果、实际driver版本与CTS覆盖应一致。layers可拦截API但受debuggable/代码加载边界约束，不允许把诊断layer任意注入生产非调试app。

[ANGLE](https://developer.android.com/games/develop/vulkan/overview) 是GLES到Vulkan实现层，Android15+提供相应可选路径；Android17的prefer-angle metadata是偏好提示，可fallback。确认GL renderer、driver选择和实际loaded libraries后再比较性能，不能把“系统支持Vulkan”当app已改用Vulkan，也不能承诺翻译层总是更快。

[New pixel formats](https://source.android.com/docs/core/graphics/new-pixel-formats) 牵涉Stable AIDL、AHardwareBuffer/Java、Gralloc、EGL/Vulkan format-colorspace映射与测试；单加enum不能形成端到端支持。位布局、分量归一化、plane/stride与dataspace契约须保持一致，本页不写外部提交流程。

## 帧节奏与诊断，不用平均FPS替代完成证据

[Frame pacing](https://source.android.com/docs/core/graphics/frame-pacing) 的Swappy通过presentation timestamps、fence和必要等待匹配显示cadence，减少短帧过早展示和长帧队列堆积。平台game intervention另可按user/UID传FPS限制；内容生产、buffer latch和panel cadence应同时观察。VSync/ARR/MRR机制由 [刷新率页](refresh-rate-arr.md) 承接，[VSync正文](https://source.android.com/docs/core/graphics/implement-vsync) 的旧相位/两帧示例不应变为所有设备固定延迟。

[AutoSingleLayer](https://source.android.com/docs/core/graphics/unsignaled-buffer-latch) 仅在单layer、纯buffer更新等条件下允许提前latch未signal buffer，并不取消硬件读取依赖；全局Always会影响sync transactions甚至冻结显示。Perfetto中检查真实选择与fence等待，不因“提前latch减少jank”就跳过多层同步。

[DPU readback](https://source.android.com/docs/core/graphics/productionized-dpu-readback) 从Android16 QPR2提供对应生产捕获能力，依赖readback attributes、产品验证和ScreenCapture请求；适合完整屏幕状态，不适合剔除可见层后的子集，更不能把DRM内容传到不安全环境。颜色/时延/闪烁/功耗应独立验证。HDR截图语义见 [显示色彩](display-color-transitions.md)。

## Winscope：对齐决策、事务、图层和View

[Winscope overview](https://source.android.com/docs/core/graphics/winscope/overview) 中WM trace解释窗口/任务/焦点/配置的决策，SF layers解释合成状态，transactions记录提交的原子变化，Shell transitions串联system-server/shell动画，ViewCapture提供单窗口View层次。dump是单时点、trace是序列，屏幕录像是可见结果；它们不能互相补造缺失历史。

[Capture overview](https://source.android.com/docs/core/graphics/winscope/capture/overview)、[adb](https://source.android.com/docs/core/graphics/winscope/capture/adb)、[on-device](https://source.android.com/docs/core/graphics/winscope/capture/on-device)、[Winscope采集](https://source.android.com/docs/core/graphics/winscope/capture/winscope) 的入口有不同build/权限与配置能力。Android15起相应数据源集成Perfetto，旧版命令不可直接套用；录像启动时display状态、root访问、trace targets与缓存容量会影响采集。复现前启用所需源，保留设备/build、时间窗和丢失/解析错误，不能把“导入成功”当所有源都在。

[Load](https://source.android.com/docs/core/graphics/winscope/load)、[Navigate](https://source.android.com/docs/core/graphics/winscope/analyze/navigate) 要对齐系统时间/时区与trace时间；超过末条记录时显示最后状态不是新采样。Shell trace的ring buffer可能仅剩finish，缺少start不能证明没有执行开始；[Transitions](https://source.android.com/docs/core/graphics/winscope/analyze/shell) 应按transition身份和截断状态分析。

[SF viewer](https://source.android.com/docs/core/graphics/winscope/analyze/sf) 对layer/buffer/visibility与parent关系取证，[WM viewer](https://source.android.com/docs/core/graphics/winscope/analyze/wm) 对window/task/activity及策略取证；visible/invisible标记不是panel像素测量。ViewCapture [采集](https://source.android.com/docs/core/graphics/winscope/capture/vc) 与 [分析](https://source.android.com/docs/core/graphics/winscope/analyze/view-capture) 依赖系统app挂钩和绘制，缺View记录不表示layer不存在。

[ProtoLog](https://source.android.com/docs/core/graphics/winscope/analyze/protolog) 的hash/字符串字典、启用组和build须匹配；[SQL search](https://source.android.com/docs/core/graphics/winscope/analyze/search) 的property/flat-property、数组字段和trace来源需理解，查询空结果也可能是缺源/版本不符。[Analysis overview](https://source.android.com/docs/core/graphics/winscope/analyze/overview) 和 [Run](https://source.android.com/docs/core/graphics/winscope/run) 为viewer导航/本地运行入口，本页不逐项复写GUI操作。

## 覆盖与限制

[Implementation testing](https://source.android.com/docs/core/graphics/implement) 区分固定负载吞吐、真实交互jank和功耗；[CTS integration](https://source.android.com/docs/core/graphics/cts-integration) 中NotSupported/QualityWarning等历史结果可映射为CTS pass，必须核实实际执行/跳过范围。旧 [dEQP部署正文](https://source.android.com/docs/core/graphics/deqp-testing) 已标不维护，应使用目标CTS和Khronos VK-GL-CTS版本，不把旧mustpass清单当现代Vulkan全覆盖。

本页承接graphics的Architecture/Surface系列、Gralloc/同步、HWC/AIDL/内存/hotplug/readback、GLES/Vulkan/测试、pacing/latch及Winscope全部子树的机制归属；HDR screenshots转显示色彩，ARR/MRR转刷新率页。未逐行展开完整mapper/composer/Vulkan接口、驱动内存布局、GPU调度、所有dEQP case和Winscope SQL/GUI选项；证据入口已提炼，不能宣称每项规范与厂商实现均已核验。
