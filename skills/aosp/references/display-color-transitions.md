# 显示色彩、亮度与可见状态过渡

用于HDR/SDR、tone mapping、广色域、截图、显示配置、cutout、旋转、fold姿态和同步转场。核实日期：2026-10-28。固定系统/QPR、composer/mapper版本、panel/外显能力与校准、当前mode、内容metadata、合成路径和用户亮度。窗口/多显示/IME/大屏/PiP见 [窗口与多显示](window-display-management.md)，MRR/ARR/expected-present时序见 [刷新率](refresh-rate-arr.md)，缓冲/合成见 [图形内存](graphics-composer-memory.md)。

## 像素布局、颜色含义与屏幕发光分别判断

Pixel format规定分量/位深/布局，dataspace规定primaries、transfer、range等含义，HDR metadata描述内容或逐帧映射信息，panel配置/校准决定最终输出。10-bit不自动等于HDR，P3不自动等于PQ，panel最大亮度不等于当前可用headroom。`Display.HdrCapabilities`、codec profile、实际buffer metadata和当前输出display必须属于同一管线。

[HDR video playback](https://source.android.com/docs/core/display/hdr) 含Android7–10及OMX的历史步骤：现代实现保留容器/extractor→codec→surface→composer/display的职责边界，但不能照搬旧OMX index、tunneled-only限制或“GL不支持HDR”等旧结论。static metadata可随输出format报告，dynamic metadata可能逐帧变化；seek/format change后沿用另一段内容的metadata会出现局部亮度/颜色错误，即使像素仍能解码。

压缩轨道、base/enhancement/metadata layers及CSD的打包要满足对应格式。识别HEVC Main10并不证明支持全部HDR profile；支持Dolby decoder也不替代正确extractor/access-unit契约。商业格式的具体profile及授权要求需相应规范，本页不枚举私有编码规则。

## 色彩管理与校准

[Color management](https://source.android.com/docs/core/display/color-mgmt) 从Android8.1通过display color modes、EGL/GLES/Vulkan颜色空间和HAL dataspaces连接内容与显示能力。支持P3输出需要真实panel特性、出厂校准与正确driver色彩变换；仅设置wide-color flag会让SDR或广色域像素被错误解释。

色彩变换可能由HWC逐layer硬件执行，也可能在GPU合成；共同输出空间、线性/非线性阶段及精度必须一致。外接屏能力变化时重新查询modes/HDR/color而不是沿用内屏校准。截图和肉眼panel比较还要控制显示亮度、环境与查看器自身变换，不能用一张sRGB截图证明P3/HDR输出准确。

[Night Light](https://source.android.com/docs/core/display/night-light) 由ColorDisplayService/Manager管理色温/时段并下发相应color transform。面板色温曲线取决于white point/gamut/校准，不宜复制样例系数；night tint、显示color mode、自动brightness与HDR tone map各有独立输入。scheduled、手动override、当前用户与显示状态需关联，不能把颜色变暖直接归为codec色偏。

## 混合SDR/HDR：增加HDR亮度时保持SDR白点

[Mixed SDR/HDR](https://source.android.com/docs/core/display/mixed-sdr-hdr) 在Android13增加按layer调暗SDR：DisplayManager按display config计算SDR白点/ratio，SF经AIDL composer传brightness/dimming信息，HWC在合适颜色阶段处理。`sdrHdrRatioMap`等配置存在与HWC硬件能力共同决定是否启用，单独支持AIDL方法不证明策略已生效。

HDR区域大小、用户亮度、panel高亮能力/限制与热/电源条件共同影响可用范围；原文的阈值是设备策略而非所有场景固定常量。硬件不能在正确线性阶段缩放或不能适当dither时需请求GPU处理，不能报告device composition后在错误gamma空间简单乘像素。

调暗会降低有效码值、可能black crush/banding，合适dithering或限制ratio可缓解；GPU fallback改善质量但增加资源成本。由此可推导：HDR小窗出现后整个UI突然变亮/变暗，先查SDR白点、ratio、layer brightness、合成切换和panel亮度，不先改变视频本身的曝光metadata。

## tone map的算法、精度与版本边界

[Tone mapping](https://source.android.com/docs/core/display/tone-mapping) 的Android13 `libtonemap`让SF、HWUI和HWC共享相应CPU/SkSL映射实现，减少GPU/DPU切换时色调不一致；输入可能是绝对nits线性空间，输出gain、uniforms和源/目标dataspace需遵守接口，不能把归一化gamma值当绝对亮度输入。

当前官方文档另说明Android16为HDR video引入`DisplayLuts`路径。应按目标composer能力、LUT维度/采样/精度与实际RenderEngine/HWC路径核对，不能把旧libtonemap hook视为所有新分支唯一入口，也不能因有新API而删掉目标设备仍需的fallback。

Android17 [HAGC](https://source.android.com/docs/core/display/hagc) 使用SMPTE ST2094-50，要求camera dynamic-range profile、codec T.35/C2 dynamic metadata、mapper存取与display LUT能力配合。LUT支持与3D LUT质量建议分开；参考GPU shader可用于对应fallback/验证，不能把debug override当硬件tone-map能力。HDR“支持播放”最终取决于整条metadata链，不是一个codec或panel的标签。

可见闪烁常出现在旋转、窗口动画、叠层出现后client/device composition切换。要比较相同输入/亮度下两条路径的transfer/色彩空间、target位深、tone-map曲线和dither。强制GPU后正常只缩小问题范围，不证明长期功耗、protected内容或全部场景满足要求。

## HDR截图和readback不是panel光学测量

[HDR screenshots](https://source.android.com/docs/core/graphics/hdr-screenshots) 解释了不同版本的输出语义：旧SDR截图会tone-map/裁高光，Android15 QPR1引入局部tone mapping以改善混合内容；Android16支持PNG内的SDR基图与gainmap，用gmAP/gdAT等结构保存HDR重建信息。文件仍是PNG并不意味着只有SDR，重新编码/传输也可能丢失gainmap。

截图生成时的FP16输入、base/gainmap关联、查看器HDR能力及当前headroom共同影响结果。屏幕上HDR很亮而普通查看器截图较暗可能是输出语义差异，不能直接归因显示driver。相反，不同路径错误套tone-map也会导致连续截图越截越暗，应保留原文件与capture路径。

[DPU readback](https://source.android.com/docs/core/graphics/productionized-dpu-readback) 从Android16 QPR2提供对应完整屏幕捕获路径，有独立能力/产品验证条件，实际捕获规则及protected内容边界见 [图形内存](graphics-composer-memory.md)。Readback、普通SF截图、virtual display和物理panel scanout不是等价观察工具。

## 显示配置变化有能力代次与资源过渡

Display mode/config不只是一个Hz，还包含尺寸、timing、group及硬件限制。用户请求、策略允许、HWC接受、timeline生效和实际panel更新分别完成；详细MRR/ARR见既有页。[AIDL composer](https://source.android.com/docs/core/graphics/aidl-hwc) 的expectedPresentTime只是未来呈现意图，不能当已经展示；boot display config支持时需保存用于下次boot，并处理目标配置不再可用的fallback。

[Hotplug](https://source.android.com/docs/core/graphics/hotplug) 可重新宣告modes、color和HDR；config ID不能在并发请求仍使用时复用为另一种分辨率。能力改变同时触发client target重分配和app display-change通知，旧buffer/metadata/输入映射寿命需收敛。[Framebuffer管理](https://source.android.com/docs/core/graphics/framebuffer-mgmt) 中旧HWC引用未释放会形成内存峰值/分配失败，表现可能像“模式切换黑屏”，不能只延长动画掩盖资源问题。

呈现诊断至少关联transaction、buffer latch、acquire/release/present fence、mode timeline与真实VSync/TE；capture callback或API返回时间不等于panel发光。时间基准和display ID不同的记录不能直接相减。[VSync](https://source.android.com/docs/core/graphics/implement-vsync)、[同步](https://source.android.com/docs/core/graphics/sync)

## Cutout、旋转和fold状态

[Display cutouts](https://source.android.com/docs/core/display/display-cutouts) 将真实硬件路径、display native orientation、像素坐标、安全insets与SystemUI布局相连接。物理notch应用像素几何，`@dp`是仿真overlay用途；用软件涂黑掩盖不准确path会使app可用区域和实际遮挡不一致。旧Android9布局/letterbox代码和尺寸示例要结合当前target-SDK、edge-to-edge与对应CDD，不能作为新版本固定策略。

旋转后需重算insets、圆角/decoration layer、nav/status bar与触摸映射，默认/never/always等cutout策略不是显示驱动crop指令。[AIDL decoration composition](https://source.android.com/docs/core/graphics/aidl-hwc) 对专用alpha mask硬件还有format/alpha interpretation契约，声明能力后必须真正匹配。

[Rotation suggestions](https://source.android.com/docs/core/display/rotate-suggestions) 在rotation lock时仍可保持传感器产生建议，用户点击改变旋转偏好，WM再结合顶层Activity与系统约束决定实际rotation。关闭auto-rotate不证明orientation sensor必须停用；显示按钮也不证明已经旋转。持久偏好、自然方向重置和UI可见性分别记录。

[按设备状态auto-rotate](https://source.android.com/docs/core/display/device-state-based-auto-rotate-setting) 从Android13支持不同posture偏好，当前指南针对Android16 QPR1重构。泛化device state ID与该功能posture key需转换，ignored姿态的读写会转发到fallback姿态；直接写settings会打破全局开关与每姿态存储的同步，应由对应controller/API维护。

[Tent/wedge](https://source.android.com/docs/core/display/foldables/tent-wedge-mode) 的Android16书本型策略用hinge angle、两侧accelerometer、方向及wakelock等延长closed状态范围，不必创建独立tent device state；不能只按铰链角度猜当前使用的屏幕。[Fold lock](https://source.android.com/docs/core/display/foldables/fold-lock-behavior-setting) 把用户选择交给LogicalDisplayMapper/PowerManager决定继续亮屏、keyguard或sleep；显示迁移、锁定状态和是否需要重新认证分别核对，折叠动画结束不能证明安全/电源状态都已同步。

## 同步动画与blur的可用性

[Synchronized app transitions](https://source.android.com/docs/core/display/synched-app-transitions) 将Launcher/SystemUI绘制帧与app surface transaction同步，避免图标/窗口变换分属不同帧。控制动画的进程也是生产者，卡顿要同时看其CPU/GPU绘制、WM/Shell状态与SF提交；单独app FPS正常不能排除控制端掉帧。该文描述Android9 remote animation入口，现代Shell transition参与者与finish/merge/abort契约需读目标树，不按旧类名认定所有动画路径。

[Window blur](https://source.android.com/docs/core/display/window-blurs) 的background blur与blur-behind范围不同，也不同于同窗口RenderEffect；window透明性、窗口背景形状及运行时支持状态会决定最终视觉。Android12+ API存在不保证设备/GPU或当前电源状态启用blur，失效时需要相应不透明/调暗等可读性fallback；不能把禁用blur等同layer被删除。半径增加改变采样范围/成本，应结合整屏负载和帧预算，不复制样例半径为统一最佳值。

转场证据用 [Winscope机制](graphics-composer-memory.md) 对齐WM决策、Shell过渡、transactions、SF layers、ViewCapture与录屏；ring buffer截断和trace未启用时须保留不确定性。

## 归属和未深入边界

本页承接display的HDR/Color management/Night Light/Mixed SDR-HDR/Tone mapping/HAGC、Cutout、Rotation suggestions/按姿态旋转、Fold lock/Tent-wedge、同步转场/Window blur，并承接graphics的HDR截图。多显示、多窗口、desktop/PiP、大屏兼容、WM Extensions及窗口放大由 [窗口与多显示](window-display-management.md) / [无障碍](accessibility.md) 承接，刷新策略另页。

Notifications/DND/media controls/task manager、Launcher icons/shortcuts/widgets/home data、Material动态色、TextClassifier与retail分支由 [SystemUI与应用体验](systemui-app-experience.md) 承接；它们的配色资源或UI可见性不能代替本页的panel色彩/呈现契约。

未深入完整SMPTE/CTA标准、每种商业HDR profile、panel校准/背光/局部调光算法、所有LUT插值细节和现代Shell transition实现；已读材料支持上述机制与版本边界，不表示所有显示硬件或完整协议均已验证。验证需要相同内容、环境、brightness/headroom与实际硬件，普通截图不能证明真实亮度、色准、闪烁和scanout时序。
