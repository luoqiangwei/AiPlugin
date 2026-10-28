# Bootloader、启动镜像与设备树

用于 boot/recovery 无法启动、bootconfig、DTB/DTBO、分区拆分和 fastboot 模式问题。核实日期：2026-10-28。
先确定首发版本、内核/GKI、镜像 header、分区/slot、recovery 布局、AVB 信任和实际装载产物；更新状态机见[启动与更新](updates-boot.md)。

## 镜像 header 是解析契约

Bootloader 必须按 header version 解释长度、字段与布局，不能按文件名或刷写成功判断格式。boot image header 的页/布局字段也不是运行内核页大小的通用查询。

v3 将 vendor 内容从通用 boot 组织中分离，v4 又支持相应签名/布局扩展；vendor boot 自身有独立 header。具体版本的 kernel、ramdisk、DTB、vendor ramdisk table 和 bootconfig 位置必须由对应 header 计算，并验证范围/整数运算，不能套用一份固定 offset。

Android 13 首发 GKI 设备中，generic ramdisk 移入 `init_boot`，`boot` 主要承载 GKI kernel；从旧内核升级的设备并不一律需要新增 `init_boot`。header 的 OS version 来源也有 GKI/AVB 条件，不能因字段为零就判镜像损坏。[Boot header](https://source.android.com/docs/core/architecture/bootloader/boot-image-header)、[Generic boot](https://source.android.com/docs/core/architecture/partitions/generic-boot)

**工程推导**：刷错组合时先对齐镜像版本、打包输入和 bootloader 解析，再排查 init。只替换 kernel 而保留不匹配的 ramdisk、DTB 或模块，可能在 first-stage mount 前失败。

## Generic、vendor 与 recovery ramdisk 的责任

Generic ramdisk 提供通用 first-stage init 等最小启动内容；vendor ramdisk 提供设备早期资源和所需模块。recovery 是否独立决定 recovery 内容放在哪个镜像，不能把所有产品都建成 recovery-as-boot。

Vendor boot v4 可包含带元数据的多个 ramdisk fragments。Bootloader 按启动模式/硬件条件选择并按规定拼接；复制全部 fragments 或错误处理 generic/vendor 覆盖关系，都可能改变实际 `/init` 和模块可见性。[Vendor boot](https://source.android.com/docs/core/architecture/partitions/vendor-boot-partitions)

`vendor_dlkm`/`odm_dlkm` 提供独立更新 vendor/ODM 模块的分区组织。正常消费者应沿稳定模块路径及 symlink 访问；在镜像目录里看到 `.ko` 不证明早期启动时已经挂载或依赖已就绪。所需模块、`modules.load`、fstab、AVB 和 OTA 分区集合要共同一致。[DLKM 分区](https://source.android.com/docs/core/architecture/partitions/vendor-odm-dlkm-partition)

产品/system_ext/vendor/odm 的内容归属还影响可独立更新性和链接接口；分区存在不意味可以绕开公开接口。共享 system image 的产品差异应落在适当配置/分区，而不是把产品内部依赖悄悄编入通用 system。[分区](https://source.android.com/docs/core/architecture/partitions)、[Product interfaces](https://source.android.com/docs/core/architecture/partitions/product-interfaces)、[Shared system image](https://source.android.com/docs/core/architecture/partitions/shared-system-image)

## Bootconfig 的数据源与内存尾部

Android 12 对应条件下，`androidboot.*` 从 kernel cmdline 迁移至 bootconfig，使 Android 用户态配置与内核参数分开。build-time 内容与 bootloader 的 runtime 内容需要合并，再生成正确 size/checksum/trailer，并位于 kernel 实际收到的 initramfs 尾部。

在 trailer 后继续追加参数会破坏识别；迁移时提前删除 cmdline 中关键配置也可能造成不可启动。应核对 vendor boot header、加载后的最终内存布局、`/proc/bootconfig` 与 init 导出的属性，而不是只看构建目录里有文本文件。换行分隔和 cmdline 的空格形式也不能混用。[Bootconfig](https://source.android.com/docs/core/architecture/bootloader/implementing-bootconfig)

## Fastboot 与 fastbootd 是不同执行环境

Bootloader fastboot 与用户态 fastbootd 支持的分区操作不同。动态分区管理需要其对应 userspace 设施；仅看到 fastboot USB 连接不能判断当前模式，应核对 `is-userspace`、logical 状态和 super 元数据。

BCB 的 `boot-fastboot` 用于进入相应 recovery/fastbootd 路径，不能随意清除已有 recovery 恢复状态。`set_active` 只选择启动 slot，不证明该 slot 完整、成功启动或可回滚。删除/resize logical partition 是实际分区操作，不是修复所有刷写失败的常规探针。[Fastbootd](https://source.android.com/docs/core/architecture/bootloader/fastbootd)

## 锁定状态与启动原因有各自的时间语义

OEM unlocking 能力、允许解锁状态、当前 bootloader lock state 和 Verified Boot 状态不同。锁/解锁涉及用户确认、数据擦除与可信状态迁移；不能靠改 Android 属性模拟安全固件中的状态，也不能以解锁后的启动成功证明量产锁定状态可启动。[锁定与解锁](https://source.android.com/docs/core/architecture/bootloader/locking_unlocking)

`ro.boot.bootreason` 保留 bootloader 提供的原因，`sys.boot.reason` 可在 userdata 挂载后经 bootstat/init 进一步规范化。早期值、重启请求原因与最终故障归因不一定相同；只匹配一个字符串会误把 watchdog/kernel panic/供电故障归为同一问题。[Canonical boot reason](https://source.android.com/docs/core/architecture/bootloader/boot-reason)

Android 16 起官方对相应 ARM64 设备推荐 GBL，将通用 Android boot 逻辑与 vendor UEFI 协议实现分离。推荐不是“所有旧设备必须替换现有 bootloader”；集成仍需验证协议、存储、随机数、AVB 与 slot 责任。[Generic Bootloader](https://source.android.com/docs/core/architecture/bootloader/generic-bootloader)

## DTO：SoC 基础树与设备覆盖共同构成硬件描述

DT 描述不可由通用枚举发现的硬件；main DT 通常承载 SoC 公共部分，overlay 承载设备差异。编译出 `.dtbo` 不等于最终树正确：还需选对 SoC/board、匹配 labels/phandles、应用正确 overlay 集合和顺序，并把合并后的树交给内核。

Main DT 是 overlay 的接口面。节点、属性、标签与存储位置改变，都可能破坏旧 overlay；从源码同时重编两边成功不能证明可独立升级。Bootloader 必须验证 DT 来源及选中对象，Android 9 的 DTO 约束也不允许任意改写已定义的 overlay 属性。[DTO 模型](https://source.android.com/docs/core/architecture/dto)、[实现及安全](https://source.android.com/docs/core/architecture/dto/implement)

多 SKU 模型通常选一个 main DT 加若干兼容 overlays；不能把所有 board 的 overlay 都应用。独立 DTB/DTBO partition 使用 table/header，即使只有一个 entry 也不能省略；该表格式与附加到 kernel image 的 blob 形式不是同一容器。[多树选择](https://source.android.com/docs/core/architecture/dto/multiple)、[DTB/DTBO 格式](https://source.android.com/docs/core/architecture/dto/partitions)

Host 端 `dtc`/`ufdt_apply_overlay` 可以检查语法和合并结果；最终仍需比对设备选中 ID/index、交给内核的树与 driver probe。裁剪未用节点/压缩可降低装载成本，但必须在所用 DTBO 格式、版本与 bootloader 解压能力内进行，不能只测 host 合并工具。[Compile/verify](https://source.android.com/docs/core/architecture/dto/compile)、[优化](https://source.android.com/docs/core/architecture/dto/optimize)

## 定位时保留同一启动尝试的证据

同时保存 bootloader 日志、slot/BCB、镜像 header/AVB 元数据、选中 DT/ramdisk、bootconfig、first-stage init 与模块/probe 失败。正常启动、recovery、fastbootd、OTA 后首启分别检查，不能拿一个模式的成功替代其余模式。

此页解释装载和分区契约，不穷举每个厂商启动固件、GBL 协议字段、旧 non-A/B 脚本命令和每代镜像结构体。实际 offset 与精确构建变量须由目标 `mkbootimg`/bootloader/header 定义复核。
