# 开发环境、源码组合与产品集成

用于 AOSP 主机准备、源码初始化/同步、增加产品或设备、multilib、运行产物与贡献上下文。
资料核实于 2026-10-28；先固定分支/tag/manifest、主机、产品、release config、build variant、内核与厂商二进制基线。
本页解释这些输入怎样连成可运行系统，不固定一套主机安装命令、设备代号或刷写步骤。
Soong/API/工具链的基础见[构建与源码演进](build-release.md)，flags 的发布值见[Feature flags](feature-flags.md)。

## 主机能力与分支工具链共同决定可构建性

当前[环境要求](https://source.android.com/docs/setup/start/requirements)面向较新 AOSP 的受支持主机是 64-bit x86 Linux，并规定相应 glibc/发行版与资源条件。
Android OS 的 macOS 开发支持已在 Android 11 时期结束；不能由用户正在使用 Mac 或旧教程存在 macOS 命令推断当前整个平台可在该主机构建。
旧 Android 的 JDK、操作系统与依赖要求应查[旧版环境说明](https://source.android.com/docs/setup/start/older-versions)，不能把新分支 prebuilt 规则倒推到旧树。

较新 release branch 带有 OpenJDK、Make、Python 等预置工具；Repo launcher 则启动 checkout 内的完整 Repo。
宿主 PATH 中某个 clang/JDK/Python 能运行，不代表 Soong 实际选择它，也不代表平台要求应通过全局替换主机工具来满足。
在故障记录中应保存实际执行工具路径、版本和调用环境；构建系统预置工具、内核构建工具与 app SDK 工具可能是不同输入。

完整 checkout、产物、符号、镜像和并行编译各占空间与内存；当前官网的容量要求是当期规模基线，不是所有历史分支或部分 checkout 的恒定值。
磁盘满、inode/权限、内存压力与并行过高应按真实失败区分，不能统一解释成源码问题。
`OUT_DIR` 可将输出放在合适位置，但切换产品或分支后仍需核对输出与输入的关联，不能仅因目录存在就复用旧产物作为新构建结果。

## Repo 初始化选择源码组合，不等于单个 Git checkout

Repo manifest 决定 project 路径、remote 与 revision；`repo init` 选择 manifest 来源/分支，`repo sync` 获取并同步这些项目。
branch/tag 和 manifest 文件名分别是不同输入；本地 manifest、项目局部切换与未提交补丁也会改变最终组合。
[下载源码](https://source.android.com/docs/setup/download)和[源码工具关系](https://source.android.com/docs/setup/download/source-control-tools)说明 Repo 与 Git 的职责；具体选项以目标 Repo 版本为准。

`android-latest-release` 是会随发布演进的 manifest 入口，不是永远固定的内容。
复现应记录解析后的各 project revision 及本地改动，不能只记录初始化命令或最顶层目录的 HEAD。
只同步某个 project 可以节省时间，却可能保留与新接口不相容的其他项目；修复跨仓库变更时需核对整个依赖组合。
partial clone 延迟获取部分对象以改善传输/容量，并不保证离线时所需对象齐全，也不修复错误分支组合。

同步失败先区分获取阶段和工作区应用阶段。
网络/代理/共享 IP 配额问题需要相应连接与认证证据；本地未提交改动、分支冲突和目标 revision 不存在则需要项目状态证据。
[同步故障说明](https://source.android.com/docs/setup/download/troubleshoot-sync)介绍认证配额、代理、镜像与 partial clone；其系统 TCP 设置示例不是遇到任何 sync 错误都应执行的修复。
不要用 reset/删除工作区抹掉本地变更来证明同步成功，也不要把认证密码写进可分享日志。

## 源码并不包含任意硬件的全部运行输入

Cuttlefish 可直接使用相应 AOSP 虚拟产品；真实设备往往另需设备匹配的 proprietary libraries、HAL、固件、内核和产品配置。
相同品牌或相同大版本不保证二进制包与本次源码/产品相容；应绑定设备代号、tag/release 和供应商交付基线。
[官方源码下载说明](https://source.android.com/docs/setup/download)单列设备专用二进制的获取与提取；不能拿任意“最新驱动”拼装出可复现组合。

闭源组件缺失、开源模块未选入、ABI 不匹配和运行时权限拒绝，可能都表现为设备功能不存在，但其修复层不同。
分析应先列出完整交付输入及可检查部分，对缺少的闭源实现保留条件，不能凭 AOSP 头文件臆造厂商行为。
虚拟设备验证适合 Framework、系统服务和可模拟接口；真实传感器、基带、功耗或安全硬件仍需相应设备证据。

## 产品、设备和架构是不同配置层

产品层描述交付能力和模块组合，board/device 层描述硬件配置，arch 层描述处理器与 ABI。
一个设备可承载多个产品，产品可继承公共定义以复用配置；复制一套 device 目录并改产品名，不能说明硬件差异已被正确表达。
[Add a new device](https://source.android.com/docs/setup/create/new-device)给出这些层次与产品定义机制；其旧 Pixel 示例和部分 Make 语法不能当作所有新分支模板。

| 输入 | 负责什么 | 集成时核对 |
|---|---|---|
| `AndroidProducts.mk` / 产品注册 | 让构建系统发现产品 makefile 与相应选择 | 实际 lunch 入口指向哪个产品 |
| 产品 makefile、继承关系 | PRODUCT_NAME/DEVICE、包、资源、属性等交付选择 | 最终有效配置及后续覆盖 |
| `BoardConfig.mk` 等设备配置 | 架构、board 约束及相应镜像/硬件构建输入 | 与真实设备、内核及 vendor 基线一致 |
| 模块定义和依赖图 | 编译变体、链接、测试与安装属性 | 所需分区/ABI/SDK/APEX 变体是否存在 |

当前 `lunch` 通常组合 product、release config 与 build variant；旧分支可能只有 product/variant，需读取本树 envsetup 和产品定义。
`user`、`userdebug`、`eng` 改变调试能力及构建行为；用 eng 运行正常不能推出 user 的权限、性能或依赖同样成立。
[Build Android](https://source.android.com/docs/setup/build/building)给出当前入口；旧文档 `add_lunch_combo` 等历史步骤有明确适用版本，不能机械补进新产品。

## 模块编译、产品选包、镜像安装与运行是四个状态

先在本 shell 加载目标树的 envsetup，再选择目标；环境是 shell 状态，另开 shell 不会自动继承这些函数和选择。
构建单个模块可验证其依赖/语法，但不证明它被该产品选入；`PRODUCT_PACKAGES` 和安装依赖图共同影响最终镜像内容。
镜像包含某文件也不证明设备正在装载它：需核对安装分区、活动 APEX/APK、进程、Build ID 与刷入/启动的实际产物。
这些关系依据[构建入口](https://source.android.com/docs/setup/build/building)及[产品配置](https://source.android.com/docs/setup/create/new-device)，实际证据应绑定同一 manifest 和输出目录。

只解析构建图、只生成测试二进制、只构建模块、完整镜像构建与启动通过，各自证明范围不同。
构建成功后运行未变化，应先找产物选择和装载问题，不要立即修改逻辑或不断 clean。
Android 17 及以上当前文档还约束构建期间源码树只读；生成物应使用正确输出路径。
临时打开 writable/broken 兼容选项可以定位违规写入，不能作为生成器继续污染源码树的永久设计。

## Multilib 需要完整的 ABI 依赖链

64 位主机不决定目标是 64 位；64 位产品也不意味着所有消费者仅有 64 位。
支持 multilib 时，产品架构与模块依赖决定哪些 32/64 位变体构建和安装；同名库有双 ABI 变体，不代表每个变体一定被打包。
一个 32 位进程需要它能加载的整条 32 位依赖链，不能只复制顶层 `.so` 或把 64 位库改名。
[32-bit and 64-bit builds](https://source.android.com/docs/setup/create/64-bit-builds)解释此模型；该页面许多变量是 Android.mk 专用，Soong 应查看本分支对应 arch/target/multilib 属性。

Make multilib 中不能仅用一次全局 `TARGET_ARCH` 条件推导每个模块的当前变体，应使用支持的模块级架构选择及后缀变量。
双 ABI 库的安装宜保持架构正确的相对路径；生成源码也需放在支持两个变体共享/依赖的生成目录，避免都写某一架构中间目录。
prebuilt 的 ELF 架构、app 的 JNI 与运行时位宽也需一起核查；某模块名在命令行仅构建第一架构的历史行为不能推成完整 multilib 验收。
实际模块属性、产品是否允许 32 位 app 及相关 AOT 产物，仍取决于目标发布与产品。

## 运行准备与调试条件也是实验输入

虚拟产品、Android Emulator 镜像和真机刷写有不同的打包/运行入口，不能把一个普通 image 当成任意运行器可直接消费的产物。
真机 bootloader 状态、设备所需镜像、活动 slot、AVB/签名与 data 状态影响启动；解锁和切换信任状态还可能改变数据与密钥可用性。
[Fastboot 运行说明](https://source.android.com/docs/setup/test/running)与[Emulator 镜像说明](https://source.android.com/docs/setup/test/avd)应按设备和版本读取，不能把网页示例命令当作无需检查的整机动作。

调试记录至少连接运行版本、构建 variant、是否 root/重挂载/覆写模块、实际安装位置和相关日志。
userdebug 的便利条件可能改变权限与时序；测试时临时状态恢复后，发布构建仍应保持预期行为。
崩溃符号必须匹配运行二进制和 Build ID；源码已更新不表示设备 image 或符号文件也同步更新。
具体 Atest、Tradefed、bugreport 与崩溃机制见[测试与诊断](testing-diagnostics.md)。

## 贡献状态不等于运行交付状态

Git commit 属于单个 project；跨 project 的一个功能需要在各项目保存相应变更和依赖。
本地 topic branch、已上传 Gerrit patchset、目标分支合入及正式镜像发布是不同状态；Change-Id 不是整机版本。
[Source control workflow](https://source.android.com/docs/setup/create/coding-tasks)和[Submit code changes](https://source.android.com/docs/setup/contribute/submit-patches)解释这些对象；原始网页的操作示例仍需结合当前工作区，不能把未暂存、已暂存和已提交混为一类。

提交前应核对项目当前贡献目标、CLA/许可与上游归属；有些第三方或半独立项目需向其上游提交。
当前[发布生命周期](https://source.android.com/docs/setup/contribute/release-lifecycle)已描述外部 latest release branch 与内部开发/发布的关系，不能永久要求所有变更上传 main。
上传评审或上游接受不证明目标旧产品已完成 backport，也不证明当前运行镜像包含该修复。
交付结论最终应能从源码组合、产品配置、工具链、产物和设备观察连成一条证据链；本页没有执行同步、构建、上传或设备操作。
