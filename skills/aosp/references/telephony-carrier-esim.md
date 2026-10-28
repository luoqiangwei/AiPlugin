# 电话、运营商与 eSIM：订阅身份、服务选择及异步事务

用于 Radio/RIL、IMS、紧急呼叫、运营商配置、5G、eSIM/MEP 和通话系统集成。核实日期：2026-10-28。先固定 release/tag、首次出厂版本、Radio/RadioConfig HAL、modem 固件、运营商与订阅、LPA/IMS 实现版本；Android 支持接口不表示设备、网络和账户已开通服务。IP 网络选择见 [网络栈](network-stack-services.md)，Carrier Wi-Fi 见 [Wi-Fi](wifi-connectivity.md)。

## 身份与状态的坐标系

| 标识/状态 | 所标识的对象 | 不应据此推断 |
|---|---|---|
| physical slot、UiccSlot/UiccCard | SIM 插槽/卡容器 | 等于逻辑 modem 或只有一个启用 profile |
| portIndex、UiccPort | 卡上的逻辑端口 | 一定已启用 profile、一定是 port 0 |
| phone/logical slot | modem 栈与逻辑映射 | 永远映射同一个物理插槽 |
| subscription ID | 平台订阅记录 | 等于 ICCID、IMEI、数组索引或默认数据订阅 |
| EID/card ID | eUICC 硬件标识/设备内卡标识 | 是某个 profile，或卡当前可达 |
| ICCID/IMSI、carrier ID、PLMN | profile/用户身份、运营商品牌归类、网络标识 | 三者可互换，或广播 PLMN 就是实际注册 PLMN |
| SIM loaded、service registered、data connected、IMS ready/registered/provisioned | 不同参与方的运行状态 | 任一成立足以证明一次实际通话/数据业务成功 |

这些映射在热插拔、profile 切换、MEP 端口映射、modem reset 和默认订阅变更时可改变。由此可推导：异步结果至少携带请求 serial/事务、phone/subId/card/port 的适用范围和状态代次；旧订阅结果不能覆盖新订阅。UI 必须说明是在展示设备能力、订阅能力、可用性还是当前调用结果。

## Radio/RIL、Telephony 与 Telecom

Telecom 组织 `PhoneAccount`、Connection/Call、并发通话和 Dialer 交互；Telephony 管理订阅、无线注册与数据/IMS 连接；Radio HAL/vendor RIL/modem 执行无线操作。常见入口包括 `packages/services/Telecomm`、`packages/services/Telephony`、`frameworks/opt/telephony`、`hardware/interfaces/radio`，需按分支核对。

[RIL refactoring](https://source.android.com/docs/core/connect/ril) 是 Android 7 的历史改进：细分错误代替 `GENERIC_FAILURE`，版本上报对应真实实现，按响应耗时区分请求并用 ACK 协调 wakelock。其 socket/legacy 函数示例不是现代 Stable AIDL Radio 的实现模板。现代请求/response/indication/ACK 的具体接口版本必须读目标 HAL；超时不自动证明 modem 已取消操作，晚到响应和服务重启需单独处理。

故障时间线至少连起：上层请求及调用身份 → serial → HAL 接受/ACK → modem 状态/indication → response/error → framework 状态和用户结果。无限延长 wakelock 会掩盖响应丢失并耗电，过早释放又可能使响应处理不完整；同步/异步划分要依据实际平台功耗与响应特征，不能从命令名字臆定统一时间阈值。

## 运营商配置、识别与权限分别有来源

[CarrierConfig](https://source.android.com/docs/core/connect/carrier) 按 key 取第一份有效值：carrier app → 随系统的 platform config app → framework 默认。加载发生在 SIM 加载、app 更新或显式通知变化等时点，bundle 有缓存；服务器账户状态变化若未触发 `notifyConfigChangedForSubId`，不能期望每次读配置自动访问后端。配置归属指定订阅，避免使用无绑定的默认实例操作另一张卡。

[Carrier identification](https://source.android.com/docs/core/connect/carrierid) 用带版本的 carrier 数据库和 SIM 属性识别运营商；MVNO 可有独立 carrier ID，Android 10 起 CarrierConfig 可以 carrier ID 索引，缺少 MVNO 配置时可查所属 MNO。`MCC/MNC` 不是完整品牌身份，更新 carrier list 与更新 CarrierConfig 是两条变化链，需分别确认装载版本和匹配结果。

[APN/CarrierConfig](https://source.android.com/docs/core/connect/update) 中 APN 定义可服务的数据用途（如 default、MMS、IMS），CarrierConfig 定义框架行为；样例 `device/sample` 的 APN 文件变更不会自动改变出货设备。数据、MMS、tethering、IMS 的实际 APN/连接需分别观察，不能从一条 default 数据连接成功推论全部用途正确。本文不包含外部提交流程。

[UICC carrier privileges](https://source.android.com/docs/core/connect/uicc) 按卡上的证书 hash、可选包名匹配签名；无包名规则可能授权同签名的多个包。规则可来自 ARA，Android 7 起还有 ARF fallback，平台加载并缓存，移卡后销毁相应规则。权限不是“安装了运营商 app 就永久获得”，也不等于平台签名、任意电话权限或任意卡的控制权；具体 API 仍查其订阅作用域与权限契约。SIM loaded 前规则可能未就绪，应区分 loading、无规则和明确不授权。

[Device identifiers](https://source.android.com/docs/core/connect/device-identifiers) 描述 Android 10 起对 IMEI/MEID、IMSI、SIM serial、build serial 的受限访问；runtime `READ_PHONE_STATE` 不能普遍替代 privileged/carrier/owner 等适用授权，拒绝结果还受 target SDK 影响。日志尽量关联匿名化事务/订阅标识，避免为诊断公开完整永久身份。CarrierConfig 的证书 allowlist 与 UICC 规则有不同来源，不应把读取设备标识的授权扩成所有 carrier API 权限。

设备级 voice/SMS/data 能力与 Android 15 起的订阅级 service capabilities 分开：data-only subscription 不因为设备有麦克风就支持语音。API 重命名/弃用和 capability array 应按目标版本读取，不能让 UI 以设备能力替代订阅业务状态。

## IMS：可信服务、feature 与注册生命周期

[ImsService](https://source.android.com/docs/core/connect/ims) 是 Android 9 起的 System API 边界。Framework 按 slot/feature 选择配置的 carrier override 或 OEM default 实现，验证预装包和绑定权限，查询 feature 后创建 MMTEL/RCS 对象；它不是任意下载 app 可接管 modem 的入口。AP 侧、modem offload 的 IMS 实现方式可以不同，AOSP 未统一其全部私有 modem 协议。

区分 ImsService 进程可用、feature 创建、能力可用、IMS 注册、provisioning、用户开关和实际呼叫。SIM/carrier 配置变更可换绑服务，服务死亡也会使已有 manager/callback 不再有效。Android 13 的 `ImsStateCallback` 用来观察服务可用性；服务恢复后重建相关注册/能力/provisioning callback，telephony 进程崩溃后的 `onError` 则需重新注册状态 callback。仅有“已注册”日志不能证明所有 feature 有效。

[Single registration](https://source.android.com/docs/core/connect/ims-single-registration) 从 Android 12 让 MMTEL 与用户选定 RCS messaging app 使用同一 ImsService 注册，涉及 provisioning、SIP delegate、QoS、GBA 与能力交换。SIP delegate 的 feature tag 和权限/角色限制是授权边界，不能把“默认 SMS app”单独等同拥有全部 single-registration 权限。文档里的旧 IMS 概览对 RCS 的描述需与此后续机制一起读，不能用旧概览否定新 API。

[TS.43 entitlement](https://source.android.com/docs/core/connect/ims-service-entitlement) 是账户服务授权查询：客户端/静态库 → HTTPS entitlement server → SIM EAP-AKA challenge-response → 服务状态 → 可选运营商门户 → `ProvisioningManager`。entitled、provisioned、registered、user-enabled 各有独立所有者。默认 HTTP 走当前默认网络，故 Wi-Fi/DNS/门户也能影响 VoWiFi 开通；本地开关打开不能替代账户授权和紧急地址等步骤。测试 override 只改变本地条件，不是网络开通证据。

## 域选择、紧急号码与紧急呼叫

[DomainSelectionService](https://source.android.com/docs/core/connect/domain-selection) 从 Android 15 为外呼/SMS 提供 IMS 与 CS 域、紧急网络扫描偏好等决策。它是由配置组件名与绑定权限约束的可信系统服务；应关联 `setEmergencyMode`、scan/cancel、scan result、`exitEmergencyMode` 的请求生命周期。一般网络选择、IMS 注册和通话域选择互相提供输入，但不是一个状态机。

[紧急呼叫](https://source.android.com/docs/core/connect/emergency-call) 使用 SIM、network、modem、平台数据库和 default 等号码源；一个号码还包含 MCC/MNC、服务类别、URN、来源与 routing。Android 10/Radio 1.4 把 emergencyDial 与普通 dial 区分，现代分支要对应其 AIDL/HIDL 接口。识别为紧急号码不等于使用 emergency routing，routing 可由契约明确指定或交给实现判断。

[Emergency number database](https://source.android.com/docs/core/connect/emergency-number-db) 带数据库版本，Android 11 起支持下载更新；装载通知、实际使用版本及 `getEmergencyNumberList`/识别结果应相互吻合。它是多个号码来源之一，不能用一份数据库覆盖网络下发的全部语义。

[Emergency Affordance](https://source.android.com/docs/core/connect/emergency-affordance) 是根据 SIM/可见网络 MCC 等条件提供锁屏和 global actions 触发入口的参考实现；它不替代号码识别、域选择或无线接通。文档含旧版本属性和历史市场背景，本页只提炼机制，不以历史叙述判定当前地区法规。多 SIM、无 SIM、锁屏、无普通注册、用户受限等状态必须与普通拨号前置条件区分；真实呼叫验证使用模拟/隔离测试设施，避免把测试请求发向公共紧急服务。

## 5G、信号、小区与 NTN

| 分支 | 所有者和关键约束 |
|---|---|
| [5G NSA](https://source.android.com/docs/core/connect/5g-nsa) | LTE 基础上的 NR secondary cell 与“驻留在支持 5G 的网络”不同；CarrierConfig/SystemUI 将无线状态映射为图标，图标不能证明当前包确经 NR |
| [Signal strength](https://source.android.com/docs/core/connect/signal-strength) | modem reporting criteria 控制何时上报，测量类型/阈值转成显示 level；原始 RSRP/RSRQ/SINR、报告节流与信号格数分开，不能通过改图标阈值修复射频 |
| [Multi-operator networks](https://source.android.com/docs/core/connect/multi-operator-networks) | 小区可广播多个 PLMN，RPLMN 独立上报且须是其 primary/additional 列表之一；共享基站不等于同一服务提供者 |
| [Small cells](https://source.android.com/docs/core/connect/small-cell) | `ClosedSubscriberGroupInfo` 是可选小区身份信息；CSG membership、网络注册和业务授权分别确认，不以小区可见当接入成功 |
| [Satellite](https://source.android.com/docs/core/connect/satellite) | Android 15+ 文档描述 Telephony/SatelliteManager、modem HAL、窗口/队列与 Connectivity 流量策略协作；NTN 支持、当前可见性、entitlement、受限/非受限数据能力分别查询，不能把平台支持解释为所有设备和账户拥有全 IP 互联网 |

[5G slicing](https://source.android.com/docs/core/connect/5g-slicing) 从 Android 12 支持请求能力 → traffic descriptor → modem/URSP 匹配 → PDU session → 按 UID 路由。企业工作资料路由要有 DPC 策略和正确 profile 作用域。`matchAllRuleAllowed` 对默认网络与明确 slice 请求有不同语义；slice 不可用不能伪装成已成功建立目标 slice，是否回落默认网络由适用策略决定。

Android 14 QPR1 起的 premium upsell 把 TS.43 entitlement、购买 UI、provisioning 与 URSP 到达串起来；付费网页成功回调不是 slice 就绪，网络配置尚未到达时会处于 pending。Android 17/Radio AIDL 2.5 新增 connection-capability descriptor，并在当前文档描述 OTT Telecom 通话按 UID 自动路由；旧版本使用 OSAppId 的规则仍要兼容，合并成 AND 规则会使缺少新字段的旧设备无法匹配。核实时检查 OS/HAL、实际 descriptor、URSP 版本、PDU session 和 UID 路由；本文不复制每项 descriptor 编码或运营商参数表。

## eSIM：下载、安装、启用和网络激活是不同事务

[eSIM 架构](https://source.android.com/docs/core/connect/esim-overview) 是调用方 `EuiccManager` → framework → 选定 LPA 的 `EuiccService` → `EuiccCardManager`/APDU → eUICC；LPA 同时与 SM-DP+/可选 SM-DS 协作。AOSP 提供 framework，**不附带完整 LPA 产品实现**。EuiccManager 的高层 profile 操作与只有 LPA 可用的 ES10 卡通信 API 不能混用；LUI 可以和 backend 分 APK，framework 按权限/声明/优先级选择实现。

[eUICC API](https://source.android.com/docs/core/connect/esim-euicc-api) 的返回是异步结果：下载、切换、删除依赖 PendingIntent，公开结果与 LPA detailed code 分开。`isEnabled()` 表示 framework/feature/LPA 等前提，不能证明目标 eUICC 当前可达；`getEid()` 可因未就绪返回空。多卡用 `createForCardId` 固定目标，移除/断电后不能静默操作另一默认卡。回调 Intent、权限、package/component 和 target SDK 限制需按实际 API 使用，避免照抄旧文档 PendingIntent 示例。

权限同时考虑当前 profile 和目标 profile。调用 carrier app 通过目标 metadata 的证书/可选包名规则获得该 profile 权限；没有当前启用 profile 的控制权时，切换可要求用户授权。`RESOLVABLE_ERROR` 交给 `startResolutionActivity` 的系统流程处理，不能把确认码、停用另一张 SIM 或权限提示变成无限自动重试。profile policy rules 由 LPA/eUICC 参与处理，Android 的 carrier privilege 检查并不包办 GSMA 全部策略。

[错误处理](https://source.android.com/docs/core/connect/esim-error-handling) 自 Android 11 分解 operation、error 或 GSMA subject/reason：HTTP/TLS/SM-DP、APDU、slot/card、安装空间、版本不兼容、carrier lock、busy 各有不同恢复范围。error code 字段不是所有 operation 都存在，缺字段不能解释为成功。超时后先读取实际 profile/卡状态再判断重试，避免重复下载/启用；诊断保留事务与 detailed/operation/error 组合，不公开 activation code、密钥或完整 APDU 敏感数据。

[Modem requirements](https://source.android.com/docs/core/connect/esim-modem-requirements) 特别要求：仅 default boot profile 的 eUICC 仍视为有效卡并保持上电；terminal capabilities 正确宣告本地管理/下载；card/slot status 的 ATR/EID/映射、SIM power、锁定状态须一致。错误地把空 profile 卡当无卡断电，会令 LPA 无法进行后续下载。eSIM OS OTA 支持取决于 vendor，不应与 Android 系统 OTA 或 profile 下载混为一谈。[Test profiles](https://source.android.com/docs/core/connect/esim-test-profiles) 需要测试证书/相应 TS.48 profile，能下载测试 profile 也不能替代生产 SM-DP+/运营商激活验证。

## MEP：一张 eUICC 的多个端口

[Multiple enabled profiles](https://source.android.com/docs/core/connect/esim-mep) 从 Android 13 允许同一 eUICC 多个 port 各启用一个 profile；一张卡/EID 可对应多个 UiccPort、ICCID、logical slot。它与 Android 10 起的“设备有多张 eUICC”不是同一个能力。`UiccCardInfo.getIccId` 的单值模型不适合 MEP，应看 port 的 ICCID 和 `SubscriptionInfo.getPortIndex`。

`setSimSlotMapping` 表达 logical slot → physical slot+port。切换明确 `portIndex`，端口可用性还包含调用方是否有当前 profile 的权限；没有空闲 port 时用户可能需要选择停用哪个订阅。Android 14 起文档区分 MEP-A1（管理 ES10 在 port 0，profile 在其他 port）与 MEP-B（命令端口等于目标端口），不能硬编码“ES10 永远在 profile port”或“port 0 永远可启用”。OS、LPA、Radio HAL、eUICC 的 MEP 模式与 card/slot events 必须一致。

由此可推导：两个订阅已启用不证明两个都可注册/通话；DSDS、modem 栈数与射频并发能力另核。跨 port 移动 profile 后，carrier 后端若错误地固定 IMEI↔ICCID/EID 的一对一关系，可能出现 framework 映射正确但业务丢失，需把设备端口映射和网络激活证据同时保留。

## 跨设备 Transfer：授权令牌与目标激活

[eSIM Transfer](https://source.android.com/docs/core/connect/esim-transfer-carrier-integration) 描述源设备 Android 10+、目标 Android 14+ 的相应客户端/运营商方案，并非任意两台 AOSP 都内置完整实现。源设备通过 TS.43 EAP-AKA、eligibility 和临时 token 授权，目标用 token 请求转移/配置并取得 activation code，再由 LPA/SM-DP+ 下载。D2D 配对、源屏幕锁验证、加密防重放通道与 token 寿命共同构成授权条件；近距离/扫描二维码本身不足以授权移动订阅。

转移意图、目标 profile 下载、目标激活与源 profile 停用应分别记录。官方建议把 transfer 与 activate 分离，使目标下载失败时源设备仍有服务；不支持这种后端语义时必须识别其返回状态。延迟下载是有状态 polling，不能按“几秒无结果”判死失败。token 需要受保护存储、完成后清理，重试/进程重启不能复活过期授权；设备数据备份也不等于复制可用 SIM 凭据。

## Calling and messaging 分支的机制归属

| 分支 | 状态与对外契约 |
|---|---|
| [Phone account suggestion](https://source.android.com/docs/core/connect/phone-account-suggestion) | Telecom 在无默认/联系人偏好账户时进入选择状态，可信唯一建议服务异步按原号码返回账户/reason/auto-select；建议结果不是最终拨号成功，旧号码结果不能用于新呼叫 |
| [Third-party calls](https://source.android.com/docs/core/connect/third-party-call-apps) | self-managed ConnectionService/Core-Telecom 与 carrier call 共存，hold 能力影响是否必须结束另一呼叫；Dialer 要显示实际影响与来源。Android 17 当前文档新增按 app 控制 VoIP 通话日志集成和可解析的设置 intent，适用设备能力/role 条件须核对 |
| [Call notifications](https://source.android.com/docs/core/connect/call-notification) | Android 7 的责任迁移把通话通知组织交给 Dialer，Android 12+ 推荐 CallStyle；铃声、前台 UI、未接/VVM 和底层 call state 仍需同一呼叫关联，不能用通知是否出现证明呼叫是否已建立 |
| [RTT](https://source.android.com/docs/core/connect/rtt) | Telecom `RttCall`/`RttTextStream`、Dialer UI 与 IMS text/modify request/response 三侧协作；请求升级、对端接受、文本流和语音路由分别完成，framework 测试不能替代 modem/IMS 互通 |
| [Number blocking](https://source.android.com/docs/core/connect/block-numbers) | `BlockedNumberProvider` 保存系统级严格匹配列表，默认 dialer/SMS/carrier 等按权限读写；用户作用域、默认角色、号码规范化与紧急呼叫后临时放行语义需一致，不能各 app 私有名单互相冲突 |

## 证据和未展开范围

问题记录应串联 `dumpsys telephony.registry`/phone、Telecom/IMS 状态、CarrierConfig、Radio log、modem/SIM/APDU（脱敏）、LPA result 与网络侧时间；具体可用命令/可见性按 build 与版本核对。区分 first failure、reset/rebind 后的连锁错误、权限拒绝和业务网络拒绝。CTS/VTS 证明相应 API/HAL 契约，IMS/eSIM 端到端需具备对应网络和 profile 条件。

本页承接 Calling and messaging、Carrier（配置/ID/UICC/设备标识/APN、IMS/domain、5G/信号/多 PLMN/CSG、Satellite）、eSIM 各分支及通用 Radio/RIL；data plans/out-of-balance 在 [网络栈](network-stack-services.md) 与 [计量](network-data-accounting.md) 归属。未逐项展开 SIP/IMS 协议、各 Radio indication、GSMA ASN.1/APDU、TS.43 全参数与服务器时序、卫星调度/天线及所有 URSP 字节编码；上述公共文档不足以补全闭源 modem/LPA 或运营商后端。目标场景必须继续核对对应规范和实现，不将本页机制覆盖标成这些细节已验证。
