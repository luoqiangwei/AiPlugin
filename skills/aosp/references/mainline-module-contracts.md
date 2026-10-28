# Mainline 模块的更新边界与状态所有者

用于解释模块独立更新后谁负责状态、哪些依赖仍在整机中，以及权限/格式兼容为什么不能靠包替换解决。核实日期：2026-10-28。
APEX 激活、签名与 OS 回退见[启动与更新](updates-boot.md)、[OTA 交付与恢复](ota-delivery-recovery.md)。
本页对官方 Architecture 与 OTA 路径的相同模块去重；`runtime` 等重定向到总览的别名不算新模块。总览表与专门页不一致时，按目标版本和专门页确认包格式，不能把名字数量当成更新能力。

## 更新原子性不等于所有状态都能无条件回退

[Mainline](https://source.android.com/docs/core/ota/modular-system)将选定组件封装成 APK/APEX，通过适用分发渠道独立交付；相互依赖的更新集可原子安装/回滚。
边界依靠稳定 SDK/System API、C 接口或 AIDL，而不是依靠所有组件恰好同次编译。
模块可包含 bootclasspath JAR、system_server 代码、应用和 native 库；APEX 不是一个独立进程，模块更新也不改变调用者 UID 的含义。

**工程推导**：至少区分 package/签名身份、活动代码版本、服务进程、持久状态、HAL/固件和调用方 API 能力。
原子替换模块包不回滚外部服务器状态、硬件固件或所有数据库副作用；数据 schema/缓存与旧代码兼容仍由相应状态所有者负责。
GMS 与 AOSP 包名/签名可能不同，不能把 `com.google.android.*` 机械替换为 `com.android.*` 就假设证书、overlay target 和授权配置都匹配。
Android 11 及以下 Mainline 分发支持在当前官网有终止说明；旧代码仍存在不表示维护渠道仍提供更新，执行时重新核对对应产品承诺。

## 运行基础、能力发现与配置

| 官方模块 | 独立交付的实际责任 | 依赖、状态和权限边界 |
|---|---|---|
| [ART](https://source.android.com/docs/core/ota/modular-system/art) | Android 12 起可更新运行时与 managed core libraries | 应用/服务启动前必须可用；Bionic、ICU 与 ART 的演进不同，不因 ART 更新假设 native ABI 变化 |
| [SDK Extensions](https://source.android.com/docs/core/ota/modular-system/sdk-extension) | 读取各模块元数据派生 extension level；Android 12+ 合并 classpath 配置 | 状态来自活动模块集合，不能只看 SDK_INT 或单个包版本；classpath 顺序属于启动契约 |
| [Config Infrastructure](https://source.android.com/docs/core/ota/modular-system/config-infrastructure) | Android 14 起把 DeviceConfig 相关基础设施模块化 | 基础设施与某特性的 flag 定义、取值和状态迁移不同；网页“无新依赖”不赋予任意调用者改配置权限 |
| [ModuleMetadata](https://source.android.com/docs/core/ota/modular-system/metadata) | 为 PackageManager 提供模块列表与显示元数据，system_server 启动时解析缓存 | 描述包存在不证明某模块处于活动版本或设备已具备其硬件能力 |
| [Time Zone Data](https://source.android.com/docs/core/ota/modular-system/timezone) | 独立更正时区/DST 规则数据 | 规则更新不等于设置设备时钟；历史 APK 更新可遮蔽 APEX 数据，不能并行沿用两种更新渠道而忽略优先级 |
| [adbd](https://source.android.com/docs/core/ota/modular-system/adbd) | Android 11+ APEX 内的调试会话 daemon | 仍依赖 ART 的 JDWP 连接和 system_server 认证接口；可更新可靠性不表示允许绕过调试授权 |

这组模块改变其它代码被加载或解释的条件。故故障既可能表现为本模块无法激活，也可能首先表现为应用启动、类加载或功能探测异常。
持久配置和派生缓存应按其产生来源失效，不能把一次读到的 extension/classpath 永久保存并套用到下次模块组合。

## 网络与无线：协议栈更新不携带任意硬件实现

| 官方模块 | 模块中拥有的状态/逻辑 | 边界外依赖与失效含义 |
|---|---|---|
| [Network Stack](https://source.android.com/docs/core/ota/modular-system/networking) | IpClient、DHCP、NetworkMonitor、门户探测/登录 | 独立进程与 stable AIDL、netd 接口及专门权限配置 APK 协作；IP 已配置、网络验证成功和门户登录成功是不同状态 |
| [DNS Resolver](https://source.android.com/docs/core/ota/modular-system/dns-resolver) | DNS 查询、缓存和 resolver 配置端点 | 对接 Bionic 兼容入口和系统服务；更新 resolver 不等于更换整个 netd，也不能把旧缓存归属到新网络 |
| [Tethering/Connectivity](https://source.android.com/docs/core/ota/modular-system/tethering) | Tethering；Android 12+ 扩展到 ConnectivityService，并承载相应 eBPF offload | DHCP server 来自 Network Stack，仍有系统 API、HAL/内核依赖；硬件 offload 与模块中的软件路径须分别观察 |
| [Wi-Fi](https://source.android.com/docs/core/ota/modular-system/wifi) | API/service、连接配置、资源及登录/对话组件 | wificond、芯片 HAL 和部分 native 库在外；原厂自定义存储格式需转换，不能仅装新模块就读旧私有网络配置；RRO target 需匹配实际资源包 |
| [Bluetooth](https://source.android.com/docs/core/ota/modular-system/bluetooth) | Host stack/API/APK/JNI；Android 13 引入可选模块，Android 16+ 可更新 | 芯片 HAL、Audio、Telephony、PAN/Tethering 在其依赖链上；host 栈更新不能保证 controller 固件/射频或音频路由同时修复 |
| [NFC Services](https://source.android.com/docs/core/ota/modular-system/nfc-services) | Android 16 的可选可更新 APEX，包含 API、NfcNci 和 NCI native 栈 | 仍依赖厂商 HAL、SE 及 Framework 运行时权限；模块存在不证明安全 applet 已部署 |
| [UWB](https://source.android.com/docs/core/ota/modular-system/uwb) | Android 13+ 的 FiRa/UCI 上层栈、会话和 API | 芯片 HAL、蓝牙 OOB、SE 与核心权限执行仍参与；成功创建 session 不能代替真实测距/密钥建立 |
| [IPsec/IKEv2](https://source.android.com/docs/core/ota/modular-system/ipsec) | 协商、rekey、dead-peer detection、handoff 的客户端库 | 通过 Android IPsec API 使用内核能力；协议库不取代 VPN 业务授权、路由或内核加密实现 |
| [CellBroadcast](https://source.android.com/docs/core/ota/modular-system/cellbroadcast) | Service 解码/去重/地理筛选，Receiver 显示并保存告警 | 仍从 RIL/Framework 接收数据；模块内历史访问权限与默认 SMS 应用访问不同，写入 SMS inbox 还需平台 AppOps 配合 |

**工程推导**：网络组共同依赖接口身份、用户/订阅作用域与异步回调。更新后保留错误的旧 session、接口索引或配置缓存，会使“单模块已升级”与实际连接行为脱节。
Tethering 专门页还描述 Android 13 的 CrossDevice 子主题：发现与认证连接依赖 Wi-Fi/Bluetooth/UWB，主体使用 APEX、资源使用 APK。该处没有给出完整包身份，不能猜包名，也不能由 Tethering 的包名推断所有分支都包含同样组成；具体交付归属以目标模块配置为准。

## 隐私、内容与用户数据

| 官方模块 | 实际责任与独立更新价值 | 状态/权限不变量 |
|---|---|---|
| [PermissionController](https://source.android.com/docs/core/ota/modular-system/permissioncontroller) | 权限 UI/策略、使用记录和 roles；Android 11+ APEX，Android 10 APK 条件不同 | 用户/包/角色关系仍是授权主体；改 UI 不消除实际权限检查，预授予/固定权限也不按普通闲置权限撤销规则处理 |
| [DocumentsUI](https://source.android.com/docs/core/ota/modular-system/documentsui) | 经系统选择器授予文档访问，APK 可独立修复 | `MANAGE_DOCUMENTS` 有签名/唯一持有者约束；隐藏 Files 图标不等于取消 GET_CONTENT 等选择器能力，Android 12 的浏览入口条件需分开看 |
| [MediaProvider](https://source.android.com/docs/core/ota/modular-system/mediaprovider) | 索引媒体元数据并经 MediaStore 提供访问，APK-in-APEX | 数据库索引、真实文件及调用者授权分别存在；更新 provider 不能使未获权应用任意读取介质 |
| [AppSearch](https://source.android.com/docs/core/ota/modular-system/appsearch) | 本地结构化索引、查询与 Icing；Android 12 已用 APEX，13 才列为 Mainline | 服务/索引状态位于设备，与 NDK/ICU/protobuf 依赖有关；“本地索引”不能推导所有业务数据自动跨应用共享 |
| [Android Health](https://source.android.com/docs/core/ota/modular-system/android-health) | Android 14+ 的健康数据管理/访问与可替换数据管理 UI | UI 自定义仍须满足该版本 API/依赖；健康记录存在与应用获得相应数据访问权不同 |
| [ExtServices](https://source.android.com/docs/core/ota/modular-system/extservices) | 通知排序、文本分类、autofill matching/inline render、cache quota、display hashing 等，按版本增长 | 接口调用和具体服务选择仍由 Framework 配置；Android 10 APK 与 11+ APEX 不应混为同一激活路径 |
| [AdServices](https://source.android.com/docs/core/ota/modular-system/adservices) | Privacy Sandbox、API APK 与 SDK Runtime 相关组成 | SDKSandbox 有独立 UID/SELinux/存储与通信限制，广告 SDK 不自动继承宿主应用权限；主 APEX 与配套 APK 需保持协同 |
| [OnDevicePersonalization](https://source.android.com/docs/core/ota/modular-system/ondevicepersonalization) | 策略控制数据进出及允许操作，含联邦计算相关组成 | 依赖 PackageManager 对相应 manifest 能力的理解；“设备端”不能替代实际策略执行和输出数据边界 |

这组模块更新往往遇到真实持久状态。数据库迁移、索引重建、权限/角色结果与用户可见配置必须各自有所有者；重建缓存不能悄悄清除用户记录或重新授予已撤销权限。

## 媒体、计算与密码服务

| 官方模块 | 模块内容与状态责任 | 外部边界 |
|---|---|---|
| [Media / Media Codecs](https://source.android.com/docs/core/ota/modular-system/media) | 两个 APEX 分别承载 extractors/相关 media API 与可更新软件 Codec2；解析输入、session、转码能力按版本不同 | vendor 硬件 codec 和 DRM/安全输出不因软件 codec 更新自动变化；插件仍须满足模块边界 |
| [NNAPI Runtime](https://source.android.com/docs/core/ota/modular-system/nnapi) | 应用与驱动之间的 `libneuralnetworks` 运行时，专门页规定 APEX | 依赖 HAL 与 AHardwareBuffer；Android 15 起 NDK API 弃用不代表 HAL 移除，旧模型/缓存与新驱动组合仍需兼容 |
| [Conscrypt](https://source.android.com/docs/core/ota/modular-system/conscrypt) | Java/native TLS 与 JCA/JSSE provider；Android 14+ 增加可更新 root trust store | 内含 BoringSSL 不使任意调用方可依赖其私有 ABI；应用 NetworkSecurityConfig/自选信任根仍改变验证结果 |
| [Remote Key Provisioning](https://source.android.com/docs/core/ota/modular-system/remote-key-provisioning) | Android 14+ 将 RKPD app、system-server fragment、密钥池/后端通信组织在 APEX | 仍依赖 `IRemotelyProvisionedComponent` 产生证明材料；模块升级不等于硬件密钥或远端信任根同时更新 |

密码、媒体和计算都处理攻击者可影响的输入；独立更新缩短修复交付链，却不能扩大外部服务、HAL 或 native 依赖的未声明接口。

## 遥测、重启时机与故障恢复

| 官方模块 | 更新单元与状态所有者 | 失败/权限边界 |
|---|---|---|
| [Statsd](https://source.android.com/docs/core/ota/modular-system/statsd) | Native metrics daemon 与 Java bridge，包含配置/原子指标消费关系 | daemon 可活过 system_server，故 Framework 重启不代表统计已清零；生产者 schema 与 pull 语义需一致 |
| [Device Scheduling](https://source.android.com/docs/core/ota/modular-system/scheduling) | `RebootReadinessManagerService` 判断是否适合不打扰用户地重启 | 提供就绪信号，安装器仍拥有实际更新/重启操作；“可重启”不是数据已提交或 OTA 已准备完毕 |
| [Crash Recovery](https://source.android.com/docs/core/ota/modular-system/crash-recovery) | Android 16 将 PackageWatchdog、RescueParty、Rollback observer 等纳入 APEX | 故障观察、缓解决策与真实包回滚有不同阶段；它不是 OS slot、AVB 或 userdata checkpoint 的替代品 |
| [Profiling](https://source.android.com/docs/core/ota/modular-system/profiling) | Android 16 APEX 提供 framework API 与 system_server 中 ProfilingService | 请求受限速且不保证获准；结果按请求进程脱敏并写应用目录，不能作为跨应用任意 trace 导出接口 |
| [UprobeStats](https://source.android.com/docs/core/ota/modular-system/uprobestats) | Android 16 的 uprobe/eBPF 动态遥测，管理附着、读取与日志 | 依赖查找可执行文件 offset/path 的平台接口和 Statsd 写入；配置已推送不等于程序已成功附着或数据完整 |

**工程推导**：一次 recovery action、一次 profiling 请求和一批遥测日志各有独立完成条件。没有结果可能是限流、无权限、未附着或目标未产生事件，不能一律解释为“没有异常”。

## 覆盖限度

本页按机制分组纳入当前缓存与官方侧栏的 32 个模块专门页；Media 页含两个模块，Network Stack/AdServices 等又含多个包，因此不以页数或包数宣称全部实现已掌握。
未逐项深入所有模块的数据库 schema、完整权限声明、允许定制资源、SDK extension 组合矩阵和 HAL 协议；模块内部算法及目标设备实际分发能力仍须专门资料和活动产物证据。
