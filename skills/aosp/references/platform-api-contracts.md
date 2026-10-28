# 平台 API 的生成表面、异步完成与客户端缓存

用于共享 Java SDK library、Framework manager/system service API、新增异步入口及减少 Binder 往返。
资料核实于 2026-10-28；先记录 Android 分支、调用表面、模块 sdk/min-sdk、可更新模块边界与历史已发布 API。
本页把当前官方新 API 设计建议应用到实现判断；旧 API 的既有行为也是兼容契约，不能为统一风格直接改坏已发布调用者。

## 编译 API 和运行实现是不同产物

可选共享 Java 库可通过 app 的 `<uses-library>` 加入 classpath；这类库同样需要 API 评审、版本基线与兼容工具。
`java_sdk_library` 用实现源码生成 public/system/test 等启用 scope 的 stub 和 API specification，并构建运行实现。
消费者的 `sdk_version` 等设置决定编译到哪一 stub 表面，不应为了获得私有方法直接链接实现库。
[Implement Java SDK library](https://source.android.com/docs/setup/build/java-library)解释 stub、实现、scope 与 `prebuilt_apis` 的关系，具体默认启用 scope 应查目标分支。

| 产物/配置 | 解决的问题 | 不能据此推出 |
|---|---|---|
| 当前生成 API specification | 源码声明与受管理表面是否一致 | 与历史版本一定兼容 |
| 已发布 API 文件与 prebuilt stubs | 新表面是否破坏旧调用契约 | 行为、权限和线程语义一定保持 |
| 编译 stub | 调用者可以使用哪些符号 | 设备上运行的就是同一库版本 |
| 运行实现及安装 XML | 设备提供什么共享库及实际代码 | 任意消费者都可绕过 API scope |

更改 annotations、srcs、api_packages 或 scope 会改变生成表面；不能只手改 current.txt 让错误消失。
新增库的初始基线处理与修改已发布库是不同阶段，文档中的临时忽略缺失历史 API 选项不应成为关闭兼容检查的常规方法。
目标分支支持的 checkapi/update-api 等目标应与实际差异一起检查；更新生成文件后仍需人工确认暴露内容及运行行为。

## 设计表面时写清状态、所有者和失败语义

API 的方法签名之外，还包括空值、单位、取值范围、线程、权限、回调顺序、取消及对象寿命。
公共 SDK、System API、测试表面和内部 Binder 接口的调用者不同，不能把内部服务的低层 DTO/异常模型原样当作稳定 SDK 设计。
[Android API guidelines](https://source.android.com/docs/setup/contribute/api-guidelines)是当前 API 设计依据；目标版本 CDD、历史签名和行为测试仍决定必须保持的兼容性。

客户端校验用于尽早报告无效输入，不是服务端信任边界。
system_server 必须在可信调用身份下重复必要检查，尤其是用户/profile、包归属、长度与对象所有者；不能因参数经由 Framework manager 构造就视为可信。
新增参数应说明缺省值对历史消费者的含义；新增可更新模块消费者，还应检查老系统/新模块与新系统/老模块组合。

## 声明应让调用者读出契约

当前[通用 API 规则](https://source.android.com/docs/setup/contribute/api-guidelines)要求命名、类型、注解与文档协作，不能只追求调用端能编译。
新引用类型的空值契约应明确用 Nullable/NonNull 及文档表达，使 Java 工具与 Kotlin 调用得到同一预期；不能以返回 null 同时表示无结果、权限失败和服务故障。
集合应使用表达顺序/唯一性的基础接口，说明是否可修改及其所有权；借用可变输入、返回内部可变对象或复用同一结果对象时，要证明客户端不能改变服务后续状态。
需要保留输入或隔离返回值时做必要拷贝，是从所有权与可变性推导的实现要求；只给外层集合套不可变包装不一定隔离内部元素。

primitive 时间值使用足够范围的 long，并在名称/注解中明确 duration、单位与 wall clock/elapsed realtime/uptime 时间基准；不同时间基准不能直接相减。
可组合 bitmask 的 FLAG 常量应有独立位，与互斥取值集合区分，并用适用的 IntDef 等描述合法取值；注解仍不能取代服务端验证。
getter 名字不应隐藏阻塞 IPC 或高代价计算，当前指南用 compute/fetch/await 等区分不同成本和阻塞语义。
API 文档还应说明失败、线程和生命周期条件；Javadoc 的单位或空值说明与实现不一致，同样属于契约缺陷。

## Callback 式异步 API：发起也必须轻量

调用接收 callback，且没有明确只在调用栈内同步回调的契约时，开发者通常期待它异步、快速返回。
把耗时工作放到回调之后，仍在发起阶段做阻塞 IPC、持有高竞争锁或等待硬件，会破坏这个预期。
可以按实现选择单向注册、轻量双向注册或调用进程工作线程转发；`oneway` 不是所有阻塞或背压问题的通用修复。
[Async and nonblocking guidelines](https://source.android.com/docs/setup/contribute/api-guidelines/async)对新异步 API 给出这些要求；实现须结合 Binder 线程与身份规则。

当前指南建议操作结果统一经 callback 返回；无效参数可同步抛出参数类异常，其余操作失败走回调，包括权限不足、配额、超时、对端死亡或硬件断开。
应明确成功、失败、进度与终结事件的关系，使调用者无需一部分错误捕同步异常、另一部分等异步回调。
这是新表面的设计基线；迁移旧 API 时必须尊重已发布异常和返回契约，不能直接按新建议改变所有旧调用行为。

工程上应为每个请求维护足够的身份、会话和完成状态，防止取消、对端死亡与正常结果并发造成重复终结、丢失清理或把旧结果交给新请求。
不要在持有服务状态锁时调用外部 callback；派发到 Executor 不会自动保存原 Binder 调用身份，授权检查与归因需要在正确边界完成。
Executor 的实际执行方式也不能被假定为总是另一线程，接口和实现需容忍同步执行/重入的合法组合。

## 取消、冻结与回调资源

取消表达调用者不再需要结果，应释放所持 callback 强引用，并让执行引擎在可能时停止无用工作。
需要明确取消与完成竞争时的可观察契约，而不是只设置一个 UI 层布尔值；硬件取消失败也不能让服务永久持有已消失的客户端对象。
资源释放和 callback 注册生命周期的原则来自[异步指南](https://source.android.com/docs/setup/contribute/api-guidelines/async)，具体取消对象/返回类型应遵守目标 API。

向 cached app 持续推送可能诱发无用工作；向 frozen app 推送会积压 Binder 缓冲，解冻后也可能只收到过时事件。
当前指南建议考虑暂停 cached app 派发，并要求暂停 frozen app 派发；恢复时根据 API 的状态语义合并事件，而不是无界补发完整历史。
例如状态快照可只送最新值；对象集合变化应基于接收者最后所见集合汇总 lost/available/changed，而不是报告冻结期间短暂出现又消失的所有对象。

当前文档给出 `IBinder.addFrozenStateChangeCallback` 和 `RemoteCallbackList.Builder` 的冻结策略等新接口。
这些符号及 DROP/ENQUEUE_MOST_RECENT 等能力有目标分支/API 条件，不能假设旧系统存在或替旧分支直接补调用；应检查当期 API 声明和对应服务实现。
选择 drop、合并或补最新状态要与接口文档一致；会话必须连续处理事件的功能还需明确相应生命周期要求。
回调到达时间也不等于事件发生时间，需要真实事件时间的 API 应显式携带相应信息。

## Suspend 不等于启动后台任务后立即返回

Kotlin suspend 函数可在等待时让出线程，但其顺序完成语义要求相关工作在返回/抛异常前完成。
它不应返回之后继续持有并调用本次传入 callback；默认回调上下文也应保持调用者 CoroutineContext，除非接口另有明确目的。
新 suspend API 应协作响应 Job cancellation；单纯把阻塞函数标为 suspend 不会消除阻塞，隐藏创建线程也不应剥夺调用者控制 dispatcher 的能力。
[官方协程相关 API 指南](https://source.android.com/docs/setup/contribute/api-guidelines/async)给出上下文、取消与拥有协程对象的关闭语义；这不表示所有 Java 平台 API 都能直接暴露 Kotlin 特性。

类若拥有并发子任务，应有明确的父 Job/context 关系和 close/cancel 等收尾能力；close 倾向允许现有任务完成，cancel 表达可以取消，返回后均不应再接受新任务。
设计时先决定并发任务由调用者还是对象所有，再选择表面；把长寿命全局 scope 当作所有资源泄漏的解决方法会失去生命周期边界。

## 客户端缓存首先是语义等价问题

缓存应减少 IPC/竞争/计算，同时保持与接口所允许服务端结果的语义一致。
若结果稳定，可按完整请求参数缓存；若结果变化，则需要由状态所有者触发失效或按明确的数据新鲜度契约使用短期 memoization。
某统计 API 未承诺每次调用读到最新值，不代表权限、用户解锁状态等 API 也能任意缓存一秒。
[Client-side caching guidelines](https://source.android.com/docs/setup/contribute/api-guidelines/caching)同时要求正确、有效与资源高效，不能只用 hit rate 证明正确性。

`IpcDataCache` 可用于系统代码及 Mainline 模块；`PropertyInvalidatedCache` 的可见范围更偏 Framework，当前指南优先考虑前者。
它们不是普通 Map 的同义词：需要统一的 cache/失效标识与正确的状态变更通知；结果变化、测试替身替换或模块重建后，旧缓存必须按契约失效。
具体构造参数、全局失效机制和并发保证随分支核对，不从工具名字推导跨多项状态的原子快照。

缓存键至少覆盖决定结果的真实维度：请求参数、用户/profile、必要的身份/归因或配置维度。
若参数相同但用户、授权、安装状态或服务代次会改变结果，应把这些关系纳入键、失效或绕过条件；这是从语义等价要求推导的工程规则。
客户端缓存不能替代服务端在执行敏感操作时的授权，也不能把一次权限快照扩展成永久委托。
高频值可以 memoize 的时长、可见陈旧程度与时间源也应可解释，不以固定 sleep 代替失效协议。

## 缓存与 callback 聚合如何验证

对返回状态的每一种修改入口，检查它是否触发相应失效；遗漏管理员操作、跨用户改变、安装更新或恢复路径，会制造只在特定状态发生的陈旧结果。
用例应覆盖先命中旧值、真实服务端变更、随后取得允许的新值；仅测第一次 miss 后得到结果不能证明失效有效。
内部单元测试使用 fake server 时要在测试间清缓存；CTS 则验证对外行为，不应要求知道隐藏缓存如何实现。
[缓存指南](https://source.android.com/docs/setup/contribute/api-guidelines/caching)也介绍 `dumpsys cacheinfo` 的 hit/miss、invalidates、skips、size/overflow 等证据，其可用性按目标系统核实。

多个 app 内监听同一底层源时，可在 client library 聚合成一份远端注册并在进程内分发，减少重复 IPC。
聚合后仍须保持各 listener 的 Executor、注册/注销、身份和生命周期语义；最后一个 listener 移除后不能继续永久持有远端注册。
聚合是传输优化，不应把本应独立授权的不同用户或归因对象合并成一个宽泛请求。

## 审查输出应说明什么

应分别给出所保护 API 表面与历史基线、消费者编译 stub 和设备实现、发起阶段耗时来源、结果/取消/死亡状态机、冻结接收者策略，以及缓存键和完整失效链。
以上机制没有替代相关 API 的目标源码与行为测试；本页未运行平台构建或设备验证。
