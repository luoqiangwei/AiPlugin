# 测试模块、Tradefed 执行协议与 VTS 覆盖

用于新增平台测试模块、准备 fixtures、调试零用例/漏实例、结果上报、重试、分片和多设备实验。核实日期：2026-10-28。
先固定源码/套件版本、产品与 ABI、运行设备和镜像、test config、filters、module parameters、依赖数据与执行模式。
以下为已读官方机制；具体 runner 类、选项和默认超时按目标分支复核，历史 HIDL/VTS 示例不作为 AIDL 分支模板。

## 1. 测试类型决定进程和依赖，套件名不决定它们

**事实**：平台测试可以经 Framework API、直接 Binder/IPC 或 HAL 接口进行断言。
instrumentation、native GTest、JAR host 和 metrics tests 有不同运行环境；CTS 与平台回归也不是互斥分类。[平台测试][platform-tests] [开发工作流][development]

| 测试组织 | 运行机制与依赖 | 必须确认的边界 |
|---|---|---|
| Instrumentation | test APK 中声明 runner 和 target package，在 Android app VM 中执行 | 目标进程重启/初始化、context、权限和目标 app 签名 |
| Native GTest | native binary，由 host 或设备 runner 驱动 | ABI、动态库、数据文件、设备/HAL 服务 |
| JAR host | `java_test_host` 等在宿主 JVM 执行 | 纯 host 算法与 host-driven 设备操作分别声明 |
| Functional test | 对结果作 pass/fail 断言 | 用例/执行次数、跳过和 runner failure |
| Metric/benchmark | 按标准协议输出指标 | 工作负载、单位、生命周期、采样与统计口径 |

**工程判断**：host-side 不等于无设备，native 不等于一定在设备。测试替身只覆盖它替代的边界，不能拿模拟 HAL 成功证明真实硬件契约。

## 2. 模块可构建、被套件发现与能执行是三个条件

**事实**：Soong test 模块声明源码、库、数据和 `test_suites`；后者使测试进入相应发现/打包路径。
常规配置可自动生成；`AndroidTest.xml` 或 `test_config` 可提供特殊 setup/runner。
同一目录有多个模块时，不应依赖一个隐式配置猜测对应关系。[简单配置][blueprints] [JAR host][jar] [复杂配置][complex-config]

- `android_test` 是测试模块，`android_app` 只是 app 构建类型；APK 名可存在但没有正确 instrumentation/config，runner 仍可能发现不到用例。
- Instrumentation manifest 的 `<instrumentation android:name=... android:targetPackage=...>` 要对应实际 runner 与目标包。
- 单独 test APK 以目标 app 为 instrumentation 对象时要满足签名/测试环境契约；平台证书仅在确实需要 signature 权限/API 时使用，CTS 模块不能照抄平台证书示例。
- 额外 APK、native binary、脚本和输入数据要声明并打包，不能依赖开发者机器上的偶然路径或前一个测试的安装结果。
- `test_suites`、`TEST_MAPPING`、suite/module filters、module controller 和实际 runner 的 case discovery 分别筛选集合；命中模块名不证明所有预期 case 已进入执行。
- 自动 config 的 `require_root`、停 framework 或 API gate 会改变环境；adb root 准备并不意味着 instrumentation 进程自然成为 UID 0。

**证据链**：源码模块→构建产物/config→suite 收录→runner 枚举→开始/结束事件→断言结果。
保留实际 config 展开结果和 filters，而不只留 `atest` 命令行。dry-run/collect-only 仅证明计划与可发现性。

## 3. Fixtures：case、module、suite 与设备有不同生命周期

**事实**：连续测试要求依赖被声明并随测试提供。普通 hermetic case 不依赖人工登录、外部网络预配置、隐式参数或 harness 为单个 case 做特殊准备。
模块确需安装 helper APK、push 文件或设置设备状态时，可以使用 module config 的 preparers/cleaners。[工作流][development] [配置][complex-config]

| 作用域 | 典型责任 | 常见污染 |
|---|---|---|
| 单 case fixture | 构造输入/临时对象、结束后恢复 | 静态状态、未关资源、依赖 case 顺序 |
| Module-level setup | 模块安装、数据、设备模式 | 下模块继承账号、设置、root/服务状态 |
| Suite top-level setup | 所有模块共同运行环境 | 重复设置或把全局状态错误归给某个 case |
| Multi-target setup | 单设备准备后建立成对关系 | 一端失败仍保留另一端配对/会话 |

- `ITargetPreparer.setUp` 执行准备；清理接口是 `ITargetCleaner.tearDown`，`BaseTargetPreparer` 具有相应基础能力。准备失败时也要处理已经完成的部分。
- 每个 preparer 聚焦一个主要职责，便于复用和判断失败阶段。先查现有 PushFile/InstallApk/RunCommand 等实现，再新增自定义类。
- `PushFilePreparer` 的源/目标格式与版本有关，文件目标应完整明确；push 成功不能代替 chmod、标签或后续运行结果。
- 清理不能假定所有 setup 都已成功，也不能依赖测试一定走到最后。具体 cleaner 顺序和异常传递在目标 harness 中核实。
- 测试前读取原状态并在适当作用域恢复，比一律写固定“默认值”更能避免污染既有环境。

Suite 的 system status checker 在模块前后检查状态变化；checker 既可记录泄漏，也可能恢复部分状态。
默认 checker 问题可能仅见于日志/bugreport；是否转成显式失败由相关选项控制，不能看到测试结果全绿就判定环境已恢复。[Target preparer][target-preparer] [SSCs][ssc]

## 4. Configuration、Command 与 Invocation

**事实**：Configuration 是 XML 声明的组件集合；加上命令行参数构成 Command；Command 分配到设备后执行的完整生命周期是 Invocation。
BuildProvider、TargetPreparer、runner、result listener 分工，以便同一测试复用于不同环境和报告后端。[Lifecycle][lifecycle]

```text
BuildProvider → IBuildInfo/测试所需产物
→ TargetPreparer → 目标环境
→ runner → case/run 事件、metrics、logs
→ cleaner 与结果报告 → 完整/部分结果及各阶段错误
```

- build retrieval 失败意味着未开始测试；target setup 失败通常进入清理并报告无测试；runner/设备失败可能留下部分结果。
- reporter 的错误与产品断言失败是不同维度；多个 reporter 相互隔离，一个上传失败不能使另一个已保存结果自动消失。
- XML 中不同 tag 的文本顺序不重排生命周期；相同 tag 的多个 preparer 按声明顺序执行，先 flash 后安装与先安装后 flash 的结果不同。[XML 结构][xml-config]
- config 中类名在 harness classpath 上解析；Java 类可编译但其 JAR 未进入当前 TF 进程，仍会在加载配置时失败。
- root-level options、对象 options、device-scoped options 有不同归属；必须证明最终参数到达预期 runner/device，而不是仅确认 CLI 接受了字符串。

## 5. Runner 向 listener 报告的是一个协议

**事实**：`IRemoteTest` 通过 listener 产生 run/case 事件；设备、构建与 context 通过相应接口注入。
runner 必须维持事件顺序，异常路径也应结束已启动的 run。[新 runner][runner] [runner 结构][runner-structure]

```text
testRunStarted
  → testStarted → [testFailed / testIgnored / 其他状态] → testEnded
  → ...
  → [testRunFailed]
→ testRunEnded
```

- case 没有失败状态可能被视为 pass，因此漏掉 failure callback 会生成错误绿灯；异常被吞掉后只发 ended 不是有效测试。
- case 全 pass 仍可 run failed，例如 binary 退出码异常或泄漏；case 数为零的 run 也可能是合法协议，但不能用来证明预期 case 已执行。
- 用例失败、run failure、invocation failure、setup/cleanup failure 分别保留；不要把设备失联导致未执行的后半部分报成断言 pass。
- 用例身份要稳定，带模块、ABI/参数与实例；多个实例覆盖同名结果键会造成覆盖丢失或错误合并。
- `testLog` 的流和资源按 API 生命周期关闭；指标与文件归入实际 case/run/invocation，而不是靠文件名猜测。

**工程判断**：验证自定义 runner 时要覆盖正常、零 case、部分失败、超时/异常和设备丢失的事件收敛，不只验证返回退出码。

## 6. Metrics：同步点与度量对象必须相符

**事实**：host-driven `BaseDeviceMetricCollector` 运行在 host，通过生命周期回调采集；同步 collector 在继续下一执行步骤前完成。
`ScheduledDeviceMetricCollector` 可做周期异步采集。device-side `BaseMetricListener` 与 instrumentation 生命周期同步，更适合精确截取设备事件。[Host collectors][host-metrics] [Device collectors][device-metrics]

- host 在 `testEnded` 做长采集会推迟下一个测试；不要把采集耗时算进产品响应而又忽略其影响。
- 异步截图/温度/trace 不一定覆盖目标瞬间；记录采样时间、窗口与 test identity，而不是把最近文件当该 case 的证据。
- device collector 的类必须打入 instrumentation APK；仅传 `--device-listeners` 不能提供缺失代码。
- metrics 的 key、数值类型、单位、聚合口径与 scope 要稳定；不同 ABI/设备温度/iteration 不能无说明合并。
- suites 从顶层统一配置通用 collector，官方说明不应在每个 module 重复嵌入；同页另给 module 文件拉取配置，需按具体 collector、suite 注入方式与目标实现区分，不能把片段套给任意 collector。
- 使用 FilePuller 类协议时，设备侧输出 key/文件路径与 host 匹配规则必须一致；拉取后自动清理影响后续读取。[报告 metrics/files][report-metrics]
- API `TestMetrics`/`TestLogData`、runner metrics 和 collector 是不同入口，最终是否保存取决于配置的 result reporter。

## 7. Retry：恢复成功与原始失败同时成立

**事实**：auto-retry 由 `RetryDecision`、`retry-strategy` 和最大 attempt 数控制。
`RETRY_ANY_FAILURE` 选择失败重跑，`ITERATIONS` 重跑所有用例以探测不稳定性；次数上限是 attempt 数，crash 后某 case 未必实际执行相同次数。[Auto-retry][auto-retry]

- 默认 reporter 可收到聚合结果：Fail→Pass 能聚成 Pass。需要 `ISupportGranularResults` 等能力保留逐次结果；聚合 Pass 不能抹掉原始失败率与环境。
- case-level retry 需要 runner 正确接受 filters（如 `ITestFilterReceiver`），或实现专门 auto-retriable 契约；不支持选择性的 runner 可能无法按预期只跑失败项。
- retry isolation 默认关闭；REBOOT 与 FULLY_ISOLATED 的清理深度不同，后者会 wipe/resetup 并重跑 preparers。CTS partner 支持范围需核对，不能把它当通用无副作用 retry。[Isolation][retry-isolation]
- suite retry 会加载以前的结果和原 command，再加失败/未执行 filters；原来只选择一个模块的 session，retry 不会自动扩成全套。[Suite retry][suite-retry]
- 以前的 result/proto、配置、产物与 session 缺失会使重试选择不完整；替换镜像或修改参数后应说明实验已改变。

**工程判断**：保留每个 attempt 的首次失败、隔离等级、设备状态、准备/清理日志和未执行数量，再判断 flaky、污染或持续产品错误。

## 8. Sharding：确定、互斥、穷尽且独立

**事实**：TF 支持 local 动态分配与 distributed 指定 shard；runner 的 `IShardableTest.split` 决定可分执行单元。
同条件下分片列表和顺序必须确定，各片不能依赖前片留下的状态，集合应互斥且合计覆盖全部预期测试。[Sharding][sharding] [Shardable runner][sharded-runner]

- distributed shard 各自生成同样的全量有序列表再取子集；随机 discovery、不同 build/filter 或依赖网络状态可能导致重跑/漏跑。
- shard 数不等于设备数，也不保证负载均衡；按 class/模块切分时，少数长用例可能支配总耗时。
- `split` 返回的 runner 必须保留必要 options、filters 与依赖；新建对象丢参数可能测试了另一集合。
- TF 对分片 invocation 的完整结果聚合不能默认假定已完成；报告服务需要识别 shard identity、完整数目与失败/缺片。
- token sharding 只在支持的 local 场景分配特殊资源；声明需要 SIM 等资源但没有匹配设备，不能当作普通 pass/无条件 skip。

**工程判断**：核对完整 discovery 集合与所有 shard 的并集/交集及实际执行数。串行一次通过不能证明 shard independence。

## 9. Multi-device：一次测试同时占有多台设备

**事实**：每个 `<device>` 有唯一名字，自己的 provider/preparers/requirements/options 放入相应 scope；分配不全时 TF 释放已分配设备并等待重新匹配。
`pre_multi_target_preparer`、逐设备 preparer、`multi_target_preparer` 的时点分别用于单机准备前/单机准备/跨机准备。[多设备架构][multi-device]

- runner 通过 `IMultiDeviceTest` 或 invocation context 获取设备与 build 关联，不能靠连接列表顺序猜设备角色。
- pairing、网络拓扑、时钟、外设和对端固件也是 fixture；两设备分别启动成功不证明通信路径已经建立。
- 多设备模块和把独立测试拆到多设备的 sharding 不同；一个共同用例不能随意拆掉对端。
- Mobly suite 模块需要打包 snippets/Python 依赖、明确 binary 总超时及设备角色；不能用单设备执行模式解释缺 controller 错误。
- coverage/helper APK 应由适当 preparer 管理，取 coverage 前过早由测试脚本卸载可能丢数据。[多设备 suite][multi-device-suite]

## 10. VTS：从声明到实例执行逐层对账

**事实**：一个 HAL 接口可以有多个实例。参数化 GTest 使用实例名作为参数，在 fixture 中按实例取得服务；多个相关接口可形成实例 tuple/组合。[VTS GTest][vts-gtest]

```text
合并后的 VINTF/适用性条件 → 测试声明的目标 HAL
→ 发现的接口/版本/实例与 ABI → 参数化生成的 case
→ 实际开始/结束和 skip/failure → 结果与服务进程 coverage
```

- 硬编码 `default` 容易漏掉 vendor 命名或额外实例。声明实例、可发现实例、生成参数和实际执行实例数要对账。
- 多接口组合要说明目标集合；没有生成 case 不等于所有组合通过。
- `test_suites: ["vts"]` 决定套件收录；`general-tests` 可另供 mapping 使用。自定义 config 从自动配置起步，避免漏掉 ABI、路径、runner 和准备条件。[VTS setup][vts-setup]
- root、停 framework、超时、shipping/vendor API controller 都会改变适用集合；当前 SDK、product first API、board first/current API、vendor API 分别核对，不能互相替换。

### 历史 HIDL testability 与 service-name-aware 支持

**事实**：Android 9 文档的 compliance tests 依赖 vendor manifest 发现已声明实例；非 compliance 路径还使用 lshal 等运行时信息。
libvintf 合并 vendor/ODM/SKU 声明，测试注册其目标 HAL 后，旧框架能进行前置检查、服务名参数化和跨进程 coverage flush。[Testability][testability] [Service-name-aware][sna]

- manifest 清单、运行注册和测试 target registration 不一致时，测试可能漏实例或测错服务；只见进程存活不是完整覆盖。
- VINTF 解析要看最终合并结果；旧页面列出的路径优先级与 HIDL version 规则必须带时代，不能直接迁移到所有 AIDL HAL。
- `VtsHalHidlTargetTestEnvBase`、`getAllHalInstanceNames`、lshal 与旧 Python templates 是对应历史实现，不声明 AIDL 测试也使用相同 APIs。
- AIDL 分支应对照其当前 VINTF/servicemanager 枚举与目标测试实现，仍然保持声明→发现→生成→执行→coverage 的对账不变式。

**工程判断**：报告应分别计数不适用、未发现、未开始、环境受阻、断言失败、通过以及 coverage 未取得。测试兼容 gate 合理跳过不能掩盖设备错误声明。
VTS 功能通过只说明对应接口和条件；不等于图像/射频/时延等硬件体验已经端到端验收。

## 11. 实验环境本身也是结果输入

**事实**：Test Harness Mode（Android 10+）与 Tradefed harness 是两种机制；前者通过清除用户数据、保留 ADB keys 和跳过首次设置来简化 UI 自动化，官方明确不用于 CTS。[Test Harness Mode][testharness]

- factory reset、root、停 framework、网络配置、thermal、供电和已有账号都可能改变执行路径；执行前后保存环境，而非仅记录设备型号。
- 配置能 wipe/flash/修改设置并不代表调试零用例必须执行这些动作；先检查配置与依赖，对真实设备副作用按当前任务授权处理。
- multi-device、CTS/VTS 或真实外设测试缺设施时，保留可构建/发现证据与受阻条件，不能将环境失败改写为通过。

## 已读依据与未覆盖的专项实施

本文覆盖模块与执行协议，不宣称已逐项核实 ATS/OmniLab 云编排、旧 VTS Dashboard/数据库、所有 runner、每个 suite parameter 和所有 result reporter 后端。
这些页面仍是专项查询入口，需先明确产品测试基础设施和目标分支再提炼。

[platform-tests]: https://source.android.com/docs/core/tests
[development]: https://source.android.com/docs/core/tests/development
[blueprints]: https://source.android.com/docs/core/tests/development/blueprints
[jar]: https://source.android.com/docs/core/tests/development/jar
[complex-config]: https://source.android.com/docs/core/tests/development/test-config
[target-preparer]: https://source.android.com/docs/core/tests/tradefed/architecture/target-preparer
[ssc]: https://source.android.com/docs/core/tests/tradefed/testing/through-suite/system-status-checker
[lifecycle]: https://source.android.com/docs/core/tests/tradefed/fundamentals/lifecycle
[xml-config]: https://source.android.com/docs/core/tests/tradefed/architecture/xml-config
[runner]: https://source.android.com/docs/core/tests/tradefed/testing/through-tf/new-test-runner
[runner-structure]: https://source.android.com/docs/core/tests/tradefed/architecture/advanced/test-runner
[host-metrics]: https://source.android.com/docs/core/tests/tradefed/architecture/metrics-collector
[device-metrics]: https://source.android.com/docs/core/tests/tradefed/architecture/metrics-collector/device-collector
[report-metrics]: https://source.android.com/docs/core/tests/tradefed/testing/through-tf/report-metrics
[auto-retry]: https://source.android.com/docs/core/tests/tradefed/testing/through-tf/auto-retry
[retry-isolation]: https://source.android.com/docs/core/tests/tradefed/testing/through-tf/retry-isolation
[suite-retry]: https://source.android.com/docs/core/tests/tradefed/testing/through-suite/suite-retry
[sharding]: https://source.android.com/docs/core/tests/tradefed/architecture/advanced/sharding
[sharded-runner]: https://source.android.com/docs/core/tests/tradefed/testing/through-tf/sharded-runner
[multi-device]: https://source.android.com/docs/core/tests/tradefed/architecture/advanced/multi-device
[multi-device-suite]: https://source.android.com/docs/core/tests/tradefed/testing/through-suite/multi-devices-suites
[vts-gtest]: https://source.android.com/docs/core/tests/vts/gtest
[vts-setup]: https://source.android.com/docs/core/tests/vts/setup11
[testability]: https://source.android.com/docs/core/tests/vts/hal-testability
[sna]: https://source.android.com/docs/core/tests/vts/sna-hal-testing
[testharness]: https://source.android.com/docs/core/tests/debug/harness
