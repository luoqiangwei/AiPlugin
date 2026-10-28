# Android 并发规则来源

本文件仅供来源和 API 语义复核；执行规则已写入专项资料。以下官方页面均于 **2026-10-27** 实际打开并读取相关正文，未将搜索摘要或读取失败的地址列为证据。示例等待图和测试方案为本地原创推演，不代表这些页面报告了对应项目漏洞。

## 已读取资料与采用语义

| 来源 | 官方页面 | 本地采用的语义 |
|---|---|---|
| 应用线程模型 | [Processes and threads overview](https://developer.android.com/guide/components/processes-and-threads) | 组件默认共用进程 main，UI 工具包须按其线程契约使用；本地 Binder 方法在调用线程，远端方法可由 Binder 池并发；Provider 数据访问也须处理并发。 |
| AIDL 本地与远端 | [Android Interface Definition Language](https://developer.android.com/develop/background-work/services/aidl?hl=en) | 本地直接调用不切线程，远端由 Binder 池分发；oneway 只改变远端调用，本地仍同步，不能以接口声明推断本地任务已异步。 |
| Binder 事务与重入 | [Handle threads](https://source.android.com/docs/core/architecture/ipc/binder-threading) | 同步事务等待回复；嵌套跨进程事务可重用原线程；锁内 IPC 有等待环与同线程重入风险，单 Binder 线程不能排除半状态重入。线程池扩大先要求实现并发正确。 |
| Binder API | [IBinder — FLAG_ONEWAY / linkToDeath / unlinkToDeath](https://developer.android.com/reference/android/os/IBinder) | 相同远端 Binder 对象的 oneway 按其顺序逐个执行，不推广到不同对象或同步混用；link 时已死可抛 RemoteException，isBinderAlive 不能保证下一时刻存活。unlink 成功与对端已死返回 false 的责任不同；应用自行排队的后续消息另管代号。 |
| 死亡通知线程 | [IBinder.DeathRecipient](https://developer.android.com/reference/android/os/IBinder.DeathRecipient) | 通知可来自 Binder 线程，其他线程可并行执行；binderDied(IBinder) 重载自 API 34 提供，旧版本需通过注册记录识别 token；死亡回调无须再对同一已死 Binder 调 unlink。 |
| JVM 可见性 | [java.util.concurrent — Memory Consistency Properties](https://developer.android.com/reference/java/util/concurrent/package-summary) | 同锁解锁/加锁、volatile 读写、任务提交和 Future 取结果等有各自 happens-before 边；volatile 无互斥，不自动保护复合条件或后续可变元素写入。native 内存模型另按语言规则核实。 |
| 执行器容量 | [ThreadPoolExecutor](https://developer.android.com/reference/java/util/concurrent/ThreadPoolExecutor) | core/max/queue 的配合决定实际排队；无界队列可持续增长；有界池和队列饱和会触发拒绝。CallerRuns 可在提交线程执行，静默丢弃不适合依赖完成结果的任务。 |
| 主线程安全与调度器 | [Best practices for coroutines in Android](https://developer.android.com/kotlin/coroutines/coroutines-best-practices) | 执行阻塞工作的一层负责正确切换 dispatcher；可注入调度器用于可控验证，不能把协程语法等同于不会占用 worker。 |
| ANR 等待定位 | [Find the unresponsive thread](https://developer.android.com/topic/performance/anrs/find-unresponsive-thread) | 受阻线程可能等待其他线程持锁或远端 Binder；应沿完成者查因果，不能只看 main 顶栈。 |

## 审查推演与边界

- 可见性、原子提交与对象存活是不同义务；整体快照示例要求元素不可变，代号比较与提交在同一同步协议内。这里没有声称仅使用 volatile 就修复所有竞争。
- 同池父任务占满全部 worker 后同步等待排队子任务，是由实际容量和依赖关系推演出的饥饿情形；需核实内联执行、独立池和拒绝策略后判断项目是否成立。
- 原生非递归 mutex 的同线程自锁与 Java monitor 的可重入半状态分开描述，不能从一种锁的结论直接推广到另一种语言/实现。
- 预留注册、锁外调用、重查提交与补偿是用于满足真实 link/register/close 交错的设计选择；具体 listener 的注销和线程保证仍按它自己的官方契约判断。
- 闩锁/barrier、延迟旧通知、真实远端死亡、队列边界与资源计数用于构造区分性验证；仅压力测试未失败不能反证全部竞态，静态链路也不能冒充已捕获 ANR。
