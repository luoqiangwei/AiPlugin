# ART、Zygote、Framework 与系统应用

ART/DEX/JIT/GC 专门机制见[Runtime 执行与格式](runtime-execution-format.md)，设置接入见[Settings 与搜索](settings-search-integration.md)，通知/Launcher/主题等见[SystemUI 与应用体验](systemui-app-experience.md)。

用于启动、进程、系统服务、包与用户状态，以及 Settings/SystemUI 扩展。本文不把应用组件、系统服务和 native daemon 混为同一种生命周期。
“事实”对应文末已读资料；“工程推导”是定位和实现判断。核实日期为 2026-10-28，具体类、线程与默认配置以目标分支为准。

## 1. ART 的执行模式是一种运行状态

**事实**：ART 使用解释执行、JIT 和 AOT；Android 7 起的混合模式可以利用 profile 决定编译重点。`dex2oat` 生成运行时加载的编译产物，文件种类和默认策略随版本变化。[R2][][R3][]
构建时 dexpreopt 与设备运行后的编译属于不同阶段。boot classpath 等依赖变化可能使预编译产物失效。[R2][]

**工程推导**：同一 APK 在首次运行、热运行、后台编译后及系统更新后可能有不同性能。
性能结论要记录编译模式、profile 状态、冷/热启动和测量场景，不能仅因一次启动更快就修改全机编译策略。
`speed` 与 `speed-profile` 是不同空间、编译成本和性能取舍，不能称为普遍更优或更安全的选择。
类加载失败、校验失败、JNI 崩溃和运行时内存压力要分开定位，不能都归因为“ART 缓存坏了”。

| 现象 | 优先解释 | 定位证据 |
|---|---|---|
| 首次启动慢 | 类加载、解释/JIT、I/O、初始化 | trace、编译状态、启动阶段耗时 |
| 更新后编译增加 | classpath 或产物依赖失效 | 系统/模块版本、编译日志、依赖配置 |
| 仅某架构崩溃 | ABI、JNI、native 实现 | 进程位数、实际库、tombstone |
| 长时间停顿 | GC、内存压力或主线程阻塞 | GC 日志、线程栈、调度与内存数据 |

## 2. Zygote 是进程创建机制，不是应用生命周期本身

**事实**：`init` 启动 Zygote；系统可按 ABI 配置一个或多个 Zygote。`system_server` 通过对应机制请求应用进程，Zygote fork 并专门化进程。[R1][]
USAP 池可预先创建尚未专门化的进程；WebView 还可使用专门的 Zygote。是否启用及具体配置须查目标产品。[R1][]
Zygote 对 fork 时继承的文件描述符有专门处理，新增预加载资源可能触及 FD 允许列表与访问约束。[R1][]

**工程推导**：向 Zygote 增加全局初始化会影响其后创建的进程，不能把它当成普通应用缓存位置。
排查启动失败应区分“未 fork”“已 fork 未绑定应用”“绑定后初始化失败”“进程被回收”，用 PID 和时间线连接事件。
不能从设备支持 64 位推出所有进程都为 64 位，也不能从某进程名猜测 JNI 实际加载的 ABI。
FD 错误应追踪创建与继承责任；把路径加入允许列表之前先证明该资源应该跨 fork 存活。

## 3. 系统服务的启动、发布与就绪分离

**事实**：`SystemService` 基类描述构造、`onStart()` 发布 Binder/本地接口、随后多次 `onBootPhase()` 的生命周期；boot phase 表示依赖逐步可用。[R4][]
该基类还提供用户生命周期回调；具体回调支持和线程派发应查目标实现，不能拿旧版本常量或示例覆盖当前系统。

**工程推导**：接口已发布和内部初始化完成是两个状态。早期调用需要明确定义拒绝、等待或有限能力行为。
依赖服务不应在构造函数里无限等待；本地内部接口也不能自动替代对外 Binder 的权限和线程语义。
启动阶段工作要控制耗时，阻塞系统主路径可能扩大为启动卡住或 watchdog；仅捕获异常不能证明服务恢复可用。
用户启动、解锁、切换与停止分别对应不同状态，不要只在整机 boot completed 时初始化所有用户数据。

```text
构造与依赖声明 → 发布入口 → 分阶段取得依赖 → 用户状态就绪 → 对外提供相应能力
                       ↘ 早期请求：返回有定义的状态或进入受控等待
```

上图是工程建模示意，具体阶段顺序和回调以目标分支为准，不能机械复制为新的启动状态机。

## 4. 包、进程、组件与用户是不同状态

**事实**：预装系统包可以按用户类型设置安装规则。系统用户、完整用户与 profile 并非同一种用户，预装镜像存在 APK 不代表每个用户都安装了该包。[R6][]
`lmkd` 监视系统内存压力并回收相对不重要的进程；现代配置可使用 PSI，而不是仅依赖某个固定“空闲内存”阈值。[R5][]

**工程推导**：安装/启用包、启动进程、绑定组件、用户解锁和后台执行资格要分别检查。
界面退出不等于进程立即结束；进程存活也不表示组件已就绪。不能把进程内单例作为必然持久的系统真相。
关键状态应有明确持有者与恢复语义；进程被杀后必须能从可信状态重建，不能依赖销毁回调一定完成最后一次落盘。
重启频繁要先区分异常、系统策略和内存回收，再考虑调节重要性；提高保活等级可能把内存压力转移给其它关键进程。

## 5. 系统应用并不自动获得所有能力

**事实**：privileged app 的身份与分区位置有关；特权权限允许列表只作用于相应分区的应用，vendor 特权权限还有保护级别限制。[R7][]
平台权限、签名、用户作用域和服务端校验共同影响能力，不能用“预装”一词代替授权模型。

**工程推导**：新增系统应用功能应追踪 manifest 请求、签名/安装身份、授予配置、运行时状态及服务端检查。
安装路径变化可能同时改变权限和依赖可见性，不能当成纯打包改动。
多用户问题要确认实际调用用户、目标用户以及执行服务所在用户；不要把固定 user 0 当作所有产品的前台用户。
权限机制进一步见 [security.md](security.md)，跨组件契约见 [architecture-ipc.md](architecture-ipc.md)。

## 6. Settings/SystemUI：展示和平台策略之间有责任边界

**工程推导**：先找到该分支实际的 preference/controller、状态持有者、订阅与呈现路径，再选择扩展点。
Settings 的显示值、可编辑性和已持久化策略可能来自不同地方；开关点击后应以服务确认的状态收敛，不能仅在 UI 内翻转布尔值。
SystemUI 的 view 生命周期、配置变化、显示器和用户变化会重建订阅；注册与取消、旧回调隔离和线程切换必须成对。
安全决策应由拥有权限与可信状态的服务执行；隐藏控件不是禁止操作，禁用控件也不等于服务端拒绝。

**事实**：RRO 通过资源映射替换既有资源值，不能替换 DEX 代码。overlayable、分区策略与发布版本影响可覆盖范围。[R8][]
因此资源差异可优先评估 overlay，行为变化则须找到代码与策略入口。
RRO 的目标包、用户、资源配置匹配和实际启用状态影响结果；只确认 overlay APK 已安装不足以证明覆盖生效。

**工程推导**：修复某一屏幕尺寸、语言或用户的 UI 差异，要核对最终资源来源与匹配配置，避免修改未生效的默认资源。
不要把 Automotive 的 SystemUI/用户示例直接当成手机或其它形态的固定设计。

## 7. 系统扩展的配置选择

**事实**：平台配置可使用系统属性、HAL 方法、系统配置 XML、构建资源与 RRO 等；官方说明不应把系统属性作为 HAL 的旁路通信协议。[R9][]
硬件事实由相应 HAL 提供，复杂静态配置适合有明确 schema 的配置文件；资源覆盖用于产品资源差异。

**工程推导**：选择配置载体时先确定所有者、变化频率、用户作用域、类型、授权、变更通知和更新兼容。
一个全局 property 不是天然可靠的状态机，也不替代持久化事务、访问控制或类型化接口。
新增扩展应尽量缩小系统公共入口；私有 API、公共 SDK API 与模块内部 API 的发布成本不同。

## 8. 开发判断需要的最小证据

| 修改 | 必须解释的关系 | 适合的验证证据 |
|---|---|---|
| 服务启动 | 发布时点、依赖就绪、错误恢复 | boot trace、阶段日志、早期调用用例 |
| 用户策略 | 状态归属、解锁与停止行为 | 多用户场景、服务实际状态、持久化恢复 |
| 系统应用 | 包安装状态、权限、进程/组件状态 | 包信息、调用结果、生命周期测试 |
| UI 订阅 | 线程、销毁、重建与过期结果 | 配置/用户切换、重复进入、延迟回调 |
| ART 配置 | 编译产物依赖与运行状态 | 同条件性能对照、编译日志、产物版本 |

**工程推导**：构建正确模块后，还要证明运行的是该次产物。只看到开关变色、进程启动或一行成功日志，不足以说明平台状态变化正确。

## 已读官方来源

- [R1 Zygote](https://source.android.com/docs/core/runtime/zygote)：fork、ABI、USAP 与 FD 继承。
- [R2 ART 配置](https://source.android.com/docs/core/runtime/configure)：执行模式、dexpreopt 与依赖失效。
- [R3 ART JIT](https://source.android.com/docs/core/runtime/jit-compiler)：profile 和 JIT/AOT 运行机制。
- [R4 SystemService 基类](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/services/core/java/com/android/server/SystemService.java)：生命周期原始契约；使用时切换到目标 revision。
- [R5 lmkd](https://source.android.com/docs/core/perf/lmkd)：内存压力与进程回收，属性默认值随版本核实。
- [R6 预装包与用户类型](https://source.android.com/docs/core/permissions/preinstalled-packages)：包的每用户安装规则。
- [R7 特权权限允许列表](https://source.android.com/docs/core/permissions/perms-allowlist)：分区、授权和 vendor 限制。
- [R8 RRO](https://source.android.com/docs/core/runtime/rros)：资源映射与覆盖范围。
- [R9 配置机制](https://source.android.com/docs/core/architecture/configuration)：属性、HAL、XML 与资源配置的用途。

[R1]: https://source.android.com/docs/core/runtime/zygote
[R2]: https://source.android.com/docs/core/runtime/configure
[R3]: https://source.android.com/docs/core/runtime/jit-compiler
[R4]: https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/services/core/java/com/android/server/SystemService.java
[R5]: https://source.android.com/docs/core/perf/lmkd
[R6]: https://source.android.com/docs/core/permissions/preinstalled-packages
[R7]: https://source.android.com/docs/core/permissions/perms-allowlist
[R8]: https://source.android.com/docs/core/runtime/rros
[R9]: https://source.android.com/docs/core/architecture/configuration
