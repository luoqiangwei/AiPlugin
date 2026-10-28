# system_server Watchdog 规则溯源

复核日期：2026-10-27。以下为本次实际打开并阅读的官方正文/源码；运行规则采用原创归纳与风险示意，不复制完整实现。源码分支是 `refs/heads/android16-release`，不是目标产品版本声明；Review 必须回到 manifest 固定的 revision、厂商改动和运行配置复核。

## Watchdog 源码

- URL：[AOSP Watchdog.java](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/android16-release/services/core/java/com/android/server/Watchdog.java)
- 仓库/分支：`platform/frameworks/base`，`refs/heads/android16-release`。
- 本次页面 blob：`d60c6c534871bae7504c55b9fc957157f07d50cb`；分支可继续移动，应按目标 revision 重新比对。
- 实读：`HandlerChecker.scheduleCheckLocked/run/getCompletionStateLocked/describeBlockedStateLocked`、构造器默认 checker、`BinderThreadMonitor`、`addThread/addMonitor`、暂停/恢复、`start/init/registerSettingsObserver/updateWatchdogTimeout`、`run/logWatchog` 及崩溃循环相关分支。
- 用途：确定 checker 与 Handler/monitor 的执行关系，队首投递与 polling 快路径、串行 monitor、挂起判定、uptime 计时、超时来源、预警及逾期后的处理条件。
- 版本敏感点：本次 monitor 使用专用 `watchdog.monitor` 线程；`PRE_WATCHDOG_TIMEOUT_RATIO` 的当前值为 4，`waitedHalf` 变量名不代表当前预警是半程。未将默认毫秒常量写成通用审查阈值。
- 配置核对点：`DB`、`Build.HW_TIMEOUT_MULTIPLIER`、`Build.IS_USERDEBUG`、自定义 checker timeout、Settings、暂停；debugger、activity controller、allowRestart 和非 user 的崩溃循环处理分别影响行为。不能笼统声称 userdebug 不会被杀。
- 审查推导：未注册/被暂停的业务链不在本轮判定内，且 dump 进程集合不等于被监测进程集合；将此限制转化为覆盖表和反证条件。

## Binder 官方线程契约

- URL：[Handle threads](https://source.android.com/docs/core/architecture/ipc/binder-threading)
- 版本：官方滚动文档，无固定 Android 分支；本次页面标注更新时间为 2026-10-09 UTC，访问于 2026-10-27。
- 实读：同步/异步事务、同一节点异步事务串行、嵌套事务复用线程、持锁跨进程死锁、单线程池重入与线程池配置章节。
- 用途：为同步等待、另一线程回调、嵌套回调、池耗尽和 oneway 反证划清边界；不能把所有回调都认作新 Binder 线程，也不能用增加池大小替代等待链分析。
- 适用限制：目标仍须核对 Java/native backend、实际 Binder 域、进程内直调及厂商池配置；文档中的线程池默认值不作为 system_server 通用容量。

## 真实服务 monitor 与生命周期

- URL：[AOSP StorageManagerService.java](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/android16-release/services/core/java/com/android/server/StorageManagerService.java)
- 仓库/分支：`platform/frameworks/base`，`refs/heads/android16-release`。
- 本次页面 blob：`3adbd229d2007dce03fbd4890c453f3fc5d0b080`。
- 实读：`WATCHDOG_ENABLE`、构造器 `addMonitor(this)`、`Lifecycle.onStart/onBootPhase`、`start/connectVold`、`monitor()`、`shutdown/H_SHUTDOWN`、`extendWatchdogTimeout`，以及 `AppFuseMountScope.close()` 关于异步 unmount 的依赖说明。
- 用途：确认实际 Monitor 可调用远端能力而非仅拿 Java 锁；服务构造、发布、daemon 连接、启动阶段和关机完成通知须分别追踪。该实现存在局部慢操作暂停，不推出“扩大超时是默认修复”。
- 审查推导：以 AppFuse 的跨线程文件请求依赖提示读到 native/I/O 完成者；运行模块中的锁/HAL/generation 例子是独立风险示意，未宣称该源码存在本次新发现的漏洞。
- 阅读边界：没有据此推断 vold/HAL 全部内部锁或目标设备的硬件行为；若 finding 依赖它们，继续读取对应仓库与目标 revision。

本次尝试读取较大 ActivityManagerService 页面时工具因内容过长失败；未将其当作已读实现。部分其他服务页面不可达，未用其填补 monitor 细节或启动时序证据。
