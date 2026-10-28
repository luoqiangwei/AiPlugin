# 平台测试与诊断证据

测试模块与 XML、Tradefed 生命周期、run failure、重试/分片、多设备和 VTS 实例发现见[测试基础设施](test-harness-infrastructure.md)。本页提供测试选择和故障诊断的总体模型。

基线核实日期：2026-10-28。测试目标、参数、依赖设施及结果格式以目标分支为准。
本页解释测试能证明什么，以及如何从日志、堆栈和时间线区分机制。
测试未执行、未发现用例、被跳过、环境失败和断言通过必须分别描述。

## 测试类型与执行位置

Host test 在主机执行；其中一部分仍会驱动设备，因此 host-side 不自动等于无设备依赖。
Instrumentation 在目标 Android 运行时中执行，适合真实组件、权限与生命周期交互。
Native GTest 适合 C/C++ 模块，是否需要设备由依赖决定，而非测试语言决定。
性能基准采集指标，功能测试判断行为；两者的环境控制和失败含义不同。

| 测试边界 | 可以提供的证据 | 留下的空白 |
|---|---|---|
| 纯 host 单元测试 | 算法、不变式、序列化与边界处理 | Android 运行时和实际 HAL 行为 |
| 设备 instrumentation | Framework 契约、权限、组件集成 | 未覆盖硬件和跨版本组合 |
| 设备 native 测试 | 实际 ABI、库、驱动/HAL 接口行为 | 未测量的长期并发和性能 |
| 真实设备场景 | 用户路径及真实硬件集成 | 其他产品、配置和升级路径 |

测试替身有利于定位模块行为，但不能替代对真实 Binder、存储或硬件边界的必要验证。
测试是否有效，要看触发了哪个调用链和断言了哪个可观察结果。

## Atest 与 Tradefed

Atest 定位测试目标，驱动构建、安装和执行；可按模块、类、方法或路径选择测试。[Atest][atest]
Tradefed 提供设备准备、运行器、结果报告与清理等测试框架能力，测试配置决定实际副作用。
同一测试名可能受 filter、ABI、设备特性和参数影响而执行不同集合。

`--dry-run` 只能确认计划，不代表执行通过；只构建测试目标也不证明断言已执行。
`--host` 用于无需设备的执行方式，不能让本来需要设备的 host-driven 测试自动脱离设备。
失败应区分准备失败、安装失败、runner 崩溃、超时和断言失败。
重试可帮助识别不稳定性，但重试成功不会抹去原失败的环境和时序证据。

## TEST_MAPPING 的选择语义

`TEST_MAPPING` 把源码目录与 presubmit、postsubmit 等测试组关联起来。
Atest 可读取当前或指定目录及父目录的映射；imports 还会扩大实际集合。[映射机制][mapping]
它不是“当前目录中所有测试自动运行”，新增文件也不必然获得正确回归覆盖。

模块名、filter、imports、host 标记与分组要匹配真实测试定义。
重命名模块或迁移目录后，原映射可能失效；仅看 JSON 格式合法不足以保证用例被发现。
测试修改的系统状态需恢复，不能依赖前一个测试留下的账号、权限、设置或 root 状态。
隔离清理失败会让后续失败伪装成产品缺陷，报告中应保留准备与清理阶段日志。

## CTS、VTS、STS 与 GTS 的边界

| 套件 | 主要目的 | 适用边界 |
|---|---|---|
| CTS / CTS Verifier | Android 公开兼容性及需人工介入的能力验证 | 按目标 Android 版本、设备能力及发布要求选择 |
| VTS | HAL、内核及相关厂商接口验证 | 与设备实现和接口组合匹配 |
| STS | 已知安全问题和补丁的回归验证 | 按适用漏洞、版本及补丁基线解释结果 |
| GTS | Google 服务相关的合作测试要求 | 闭源且受相应产品/合作范围约束 |

CTS 覆盖 API 签名、行为、权限和资源等兼容性，但不是全部内部实现回归。[CTS][cts]
VTS 可包含 GTest、内核及 host-driven 测试；一个 HAL 功能演示不能替代接口兼容验证。[VTS][vts]
安全补丁回归需要可证明的安全边界与目标版本；没有触发崩溃不等于漏洞不存在。[安全回归机制][security-tests]
GTS 不能从 AOSP checkout 推定已安装或有权运行，也不能用公开 CTS 结果声称 GTS 通过。[官方 GTS 边界说明][gts]

局部功能开发选择相关回归；整机兼容性或正式发布还需遵循产品既定的完整验证要求。
“本次不需要跑全套”与“该产品没有兼容性义务”是不同判断。

## Fuzz 与内存错误

Fuzz harness 把变化的输入送入真实解析器或服务边界，sanitizer 辅助发现越界、UAF 等问题。[libFuzzer][fuzz]
输入 corpus、字典、harness 状态重置与可达代码决定有效覆盖，运行时长本身不能代表质量。
Harness 若把错误输入全部过滤掉，或用 fake 替换目标解析器，可能得到毫无意义的“零崩溃”。

Native、Binder/AIDL、文件格式和协议入口有不同状态空间，需选择实际风险边界。
异常、超时、资源泄漏及逻辑绕过可能没有 native crash，不能只把崩溃计数作为安全结论。
每个可复现问题应保留最小输入、架构、构建模式、sanitizer、符号及对应 revision。
修复后保留能触发真实缺陷的回归输入，避免只断言与实现同构的内部判断。

## Tombstone 与 native 崩溃

Native crash 的 signal、code、fault address、abort message、线程和 maps 共同约束原因。
SIGABRT 常是主动终止，应先读 abort message 和更早日志，不能一律归为野指针。[崩溃机制][native-crash]
SIGSEGV 的出错指令可能只是更早内存破坏的结果，顶层栈不是天然的根因位置。

符号化需要匹配 ABI、Build ID 与未剥离二进制；相似版本的 symbols 会产生看似合理的错误行号。
完整 tombstone 还能解释其他线程、映射和持有资源，截取首帧常会丢失关键上下文。
收集时保留进程、线程、时间和 fingerprint，区分同名进程的多次重启。

## ANR、watchdog 与死锁

ANR 表达某种响应时限被违反，其超时类型与触发条件需结合目标版本和 reason 字段判断。
主线程等待、Binder 服务阻塞、CPU 饥饿、I/O 和系统负载都可能参与同一超时。[Bugreport 诊断][bugreports]
采样堆栈只代表采样时刻；它可能晚于真正的长时间阻塞，不能仅凭一张栈确定因果。

死锁需要找到等待关系，例如 A 持有锁 X 等待 B，而 B 需要 X；Binder 回调也可能形成等待环。
线程池耗尽会使请求排队，即便没有锁环也可导致系统失去响应。
系统 watchdog 杀死 `system_server` 与内核重启不同，应结合启动原因、进程重启和 pstore 区分。
延长 watchdog 或吞掉超时只能改变症状，不说明锁顺序、远端调用或资源压力已修复。

ANR 的完成条件与计时区间按类型区分：input dispatch 等待输入响应；同步广播关注处理返回，`goAsync()` 广播还需在期限内完成 `PendingResult.finish()`；service 等类型有各自条件。
异步派发不自动结束超时责任，主线程空闲也不能排除负责广播的其他线程阻塞。[ANR 分类机制](https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs)

`system_server` Watchdog 的 `HandlerChecker` 向被监控 Handler 安排检查，并运行该 checker 登记的 `Monitor`；完成状态取决于检查任务与 monitor 是否完成。
因此需要区分任务还未获调度、Handler 上已有工作阻塞、以及检查任务进入 monitor 后受阻；报告中的 blocked handler/monitor 与同时刻线程栈可帮助定位。
检查存在完成、等待、预警与超期等状态，暂停、调试与超时配置还会影响处置；注册对象、状态名和阈值按目标分支实现核实，不固定成所有 Android 版本的同一个秒数。
[Watchdog 实现依据](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/services/core/java/com/android/server/Watchdog.java) 是机制定位入口，正式结论引用实际 revision。

## Perfetto 与时序归因

Perfetto 可在同一时间线中关联调度、频率、用户空间标记及其他数据源。[系统跟踪][perfetto]
Trace 配置、buffer、采集窗口和事件丢失决定可解释范围；未采到事件不代表事件未发生。
耗时较长可能包含执行、可运行等待、睡眠或远端工作，不能直接等同 CPU 消耗。

例如 Binder 调用慢，应关联客户端阻塞、服务端排队/执行与调度，而非只统计客户端函数总时长。
性能比较需要一致的负载、温度、电源模式、构建类型与量测区间。
改动前后一次运行的差值不自动等于稳定收益；测试次数与统计方式由噪声和风险决定。
采集工具也有开销，长时间重负载 trace 可能改变原问题，应记录采集配置。

## 让结论与证据相符

| 结论 | 足够支持它的证据形态 | 不能替代的材料 |
|---|---|---|
| 回归测试通过 | 明确用例、执行数量、断言结果与环境 | dry-run、只编译、零用例 |
| 设备场景已验证 | 匹配产物、真实调用、结果与关键日志 | 仅单元测试或安装成功 |
| 根因为死锁 | 时间匹配的线程、锁与跨进程等待环 | 单个线程的 blocked 标签 |
| native 修复有效 | 原复现输入失败被修复且相关行为仍正确 | 删掉断言或忽略 signal |
| 性能改善 | 可复现负载、匹配配置、可解释的重复量测 | 一次主观感觉或不同硬件比较 |
| 兼容性已满足 | 对应版本及范围的套件和产品要求证据 | 任意一个测试模块通过 |

环境缺失时，应报告已执行的部分、未执行的原因与剩余证据，保留可复现命令和必要产物定位。
敏感日志与安全复现产物按项目权限保存；诊断本身不要求对外上传 bugreport。

## 官方依据与版本复核

以下页面已阅读。套件版本、Atest 参数、测试模块名与日志字段需在目标分支复核。
较旧文档中的固定超时、进程名、路径或输出示例，不应作为所有 Android 版本的硬规则。

[atest]: https://source.android.com/docs/core/tests/development/atest
[mapping]: https://source.android.com/docs/core/tests/development/test-mapping
[cts]: https://source.android.com/docs/compatibility/cts
[vts]: https://source.android.com/docs/core/tests/vts
[security-tests]: https://source.android.com/docs/security/test/autorepro
[gts]: https://source.android.com/docs/core/audio/combined-audio-routing#validation
[fuzz]: https://source.android.com/docs/security/test/libfuzzer
[native-crash]: https://source.android.com/docs/core/tests/debug/native-crash
[bugreports]: https://source.android.com/docs/core/tests/debug/read-bug-reports
[perfetto]: https://perfetto.dev/docs/getting-started/system-tracing
