# 系统配置：属性、启动依赖、资源覆盖与设备树

本页用于产品配置、属性接口、init、RRO 和 DT/DTBO 变更。核实日期：2026-10-28。
先确定目标分支、构建变体、分区归属、启动阶段和消费配置的进程/用户；相同名字不代表相同配置机制。
当前文档的版本规则分开使用：Sysprop API 为 Android 10+，RRO 的 Android 10 与 11+ 配置方式不同。
init 的具体行为优先读目标树；本文参考 Android 16 的语言说明，属性服务源码链接仅用于解释实现检查点。

## 配置并非一个全局开关系统

| 机制 | 主要消费者 | 何时产生作用 | 不能替代的东西 |
| --- | --- | --- | --- |
| 构建配置/产物 | 构建系统、镜像和启动过程 | 构建或镜像加载时 | 已运行服务的重新初始化协议 |
| system property | 有读取权限的进程及 init | 设置、读取或触发检查时 | 多字段事务和完整服务 API |
| RRO | 目标包的资源解析 | 对应用户/配置下解析资源时 | 代码替换、驱动能力或任意资源新增 |
| DT/DTBO | bootloader、内核及驱动 | 引导时选取和合并设备描述 | Android 包资源和应用设置 |

先找到真正的消费者：同一产品的 DTS、资源 bool 与属性值，可能控制完全不同阶段的工作。
配置文件存在、值可读取和功能已按新值重建，是不同证据；不要以文件名或一次读取替代完整因果链。

## 属性服务：名称、类型与 SELinux 分别约束不同问题

sysprop 是全局字符串键值接口，但现代属性定义还通过上下文和类型约束写入。[1][][2][]
名称应体现所属子系统与含义；厂商属性使用相应 vendor/odm 命名空间，避免与平台或其他分区冲突。
`property_contexts` 把属性精确名或前缀映射到 SELinux 类型；精确匹配与前缀匹配不能随意混为一条。[1][]
可声明 bool、整数、enum 等值类型；属性名看似合法，不代表值通过类型校验。
读权限与写权限分别授予，设置属性还检查调用方 SELinux 域；普通文件权限或 root 身份不是完整解释。
`ctl.*` 等控制请求还有专门处理路径，不能按普通状态属性推理其持久化或读取语义。[9][]

- 新增属性同时审查所有者、读取者、写入者、类型、默认值与生命周期。
- 使用 `get_prop`、`set_prop` 和合适的属性声明宏表达访问范围，保留必要的 neverallow 约束。
- 不能为绕过一次 denial 而给整个进程域开放一组无关属性。
- 不把安全决策建立在攻击者可写的属性上，也不假设读到配置的进程因此获得操作授权。
- 从 system/product 直接依赖厂商私有属性会破坏分区边界；需要按正式稳定配置接口设计依赖。

## 构建默认值、运行时值与持久值

构建变量可把属性写入对应分区的 `build.prop`，随后由 init 加载；构建赋值不是运行时写权限。[1][]
`ro.*` 的实现语义是首次设置后拒绝再次设置；它不等于“源码中写死”，也不等于读取者能判断来源。[9][]
新设计若只是需要限制写入者，应先考虑 SELinux 范围，不机械地给属性加 `ro.` 前缀。[1][]
`persist.*` 表达跨重启保存需求，应只在确实需要且适合属性接口时采用。
已保存的持久值与镜像默认值有加载先后；仅修改构建默认值不能证明升级设备会获得该值。
普通运行时属性的改变也不保证消费者重新读取；检查它在进程启动、每次请求还是回调时读取。
多属性连写没有自动变成一个事务；消费者不能假设看到的若干字段来自同一次配置更新。
启用异步持久属性写入的分支还需核对完成与触发顺序，不能依赖与普通 setprop 的隐含先后。[3][]

## Sysprop API：访问范围与升级稳定性是两条轴

Android 10+ 可用 `.sysprop` 描述生成有类型的访问 API，并在构建时检查接口兼容性。[2][]
schema 描述 owner、scope、access、类型和底层属性名；生成 getter 不会替代 SELinux 授权。
“公开给哪些客户端”与“未来能否改名/删改”不同；跨分区或跨独立升级模块的依赖需要稳定接口。[1][]
API 检查能发现签名层面的不兼容，不能证明默认值、单位或值含义保持兼容。
可选/缺失/解析失败的值应有明确处理；不能让默认值悄悄把配置错误伪装成合法禁用。
`legacy_prop_name` 是只读属性迁移的兼容读回退，不是任意可写属性双向同步器。[2][]
改默认值时同时推演旧 vendor、新 system 和已保存配置的组合，不只验证全新整机镜像。

## init：事件触发有时点，服务启动不等于服务就绪

init 把匹配 action 放入队列，按规则依次执行命令；其他管理工作可穿插在命令之间。[3][]
事件触发表示一次时点，属性触发表示检查时满足的条件；组合条件不是无限等待表达式。
例如 `on boot && property:x=1` 需要 boot 发生时满足条件；boot 以后把 x 设为 1 不会重放过去事件。
纯属性触发还有启动时的一次检查及之后变化检查，具体时机按目标版本语言和实现核对。
`start` 是异步启动：先 start A 再 start B，不保证 B 连接时 A 的 socket/Binder 服务已经可用。
`init.svc.*=running` 也只是进程管理状态，不能代替业务就绪、设备可用或存储已解锁。

- 用真实就绪信号、可重试连接或明确握手表达依赖，不靠固定 sleep 猜测启动耗时。
- `disabled`、`oneshot`、class 和重启策略解决不同问题；修改后检查故障恢复与重复启动行为。
- 同步命令等待不能形成循环：A 的 action 等 B，B 却需要尚未执行的 action 才能启动。
- 检查 rc 实际安装分区与 import/解析来源，不能假设修改的同名文件就是运行设备采用的那份。
- 属性触发可能因重启、恢复或重新设置再次到达；动作应按真实重复执行条件设计。

## RRO：资源映射、覆盖授权、用户状态和配置匹配

RRO 修改目标包已有资源的值，不携带替换代码；OverlayManagerService 通过 idmap2 建立资源 ID 映射。[4][]
安装成功仍可能因目标包、targetName、资源映射或策略不满足而无法生成有效 idmap。[5][]
Android 10+ 的 `<overlayable>` 声明允许覆盖的资源集合，policy 再约束来源/签名等资格。[4][]
目标存在 overlayable 时，RRO 必须正确指定相应集合；不能以同名资源绕过覆盖边界。
启停 mutable overlay 需要相应权限/目标身份；是否可覆盖与是否有权启停不是同一个判断。
overlay 状态按用户处理；系统用户不必等于前台用户，排查时记录目标进程与实际 userId。
不要把示例中的 `0`、`10` 或 `--user current` 固定解释成某种用户角色，实际设备用户拓扑可能不同。

Android 11+ 的分区 overlay 配置文件可控制启用、可变性和配置顺序；不能仅看 manifest priority。[4][]
对应配置的跨分区顺序从低到高为 system、vendor、odm、oem、product、system_ext。
Android 10 及以下主要使用静态 manifest 属性控制优先级；不要把这套数字直接套到新版配置文件。
未显式配置的 overlay 不应依赖偶然的顺序；多个 overlay 争用同一资源时，固定并验证解析结果。
即使覆盖已启用，locale、density、方向等资源限定符仍参与最佳匹配，不能只核对默认值资源。
配置变更会传播到目标，但组件缓存/重建方式仍需确认；包安装状态不能证明现有对象已更新。
诊断依次区分 package/目标存在、overlay 状态、idmap、资源映射、用户及最终解析配置。

## Device tree 与资源配置：都叫 overlay，消费层不同

DT 描述不可自动发现的硬件，DTS 编译成 DTB；DTO 让 bootloader 把设备相关 DTBO 合并到基础 DT。[6][]
DTB 的节点、属性、label 及相应 binding 是内核驱动的输入；改名会影响 overlay 引用和驱动读取。
把 SoC 基础树与设备 overlay 分离后，两者的引用关系就成为需要维护的兼容边界。[7][]
DTBO 合并成功仅证明结构可合并，不证明 regulator、时钟、GPIO、中断或硬件电气配置正确。
同时检查最终合并树、实际选中的 overlay、内核 binding 和驱动探测日志，而非只看某份 DTS 源码。
DTB/DTBO 的存储位置、条目选择及 A/B 配对以目标 bootloader/镜像格式为准；不是所有设备都同布局。[7][][8][]
这些描述参与启动信任链；修改分区位置时同步考虑验证与更新一致性，不以手工复制替代镜像集成。
Android 12 且内核 5.10+ 的 `androidboot.dtbo_idx` 传递方式涉及 bootconfig，旧命令行示例有版本条件。[10][]
RRO 调整 framework 资源无法修复驱动读错硬件节点；改 DTBO 也不会自动启用某个用户的应用资源覆盖。

## 诊断时保存的最小因果证据

| 问题 | 有辨识度的证据 | 不能直接下的结论 |
| --- | --- | --- |
| 属性设不进去 | 调用域、属性上下文/类型、返回错误、首次写入来源 | 一律缺 root |
| 新默认值没生效 | 分区产物、持久旧值、加载时间、消费者读取点 | 构建系统忽略了改动 |
| 开机偶发失败 | action/触发时间、进程启动、真实就绪信号、依赖环 | 加 sleep 就修复依赖 |
| RRO 不生效 | target/user、状态、idmap、最终资源限定符 | APK 已安装所以覆盖代码有 bug |
| 硬件配置不符 | 选中的 DTBO、合并树、binding、驱动探测 | 修改任意同名配置就能影响设备 |

## 已核实的官方来源

1. [Add system properties：名称、类型、SELinux、稳定性与构建赋值](https://source.android.com/docs/core/architecture/configuration/add-system-properties)
2. [Sysprop APIs：Android 10+ schema、生成 API 与兼容检查](https://source.android.com/docs/core/architecture/configuration/sysprops-apis)
3. [Android 16 init language：触发、队列、服务选项与异步 start](https://android.googlesource.com/platform/system/core/+/android16-release/init/README.md)
4. [RRO：overlayable、用户、idmap 与 Android 11+ 配置顺序](https://source.android.com/docs/core/runtime/rros)
5. [RRO troubleshooting：状态、目标和映射诊断，注意 Automotive 示例范围](https://source.android.com/docs/core/runtime/rro-troubleshoot)
6. [Device tree overlays：DTB/DTBO 的消费边界](https://source.android.com/docs/core/architecture/dto)
7. [Implement DTOs：兼容、分区、A/B 与信任链](https://source.android.com/docs/core/architecture/dto/implement)
8. [DTB and DTBO partitions：表结构与条目选择](https://source.android.com/docs/core/architecture/dto/partitions)
9. [Property service 源码：当前主干的权限、类型与持久写入检查点](https://android.googlesource.com/platform/system/core.git/+/master/init/property_service.cpp)
10. [Compile and verify：合并验证、overlay 索引与 bootconfig 条件](https://source.android.com/docs/core/architecture/dto/compile)

[1]: https://source.android.com/docs/core/architecture/configuration/add-system-properties
[2]: https://source.android.com/docs/core/architecture/configuration/sysprops-apis
[3]: https://android.googlesource.com/platform/system/core/+/android16-release/init/README.md
[4]: https://source.android.com/docs/core/runtime/rros
[5]: https://source.android.com/docs/core/runtime/rro-troubleshoot
[6]: https://source.android.com/docs/core/architecture/dto
[7]: https://source.android.com/docs/core/architecture/dto/implement
[8]: https://source.android.com/docs/core/architecture/dto/partitions
[9]: https://android.googlesource.com/platform/system/core.git/+/master/init/property_service.cpp
[10]: https://source.android.com/docs/core/architecture/dto/compile
