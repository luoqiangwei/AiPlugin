# Feature launch flags 的声明、发布与测试语义

用于 aconfig、release config、构建 flag、尚未发布代码的集成，以及按 flag 选择测试。
资料核实于 2026-10-28；先固定分支、产品、release config、模块/容器和生成代码版本。
较旧分支不一定提供这些模块类型、运行时工具或 JUnit 规则；本页描述当前官方模型，实际名称与限制以 checkout 为准。

## 三类 flag 的生效时机不同

| 类型 | 值的性质 | 适合控制什么 | 不能假设什么 |
|---|---|---|---|
| Read-write aconfig | 可运行时覆盖的布尔值 | 测试/发布时选择行为路径 | 改值后所有已启动进程立即刷新 |
| Read-only aconfig | 运行时不能改变的布尔常量 | 稳定发布行为及可能的未启用代码剔除 | 所有编译器都会移除未执行代码 |
| Build flag | 构建期字符串常量 | prebuilt、依赖、构建系统或 aconfig 可用前的选择 | 可用 aflags 在设备上改变 |

[Determine flag usage and type](https://source.android.com/docs/setup/build/feature-flagging/determine-flag)规定这些区别及适用场景。
当前 feature launch flag 的整体目的，是隔离可能破坏分支稳定性的未发布行为；是否需要 flag 取决于变更风险，而不是每个注释修改都加开关。
旧版 DeviceConfig、sysprop 与普通产品布尔变量也有各自机制，不能仅因都叫 flag 就套用 aconfig 存储和测试规则。

关闭路径必须保持既有契约，开启路径也不能在第一次读 flag 前就无条件写新数据或改变外部协议。
持久格式、API、跨进程状态一旦被发布或写入，关闭执行分支不自动撤销已有影响；这是对 flag 隔离目的的工程约束。

## 从声明到运行时读取是一条构建链

`.aconfig` 声明包括 package、container 以及 flag 的 name/namespace/description 等信息；package 与 name 形成唯一键。
container 表达一起构建交付的代码集合，例如分区或特定 APEX/APK；不能凭包名推断实际容器。
当前[声明文档](https://source.android.com/docs/setup/build/feature-flagging/declare-flag)限定：不随 APEX 或 system partition 构建的 APK，不支持照此使用 flags。
向 AOSP 贡献时 namespace 等元数据需按官方贡献流程协调，自有镜像则可采用自己的命名体系；不要把文档演示值当作已分配命名空间。

声明需要进入 Soong 的 `aconfig_declarations`，再由相应语言生成库提供 accessor，消费者显式依赖该库。
Java、C/C++、Rust 访问器不是手写一个同名常量的替代物；生成器、库变体与运行端 flag 存储必须相容。
C/C++ 和 Rust 的 `cc_aconfig_library`/`rust_aconfig_library` 等模块应匹配消费者 host/device、vendor/product 等实际变体。
静态链接和动态链接带来的额外 runtime 依赖按目标[生成库集成规则](https://source.android.com/docs/setup/build/feature-flagging/declare-flag)核实，不能用复制生成文件掩盖 missing variant。

诊断应分别确认声明被收集、accessor 正确生成、消费者确实使用该版本库、运行容器能取得该 flag，以及代码分支真的执行。
只看到 `.aconfig` 文件或模块编译成功，不能证明设备具备正确 flag 值。

## Release config 决定构建默认值

当前模型默认 flag 为 DISABLED/READ_WRITE；flag values 文件为具体配置指定 state 与 permission。
release config 汇总一组 flag values，`lunch` 选择产品和 variant 时还会选择相应 release config；具体 lunch 字符串随分支演进，不能固定官网某次示例。
`aconfig_values`、其值集合与构建配置须能对应到声明 package/name，漏接构建链不能由设备端手工 enable 补成正式发布默认值。
[Set feature launch flag values](https://source.android.com/docs/setup/build/feature-flagging/set-values)解释这些关系，并区分用于开发与正式发布的配置。

一般发布配置更多使用只读 flags，开发配置允许对读写 flags 做运行时实验；这是当前官方配置策略，不是每个 OEM fork 必须采用相同目录名字。
Google 提供的 release configurations 不接受任意贡献者直接改变其发布值；自有 fork 可定义自己的配置。
评审应记录该功能在实际产品配置中的最终值，而不是仅引用声明默认值或某个开发机 override。

## Build flag 要同时核对类型和空值

build flag 通过 `build/release/flag_declarations` 中的 textproto 声明，命名、workflow、containers 和默认值遵守当前构建 schema。
LAUNCH 面向启用过程，PREBUILT 常用于选择版本或预置内容；不能把字符串版本 flag 按普通布尔解释。
布尔 true 编码为 `"true"`，false 编码为空串，尤其 Make 条件应按空串比较，字符串 `"false"` 不是等价 false。
[Declare and use a build flag](https://source.android.com/docs/setup/build/feature-flagging/build-flags)说明 Soong `release_flag`/`select` 与 Make 只读变量的访问方式。

用于依赖选择的 flag 可能改变最终镜像中是否存在某库或二进制，因此“关闭后不调用它”不等于关闭组合仍能构建和启动。
检查开启/关闭两种构建图、required/链接依赖、安装集合及早期启动消费者；运行时覆盖不能补回未打包的文件。
解析 schema 或 Make/Soong 语法错误时先查该分支实现，不将官网示例中的命名笔误复制进产品配置。

## 运行时覆盖需要确认实际生效时点

只有 RW aconfig 值可用运行时工具改变；只读值需要改变构建配置并重新生成相应产物。
当前[运行时修改教程](https://source.android.com/docs/setup/build/feature-flagging/flip-a-flag)使用 `aflags` 查询/覆盖，并在重启后核对值及功能行为。
不能由一次 enable 命令返回成功就推断所有进程内已缓存 accessor 值或长生命周期对象都采用新状态；具体刷新与持久化以目标实现为准。

记录完整 flag 键、原值、构建默认值、覆盖值、进程/设备重启情况及观察到的行为。
测试结束应恢复原状态，防止后续测试误用开发者覆盖值；“清掉 override”与“把值写回某个猜测默认值”含义不同。

## 测试规则同时约束值和 fixture 生命周期

官方[flags 测试规则](https://source.android.com/docs/setup/build/feature-flagging/test-with-flags)要求覆盖启用与关闭行为、使用官方设值机制，并且 xTS 测试不应覆盖设备 flags。
因此一套能 override 的内部单元测试，不能直接照搬为 xTS 对设备发布配置的验证。

| 场景 | 当前官方机制 | 应观察的边界 |
|---|---|---|
| Java/Kotlin 单元测试设值 | SetFlagsRule、EnableFlags/DisableFlags | 目标代码和 fixture 读取发生在规则控制期内 |
| 多 flag 组合 | FlagsParameterization | 运行/跳过的组合是否符合用例条件 |
| 端到端设值 | FeatureFlagTargetPreparer | 测前修改、设备准备、测后恢复 |
| 不能设值的设备验证 | CheckFlagsRule、RequiresFlagsEnabled/Disabled | 按实际值过滤，不能把跳过算作断言通过 |
| Native flag 条件用例 | TEST_WITH_FLAGS/TEST_F_WITH_FLAGS 等 | 所需 flag 条件及实际执行数量 |

方法级 SetFlagsRule 通常围住 `@Before`/测试/`@After`，但测试对象构造与 `@BeforeClass` 可能更早。
如果 fixture 构造时读取 flag，应按文档使用 ClassRule/类级条件或调整构造时点；不能因为测试方法上加了注解就认定构造期也使用该值。
规则初始化取设备值，包括可能存在的运行时 override；未显式设置的其他 flag 因产品 release config 而变。
测试日志应保留必要的配置和跳过原因，避免把不同设备默认值造成的覆盖差异误报成完全相同测试。

组合测试有成本：allCombinationsOf 是指数级组合，progressionOf 是逐步推进，二者不能互相声明同等交互覆盖。
选取组合应对应真实共享状态或依赖关系，既不能只测默认值，也无需为无交互 flag 盲目制造完整笛卡尔积。
关闭、开启、恢复后的行为都应落在真实入口；通过 mock 绕过 accessor 或只断言 getter 返回值，不能证明功能隔离正确。

## 常见失败的机制定位

| 现象 | 先核对 | 不应直接采取的捷径 |
|---|---|---|
| flag 已声明但始终 false | values 被哪套 release config 收集、容器、完整键和生成库 | 在客户端硬编码 true |
| 一些进程变了、另一些没变 | 生命周期、缓存、运行时覆盖生效阶段与活动模块 | 加 sleep 假定完成传播 |
| 只在关闭配置链接失败 | build flag 选依赖与实际安装图 | 将全部依赖永久装入产品 |
| 单元测试值正确但对象行为旧 | fixture 构造时点、静态初始化和规则范围 | 每个断言前反复覆盖值 |
| xTS 大量跳过 | 设备发布值、条件注解与实际执行统计 | 把跳过记成所有模式通过 |

本页没有修改设备值或运行测试；它将官方 flags 子主题提炼为构建、生效和验证的关系，供目标分支实际实现复核。
