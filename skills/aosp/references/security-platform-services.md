# Safety Center、Private Space 与蜂窝安全状态

用于理解系统安全状态汇聚、私密 profile 和移动网络防护的职责边界。核实日期：2026-10-28。
三者的界面都出现在系统设置附近，但状态分别来自安全数据源、用户/profile 服务和 Telephony/基带；不能把界面开关统一视为一个权限布尔值。

## Safety Center 汇聚状态，源组件仍拥有事实

[Safety Center](https://source.android.com/docs/security/safety-center/overview)自 Android 13 引入，由多个系统应用来源提供入口状态、风险 issue、解决 action、取数错误与事件原因；第三方应用不能充当安全来源。
官网列出的 Google 账户、Play Protect 等是来源示例，不表示纯 AOSP 产品必然具有相同服务。
汇聚层能展示和协调行动，但屏幕锁、生物识别、补丁或账户状态仍由各来源维护。

官方 [SafetyCenterManager 源码](https://android.googlesource.com/platform/packages/modules/Permission/+/db906a39b759578ecabe5ed9be819b88b9b6829f/framework-s/java/android/safetycenter/SafetyCenterManager.java)给出更具体的状态模型：数据按 source ID 与调用用户区分，`setSafetySourceData` 替换该来源的旧数据；设置 `null` 清除动态数据并回到配置的占位内容。
刷新广播携带本次请求标识，来源响应通过 `SafetyEvent` 带回同一标识；无法提供数据或完成预期 action 时有错误报告接口。
以上以所链接 revision 为证据，新版聚合策略、去重与超时配置应查目标 Permission 模块。

[服务端实现](https://android.googlesource.com/platform/packages/modules/Permission/+/774cf953ac2fac2b1f18226b5682121a76a97299/service/java/com/android/safetycenter/SafetyCenterService.java)检查更新权限、调用 UID 与包名的对应关系、跨用户条件及 API 是否启用，然后把更新送入相应用户组的仓库和监听者。
因此 source ID 字符串、系统应用身份、跨用户能力和该数据属于谁是不同约束，不能只验证其中一个。

**工程推导**：取数失败、尚无数据、明确检测到安全和已解决 issue 必须有不同含义。
来源进程没响应不能推断“没有风险”；点击 action 也不能直接推断底层状态已改变。需要让完成结果与来源重新提供的事实保持一致。
刷新期间迟到回调必须关联对应来源、用户和请求；错误用户的安全状态会造成数据泄露，也会使“全部正常”结论失真。
一张绿色汇总卡至多说明当前配置中已报告的状态，不能证明未接入的硬件、服务或漏洞均已检查。

## Private Space 是独立 profile 的生命周期

[Private Space 官方机制](https://source.android.com/docs/security/features/private-space)建立 `android.os.usertype.profile.PRIVATE`。
其中安装的应用是独立副本，初始不会复制主空间应用数据；账户和用户内容也分离。它可与 work/clone profile 共存，但每台设备只允许一个 private profile，且属于 main user。
这里的 main user 不应在所有设备形态中硬编码为 user 0。

| 状态 | 系统行为 | 可见性含义 |
|---|---|---|
| 解锁 | 启动 private profile user | 应用可在对应 Settings、Sharesheet、Photo Picker、DocsUI 中出现 |
| 锁定 | 停止 private profile user | 隐藏应用、最近任务、通知和相应设置内容 |
| 隐藏 | 进一步隐藏 launcher 的空间入口 | 不能单靠 launcher 的可见性判断 profile 授权状态 |

Launcher 访问 private profile 需要 `ACCESS_HIDDEN_PROFILES` 与 `ROLE_HOME`；可以通过 `LauncherApps#getLauncherUserInfo` 识别 profile，并结合状态广播的 `EXTRA_USER` 和 `UserManager.isQuietModeEnabled()` 关联正确用户。
这些是系统侧接入条件；它们不把主空间应用变成可任意读取 private profile 数据的应用。
解锁状态下可经系统 Sharesheet 或 Photo Picker 取得受控的跨空间内容访问，不等于两个用户目录合并。

**工程推导**：只把图标移入隐藏文件夹没有实现该边界；profile 锁定后，搜索、通知、最近任务及设置缓存仍显示应用名称，也会泄露其存在。
解锁/锁定是用户生命周期事件，应以目标 profile 的当前状态处理异步包列表和内容结果，不能把主用户解锁广播当作私密空间也已解锁。
Telephony intent 按官方机制路由给主用户并显示通知，其余 intent 限于 private profile，不自动重定向到主空间。

Android 16 QPR2 及以上增加从外部向 private space 复制/移动文件：用户经系统文件选择器选取，服务仅在 private profile 内以前台服务运行，目标为该空间 Downloads；移动在成功传输后删除原件。
据此，跨 profile 的源 URI 授权、目标用户、完成状态与原件删除应属于同一次操作；“用户点了移动”不能作为尚未成功写入时删除原件的依据。
此新增能力不能倒推旧版本已有相同服务和入口。

## 蜂窝保护作用于设备到基站的链路

[蜂窝安全概览](https://source.android.com/docs/security/features/cellular-security/overview)限定了保护范围：空口加密保护设备与基站间传输，语音和 SMS 不因此获得端到端加密；归属运营商仍可接触明文。
身份标识暴露、降级到 2G 与链路算法状态也是不同信号，不能以“4G 图标”概括全部安全属性。

[禁用 2G](https://source.android.com/docs/security/features/cellular-security/disable-2g)在实现 `CAPABILITY_USES_ALLOWED_NETWORK_TYPES_BITMASK` 的设备上，从无线硬件层阻止普通用途的 2G 扫描和连接；紧急呼叫例外仍可使用 2G。
自 Android 14 起，使用 `ALLOWED_NETWORK_TYPES_REASON_ENABLE_2G` 改变该限制需要 `MODIFY_PRIVILEGED_PHONE_STATE`，carrier privileges 不足以代替。
为安全禁用后不会因为漫游自动重启 2G；2G 缺少双向认证，假基站可伪造网络身份，因此“检测到漫游就自动允许”会破坏防护条件。

Android 16 的[开关变化](https://source.android.com/docs/security/features/cellular-security/toggle-2g)把“Allow 2G”改成“2G network protection”，UI 极性随之反转，但默认的实际 2G 连接状态没有改变，用户既有选择也要保持。
因此保存或迁移状态时应明确语义是“允许 2G”还是“启用保护”，不能只保留同一个 on/off 值。
安全中心新增每张物理 SIM/eSIM 的入口，与 SIM 设置指向同一状态；UI 实例并非两份独立策略。

## 蜂窝通知依赖基带提供可观察事件

Android 16 的 [Mobile network security](https://source.android.com/docs/security/features/cellular-security/mobile-network-security)包含通知和每 SIM 的 2G 控制；设备需同时支持通知与 2G toggle 才显示整个 section。
通知开关默认关闭；显示还要求 modem 支持 IRadio 3.0 及 `securityAlgorithmsUpdated`、`cellularIdentifierDisclosed` 等相应启用/回报接口。
通知说明无加密链路、恢复加密或 IMSI/IMEI 等标识交换，可由通知跳到 Safety Center 查看细节。

**工程推导**：无通知可能是用户关闭、能力不支持或事件未上报，不能直接证明没有标识交换。
正常网络操作也会有限地交换身份标识，单次提示不能独立证明存在假基站；频繁事件需要结合订阅、网络和时间序列解释。
多 SIM 场景要关联实际 subscription 与 modem 事件，避免卡槽变化后把上一订阅的告警或 2G 选择套到另一张卡。

## 状态证据应能跨层对应

| 问题 | 需要对齐的事实 |
|---|---|
| Safety Center 一直显示旧 issue | 来源、user、刷新 ID、动态数据/占位数据及 action 完成结果 |
| Private Space 锁后仍泄露名称 | profile 启停/quiet 状态、收到的目标 user、各界面的缓存和未完成回调 |
| 开关迁移后 2G 行为相反 | 版本、旧新 UI 极性、reason 对应的实际网络类型限制与订阅 |
| 支持 Android 16 却看不到蜂窝安全项 | IRadio/通知接口、2G 能力、产品启用条件及通知偏好 |

本页未穷举 Safety Center XML、issue 去重/排序算法、Private Space 全部跨 profile 策略以及 modem 内部实现和运营商矩阵；这些仍需目标分支与设备能力证据。
