---
name: aosp
description: AOSP / Android 平台领域知识，用于理解、设计、实现、调试和审查系统应用、Framework、Native 服务、HAL、内核及设备集成。按涉及的子系统提供机制、接口契约、安全和兼容性边界、诊断证据与官方文档定位；适用于 AOSP、BSP、AAOS、系统定制及平台问题分析。
---

# AOSP

提供 Android 开源平台的领域知识。回答具体问题时，将机制、不变式、版本条件和可观察证据应用到目标源码；按涉及的子系统读取资料，不默认执行一套完整开发流程。

## 事实边界

- **先固定平台事实**：Android 版本/分支、设备与产品、启动或首次出厂版本、源码 revision、运行镜像、构建变体、相关模块及权限。SDK/target SDK、设备 launch level、当前系统版本和 vendor 接口版本可能分别影响行为，不能互相代替。
- **证据有层次**：目标分支实现与配置说明“此处实际如何运行”；对应版本的 CDD、接口稳定性与安全要求说明“必须满足什么”；最新官方概览帮助导航。现有实现可能违反规范，不能以源码存在为理由豁免兼容要求，也不能把最新特性倒灌旧分支。
- **辨认运行边界**：Java/Kotlin/C++/Rust 是实现语言；进程、UID、SELinux 域、用户/profile、安装分区、构建模块、APEX 与接口版本分别承担不同职责，不作一一映射。
- **区分事实与推断**：指出官方机制或目标源码支持的事实，说明据此推导的约束；未确认的设备行为、厂商实现与硬件能力保留条件。源码树不包含的闭源实现不能凭空补全。
- **证据绑定产物**：讨论构建或测试结果时核对 revision、产品、模块、产物与设备，保留实际执行范围、失败、跳过和环境受阻状态。日志出现、编译成功或某套件通过，都只证明相应检查覆盖的条件。

## 平台心智模型

Android 的可观察行为来自多层协作：应用和系统应用通过 Framework API 与系统服务交互；跨进程调用经 Binder 等 IPC；系统服务可能调用 native 组件和 HAL；HAL/内核与硬件协作。部分服务运行在 `system_server`，其他服务有独立进程，实际布局以目标实现为准。

分析一个功能时，追踪以下关系，而不是只按目录名字判断归属：

```text
入口与调用身份 → 权限和用户作用域 → 状态所有者/策略 → IPC/线程边界
             → native/HAL/内核（实际涉及时） → 结果与回调 → 恢复和资源释放
```

同一逻辑动作可跨越不同生命周期和版本边界。对新功能，找控制该行为的现有状态与扩展点；对缺陷，沿真实调用链寻找不变式的破坏点；对接口或平台演进，检查旧调用者、新服务与回滚组合是否仍满足契约。

## 按领域读取知识

根据变更机制选择模块；涉及多个边界时组合读取。每份资料包含原理、失效方式和官方深链，不能把整张表作为每次任务的必读清单。

| 领域与触发线索 | 知识文件 |
|---|---|
| 进程/分区、Treble、Binder、AIDL/HIDL、HAL、IPC 身份和同步 | [架构与 IPC](references/architecture-ipc.md) |
| ART、Zygote、系统服务、进程与包、用户生命周期、Settings/SystemUI | [Runtime 与 Framework](references/runtime-framework.md) |
| JIT/GC/ART TI、DEX/register/code-unit 验证、Zygote、Signed Config | [Runtime 执行与格式](references/runtime-execution-format.md) |
| GKI/KMI、驱动、BPF、native 链接/资源、JNI | [内核与 Native](references/kernel-native.md) |
| Kleaf、KMI/ABI/STG、模块类别、DMA-BUF、kernel 发布/respin | [内核构建与集成](references/kernel-build-gki.md) |
| 16 KB 页、ELF/APK 对齐、page-size compat、Vendor API、LLNDK/VNDK | [Native 页与 ABI](references/native-page-size-abi.md) |
| boot/vendor_boot/init_boot、bootconfig、fastbootd、DTB/DTBO 与 GBL | [Bootloader 与设备树](references/bootloader-device-tree.md) |
| 权限、SELinux、AVB、TEE、KeyMint/Keystore、加密和安全公告 | [安全模型](references/security.md) |
| LockSettings、Gatekeeper、Weaver、生物识别、认证与操作确认 | [认证链](references/security-authentication.md) |
| 密钥域/授权、KeyMint 操作、attestation 信任链与 RKP | [密钥与证明](references/security-keystore-attestation.md) |
| public/private sepolicy、版本映射、跨 system/vendor 升级 | [SELinux 兼容](references/selinux-compatibility.md) |
| APK 签名/轮换、MTE/HWASan、CFI/SCS、内存缓解与诊断 | [签名与内存安全](references/signing-memory-hardening.md) |
| Trusty TA、port/channel、message/handle、DICE 派生与可信身份 | [可信执行](references/security-trusted-execution.md) |
| Identity Credential、会话/认证密钥、OMAPI/SE 的 UID/AID 访问 | [身份凭据与安全元件](references/security-identity-secure-elements.md) |
| Safety Center、Private Space、蜂窝安全与通知 | [平台安全服务](references/security-platform-services.md) |
| wrapped keys、FBE 密钥依赖、Adiantum、adoptable/FDE 与恢复 | [加密密钥生命周期](references/encryption-key-lifecycle.md) |
| runtime permissions、AppOps、角色、前后台能力与隐私数据路径 | [权限与隐私](references/permissions-privacy.md) |
| Device/Profile Owner、策略冲突、委托、受管 profile 和撤管 | [企业设备策略](references/enterprise-device-policy.md) |
| CDD、CTS/VTS、VINTF、接口稳定性、跨版本与发布兼容 | [兼容性](references/compatibility.md) |
| CTS/CTS-V、Camera ITS、音频/传感器仪器测试、SE/多设备测量 | [兼容性设备验证](references/compatibility-device-verification.md) |
| Repo/manifest、Soong、产品/变体、API surface、编译与发布 | [构建与源码演进](references/build-release.md) |
| 主机构建条件、同步归因、产品继承、BoardConfig、镜像与硬件差异 | [环境与产品集成](references/setup-product-integration.md) |
| SBOM、组件/文件来源、应用更新所有权、参考板与交付输入 | [构建来源与更新归属](references/setup-supply-chain.md) |
| aconfig、声明/容器、release config、运行时取值与开关测试 | [Feature flags](references/feature-flags.md) |
| java_sdk_library、API scope、异步/取消、IPC cache 与失效 | [平台 API 契约](references/platform-api-contracts.md) |
| sysprop、属性服务、init 触发、RRO/idmap、设备配置 | [系统配置](references/system-configuration.md) |
| 启动链、init、分区、OTA、A/B/Virtual A/B、APEX、回滚 | [启动与更新](references/updates-boot.md) |
| OTA 包/签名、super、snapshot merge、checkpoint、DSU/RoR/vendor APEX | [OTA 交付与恢复](references/ota-delivery-recovery.md) |
| 各 Mainline 模块的更新、依赖、权限、数据与状态归属 | [模块契约](references/mainline-module-contracts.md) |
| Wi-Fi、Bluetooth、NFC/UWB、网络栈、共享网络、RIL/IMS/eSIM | [连接与通信](references/connectivity-telephony.md) |
| Wi-Fi HAL、扫描/选择、STA/AP 并发、SoftAP、Passpoint/TOFU/MLO | [Wi-Fi 集成](references/wifi-connectivity.md) |
| RIL/IMS、紧急呼叫/域选择、运营商/订阅、5G/卫星与 eSIM | [电话与运营商](references/telephony-carrier-esim.md) |
| Bluetooth profile、NFC/钱包、UWB、Presence/Ranging OOB | [蓝牙与近距通信](references/bluetooth-proximity.md) |
| Network selection/validation、APF、CaptivePortal、VPN、companion | [网络栈服务](references/network-stack-services.md) |
| UID/tag 统计、VPN/464xlat 归属、tethering offload、Data Saver 与配额 | [网络数据计量与控制](references/network-data-accounting.md) |
| Camera HAL、流/缓冲/元数据、音视频、Codec2、DRM、音频策略 | [相机与音视频](references/media-camera-audio.md) |
| Codec2/extractor、transcoding、编码统计/ROI、低延迟、VVC/安全媒体 | [媒体管线](references/media-pipeline-codecs.md) |
| 逻辑多摄/独立并发、流组合、session 参数、动态 surface、HDR | [相机流与会话](references/camera-stream-sessions.md) |
| 3A/crop/reprocess、扩展、系统/外接相机、webcam、torch/稳定/HEIF | [相机扩展与成像](references/camera-advanced-features.md) |
| Audio Policy/CAP、效果/预处理、并发录音、空间音频、蓝牙与音量安全 | [音频策略与 Framework](references/audio-framework-policy.md) |
| FAST/MMAP、实时线程、延迟量测、USB/bit-perfect、MIDI、采样转换 | [音频性能与 I/O](references/audio-performance-io.md) |
| SurfaceFlinger、HWC、BufferQueue/fence、显示模式、输入与传感器 | [图形、显示与输入](references/graphics-input.md) |
| Mapper/Gralloc/DMA-BUF、Composer、GPU/GLES/Vulkan/ANGLE、Winscope | [图形内存与合成](references/graphics-composer-memory.md) |
| HDR/color/tone mapping、brightness、cutout/rotation、显示配置与转场 | [显示色彩与转场](references/display-color-transitions.md) |
| task/Activity 落屏、多窗口、multi-resume、IME、输入关联与显示信任 | [窗口与多显示](references/window-display-management.md) |
| ARR/MRR、TE/Vsync、最小帧间隔、present 时序与模式切换 | [刷新率与 ARR](references/refresh-rate-arr.md) |
| 辅助服务、窗口/节点、放大与坐标、受限屏幕读取 | [无障碍交互](references/accessibility.md) |
| locale、资源与字体回退、系统时间、时区与规则数据 | [本地化与时间](references/localization-time.md) |
| CE/DE、FBE、vold、文件系统、存储访问、数据用量和备份 | [存储与数据](references/storage-data.md) |
| FUSE/passthrough、卷挂载、scoped/adoptable、容量统计与磁盘 quota | [存储访问集成](references/storage-access-integration.md) |
| 电源/Doze、thermal、Power HAL、内存/LMKD、调度和性能证据 | [电源与性能](references/power-performance.md) |
| SystemSuspend/wakeup、PowerStats、Wattson、无电池与 TV 待机 | [Suspend 与能量观测](references/power-suspend-energy.md) |
| Settings Controller、动态 tile、索引/可见性、建议排序与用户状态 | [Settings 与搜索](references/settings-search-integration.md) |
| 通知/FGS/Conversation、媒体控制、Launcher/Widgets、主题与文本分类 | [SystemUI 与应用体验](references/systemui-app-experience.md) |
| ART CLC/boot profile、R8/PGO/AutoFDO、启动关键路径与性能归因 | [性能优化](references/performance-optimization.md) |
| freezer/hibernation、cgroups、memory limiter/budgets、mmd/pmgd | [内存与资源管理](references/memory-resource-management.md) |
| atest、TEST_MAPPING、Tradefed、测试套件、fuzz、tombstone/ANR/Watchdog | [测试与诊断](references/testing-diagnostics.md) |
| 测试模块/XML、Tradefed 生命周期/失败、retry/shard、多设备与 VTS 实例 | [测试基础设施](references/test-harness-infrastructure.md) |
| AAOS、CarService/VHAL、车辆电源/音频、多用户与多显示 | [车载](references/automotive.md) |
| VHAL property/area、异步请求、车辆电源、watchdog、remote access | [车辆服务](references/automotive-vehicle-services.md) |
| Occupant zone、Scalable UI、用户/显示、驾驶分心与车载语音 | [乘员与 HMI](references/automotive-occupants-ui.md) |
| Car audio zones/focus/volume、EVS/Camera2、radio、音视频集成 | [车载媒体](references/automotive-media-integration.md) |
| SDV 多 VM、服务发现、跨 VM 协作、车辆安全与更新责任 | [车载 SDV](references/automotive-sdv.md) |
| SDV 服务/topic/channel、DataLoss/离线、跨 VM I/O、部署与更新 | [SDV 服务协议](references/sdv-service-protocols.md) |
| Cuttlefish、虚拟设备、AVF/pKVM/Microdroid、其他设备形态 | [设备与虚拟化](references/devices-virtualization.md) |
| Cuttlefish 实例/reset/snapshot、GPU/WebRTC/虚拟无线、CHD/多租户 | [Cuttlefish host/guest](references/cuttlefish-host-guest.md) |
| TV TIF/Tuner/CAS、HDMI-CEC、tunneled playback 与 TV App 定制 | [TV 集成](references/tv-device-integration.md) |
| NNAPI/计算驱动、Context Hub/CHRE、触觉、USB 与外设生命周期 | [硬件能力与计算](references/hardware-compute.md) |
| Sensors/FMQ/flush/wake、Input .kl/.kcm、多触点、Haptics/CHRE/USB | [传感器、输入与触觉](references/sensors-input-haptics.md) |
| 文档/源码/API reference 对照、版本演进、资料覆盖与查漏 | [资料与演进依据](references/reference-and-evolution.md) |

## 高频边界

以下是定位方向，具体约束和反例在对应知识文件中：

- Binder 的线程与同步调用可能跨进程重入；持锁外部调用、身份切换和异步派发都需要保持原有授权、顺序与状态语义。
- 用户/profile 与调用者身份不是同一维度；设备级、用户级和 profile 级状态必须由实际所有者维护。开机可用不代表解锁前可用。
- AIDL 是接口描述方式；Stable AIDL、VINTF 稳定性与接口冻结有具体适用范围。API 可编译不等于跨版本或跨分区可用。
- Android 权限、Linux DAC/capabilities 和 SELinux 是不同控制层。某层允许不能替代其他层检查；root 也不自动绕过 SELinux。
- Buffer、文件描述符、JNI 引用、回调注册、wakelock 和设备句柄具有所有权与释放责任；进程退出前的资源泄漏也可能导致功能或系统退化。
- OTA 和 APEX 改变的不只是文件内容，还涉及签名、版本、依赖、数据与回滚兼容。A/B、Virtual A/B、动态分区和 AVB 分别解决不同问题。
- CTS 验证兼容性的一部分，平台测试验证具体实现；设备行为、HAL/内核、性能和安全检查按实际风险选择，不能互相充当全覆盖证明。

## 官方资料检索与覆盖

以 [Google AOSP 文档](https://source.android.com/docs) 为主要资料体系；[Android Code Search](https://cs.android.com/) 和目标分支代码用于确认实现，官方 API reference 用于核对符号与签名。

本地 [主题深度核对表](references/sources/topic-coverage.md) 区分机制已提炼、概览和仅检索入口，记录已知薄弱处。[实际侧边栏](references/sources/sidebar.json) 跟随顶部栏目标签保留可折叠标题及后代，分别记录知识候选文件、直接引用与采集状态；候选路由不代表叶子全文已提炼。[采集记录](references/sources/coverage.json) 区分已发现、已抓取正文、不可访问和待处理页面。[文档目录](references/sources/catalog.jsonl) 是可检索的出处索引，**正文结构提取不等于每条陈述均已完成语义核实**；各领域文件中的资料是相应知识提炼的直接依据。

不批量把全站目录加载进上下文。先搜索英文机制名、接口或错误信息，例如：

```sh
python3 scripts/docs_catalog.py search "binder identity"
python3 scripts/docs_catalog.py search "virtual a/b snapshot"
python3 scripts/docs_catalog.py search "camera buffer fence"
```

命令在本 skill 目录运行，或使用脚本的实际绝对路径。命中索引后只打开相关原文；涉及版本敏感结论时核对适用版本和源码。离线情况下使用本地知识继续推理，明确尚待复核的条件。

侧边栏不是从 URL 前缀猜测。运行 `scripts/sidebar_inventory.py` 可重新读取各栏目及其标签导航；`--html-dir /tmp/aosp-sidebar-cache` 可选择临时缓存，省略该参数则重新取导航。`references/sources/sidebar-routes.json` 维护知识归属，不把路由存在自动提升为语义完成。

继续未完成采集时使用 `scripts/docs_catalog.py sync --resume`；重新获取已有页面及发现新增内容时使用 `sync --resume --refresh`；`--retry-failed` 重试不可访问项。工具只读访问公开官方页面，不会自动将新网页变成已核实规则，也不会修改平台代码或设备。只有出现真实需求、规则变化或反例时，才修订对应的知识文件与出处。
