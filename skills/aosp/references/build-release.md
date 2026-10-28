# 多仓库构建、接口稳定性与发布

具体集成约束见[环境与产品集成](setup-product-integration.md)、[Feature flags](feature-flags.md)和[平台 API 契约](platform-api-contracts.md)。本页解释构建图、版本身份与发布之间的关系。

SBOM、构建来源和更新安装器的责任见[构建来源与更新归属](setup-supply-chain.md)。

基线核实日期：2026-10-28。构建命令、产品配置、工具链与发布分支均以目标 checkout 为准。
本页解释构建输入与交付物的关系，不固定某一版本的 lunch 字符串、主机配置或发布分支名。
官网与 `main` 源码是机制入口；复现问题需要实际 manifest、各仓库 revision、补丁与配置。

## Repo manifest 是系统版本的一部分

AOSP checkout 由多个 Git project 组成，每个 project 有自己的历史、工作区与提交。
Repo manifest 描述 project、path、remote、revision 及默认值；分支名可以移动，SHA 才固定具体内容。[Manifest 格式][manifest]
本地 manifest、覆盖规则与未提交补丁也会改变最终源码，单个仓库的 `HEAD` 无法代表整机版本。

| 标识 | 表达什么 | 不能替代什么 |
|---|---|---|
| manifest branch / tag | 一组项目的选取规则 | 每个 project 的实际 SHA 与本地改动 |
| project revision | 一个源码仓库的内容基线 | 其他协同仓库的版本 |
| Gerrit Change-Id | 评审变更身份 | 已合入状态、Git commit SHA |
| build fingerprint | 设备报告的构建身份 | 完整可复现输入与活动模块版本 |
| target-files / 发布产物 | 打包与签名阶段使用的系统内容 | 任意后来重新构建的 image |

跨 project 功能需要说明补丁依赖和组合，避免某个仓库单独更新后失去构建或运行兼容性。
同步或切换 revision 前应理解当前本地改动；“获取最新代码”不是修复混合版本的充分说明。

## Soong 的模块图

`Android.bp` 声明模块、源文件、依赖和变体属性，Soong 按图生成构建规则。
旧分支可能混用 Make；其他构建系统是否参与，以实际分支为准，不能从一个 README 推出全树已迁移。[Soong][soong]
产品选包、模块编译、镜像安装与运行时动态装载是相关但不同的步骤。

一个模块成功编译不说明它已进入目标产品，也不说明设备运行的是刚编译的版本。
依赖应表达真实编译与链接关系；仅通过 `required` 安装某库不能替代正确的链接依赖。
`static_libs`、`shared_libs` 和 Java/Rust 依赖属性改变链接及装载行为，不能只为消除报错随意切换。

模块名在 namespace 范围内解析，package 控制目录归属，visibility 控制其他 package 能否依赖。
扩大 visibility 可能改变架构边界；它与增加 namespace imports 解决的不是同一问题。
面对 missing variant，需解释架构、host/device、分区、SDK 或 APEX 变体为何不匹配。
直接复制源码或打开全局可见性，可能掩盖本应被阻止的依赖。

## 产品、release config 与 build variant

产品定义了硬件目标和被组合的系统能力；variant 定义开发/调试与发布行为。
`user`、`userdebug`、`eng` 在调试能力与构建属性上存在差异，调试版本通过不证明发布版本通过。[构建目标][building]
现代分支还可能在 lunch 中引入 release config；旧分支格式不同，应读取本分支 `envsetup.sh` 和产品定义。

影响有效构建输入的因素包括产品继承、BoardConfig、overlay、包列表和 feature 配置。
默认值可能被后续产品配置覆盖，所以只找到一处定义不足以证明最终值。
模块测试与增量构建适合快速反馈，镜像级依赖或 API 改动还需要覆盖受影响消费者。
没有新增变更或失败线索时，重复全树 clean build 不会自动提供更多行为证据。

## SDK、平台 API 与稳定接口

公开 SDK、System API、测试 API 与内部实现 API 有不同的调用对象与兼容性承诺。
签名文件、stub、API lint 和行为测试共同约束接口，不能只更新一个签名文件使构建通过。[API 规则][api-guidelines]
新增公开 API 应有实现、文档和可用性测试；内部 Binder 接口不宜直接作为公开 SDK 的语言契约。

`sdk_version`、`platform_apis`、`min_sdk_version` 等属性应按模块类型及分支含义核实。
改为私有平台 API 或扩大可用范围，会改变模块可发布到哪些系统及模块边界。
API 兼容不止方法是否存在，还包括权限、空值、异常、线程、生命周期与历史调用行为。
隐藏 API 不是可以任意跨版本依赖的稳定扩展口。

Stable AIDL 通过结构化类型、接口快照与版本约束管理兼容性。
其 API/ABI 校验不证明权限检查、服务状态或线程行为正确。[Stable AIDL][aidl]
新增字段和方法按兼容规则演进；不能覆盖已发布接口快照来逃避检查。
接口是否必须稳定、是否 VINTF-stable，取决于边界和版本，不是所有 `.aidl` 的统一属性。

## Native ABI 与工具链

Native 调用者依赖导出符号、数据布局、调用约定和架构，而不只是头文件文本。
ABI checker 能发现被追踪接口变化；错误的对象生命周期或语义仍需运行验证。[ABI 稳定性][abi]
VNDK 有版本适用范围，不能把其旧版本规则推广为所有新产品的统一发布模型。

保持目标分支的编译器、链接器、sysroot、生成器和构建工具输入一致，有助于复现产物。
宿主默认 clang、JDK 或 rustc 与平台预置工具链可能不同，手工命令成功不能替代平台模块构建。
更换工具链可能改变警告、代码生成、链接、sanitizer 与 ABI 结果，需要明确影响面。
混用旧 symbols 与新二进制会制造错误的崩溃定位结论，诊断应匹配 Build ID。

## Rust 模块的集成语义

平台 Rust 使用 `rust_*` Soong 模块表达二进制、库、测试、FFI 和 fuzz 目标。[Rust 模块][rust]
Cargo 的依赖及 feature 默认值不能未经转换就视为 Soong 的实际设置。
`crate_name`、模块名与装载库名称分别有作用，改名可能影响 import、链接或运行时加载。

Rust 内部库与 C ABI 的 FFI 库拥有不同边界；跨语言类型和所有权需显式设计。
`unsafe`、原始指针、回调和 FFI 仍可破坏内存安全，不能以 Rust 编译通过免除边界验证。
host 与 device 的库变体、标准库和链接方式应由模块图确定，不靠复制宿主产物替代。

## Feature flags 与发布分支

Feature launch flags 用于隔离尚未启用的行为；构建 flag 与运行时 flag 的生效阶段并不相同。[Flags][flags]
关闭路径也需保持可构建和可运行，避免“默认关闭”掩盖对共享状态的副作用。
接口表面、持久状态与跨组件协议一旦发布，关闭 flag 不保证能安全撤销它们。

公开分支、内部开发与 release snapshot 的关系随官方发布策略演进。[发布生命周期][release]
不硬编码“所有贡献必须提交 main”或把 `android-latest-release` 当成永久固定的代码版本。
提交目标应从目标项目与当前官方贡献说明确定，第三方上游组件可能需先向上游贡献。
安全维护与产品 backport 还需明确补丁前置依赖及目标旧分支的语义差异。

## Gerrit 变更与可复现交付

Gerrit 对每个 Git project 的提交进行评审，Repo 协调多仓库工作区。
一个 Change-Id 的多次 patchset 是同一评审的迭代，不等于多个独立功能版本。[提交机制][contribute]
跨仓库 topic 可以表达相关变更，但不能假定所有平台都提供原子合入或自动保证版本组合。
未发布的本地补丁、已上传评审和已合入目标分支应分别描述。

| 现象 | 诊断应锁定的输入 | 避免的修复捷径 |
|---|---|---|
| 模块不存在或不可见 | manifest、namespace、visibility 与产品选包 | 把所有依赖改为 public |
| missing variant | 架构、分区、SDK、APEX 与 host/device 组合 | 随意关闭变体约束 |
| API 检查失败 | 受保护表面、兼容差异与目标历史版本 | 直接覆盖基线文件 |
| 本地正常、CI 失败 | 固定 SHA、工具链、flag、增量残留 | 用 clean 掩盖输入不一致 |
| 包存在但设备行为没变 | 安装路径、活动模块版本、进程与实际装载库 | 只引用编译日志证明已运行 |

交付判断应能将源码组合、构建配置、打包签名与实际运行版本连成同一证据链。
发布产物、签名与更新状态的关系可结合 [启动和更新机制](updates-boot.md) 判断。

## 官方依据与版本复核

以下页面均已阅读；链接中的 `main` 用于定位机制，实际复现应换成 manifest 固定的 revision。
构建属性可从本分支 Soong 生成文档和模块实现核实，不能照搬官网其他版本的属性集合。

[manifest]: https://android.googlesource.com/tools/repo/+/refs/heads/main/docs/manifest-format.md
[soong]: https://android.googlesource.com/platform/build/soong/+/refs/heads/main/README.md
[building]: https://source.android.com/docs/setup/build/building
[api-guidelines]: https://source.android.com/docs/setup/contribute/api-guidelines
[aidl]: https://source.android.com/docs/core/architecture/aidl/stable-aidl
[abi]: https://source.android.com/docs/core/architecture/vndk/abi-stability
[rust]: https://source.android.com/docs/setup/build/rust/building-rust-modules/android-rust-modules
[flags]: https://source.android.com/docs/setup/build/feature-flagging
[release]: https://source.android.com/docs/setup/contribute/release-lifecycle
[contribute]: https://source.android.com/docs/setup/contribute/submit-patches
