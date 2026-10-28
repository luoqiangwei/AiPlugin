# AOSP 主题深度核对表

核对日期：2026-10-28。范围是官方导航中可发现的 `/docs` 页面与本 skill 的实际知识文件。它是人工对照的主题清单，不是“全站每句话均已核实”的证明，也不把同一页面的别名或安全公告月份当成新的机制。

## 完整导航的核对方式

不能只读取栏目首页的正文链接，也不能只按 URL 前缀推测侧边栏。[实际导航快照](sidebar.json) 递归跟随顶部 lower-tabs，为每套导航读取第一棵完整 `menu=_book`，保留无 URL 的可折叠标题及所有后代，并去除重复的 mobile/desktop 菜单。

本次共核对 26 个导航入口（含本身没有侧边栏的汇总页）。导航中的 `/docs` 地址与文章目录逐项对照；旧 CDD PDF、GKI 发布 JSON 等记录为链接资料，不能计为正文已读取。`unavailable_sections` 与 `uncataloged_docs_urls` 显式记录失败或目录缺失，不能静默省略。

`knowledge_candidates` 表示按[归属规则](sidebar-routes.json)或出处可以查阅的知识文件；`directly_cited_in` 只是直接出处。`partial_topic_route` **不是全文语义完成状态**。本表与各文件的“深度边界”才说明实际提炼范围。

| 导航组 | 本地核对范围 |
|---|---|
| Getting Started | About/Start/Download/Build/Create/Test/Contribute/Community/Reference |
| Security Overview | 安全概览、实现/增强、更新、漏洞报告等 |
| Security Features | Sandbox/OMAPI/签名/认证/DICE/加密/Keystore/Identity/SELinux/Trusty/AVB/Safety Center/蜂窝安全/Private Space/GPU 过滤 |
| Security Testing、Best practices | Memory safety/MTE/sanitizers/fuzz/hardening 与组织/系统/应用/网络/硬件/隐私实践 |
| Bulletins | AOSP、Pixel/Wear、AAOS/XR/Chromecast 各自的历史公告树；逐个 CVE 修复状态仍需按产品核对 |
| Architecture and Platform | HAL/HIDL、Kernel/ABI/modules/release、配置/DTO、VNDK/VINTF/AIDL/Binder、Bootloader/Partitions/16 KB，及 Power/Settings/Fonts |
| Connectivity and Input | 网络与无线、电话/运营商、Interaction/Sensors/Haptics/Input/Accessories/CHRE/NNAPI，及 Camera |
| Media and Display | Audio、Display、Graphics/Winscope、Media |
| System health and Updates | Performance、Runtime/ART/DEX、Updates/APEX/Mainline/OTA |
| Testing、Data storage and access | Tests/Tradefed/VTS，以及 Data/Permissions/Storage/Virtualization |
| Compatibility | CDD HTML/PDF 与 CTS/CTS-V/ITS/物理装置/发布说明 |
| Android Devices | Enterprise、Cuttlefish、TV 分别具有独立侧边栏；汇总首页没有 sidebar 不视为读取失败 |
| Automotive | Getting started、IVI/HMI/VHAL/电源/媒体/用户/测试、SDV，以及 releases/unbundled apps 独立导航 |
| What's New | Release notes、最新公告/CDD、站点更新；不将版本页面当作永久规则 |

状态含义：

- **机制**：已归纳状态/数据路径、关键契约、典型失效方式及证据。只承诺表中列出的范围，具体参数和版本仍需查目标实现。
- **概览**：已有架构关系和一般边界，不能据此独立完成该子系统的所有实现。
- **入口**：可通过目录查原文，尚未形成足够的本地机制知识。
- **历史/版本条件**：与前述深度并列，禁止作为所有分支的默认配置。

采集成功率、被引用页面数、知识文件数与这些状态分别统计；不能互相替代。叶子文档出现于引用中，也不表示其所有表格、命令和例外已被提炼。

## Setup

官方范围：[Setup](https://source.android.com/docs/setup)。

| 子主题 | 已有深度与所在文件 | 仍需查原文的边界 |
|---|---|---|
| Repo/manifest、多仓版本身份、Soong 模块图、产品/变体、工具链 | 机制：[构建与发布](../build-release.md) | 每个 Soong module type、工具选项及分支工具链精确版本 |
| 主机条件、下载/sync 归因、设备产品继承、BoardConfig、选中模块到镜像 | 机制：[环境与产品集成](../setup-product-integration.md) | 板级配置值、厂商二进制与目标设备的具体集成文档 |
| aconfig、build/release flags、运行时覆盖、flag 测试 | 机制：[Feature flags](../feature-flags.md) | 目标版本的工具语法、产品 release config 及开关存储实现 |
| java_sdk_library/stubs/scope、异步 API/取消、IPC cache/失效 | 机制：[平台 API 契约](../platform-api-contracts.md) | 全部 API style 条款和每类 API 的特殊审查要求 |
| Gerrit、Change-Id、依赖关系、构建测试身份 | 机制与概览：[构建与发布](../build-release.md)、[测试与诊断](../testing-diagnostics.md) | 社区流程、贡献者协议、账号设置等行政说明仅作入口 |
| SBOM、应用更新所有权、参考板与构建来源 | 机制：[构建来源与更新归属](../setup-supply-chain.md) | 精确 SBOM 字段/工具、每个板级方案和产品更新安装器仍需查目标实现 |

## Security

官方范围：[Security](https://source.android.com/docs/security)。大量子页是按月、按设备发布的公告；公告有检索价值，但不是数百种独立安全机制。

| 子主题 | 已有深度与所在文件 | 仍需查原文的边界 |
|---|---|---|
| sandbox/身份、DAC/SELinux/权限、AVB/rollback、TEE、版本绑定 | 机制与概览：[安全模型](../security.md)、[启动与更新](../updates-boot.md) | 完整厂商 TA 协议和板级安全配置仍需专项查阅 |
| Trusty IPC/handle、TA 生命周期、DICE 派生 | 机制：[可信执行](../security-trusted-execution.md) | 全部 DICE 编码、Secretkeeper 策略与 TA 业务协议 |
| LockSettings→Gatekeeper→HAT→KeyMint、SID、Weaver、biometric classes、Protected Confirmation | 机制：[认证链](../security-authentication.md) | 具体 HAL 方法、测试阈值、传感器校准及新版本限速条件 |
| Keystore 域、keyblob 授权、操作生命周期、attestation 验证、RKP | 机制：[密钥与证明](../security-keystore-attestation.md) | 全部 KeyMint tags、证明 ASN.1 字段、具体后端与根证书更新 |
| SELinux public/private、标签归属、mapping、vendor_init、跨镜像升级 | 机制：[SELinux 兼容](../selinux-compatibility.md) | 每个 release 的政策差异及产品本地规则；不能仅用重编 vendor 代替旧 vendor 升级验证 |
| APK v1/v2/v3/v3.1/v4、轮换、Android 17 v3.2 条件 | 机制、版本条件：[签名与内存安全](../signing-memory-hardening.md) | 精确二进制布局、算法 ID 和产品发布工具参数 |
| MTE/HWASan、GWP-ASan/KFENCE、Scudo、CFI/SCS、pointer tags/zero-init | 机制、版本条件：[签名与内存安全](../signing-memory-hardening.md) | 各 sanitizer 的完整构建配置、KASAN/KCFI/UBSan 专项实现仍需原文 |
| GPU IOCTL 分类、SELinux xperm、target SDK/debuggable 边界 | 机制、版本条件：同上 | 驱动 IOCTL 全量分类及厂商实现须按版本验证 |
| FBE、CE/DE、metadata encryption、wrapped keys、Adiantum、adoptable/FDE 与恢复 | 机制、历史/版本条件：[存储与数据](../storage-data.md)、[密钥生命周期](../encryption-key-lifecycle.md) | 全部加密参数、厂商 inline engine 和硬件算法实现 |
| 安全公告、补丁级别、STS 与分支回移 | 机制：[安全模型](../security.md)、[测试与诊断](../testing-diagnostics.md) | 不预先判定每个 CVE 已修复；需逐项对照实际补丁 |
| Identity Credential、OMAPI/SE、凭据与认证密钥、UID/AID 授权 | 机制、版本条件：[身份与安全元件](../security-identity-secure-elements.md) | mdoc/GlobalPlatform/APDU 全协议、芯片 applet 与参考测试 profile |
| Safety Center、蜂窝安全、Private Space | 机制、版本条件：[平台安全服务](../security-platform-services.md) | Safety Center 全部排序/去重、闭源 modem 行为与产品策略 |

## Core 的横向范围

官方范围：[Core topics](https://source.android.com/docs/core)。Audio、Perf、Tests、Data 是其子集，不能把下面四组再与 Core 相加计算覆盖率。

| 子系统 | 已有知识入口 | 深度边界 |
|---|---|---|
| 架构、Binder、AIDL/HIDL、Treble/VINTF、模块化、内核/native | [架构与 IPC](../architecture-ipc.md)、[兼容性](../compatibility.md)、[内核与 Native](../kernel-native.md) | 关键机制；每个 HAL/内核驱动的全部细节未穷举 |
| 页大小/ELF、Vendor API/LLNDK/VNDK | [Native 页与 ABI](../native-page-size-abi.md) | 机制与版本条件；所有 ELF/CPU/工具链细节及厂商 prebuilt 仍需原文/实物 |
| Bootloader、分区、bootconfig、DTB/DTBO、GBL | [Bootloader 与设备树](../bootloader-device-tree.md) | 装载/版本/组合契约；完整固件、结构体字段与板级树仍需目标实现 |
| Kernel 构建/ABI/modules、DMA-BUF、发布/respin、专项内核能力 | [内核构建与 GKI](../kernel-build-gki.md) | 机制；完整工具参数、每条发布产物与厂商驱动实现未穷举 |
| Runtime/ART、JIT/GC/ART TI、DEX、Zygote、系统服务/用户 | [Runtime 与 Framework](../runtime-framework.md)、[Runtime 执行与格式](../runtime-execution-format.md)、[性能优化](../performance-optimization.md) | 关键机制与格式约束；全部字节码表、GC/JIT 算法和调试插件实现仍需原文 |
| 权限、AppOps、角色、后台能力、隐私与企业策略 | [权限与隐私](../permissions-privacy.md)、[企业设备策略](../enterprise-device-policy.md) | 关键机制；每项权限和设备策略的版本矩阵未穷举 |
| 系统配置、init/sysprop/RRO，启动、OTA/APEX | [系统配置](../system-configuration.md)、[启动与更新](../updates-boot.md)、[OTA 交付与恢复](../ota-delivery-recovery.md) | 关键机制；全部 payload/COW 编码、recovery 扩展与设备实现仍需原文 |
| 各 Mainline 模块的职责/更新/权限/状态边界 | [模块契约](../mainline-module-contracts.md) | 按模块组归纳；完整 schema、权限矩阵和每代 API 仍需专门页/实现，不以名单视作全部机制完成 |
| Wi-Fi、Bluetooth、NFC/UWB、网络栈、RIL/IMS/eSIM | [Wi-Fi](../wifi-connectivity.md)、[电话与运营商](../telephony-carrier-esim.md)、[近距通信](../bluetooth-proximity.md)、[网络栈](../network-stack-services.md) | 主要分支机制；HCI/NCI/UCI/GSMA/SIP 全字段、厂商射频/调度、modem/LPA 与运营商后端未穷举；Wi-Fi Aware 架构 PDF 只提炼指定机制 |
| Camera 请求/缓冲、流组合、多摄/并发、session、HDR、3A/crop/reprocess/扩展/外接相机 | [相机与音视频](../media-camera-audio.md)、[相机流与会话](../camera-stream-sessions.md)、[相机扩展](../camera-advanced-features.md) | 关键机制；3A 调优、ITS 图像质量、全部扩展参数和完整流表未穷举 |
| Media、Codec2、DRM、安全输出、转码/低延迟/ROI/VVC | [相机与音视频](../media-camera-audio.md)、[媒体管线](../media-pipeline-codecs.md) | 机制与版本条件；codec 全部参数/码流格式及厂商安全路径仍需原文 |
| BufferQueue、Gralloc/Mapper/DMA-BUF、fence、SurfaceFlinger/HWC、GPU/Vulkan/ANGLE、Winscope | [图形、显示与输入](../graphics-input.md)、[图形内存与合成](../graphics-composer-memory.md) | 关键机制及诊断契约；每代 graphics HAL/GPU 驱动、全部扩展和 Winscope GUI 教程需原文 |
| 多窗口/多显示、Activity/IME/输入归属、Extensions、桌面窗口、ARR | [窗口与多显示](../window-display-management.md)、[刷新率与 ARR](../refresh-rate-arr.md) | 关键机制与版本条件；全部窗口转场、桌面操作行为及硬件面板时序未穷举 |
| 显示 color/HDR/tone-map/brightness、配置与转场 | [显示色彩与转场](../display-color-transitions.md) | 机制及版本条件；全部面板/LUT 校准、兼容标志和显示驱动实现需原文 |
| 输入/传感器/触觉/CHRE/USB/NNAPI、无障碍、本地化、字体与时间 | [传感器/输入/触觉](../sensors-input-haptics.md)、[硬件能力](../hardware-compute.md)、[无障碍](../accessibility.md)、[本地化与时间](../localization-time.md) | 关键路径；完整 USB/输入/传感器协议、融合/校准、各算子及语言特例需原文 |
| 存储、文件系统、FUSE/passthrough、访问隔离、容量/quota、备份 | [存储与数据](../storage-data.md)、[存储访问集成](../storage-access-integration.md) | 关键机制；全部存储迁移、备份传输协议与性能参数未穷举 |
| Power/thermal、BatteryStats、ADPF、内存与调度 | [电源与性能](../power-performance.md)、[内存与资源管理](../memory-resource-management.md) | 关键机制；硬件功耗模型与具体 hint/thermal policy 必须按产品确认 |
| SystemSuspend、能量/驻留观测、Wattson、无电池/TV 待机 | [Suspend 与能量](../power-suspend-energy.md) | 机制；SoC 模型/rail、完整 SQL 与产品唤醒源需专项验证 |
| Settings controller、tile、索引与建议 | [Settings 与搜索](../settings-search-integration.md) | 机制、历史条件；具体版本组件与视觉规范需查分支 |
| SystemUI 通知/FGS/Conversation、Launcher/Widgets、动态色、文本分类 | [SystemUI 与应用体验](../systemui-app-experience.md) | 机制、版本条件；全部 app API、视觉规范和模型算法需原文；旧 retail demo 明确作历史资料 |
| 虚拟化、Cuttlefish、AVF/pKVM/Microdroid、外设/计算 | [设备与虚拟化](../devices-virtualization.md)、[硬件能力与计算](../hardware-compute.md)、[性能优化](../performance-optimization.md) | 架构及关键边界；专用硬件协议、VM 内部实现和计算驱动调度的硬件实现仍需专项查阅 |

## Devices 与 Automotive 的独立导航

| 子主题 | 已有深度与所在文件 | 仍需查原文的边界 |
|---|---|---|
| Enterprise、device policy resolution、用户类型/工作资料、委托/撤管、企业 OTA/电话 | 机制：[企业设备策略](../enterprise-device-policy.md) | 全部管理 API/策略及版本矩阵；管理员策略不能替代服务端授权 |
| Cuttlefish 全侧栏、实例/恢复、GPU/虚拟无线、host/guest、多租户/CHD | 机制：[Cuttlefish host/guest](../cuttlefish-host-guest.md) | snapshot 等支持条件需按版本；VMM 协议、host 驱动与完整部署仍需专项查阅 |
| TV/TIF/Tuner/CAS/CEC、tunneled playback、参考 TV App/定制 | 机制：[TV 集成](../tv-device-integration.md) | 各广播标准、CA 系统及完整 HDMI/CEC 协议仍需实现/规范 |
| VHAL、CarService、vehicle power/watchdog/remote access、连接/时间/开发工具 | 机制：[车辆服务](../automotive-vehicle-services.md)及其分支归属表 | 全部 vehicle property/vendor extension、实车 MCU 和部署配置未穷举 |
| 用户/occupant zone/显示/输入、HMI/Scalable UI/语音/分心限制/安全 | 机制：[乘员与 HMI](../automotive-occupants-ui.md) | 完整交互规范、驾驶法规和车型策略不能由通用知识代替 |
| 车载音频 zone/focus/volume/电源、EVS/Camera2、radio | 机制：[车载媒体](../automotive-media-integration.md) | 硬件通道/放大器、图像质量、完整 tuner 与车型音频策略 |
| SDV 架构及服务/topic/channel、跨 VM I/O、部署/恢复/诊断 | 机制与设计边界：[SDV 概览](../automotive-sdv.md)、[SDV 服务协议](../sdv-service-protocols.md) | 每代实验特性、完整 wire/schema、生产级安全认证与厂商虚拟化实现需核实 |
| AAOS releases/unbundled apps、工具/测试基础设施 | 各车辆页的版本与责任边界，具体版本沿目录查阅 | 不把 release note 累计成所有产品均支持；每个 app 的全部 UI/发布配置未逐项展开 |

## Audio

官方范围：[Audio](https://source.android.com/docs/core/audio)。

| 子主题 | 已有深度与所在文件 | 仍需查原文的边界 |
|---|---|---|
| AIDL/HIDL 代际、policy/CAP、attributes/strategy/volume、路由/profile | 机制：[音频策略与 Framework](../audio-framework-policy.md) | 目标 HAL 的 XML/接口和每种设备组合配置 |
| Focus、effects/session、预处理、并发 capture、SoundTrigger | 机制：同上 | 完整仲裁矩阵、DSP 实现、效果算法和所有测试参数 |
| Spatializer/head tracking、LE audio、AMSCO、sound dose、TV/soundbar | 机制、版本条件：同上 | 音频校准、姿态融合算法、完整 HDMI-CEC 协议、蓝牙协议与硬件一致性测试细节 |
| FAST、实时线程、priority inversion、AAudio/MMAP | 机制：[音频性能与 I/O](../audio-performance-io.md) | 产品实时预算、HAL/驱动队列和硬件时钟实现 |
| 延迟/loopback/warmup、数据格式/SRC、高解析效果 | 机制：同上 | dongle 制作细节、完整滤波算法与设备实测数据 |
| USB role/profile/clock、preferred attributes/bit-perfect、MIDI | 机制、版本条件：同上 | 完整 UAC descriptors/协议、MIDI 2.0 UMP/property exchange 与全部合规测试步骤 |
| 调试、共享库、能力声明 | 机制与历史条件：同上及[相机与音视频](../media-camera-audio.md) | 历史示例产品不作为当前产品配置模板 |

## Perf

官方范围：[Performance](https://source.android.com/docs/core/perf)。相关 ART 页面位于 runtime，而刷新率位于 display；按机制读取，不受栏目路径限制。

| 子主题 | 已有深度与所在文件 | 仍需查原文的边界 |
|---|---|---|
| ART CLC/uses-libraries、boot profile、R8、PGO/AutoFDO | 机制、版本条件：[性能优化](../performance-optimization.md) | 产品 profile、编译参数、反射/JNI keep 规则必须由实际依赖验证 |
| boot 关键路径、调度/CPU/等待、测量条件 | 机制：同上及[电源与性能](../power-performance.md) | 文档中的旧设备调参不作为通用默认值 |
| LMKD、freezer、hibernation、cgroups/task profiles | 机制、版本条件：[内存与资源管理](../memory-resource-management.md) | OS×target SDK 行为、产品阈值与 vendor 覆盖 |
| Android 17 memory limiter/budgets、mmd/pmgd、ZRAM | 机制、版本条件：同上 | 新服务是否存在、构建启用和实际控制权须查分支；不倒灌旧 BSP |
| ADPF/性能 hint、游戏 boost、thermal | 机制与概览：[电源与性能](../power-performance.md) | 产品 HAL、负载与硬件温度限制 |
| APK caching、compatibility WAL、task snapshots | 机制、历史/版本条件：[性能优化](../performance-optimization.md) | 工厂预载与 OTA 失效、SQLite 连接行为、snapshot 共享/磁盘缓存需与目标实现匹配；旧属性不是通用调参 |
| Health HAL、trade-in、游戏 hint、NPU manager | 机制、版本条件：同上 | Health 2.1 是历史接口条件；trade-in 的受限状态与可信诊断、新 NPU 预约协议不能倒灌旧产品；vendor 服务和固件仍需验证 |
| MM 历史压力统计 | 机制、历史/版本条件：[内存与资源管理](../memory-resource-management.md) | 启用、数据源和历史窗口按目标分支确认；不以事后单张内存快照代替 |

## Tests

官方范围：[Tests](https://source.android.com/docs/core/tests)。

| 子主题 | 已有深度与所在文件 | 仍需查原文的边界 |
|---|---|---|
| 测试选择、atest、TEST_MAPPING、CTS/VTS/STS 边界 | 机制：[测试与诊断](../testing-diagnostics.md) | 每个套件版本的计划、排除、重试与认证要求 |
| 测试模块/build 配置、target/preparer、runner/listener、清理 | 机制：[测试基础设施](../test-harness-infrastructure.md) | 全部 Tradefed 扩展接口与 XML 参数 |
| run failure/零用例、结果事件、metrics、retry、shard、多设备 | 机制：同上 | 实验室调度、厂商基础设施和结果后端未专门实现 |
| VTS 实例发现/参数化、测试适用性、HIDL 历史能力 | 机制、版本条件：同上 | 各 HAL 套件及接口版本的测试细节 |
| Fuzz/sanitizer、tombstone、ANR/watchdog、Perfetto | 机制：[测试与诊断](../testing-diagnostics.md)、[签名与内存安全](../signing-memory-hardening.md) | 专门 fuzzer corpus/coverage、长稳可靠性与性能基准须按模块设计 |
| 全部 host/target runner 插件、ATS/OmniLab 编排、旧 VTS Dashboard/数据库、测试教程的逐个实例 | 入口 | **未逐项提炼**；已有生命周期知识不代表支持所有插件选项或后端部署 |

## Data（网络数据，不是磁盘存储）

官方范围：[Data](https://source.android.com/docs/core/data)。

| 子主题 | 已有深度与所在文件 | 仍需查原文的边界 |
|---|---|---|
| UID/tag/interface 计量、eBPF、VPN/464xlat 归属 | 机制：[网络数据计量与控制](../network-data-accounting.md) | 具体 map/计数修正顺序绑定目标 revision；历史桶插值、VPN 分摊算法尚未逐项提炼 |
| tethering 数据、硬件 offload、NAT/配额责任 | 机制：同上 | vendor offload 的连接跟踪和硬件统计实现 |
| Data Saver、网络配额、计费周期、排除网络类型 | 机制：同上 | 现代 NetworkPolicy 全部优先级、运营商/产品策略及 UI；同接口上不同 APN 的统计限制不能靠配置魔法解决；文档的 UTC 周期示例不能覆盖源码中带时区的实际 recurrence rule |
| 历史 kernel quota2/qtaguid 说明 | 机制、历史条件：同上 | 不能用旧补丁/节点指令覆盖当前 eBPF 路径 |

## 后续查漏的判定

新增主题只有在知识文件实际解释其状态关系、关键约束和失效证据后，才从“入口”提升为“机制”。补充某个局部机制不提升整个栏目；没有适用设备、源码和验证条件时，不宣称能够覆盖该主题的全部开发需求。
