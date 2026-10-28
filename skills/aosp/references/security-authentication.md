# 认证、凭据保护与可信交易确认

用于锁屏凭据、生物识别、认证绑定密钥、Gatekeeper/Weaver 集成及 Protected Confirmation。
正文依据核实于 2026-10-28；先固定 Android 分支、设备首发版本、HAL 版本、安全环境与用户/profile。
当前官网已包含 Android 16 QPR2、Android 17 的行为，不能据此要求旧产品已有同样接口、限速策略或 UI。

## 认证结果怎样成为密钥授权

用户在 UI 输入成功、Framework 认为用户已解锁、安全环境接受一次认证、某把密钥允许使用，是不同状态。
典型凭据认证由 `LockSettingsService` 经 `gatekeeperd` 和 HAL 到达安全环境中的 Gatekeeper TA；生物识别有各自的服务、HAL 和 TA。
TA 产生 `HardwareAuthToken`，经 Android 的 keystore2 转交 KeyMint；Android 进程负责传递不等于可以自行制造可信认证结果。
KeyMint 根据 token 及密钥授权条件决定是否允许操作，而不是只信任一个 Java 布尔值。
[官方认证架构](https://source.android.com/docs/security/features/authentication)区分 Android 服务、HAL 和 TA；具体 daemon 名称及 Binder 接口应核对目标分支。

认证 token 带有 SID、认证类型、时间及适用的 challenge 等字段，并由共享 HMAC secret 认证。
该共享认证 secret 每次启动重新生成并在安全组件间安全建立，不能暴露给普通 Android 执行环境；旧启动周期 token 不能沿用为新启动的认证证据。
跨 TA 的共享密钥协商与 TA 内部 IPC 是实现选择，不能假设所有 TEE 都采用 Trusty 的内部调用方式。
每次操作认证与限时认证的差别见 [KeyMint 授权与证明](security-keystore-attestation.md)。

审查异步认证时，应分别追踪请求、用户、当前 challenge、取消和最终 token 的归属。
旧请求回调到达、新用户切换或新会话启动后，不能把一次历史成功套用到当前请求；这是对上述绑定关系的工程推导。

## Gatekeeper：SID、重新注册与失败限速

Gatekeeper 的注册结果是安全认证的 password handle；校验需要硬件保护的长期秘密，成功后发出使用每启动共享 secret 认证的 HAT。
这两类秘密的寿命不同：用于注册/验证凭据的秘密需稳定且能在重启后重新取得，认证 token 的共享 secret 则每启动变化。
[Gatekeeper 官方说明](https://source.android.com/docs/security/features/authentication/gatekeeper)同时规定 handle、HAL、可信时钟及限速职责；旧分支 HAL 形态可能不同。

SID 是安全环境的用户标识，不是 Android userId，也不是应用 UID。
验证旧凭据后换密属于 trusted re-enroll，可把原 SID 迁移到新 handle；不提供有效旧凭据的 untrusted re-enroll 产生新 SID，旧 SID 绑定的密钥不能因此获得新凭据授权。
当前使用 synthetic password 的完整系统还需同时检查该秘密与相应 Gatekeeper enrollment，不能只修改锁屏 UI 状态或一份数据库字段。

Gatekeeper 必须在可信侧拒绝尚在 timeout 中的请求，并对提供旧凭据的 enroll 同样实施限速。
失败计数须在验证前可靠写入，成功后清除，避免攻击者利用掉电或阻断存储写入规避计数。
安全存储、单调且休眠时继续计时的可信时钟、重启后的失败状态共同构成抗暴力猜测边界；Android 屏幕倒计时只是反馈。
诊断应区分密码不匹配、仍在 timeout、HAL/TA 通信失败与存储故障，不能把它们统一处理成“再重试一次”。

## Weaver：由低熵凭据释放高熵秘密

Weaver 自 Android 8.1 引入，提供固定数量、固定 key/value 大小的持久槽位。
`read(slot, key)` 仅在匹配且未处于可信限速 timeout 时返回 value；`write` 原子替换该槽位并使旧值永久不可恢复。
它适合 SE，也可在 TEE 实现；不能把有 Weaver 等同于有独立 StrongBox 硬件。
[Weaver 文档](https://source.android.com/docs/security/features/authentication/weaver)明确：Android 13 及以下使用 HIDL，当前接口使用 AIDL；`warmUp()` 及通用 `system/weaver` 参考实现属于 Android 17 及以上条件。

当设备提供 Weaver 时，`LockSettingsService` 为用户管理槽位：由 LSKF（PIN/图案/密码）派生槽位 key，value 是随机高熵 secret。
两者共同保护 synthetic password；后者再参与保护 FBE 的 CE 数据与认证绑定 Keystore 密钥。
仅得到磁盘上的加密数据或尝试任意 PIN，不能绕过可信环境释放 secret 的条件。
Weaver 接管 LSKF 验证和限速职责，Gatekeeper 仍用于产生 HAT；不能删掉 Gatekeeper 就宣称完成等价替代。

换密应检查新槽位写入、synthetic password 保护记录切换与旧槽位擦除的顺序。
官网描述的 Weaver 路径先写新槽位、确认安全后删除旧槽位，以支持原子变更；错误清理顺序会导致数据不可恢复，或留下本应销毁的旧凭据路径。
槽位分配、用户删除、恢复和掉电都需由同一状态所有者协调，不能只测试单次 `read` 成功。
VTS 执行有时间上限，不能验证一天或更长的所有限速 tier；这部分还需检查 TA 实现与相应单元验证。

## 限速策略也有版本和执行层

安全要求取自目标版本的 CDD 9.11；具体错误次数和 timeout 不能抄成所有版本的常量。
当前[限速文档](https://source.android.com/docs/security/features/authentication/rate-limiting)将更强默认策略与 Android 16 QPR2 及以上绑定，并描述 Android 17 的锁屏反馈变化。
其可选 `SoftwareRateLimiter` 是 system_server 中的次级限制器，在 enforcing 配置下与主 TEE/SE 限制器并行求较长 timeout；它不能取代抵抗 Android 被攻陷的主限制器。

重复错误猜测去重也有能力条件：当前软件路径要求 Weaver 与相应 enforcing 配置；Gatekeeper 不区分所有失败种类，不能照搬同样去重判断。
UI 应使用目标分支提供的共享锁定状态；在多个凭据提示界面分别缓存 timeout，可能产生一个界面仍允许输入的假象。
诊断报告应保留主限制器种类、可信侧返回的剩余时间、软件配置和触发次数，而不是只截图 UI 文案。

## 生物识别的安全级别决定可用能力

Class 3/Strong、Class 2/Weak、Class 1/Convenience 是安全分类，不是指纹/人脸的同义词。
当前[Biometrics 文档](https://source.android.com/docs/security/features/biometric)列出的能力如下；实际产品仍须满足对应版本 CDD 与测试要求。

| 认证方式 | 锁屏集成 | BiometricPrompt | Keystore 限时/逐次操作密钥 |
|---|---|---|---|
| Class 3 | 可 | 可 | 可 |
| Class 2 | 可 | 可 | 不可据此授权 |
| Class 1 | 可 | 不可 | 不可据此授权 |
| Device credential | 可 | 可，按 API/版本支持 | 可，按目标 API 契约 |

BiometricPrompt 自 Android 9 引入；人脸集成、允许认证器组合、逐次操作支持及设备相关字符串在后续版本继续演进。
应核对调用的 API/重载、allowed authenticators、实际注册方式和密钥参数，不能由一张统一提示框推出所用认证满足 Class 3。
生物模板、采集与匹配的可信边界、设备/用户绑定及删除用户后的清理是 HAL 集成契约；日志和调试转储不得成为模板导出渠道。
旧文档的 `setActiveUser()` HIDL 路径只是相应版本示例，当前 AIDL 设备应沿实际用户会话实现追踪清理。
解锁准确率与抗假体攻击能力的验证口径见[生物解锁安全测量](https://source.android.com/docs/security/features/biometric/measure)，不能用“识别很快”替代安全分类证明。

## Protected Confirmation 绑定交易内容

Protected Confirmation 自受支持的 Android 9 设备起提供，由 Trusted UI 和 KeyMint 的 `TRUSTED_CONFIRMATION_REQUIRED` 授权协作。
确认 token 证明可信界面所显示消息获得用户确认；它解决特定交易的意图证明，与认证“是谁/是否在场”不同。
[机制说明](https://source.android.com/docs/security/features/protected-confirmation)要求确认能力实际可用，不能以普通 Android 对话框或一次指纹成功替代。

威胁模型包含 Android/Linux kernel 已被攻陷：显示内容、物理输入与输入输出原子性仍须受保护，触摸控制器或显示固件也在设备论证范围内。
系统可以阻断界面可用性，但这种情况下不得发出确认 token。
来电/电源等导致会话中断应以 aborted/canceled 结束；正文未完整显示、超过格式限制或不可信屏幕共享输入都不能当作成功。
当前[实现要求](https://source.android.com/docs/security/features/protected-confirmation/implementation)还规定可信侧至少一秒输入宽限、活动界面不得被通知覆盖等约束；大小与 UI 常量应核对目标接口，不能只在 Android 客户端校验。
定制布局与辅助功能时继续保持[设计要求](https://source.android.com/docs/security/features/protected-confirmation/design)和[无障碍要求](https://source.android.com/docs/security/features/protected-confirmation/accessibility)；扩大字体导致信息裁切必须失败而不是隐藏关键文字。

## 用失败行为验证边界

| 变化/故障 | 应保持的不变式 | 观察证据 |
|---|---|---|
| 换密或重置凭据 | 可信换密保持合法访问，非可信替换不接管旧 SID 绑定 | enrollment、SID 关联、旧/新密钥行为 |
| 重启后复用 token | 旧启动 token 不获得新启动授权 | token 使用结果、共享 secret 建立路径 |
| Weaver 槽位更新中断 | 不提前删除唯一可恢复记录，完成后旧秘密不可恢复 | 状态切换/清理顺序、掉电恢复路径 |
| 错误凭据与 timeout | 可信侧执行限速，UI/软件错误不增加猜测机会 | HAL 返回、计数持久化、可信时间 |
| 弱生物识别成功 | 不取得超出强度允许的密钥能力 | authenticator 分类、密钥授权和真实失败 |
| 交易确认取消/显示失败 | 不产出可用确认 token | HAL 状态、回调、KeyMint 操作结果 |

上述是根据官方机制提出的工程检查，不表示本机已运行测试；设备和闭源 TA 的行为必须由相应证据确认。
