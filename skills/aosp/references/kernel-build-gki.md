# Kernel 构建、GKI 模块与发布产物

用于内核构建身份、KMI 证据、模块归属、内存分配接口及 GKI 发布选择。核实日期：2026-10-28。
KMI 基本模型见[内核与 Native](kernel-native.md)，启动镜像与模块分区见[Bootloader 与设备树](bootloader-device-tree.md)；本页不重复页大小、Vendor API 或镜像 header。

## 构建输入不是只有 kernel/common 的提交

[Build kernels](https://source.android.com/docs/setup/build/building-kernels)区分 Android 平台树中的内核 prebuilt 与独立 kernel manifest 树中的源码、工具链和构建工具。
同一个 `Image` 文件名不能标识分支、配置、Clang、GKI/设备模块及打包输入。可靠的产物身份应包含 manifest/revision、架构、build target、配置片段、工具链及最终 dist 文件集合。
平台重新打包成功只证明容器可生成，不证明装入了预期内核或匹配模块。

| 构建体系 | 适用条件与配置来源 | 容易混淆的状态 |
|---|---|---|
| Kleaf/Bazel | Android 13 引入；由 BUILD 定义、target 和命令参数表达依赖 | 旧 build.sh 环境变量通常不会自动改变 Kleaf 行为 |
| `build/build.sh` | 旧分支采用 build config 与环境变量；Android 14+ 不再支持 | 一条旧机型命令可运行，不说明它是当前分支受支持方式 |
| GKI 与 virtual-device modules | 通用内核与设备模块分别有分发 target | 只取内核 binary，遗漏 initramfs/模块会在启动或设备发现阶段失败 |

精确矩阵以[分支与构建体系](https://source.android.com/docs/setup/reference/bazel-support)及目标 BUILD 为准：Android 13 的部分目标同时支持两种体系，设备/架构的官方方式还可能不同。
Android 14+ 的 defconfig fragment 是配置输入；直接编辑一次输出 `.config` 不代表下一次干净构建还能复现。
dist 中的内核、模块、模块 staging archive、符号/ABI 产物和镜像服务于不同消费者，不能把任意一个当作完整交付包。

[ACK 分支](https://source.android.com/docs/core/architecture/kernel/android-common)还区分开发、接口稳定化与 KMI frozen 阶段；LTS 修复继续进入对应分支，不代表已冻结 KMI 可随意改变。
上游 stable/LTS、ACK development branch 与某个季度认证 binary 有不同来源与寿命。[Stable releases 说明](https://source.android.com/docs/core/architecture/kernel/releases)中的旧版本例子不是当前支持清单，实际仍需当期发布/ASB 条件。

## ABI 工具比较二进制接口的可达类型

[ABI monitoring](https://source.android.com/docs/core/architecture/kernel/abi-monitor)从 `vmlinux` 和 GKI 模块提取表示，再依 symbol list 的并集限定稳定 KMI 表面。
受监控对象包含函数签名与关联结构体布局；符号名字相同仍可能因嵌套类型变化而不兼容。
模块能本地编译与能加载到另一个 GKI binary，分别回答源码可构建性和二进制契约。

[当前 ABI 工具说明](https://source.android.com/docs/core/architecture/kernel/howto-abi-monitor)使用 STG，Android 13 及以下有 libabigail/XML 的历史路径；Android 16+ 与 14/15 的 reference 路径也不同。
例如 Android 16+ 的 `kernel_aarch64_abi_dist` 同时产生 ABI、内核和模块，比较失败以非零退出码表达。不能只搜索日志中的报告文件是否存在来判通过。
开发阶段分支可能没有 reference ABI，此时“没有报告差异”不证明已满足冻结接口。

[Symbol lists](https://source.android.com/docs/core/architecture/kernel/howto-symbol-lists)来自实际模块的未解析依赖；设备 in-tree/out-of-tree 模块的 target 都需进入提取范围，GKI 模块不按 vendor 消费者重复列入。
若模块被不适当签名或模块集合遗漏，生成的空列表可能只是提取失效。
同一 list 服务多个设备时，当前设备未用符号不表示其它已发布设备不再依赖；冻结后移除已用符号会破坏兼容。
更新 reference 是记录已确认的接口变化，不会让一个本来破坏兼容的修改自动安全。

## Protected GKI、unprotected GKI 与 vendor 模块

[模块分类](https://source.android.com/docs/core/architecture/kernel/modules)不是按文件夹命名：protected GKI 模块可访问非 KMI 核心符号，不能由 vendor 模块覆盖；unprotected 模块受类似 vendor 的导出限制，并在可替换时仍须保持其已公开 KMI。
构建签名参与区别模块类别，不能由“某个 unsigned 模块能加载”推出所有签名策略都被禁用。
vendor 模块实现设备/SoC 能力；当相同通用功能后来成为内核内建或 protected GKI 实现，原 vendor 副本可能不再能加载。

[模块化功能](https://source.android.com/docs/core/architecture/kernel/convert-or-add)还影响 GKI 模块清单、protected exports、`system_dlkm` 与 staging archive；仅将 Kconfig 从 `y` 改成 `m` 会改变启动时可用性，不能保证镜像已包含模块及依赖。
早期必需驱动、正常运行驱动与可选库的装载时机不同。模块已注册 driver、设备已被枚举、probe 成功和硬件可用也不是同一状态。

[GKI module testing](https://source.android.com/docs/core/architecture/kernel/test-kernel)特别区分内核产物中的开发用 `system_dlkm.img` 与生产镜像：前者不能拿来运行 CTS/VTS 或作为量产镜像；生产组合使用相应 staging archive 中的签名模块重新组织分区。
[Loadable modules](https://source.android.com/docs/core/architecture/kernel/loadable-kernel-modules)又区分 vendor 模块所在验证分区的真实性与 GKI 模块的类别签名；不能把二者都简化为“每个 ko 必须同一方式签名”。

[Vendor module guidelines](https://source.android.com/docs/core/architecture/kernel/vendor-module-guidelines)强调由 driver core 管理 probe 与资源关系。
`module_init` 注册驱动而非抢先初始化所有硬件；`MODULE_DEVICE_TABLE` 让用户态了解支持的设备。
绕过公开函数直接访问 core 结构、补入私有类型定义或手工解析其它设备节点，会破坏所有权、CRC 及依赖模型。
`fw_devlink` 等机制需要真实 supplier/consumer 关系；固定 sleep、硬编码 probe 次序或绕开 deferred probe 不能替代它。

## DMA-BUF heaps 替换的是分配入口

[ION→DMA-BUF heaps 说明](https://source.android.com/docs/core/architecture/kernel/dma-buf-heaps)是官方已标记弃用的历史迁移文档，侧栏注明 5.4 kernel；其中旧 API、堆名和回移指令不能当作新 GKI 的通用集成步骤。
可保留的机制区别是：ION 经单一 `/dev/ion` 加 heap ID/私有 flags 选择分配；DMA-BUF heaps 为不同堆提供独立字符设备，使分配接口与 SELinux 授权按堆区分。
两者都能导出 DMA-BUF；只导入 buffer 的驱动不因分配器变化就自动需要另一套 buffer 导入协议。

**工程推导**：heap 访问权、分配的 buffer 属性、DMA 映射/缓存同步及 buffer 生命周期应分别解释。
把 cached/uncached 或 protected 变体都映射到同一个普通 heap，会改变消费者依赖的内存属性；仅让 allocation 返回成功没有保持原契约。
历史 `libdmabufheap` 支持按名称寻找 DMA heap 并回退至对应 ION 堆，故接口调用名称不能独立证明运行时没有使用 ION。
protected memory 需要厂商安全实现；普通系统堆和可 mmap 的测试 buffer 不能证明可信显示或安全视频内存隔离。

## 发布、内核版本与 respin 的身份

[GKI versioning](https://source.android.com/docs/core/architecture/kernel/gki-versioning)区分 kernel release、KMI version 和 sublevel。
同一 KMI version 可对应多个安全修复后的 release；同为某个 Linux LTS 主次号不能推出 KMI 相同。
版本单调条件还包括 Android release、KMI generation 和同 KMI 下的 sublevel，不能把替换 `uname` 字符串当作兼容实现。

[当前发布说明](https://source.android.com/docs/core/architecture/kernel/gki-releases)采用 KMI freeze 后的季度发布与认证 respin；资格依据参考硬件、Cuttlefish 和相应套件，不能直接替代产品自身硬件集成证据。
[Respin](https://source.android.com/docs/core/architecture/kernel/gki-respin)基于选定已发布基线重建、重新验证并认证，包含该基线接收的修复，不等于滚到最新开发分支，也不是只包含一家厂商补丁的私有 fork。
是否仍可使用/申请取决于当期 ASB 的 LTS 要求及具体发布 deprecation 状态；不把旧页面的日期永久写成当前支持承诺。
各 Android/LTS release-builds 与 deprecated-builds 页主要是产物/日期索引，同一机制不因季度表或 JSON 表重复出现而新增一种内核模型。

## 内核其它侧栏能力的机制边界

| 分支 | 核心关系与限制 |
|---|---|
| [FIPS crypto module](https://source.android.com/docs/core/architecture/kernel/gki-fips140-module) | `fips140.ko` 缩小可认证密码模块的变化范围，启用算法前自检；可送认证不等于设备已获证，加载它也不增加一般密码能力 |
| [IncFS](https://source.android.com/docs/core/architecture/kernel/incfs) | 在已有文件系统上支持按需交付 APK 数据，依赖 PackageManager/ADB/签名协作；Android 11 的可装载模块模式不可直接推广到新版本 |
| [EROFS](https://source.android.com/docs/core/architecture/kernel/erofs) | 只读压缩文件系统，原位解压减少额外页；压缩 cluster 与库版本也影响读性能和 OTA delta，不能从压缩率推断速度 |
| [Boot-time optimization](https://source.android.com/docs/core/architecture/kernel/boot-time-opt) | 模块读取、解压、重定位、probe 都占启动路径；异步 probe 只适合有正确依赖的驱动，优化须区分这几类等待 |
| [Proxy Execution](https://source.android.com/docs/core/architecture/kernel/proxy-exec) | 被 mutex/rwsem 阻塞的任务可捐出调度时间给锁拥有者，执行者与计费 donor 分开；不能让依赖 `rq->curr` 的 vendor hook 继续假定二者恒相同，支持和默认值绑定分支 |
| [eBPF kernel telemetry](https://source.android.com/docs/core/architecture/kernel/kernel-telemetry) | 事件在内核聚合、BTF/CO-RE 处理类型差异、用户态拉取 delta；累计 map 与事件 ring buffer 的消费语义不同，未加载/跳过不能解释成零事件 |
| [DebugFS 条件](https://source.android.com/docs/core/architecture/kernel/using-debugfs-12) | Android 12 首发条件下 user 与 userdebug 的挂载/访问边界不同；生产功能不能依赖调试文件始终存在 |
| [GKI debug features](https://source.android.com/docs/core/architecture/kernel/debugging-with-gki) | 标准 GKI 的 tracing/BPF 与需要专用配置的 intrusive debug 不同；调试配置可能改变 KMI，不能把仅在 debug kernel 正常当作生产内核正常 |
| [Kernel networking tests](https://source.android.com/docs/core/architecture/kernel/network_tests) | 以 UML/TAP/socket 行为检验内核网络语义，可暴露回移补丁遗漏；不验证真实网卡驱动、射频或完整产品 CTS |
| [6.12 errata](https://source.android.com/docs/core/architecture/kernel/android16-6.12-errata) | 新 sanitizer 对 `__counted_by` 的边界及 OF_DYNAMIC 的节点引用计数，可暴露旧驱动初始化/UAF 问题；出现新 panic 不自动表示编译器错误，具体修复绑定该分支 |

本页覆盖构建/ABI/模块/发布及上述机制；[release notes](https://source.android.com/docs/core/architecture/kernel/release-notes)中的调度、MM、io_uring 等逐项实现仍需相应子系统资料，不能由版本标题推断目标配置全部启用。
未穷举 ABI 类型差异工具的全部选项、KABI 宏技巧、各 release 表每个 build、内核网络测试案例、FIPS 算法认证材料、Proxy Execution 全部 hook 或厂商驱动实现。
