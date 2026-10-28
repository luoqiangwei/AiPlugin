# Native 页大小、Vendor API 与链接兼容

用于 16 KB 迁移、native prebuilt/运行时映射失败、混合 system/vendor 与旧 VNDK 问题。核实日期：2026-10-28。
定位：页大小见前四节，Vendor API/LLNDK/VNDK 见后两节；一般链接 namespace 与 JNI 所有权见[内核与 Native](kernel-native.md)。

## 页大小、ELF 对齐和安装布局分别验证

Android 15 开始提供 16 KB 构建支持；在文档规定的分支中，16 KB 对齐用户态可服务 4 KB/16 KB 内核。不能从“ELF 对齐为 16384”推定当前内核已经使用 16 KB，或从内核启动成功推定所有 APK/native 库均兼容。

| 层次 | 实际含义 | 证据 |
|---|---|---|
| 内核页大小 | 虚拟内存管理的基础粒度 | 运行时 `getpagesize()`/`sysconf(_SC_PAGESIZE)`、`getconf PAGE_SIZE`、适用的内核配置 |
| ELF segment 对齐 | loader 映射 LOAD segments 的布局条件 | 最终交付 ELF/program headers，包含间接依赖和 prebuilts |
| APK 中未压缩库的 ZIP 对齐 | 库在容器中的可映射位置 | 最终签名 APK 的打包布局与实际安装/加载 |
| 产品预期/切换能力 | 产品声明及双内核/模块集成 | 产品属性、选中内核/模块、启动后实际值 |

主要机制及构建变量来自[16 KB 平台说明](https://source.android.com/docs/core/architecture/16kb-page-size/16kb)；实际值的读取方式见[获取页大小](https://source.android.com/docs/core/architecture/16kb-page-size/getting-page-size)。物理设备路径面向 arm64；x86-64 Cuttlefish 的模拟路径不证明对应 arm64 硬件性能。

## 去掉硬编码只是第一步

`PRODUCT_NO_BIONIC_PAGE_SIZE_MACRO` 促使组件按运行时取得页大小，`PRODUCT_MAX_PAGE_SIZE_SUPPORTED` 控制期望的 ELF 对齐；二者不是同一个开关，也不会重编未提供源码的外部库。

分析 `mmap`/`mprotect`/`munmap`、共享内存、文件偏移和自定义 allocator 时，分别核对起始地址、长度、偏移对齐及向上取整后的真实占用。把 4096 常数全局替换成 16384，会破坏真正表示协议块大小的常数，并不能证明在两种内核上正确。

小映射在大页上有更大尾部浪费；合并具有相同保护/寿命的区域可能减少占用，但不能为了节省一页而让不同权限的数据共享可写映射。实际 RSS/PSS、页表、映射数量、文件 padding 与磁盘块占用需要分开测量。[16 KB 优化](https://source.android.com/docs/core/architecture/16kb-page-size/optimize)

构建检查、ELF alignment test 与真实运行覆盖不同边界。Android 16 起文档提供 prebuilt alignment 检查，临时 ignore 属性不会使库兼容。验证还需经过动态加载、错误恢复与实际 `mmap` 路径；只启动系统或运行不加载 native 库的界面不充分。

## 属性分别描述事实、期望与能力

`ro.product.cpu.pagesize.max` 描述产物期望的最大对齐；Android 16 的 `ro.product.page_size` 描述产品预期页大小，用于识别刷错内核；`ro.product.build.16k_page.enabled` 表示切换选项能力。
`ro.boot.hardware.cpu.pagesize` 的来源又有 bootloader/init 的版本条件。不能只读一个属性，或通过改属性把运行内核“变为”另一种页大小。[属性语义](https://source.android.com/docs/core/architecture/16kb-page-size/system-properties)

证据链应连接产品配置→ELF/APK→选用内核及模块→运行时页大小→具体进程行为。只看 `get_build_var` 不能证明设备装载了本次产物。

## 双内核切换与 app backcompat 是不同机制

开发者切换功能需要两套匹配的内核/模块及 boot OTA。切换可能涉及 bootloader 条件和文件系统/data 迁移；ext4 subpage 模式也可能使性能不同于原生 16 KB 产品。它适合兼容性实验，不能拿该模式的结果直接声称量产性能改善。[开发者切换](https://source.android.com/docs/core/architecture/16kb-page-size/16kb-developer-option)

App backcompat 针对 4 KB 对齐 ELF/ZIP 的部分兼容问题，包含安装侧和 linker 侧的分别控制；它不是第二个 4 KB 内核，也不会修复库内部的页大小假设。消除首次运行警告或开启 manifest 开关，不能替代原生对齐及真实路径验证。[兼容选项](https://source.android.com/docs/core/architecture/16kb-page-size/16kb-backcompat-option)

## Vendor API level 不等于 SDK level

Vendor API 描述 vendor 向 system 提供的 HAL，以及 vendor 从 system 依赖的 LLNDK 契约，也影响 VSR 适用范围。Android 14 QPR3 起采用独立的 `YYYYMM` 级别；不能与整数 SDK level 直接比较大小。

首发 SDK、chipset first API、board 当前 API、vendor API 与 system 提供的 LLNDK level 是不同事实。首发值不应在普通 OS 升级时被修改，vendor freeze 资格又影响 vendor level 的推导；应使用目标实现的 SDK→vendor 映射，不编造日期换算。

**工程推导**：新 system 配旧 vendor 时，检查实际 vendor level、VINTF、LLNDK 和特性降级路径。提高属性不能补出 HAL 能力；删除版本判断可能让新 system 调用旧 vendor 不具备的接口。[Vendor API level](https://source.android.com/docs/core/architecture/api-flags)

## VNDK 的历史责任与废弃边界

旧 VNDK 为独立升级的 system/vendor 提供受约束的 native 依赖集合。它不把所有系统库都变成稳定 API，也不使同一进程中的两份库自动安全：全局状态、分配/释放跨库、对象布局和 singleton 都可能受双加载影响。

Android 15 起 VNDK 废弃改变了新 vendor/product 中原 VNDK 库的安装归属；用于兼容旧 vendor 的 14 及以下 VNDK APEX 仍有责任。LLNDK 继续存在，不能把 VNDK 废弃解释成 native 跨分区依赖不再受限。

旧文档中的 `ro.vndk.version`、vendor snapshot 和 `use_vndk_as_stable` 有对应版本条件。定位时先确认 vendor 是按哪个版本构建，再读历史设计，而不是要求所有新产品创建旧属性/APEX。[VNDK 概览与废弃说明](https://source.android.com/docs/core/architecture/vndk)

此页没有穷举 ELF 格式、CPU MMU、全部 VNDK 构建选项或厂商二进制认证要求；这些具体细节应继续读目标工具链与接口定义。
