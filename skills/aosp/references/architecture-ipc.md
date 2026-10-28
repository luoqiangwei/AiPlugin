# 架构边界、Binder、AIDL 与 HAL

内核产物与模块见[内核构建/GKI](kernel-build-gki.md)，独立系统组件的职责见[Mainline 模块契约](mainline-module-contracts.md)，native 分区版本边界见[页大小与 ABI](native-page-size-abi.md)。

用于定位跨进程调用、系统与厂商边界、HAL 扩展和接口演进。本文是原创机制提炼，不替代目标分支的接口声明。
“事实”来自文末已读官方资料；“工程推导”表示据这些机制形成的设计和定位判断。资料核实于 2026-10-28，版本敏感行为须回到目标 branch。

## 1. 六种边界不能互相代替

**事实**：Android framework 的客户端代码可以运行在应用进程；系统服务还包含独立 native 服务，并非都在 `system_server`。[A1][]
源码目录、Soong 模块、安装分区、Linux 进程、服务接口及更新单元描述的是不同关系。

| 边界 | 回答的问题 | 典型定位证据 |
|---|---|---|
| 源码与构建模块 | 哪个仓库、模块生成这段实现 | manifest revision、构建文件、依赖图 |
| 分区 | 产物放在哪里，与哪些镜像一起交付 | 安装规则、目标产物清单 |
| 进程 | 谁执行代码，谁持有状态与资源 | 进程名、UID、SELinux 域、启动配置 |
| IPC 接口 | 谁可调用，数据和错误怎样传输 | AIDL/HIDL、服务注册、客户端代理 |
| 模型与策略 | 哪个组件解释状态和业务规则 | 状态所有者、调用链、持久化位置 |
| 更新单元 | 哪些实现可以独立替换 | APEX/APK、分区更新策略、稳定契约 |

**工程推导**：先画“入口 → 客户端库 → IPC → 服务 → HAL/驱动 → 回调”的实际调用链。
看到包名不能确定运行进程；看到 `frameworks/` 不能确定安装分区；新建接口也不自动创建隔离边界。
一项功能跨多个边界时，应分别记录接口所有者、状态所有者和失败责任，不能只画层次图。

## 2. Treble 解决更新耦合，不消除硬件差异

**事实**：system、system_ext、product 等承载不同系统内容；vendor、odm 等承载硬件与产品实现；分区布局随发布和设备变化。[A2][]
Treble 通过稳定接口分开框架与厂商实现，VINTF 描述相互提供与要求的能力。分离使系统更新可以减少对硬件实现同步更新的依赖。[A2][]
这不是任意 system 与任意 vendor 都能组合；具体兼容匹配见 [compatibility.md](compatibility.md)。

**工程推导**：跨分区变化要追踪实现、声明、链接依赖和更新组合，不仅验证当前整机能启动。
`vendor` 源码禁止修改属于具体项目约束，不能由分区名称推出；设备上分区的挂载属性也不是源码访问策略。
不要把厂商功能无条件塞入 framework，或以私有库链接绕过正式接口：二者都会扩大更新耦合。

## 3. Binder：远端调用带来执行和失败边界

**事实**：客户端 proxy 将节点、方法和参数打包为 transaction，经内核 Binder 驱动交给服务进程线程；服务执行后可返回 reply。[A3][]
同一后端的同进程 AIDL 调用可能直接进入本地对象，不发生同样的打包与远端调度。[A5][]
因此本地替身不能证明跨进程序列化、身份、死亡和调度行为正确。

**工程推导**：接口契约至少说明输入有效性、结果含义、传输失败和业务拒绝的区别。
服务名可查询不代表服务已就绪；拿到 Binder 引用不代表远端始终存活。死亡后的失效、重连及未完成请求由协议设计处理。
远端调用超时或客户端取消也不能直接证明远端副作用未发生；需要用实际请求状态和幂等语义作判断。

## 4. 同步、oneway、并发与重入

**事实**：未标记 `oneway` 的方法是同步调用，即使返回 `void` 也会等待回复；`oneway` 不等待远端业务执行完成。[A4][]
同一 Binder 节点的异步 transaction 被串行处理，但可能落到不同线程；不同节点不共享这个串行保证。[A4][]
同步调用链可嵌套回到原进程并复用调用线程；单个 Binder 线程不等于没有重入。[A4][]

**工程推导**：不要把 `oneway` 当作可靠消息队列、完成确认或无限缓冲。需要确认的操作要有结果协议和积压处理。
线程池大小不修复错误锁序。优先解释“谁持锁、谁等待谁、回调运行在哪条线程”，再决定锁外调用或任务派发。
把同步接口改成异步接口会改变完成时点、顺序、错误可见性和调用身份，不能当成仅优化性能的改动。
锁外调用也需保护状态快照与返回后的状态更新；放开锁后状态可能已被其它请求改变。

## 5. AIDL 的三层含义

**事实**：AIDL 描述跨进程类型与方法，并生成语言后端；Structured AIDL 的类型由 AIDL 完整描述；Stable AIDL 进一步跟踪和版本化接口兼容性。[A5][][A6][]
结构化不自动等于稳定，生成接口也不自动等于公共 SDK API。
独立更新的平台组件之间使用 AIDL 时，需要 Stable AIDL；适用边界包括相应版本的 APEX 和 HAL。[A5][]

稳定演进通常允许追加方法、带默认值的字段等受限变化；新客户端调用旧服务的新方法仍可能得到“不支持”，应协商能力或降级。[A6][]
API 更新与版本冻结是不同操作：前者同步当前描述，后者形成已发布版本与 hash；不能改写旧版本快照来消除不兼容。[A6][]
`aidl_interface` 的 `stability` 属性只支持 `"vintf"`；不设置且未标记 `unstable` 时仍检查向后兼容，承诺范围是同一 system 或 vendor 编译上下文。[A6][]
因此稳定的 system 内部接口不必是 VINTF 接口，也不存在通用的 `stability: "system"` 配置；接口版本化与跨 system/vendor 承诺是不同维度。

**工程推导**：设计新字段时先回答“旧服务忽略它是否仍安全”；设计默认值时先回答“未支持该能力是否会被误认为成功”。
区分 transport status、服务特定错误和可恢复状态；不要把所有失败压成一个布尔值或捕获异常后返回成功。
接口版本、导入版本及进程依赖必须共同检查，不能只看被编辑的 `.aidl` 文件。

## 6. HAL：标准接口与设备实现的分界

**事实**：HAL 将标准能力与硬件实现分开。Binderized HAL 独立于客户端进程运行，但历史上还存在受限 same-process HAL、legacy/wrapped HAL。[A7][]
新实现优先 AIDL；已有 HIDL HAL 仍受支持，目标上游接口使用 HIDL 时应遵循该接口。[A7][][A8][]
因此既不能为旧产品强制全量迁移，也不能照历史例子为新接口默认选 HIDL。
**资料差异**：HIDL 概览写 Android 10 起弃用，HAL 概览写 Android 13 起弃用；AIDL HAL 文档又以 Android 11 引入其支持为界。[A7][][A8][][A9][]
这些页面的历史措辞不能合成“某年全平台切换”的统一规则。实际迁移要查目标接口、发布要求、已交付版本与源码，不以单个年份判定旧接口非法。

**事实**：使用 AIDL 跨 system/vendor 的 HAL 需要 Stable AIDL、相应 VINTF 稳定性与声明。[A8][]
在该适用范围内，各 AIDL 类型定义标记 `@VintfStability`，对应 `aidl_interface` 设置 `stability: "vintf"`；接口所有者维护声明，服务实例还要列入相应 VINTF manifest。[A8][]
发布时需配套冻结版本/API dump 与 hash、生成库的版本依赖、manifest 声明和真实注册实例；目标分支相关 VINTF/VTS 检查会核对冻结与声明/服务版本，单加注解不构成完整集成。[A6][][A8][]
Native vendor 实现应使用该发布支持的稳定后端，例如 NDK 后端及 `libbinder_ndk`，不能把不稳定 C++ `libbinder` 当跨分区 ABI。[A8][]
同分区通信没有一律采用 VINTF Stable AIDL 的要求，但若组件独立更新，仍需按其更新契约判断。

**工程推导**：HAL 新功能要检查标准接口是否已有表达方式，再选择扩展；复制一个私有接口会长期增加适配与维护成本。
实例名、注册名、manifest fragment、客户端查询和测试发现机制必须一致。
把 XML 声明补齐不能替代 HAL 行为实现；服务能注册也不能证明所有必要实例或方法可用。

## 7. 用证据判断问题落在哪一层

| 现象 | 先核对的机制 | 有价值的证据 |
|---|---|---|
| 找不到服务 | 产物、启动、注册与声明 | 目标镜像、init 配置、服务注册日志、VINTF |
| 仅跨进程失败 | 编组、身份、线程、远端版本 | transaction 错误、调用 UID、接口版本 |
| 偶发卡死 | 同步调用链、持锁调用、线程池饱和 | 各方同时刻线程栈、锁等待、调度轨迹 |
| 升级后失效 | 稳定接口、导入版本、更新组合 | 新旧客户端/服务矩阵、冻结 API、manifest |
| 回调顺序错误 | 节点边界、任务队列、生命周期 | 节点实例、请求序号、派发与销毁时序 |

**工程推导**：结论必须落到具体调用、状态或契约。仅因“跨层调用”“用了回调”或“目录不整齐”不能判定架构缺陷。
最小修复应保留原有安全与发布边界，并能用修前失败、修后通过的场景解释收益；架构迁移另需证明收益。

## 已读官方来源与使用边界

- [A1 架构概览](https://source.android.com/docs/core/architecture)：客户端 framework 与系统服务职责；概览图不替代实际进程布局。
- [A2 分区](https://source.android.com/docs/core/architecture/partitions)：分区职责和更新关系；分区集合按目标设备核实。
- [A3 Binder 概览](https://source.android.com/docs/core/architecture/ipc/binder-overview)：proxy、node、transaction 与 reply。
- [A4 Binder 线程](https://source.android.com/docs/core/architecture/ipc/binder-threading)：同步、异步、节点串行、重入与锁。
- [A5 AIDL 概览](https://source.android.com/docs/core/architecture/aidl)：IPC 与独立更新边界。
- [A6 Stable AIDL](https://source.android.com/docs/core/architecture/aidl/stable-aidl)：版本、冻结、兼容字段与新旧服务交互。
- [A7 HAL 概览](https://source.android.com/docs/core/architecture/hal)：binderized、same-process 和历史实现。
- [A8 AIDL HAL](https://source.android.com/docs/core/architecture/aidl/aidl-hals)：分区边界、后端与 VINTF 约束。
- [A9 HIDL 概览](https://source.android.com/docs/core/architecture/hidl)：历史接口及弃用措辞；与 HAL 概览的年份表述存在差异。

[A1]: https://source.android.com/docs/core/architecture
[A2]: https://source.android.com/docs/core/architecture/partitions
[A3]: https://source.android.com/docs/core/architecture/ipc/binder-overview
[A4]: https://source.android.com/docs/core/architecture/ipc/binder-threading
[A5]: https://source.android.com/docs/core/architecture/aidl
[A6]: https://source.android.com/docs/core/architecture/aidl/stable-aidl
[A7]: https://source.android.com/docs/core/architecture/hal
[A8]: https://source.android.com/docs/core/architecture/aidl/aidl-hals
[A9]: https://source.android.com/docs/core/architecture/hidl
