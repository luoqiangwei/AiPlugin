# Android 无响应规则来源

本文件仅供来源复核；运行规则已完整写在专项资料中。下列官方页面均于 **2026-10-27** 实际打开并读取相应正文，未把搜索摘要或无法读取的 URL 当核验证据。时限随平台分支、OEM、运行条件与 target 变化，不能凭本表宣称当前项目已发生 ANR。

## 已读取资料与采用语义

| 来源 | 官方页面 | 本地采用的语义 |
|---|---|---|
| ANR 诊断 | [Diagnose and fix ANRs](https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs) | 先分输入、无焦点窗口、广播、执行 Service、Provider 等类型；区分 app 阻塞与系统调度/远端服务问题；默认时间面向 AOSP/Pixel，OEM 可有差异。广播包含冷启动/排队，goAsync 以 finish 结束；Service 执行也包含冷启动；Provider 可能受远端启动或 Binder 耗尽影响。 |
| 责任线程 | [Find the unresponsive thread](https://developer.android.com/topic/performance/anrs/find-unresponsive-thread) | 输入/服务/Job 先查 main；同步广播查接收线程，异步广播查工作线程；Provider 查 Binder 查询或冷启动 main。根因还可能位于锁持有者或远端回复线程。 |
| 广播 API | [BroadcastReceiver — goAsync / onReceive](https://developer.android.com/reference/android/content/BroadcastReceiver?hl=en) | goAsync 保持广播有效但不免除及时处理，直到 PendingResult.finish 的时间仍在执行预算内；onReceive 默认 main，可按注册 Handler 另行调度；Manifest 接收器返回后的普通异步线程没有可靠存活保证。 |
| Provider 初始化 | [ContentProvider — onCreate / threading](https://developer.android.com/reference/android/content/ContentProvider) | 构造与 onCreate 在应用 main，避免重初始化；数据访问可并发。将数据库打开等延到使用时，还须检查首次访问成本。 |
| Job 生命周期 | [JobService](https://developer.android.com/reference/android/app/job/JobService) | 回调在 main；返回 true 与 jobFinished/停止协议管理任务存续，不能替代回调及时返回。API 34 的 setNotification 对要求通知的用户发起 Job 有独立期限；不把该期限视为所有 Job 的运行预算。 |
| Job target 条件 | [Android 14 — JobScheduler reinforces callback and network behavior](https://developer.android.com/about/versions/14/behavior-changes-14#jobscheduler) | target API 34 及以上，onStartJob/onStopJob 超时可触发显式 ANR；main 被其他工作占用与回调内部阻塞均可导致。旧行为静默清理也不表示任务成功。 |
| 前台服务失败分类 | [Troubleshoot foreground services](https://developer.android.com/develop/background-work/services/fgs/troubleshooting) | 前台提升超时的 ForegroundServiceDidNotStartInTimeException、shortService 超时未停的 ANR、其他限时类型未停的异常应分开归因。具体类型/API/target 与本分支约束另核对。 |
| 协程主线程安全 | [Best practices for coroutines in Android](https://developer.android.com/kotlin/coroutines/coroutines-best-practices) | suspend 函数仍应由执行阻塞操作的一层负责切换合适 dispatcher；注入 dispatcher 支持受控测试，不能只凭 suspend 标记证明 main 安全。 |

## 版本与表述取舍

- 广播 API 页保留概括性历史秒数，ANR 专项页按 Android 13 及以下、Android 14 及以上与前台标志细分；运行规则因此要求先核对实际条件，不提供一个通用秒数。
- JobService 概览使用平台版本概括显式 ANR，Android 14 行为变更页明确 target 条件；本地规则保留 target/API 双条件检查，不把概览推广成所有旧 target 必然出现相同报告。
- Provider 检测配置按实际框架/调用链取证；专项指南提及的 setDetectNotResponding 不被转述为所有普通应用可调用的公共调参 API。
- 等待图、受控闩锁测试、提交拒绝/队列取消清理以及“静态风险/复现 ANR”的证据分级，是依据上述执行契约制定的审查推演，不是官方页面中的原始案例或已核实漏洞。
