# 窗口、任务与多显示

图像被合成到某块屏幕，不代表 Activity、输入、IME 和授权已经迁移到该屏幕。先把逻辑 display、task、Activity、Window、Surface、焦点、输入设备和用户归属分开，再追踪它们之间的关系。BufferQueue 与显示合成见[图形、显示与输入](graphics-input.md)。

## 启动与任务复用决定落屏

启动位置由调用上下文、manifest launch mode、Intent flags、ActivityOptions、已有 task/Activity 和显示权限共同决定。带 display 的 Activity context 与 Application/shell context 不等价；没有 display 上下文的启动可能采用最后交互的显示。Intent 若复用已有实例，结果还受该 task 所在显示影响。

指定 launch display 是请求，不是越权通行证。私有 display 的所有者、已有参与 Activity、系统权限和嵌入条件都会影响是否允许启动；窗口添加也有相应限制。官方页包含历史内部类名和 API 拼写示例，使用时核对目标分支的公开/系统 API，不能直接复制旧内部方法。[启动行为及安全限制](https://source.android.com/docs/core/display/multi_display/activity-launch)

“点击后到了错误屏幕”应记录调用者 user/UID、Context/display、Intent flags、目标与实际 task/display、是否发生实例复用、拒绝原因。只改一个默认 display ID 容易掩盖任务复用或身份错误。

## 可见、Resumed、焦点与独占资源

Android 10 的 multi-resume 允许多个可见栈顶 Activity 同时处于 RESUMED。RESUMED 不代表获得输入焦点、位于最高交互位置，或独占 Camera 等资源；相机可能在 Activity 仍 resumed 时被其他客户端抢占。

`onTopResumedActivityChanged()` 用于表达与普通生命周期不同的顶层 resumed 关系，但仍不能替代具体资源服务的授权与仲裁。应用应处理相机断开、失去可用性及恢复，不能假设 `onPause()` 必定先于资源被回收。把 resizeableActivity 设为 false 也不保证其他显示上没有竞争者。[Multi-resume 与相机竞争](https://source.android.com/docs/core/display/multi_display/multi-resume)

验证多窗口切换时分开检查可见性、生命周期、输入焦点、top-resumed 回调及资源服务日志。它们不是同一个事件，不能仅通过一条 Activity 生命周期日志推断其他状态。

## IME 的目标、显示策略与信任边界

IME 的输入目标窗口与键盘自身窗口可以位于不同显示。显示策略可以要求键盘跟随目标、回到默认显示，或不显示。先判断策略与安全条件，再排查布局；焦点在副屏而键盘在主屏不一定是错误。

Android 10 的标准单 IME 模型会在焦点跨显示时重新建立连接，并可能解绑/重建服务，使 Context、window token、资源和尺寸匹配目标显示。旧 input connection、window token 或 display metrics 不能在迁移后继续当作有效状态。后续分支若引入不同的会话模型，应以其 IMMS/IMS 实现为准。

系统对非系统拥有的虚拟显示限制 IME 展示，原因包括恶意显示所有者读取输入预测等敏感界面。不能为修复“键盘不显示”而普遍放宽信任或系统装饰限制。诊断时对齐 focused window、IME target/control target、display IME policy、连接/token 生命周期和显示所有者。[IME 多显示支持](https://source.android.com/docs/core/display/multi_display/ime-support)

## 输入设备关联依赖稳定拓扑

触摸设备与物理显示的关联不能简单绑定枚举顺序或会变化的 logical display ID。Android 10 的输入端口关联使用稳定的物理端口信息；USB 输入路径与视频输出路径是不同拓扑，外观上同一块屏幕不保证系统已正确配对。

目标产品可使用 `/vendor/etc/input-port-associations.xml` 等对应版本的配置。检查时比对 InputReader/EventHub 中设备 location 与显示物理端口，覆盖开机、拔插、交换端口和显示重建。临时 display ID 恰好一致，只能证明当前这次枚举。[输入路由](https://source.android.com/docs/core/display/multi_display/input-routing)

## 锁屏与私有显示的责任

在官方描述的默认设备锁屏模型中，主显示承载交互式 keyguard，公共副屏有遮挡/锁定窗口；私有显示的所有者仍有隐藏敏感内容的责任。设备锁定不是“某一个 Activity 当前失焦”，也不能只通过隐藏启动器模拟。

验证锁定、解锁和显示热插拔时，检查所有相关显示上是否仍暴露受保护内容，及窗口/输入是否随状态恢复。AAOS、多用户和新显示形态可能有专用策略，不能把默认设备模型推成所有显示各自独立或永远共用一套锁屏的普遍结论。[多显示锁屏](https://source.android.com/docs/core/display/multi_display/lock-screen)

## WindowManager Extensions 与桌面窗口

Jetpack WindowManager 是应用侧库；设备侧 Extensions 是提供窗口布局、嵌入及窗口区域能力的平台模块。应用库更新不等于设备实现已具备相应能力。Extensions 可按设备形态提供有限组件，是否必须实现还受对应 CDD 要求约束；空组件、stub 返回与真实硬件行为需分辨。旧 Sidecar 是历史兼容路径，不能作为所有新功能的通用实现入口。[Extensions 的分发与契约](https://source.android.com/docs/core/display/windowmanager-extensions)

桌面窗口需要同时处理 task 布局/数量、自由调整大小、显示配置、输入与焦点、窗口装饰及应用兼容。不能把打开一个 feature flag 当作功能完成。当前官方页的 per-display desktop windowing 标为 Android 17+，应先核对目标版本与产品配置；任务数量等 overlay 是政策参数，不能替代资源压力下的实际行为验证。[桌面窗口](https://source.android.com/docs/core/display/desktop-windowing)

配置变化可能触发 Activity 重建，也可能由应用声明自行处理。窗口迁移后仍沿用旧屏幕密度、insets、旋转或输入坐标，是不同层次不同步的信号。定位时保存 `dumpsys activity`、`dumpsys window`、`dumpsys display`、`dumpsys input` 的同一时间段快照及相关 WM/SurfaceFlinger trace，核对这些状态的因果顺序，而不是只依赖最终截图。
