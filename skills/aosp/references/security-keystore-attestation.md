# Keystore 访问域、KeyMint 授权与远程证明

用于系统密钥共享、认证绑定操作、KeyMint HAL、attestation、RKP 及升级后密钥不可用。
资料核实于 2026-10-28；记录 Android/KeyMint 或历史 Keymaster 版本、安全级别、启动状态、用户状态与活动 RKP 模块。
KeyMint 自 Android 12 替代 Keymaster HAL，keystore2 同期引入；旧接口、旧 tag 和新 AIDL 对象不能按名字直接等同。

## 先区分调用入口、存储服务与安全实现

`AndroidKeyStore` 是调用进程中的 Framework/JCA 接口；keystore2 保存及管理 keyblob 并执行访问控制；KeyMint HAL 服务转发到安全环境中执行密钥操作的 TA。
硬件保护 keyblob 可存于 Android 文件系统，关键是密钥材料及授权绑定不能由该环境读出或篡改后继续使用。
普通 Binder 服务进程、内核、TEE/StrongBox 分别处于不同边界，不能由“用了 HAL”推断所有秘密操作都在安全环境中。
[Hardware-backed Keystore](https://source.android.com/docs/security/features/keystore)解释这些职责及版本演进；实际支持的安全级别与算法仍由目标实现决定。

## Key descriptor 标识密钥，但不代替授权

| Keystore domain | 标识和用途 | 应保持的边界 |
|---|---|---|
| `APP` | 应用 alias 与调用 UID 的组合 | 同名 alias 不跨应用成为同一授权 |
| `KEY_ID` | 已加载密钥的数值标识 | 猜到 ID 也不能跳过所有者检查 |
| `GRANT` | 向指定 UID 授予使用权后返回的 grant ID | 其他 UID 得知 grant ID 不自动成为被授权者 |
| `SELINUX` | 系统组件的数值 namespace 映射到 SELinux 类型 | 按 `keystore2_key_contexts` 与 `keystore2_key` 策略授予操作 |
| `BLOB` | 调用者管理 blob 的内部用途，例如挂载 data 前的组件 | 不由 app alias 的语义推导其存储/访问条件 |

上述映射依据[Keystore access control](https://source.android.com/docs/security/features/keystore)；文件名、namespace 配置及权限集合应核对目标分支。
一个系统组件代另一 UID 操作时，应检查 descriptor 的 domain、namespace、grant 目标和调用身份是否一起保持；只检验字符串 alias 不能证明所有权。
授权生命周期还包括撤销、用户删除和服务死亡后的引用，不应把可缓存 key ID 当作永久使用权。

## Authorization list 随 keyblob 绑定

创建或导入密钥时指定 purpose、算法、mode、padding、认证条件等授权；KeyMint/Keystore 补充 origin 等最终属性，并把最终授权与 keyblob 绑定。
篡改授权后继续使用必须失败，不能通过编辑数据库把仅签名密钥变成通用解密密钥。
合法 API 参数组合也可能产生不安全或无用的密钥；上层仍负责 nonce/IV、purpose 组合和协议设计。
[Features](https://source.android.com/docs/security/features/keystore/features)说明授权列表，[KeyMint functions](https://source.android.com/docs/security/features/keystore/implementer-ref)说明 HAL 不替调用者诊断所有协议误用。

安全环境能实际执行的条件与 Keystore 在 Android 中执行的条件需分开看。
返回的 key characteristics 按 enforcement security level 分类；attestation 中对应 hardwareEnforced/softwareEnforced。
例如依赖不可信墙上时钟的有效期通常由 Android 侧执行，不能因密钥材料位于 TEE 就说全部授权都抵抗 Android 被攻陷。
具体 tag 可否重复、单位及适用算法以目标 [KeyMint tag 定义](https://source.android.com/docs/security/features/keystore/tags)和 AIDL 为准，不从整数名推断含义。

`UNLOCKED_DEVICE_REQUIRED` 与 HAT 认证超时是不同条件。
该条件由 Keystore 执行；Android 12 及以上增加 superencryption，在可能情况下使锁定时即使 Keystore 被攻陷也无法使用相应密钥。
当前实现对仅凭据、Class 3 生物识别及弱生物识别/trust agent 的 super key 保存方式不同，后一类存在无法提供同等密码学保护的回退。
因此“屏幕已锁”不独立证明某密钥的所有明文保护材料已清除；应核对该用户的解锁方式、实际分支及[具体保护机制](https://source.android.com/docs/security/features/keystore/features)。

## 认证条件与操作对象的状态机

`USER_SECURE_ID` 绑定可信用户 SID；`USER_AUTH_TYPE` 限定可接受认证方式；`AUTH_TIMEOUT` 给出认证新鲜度。
限时认证不能跨启动周期继续有效；AIDL 的 `NO_AUTH_REQUIRED` 只去掉用户认证条件，不去掉 Keystore 所有权检查，且与 `USER_SECURE_ID` 互斥。
tag 符号与细节以目标 [Tag.aidl](https://android.googlesource.com/platform/hardware/interfaces/+/refs/heads/main/security/keymint/aidl/android/hardware/security/keymint/Tag.aidl)为准；概览中的自然语言写法不能直接作为代码常量复制。
不带 timeout 的认证绑定密钥需要逐次操作授权，不能拿任意一次历史解锁结果满足当前操作。
HAT 的产生和 SID 生命周期见[认证链](security-authentication.md)。

现代 KeyMint `begin` 返回 `IKeyMintOperation` 及该操作的 challenge，后续通过操作对象处理输入并 `finish` 或 `abort`。
大部分授权在 begin 检查；逐次操作认证还需在 update/finish 提交 HAT，验证 HMAC、SID、认证类型与当前 challenge。
对象方法返回非 OK 错误时，操作被终止、句柄失效；重试同一无效对象不能恢复它。
资源并非无限，客户端必须终结不再需要的操作；实际并发上限和 Keystore 淘汰策略应查目标 [HAL 实现约定](https://source.android.com/docs/security/features/keystore/implementer-ref)，不要把资源不足改成无界排队。

对流式加解密，还应在协议层明确终结失败时先前输出是否可发布；收到部分字节不等于整个消息已验证。
这是操作生命周期对上层协议的工程约束，不能仅由 Binder 调用成功证明消息完整性。

## 删除防恢复、启动信任与版本绑定是三种关系

`ROLLBACK_RESISTANCE` 指受保护删除：deleteKey/deleteAllKeys 后，攻击者恢复先前备份的 keyblob 也不能重新使用。
它通常需要防重放可信元数据；安全存储耗尽可以导致创建受保护密钥失败，不能默默降级而仍声称有此属性。
[KeyMint implementer reference](https://source.android.com/docs/security/features/keystore/implementer-ref)区分这个属性与普通删除 Android 文件。

启动 root of trust 绑定包含启动验证 key 和 lock state；系统/补丁版本绑定则约束密钥随可信版本前进。
二者分别回答“属于哪个受信启动环境”和“是否允许在该版本使用”；它们也不能代替 AVB 分区 rollback index。
升级可能要求 keyblob 升级；密钥随版本 ratchet 后，回退系统可能无法使用。
诊断应核对可信侧取得的 system/vendor/boot 版本和真实补丁，而不是伪报 patch level。
[版本绑定说明](https://source.android.com/docs/security/features/keystore/version-binding)含 Treble 分区信息的适用差异，不能只比较 Framework 报告的一项版本。

## Attestation 证明哪些属性

Key attestation 自 Android 7.0 引入，ID attestation 自 Android 8.0 引入；当前 schema 已包含多个后续版本，解析器应按 attestation/KeyMint 版本读取。
HAL 正常返回链的首项是所证明公钥的证书，证明签名 key 可以使用另一算法；产生证书不等于已经执行一次该业务密钥的受认证签名。
[Key and ID attestation](https://source.android.com/docs/security/features/keystore/attestation)同时描述历史 attestKey 入口与版本化扩展，不能把旧 HAL 方法直接用于现代分支。

远程验证方需要把证书路径、信任根、challenge 与业务会话绑定起来，而不是接受客户端返回的“hardware backed=true”。
应确认 challenge 是本次请求的值且没有重放、所证明公钥是准备使用的公钥，证书链在验证方认可的信任体系内，并依据其生命周期检查有效性和撤销状态。
验证根与撤销资料必须按当前[Android key attestation 验证说明](https://developer.android.com/privacy-and-security/security-key-attestation)复核，不能将某份静态证书长期硬编码为唯一可信根。
不应假定不可信客户端提交链的最末叶一定承载可信扩展：应从可信根方向定位首次 attestation 扩展，并按官方规则检查其与 provisioning information 扩展的相邻关系。
攻击者可以在合法链后追加自己签发的证书和伪造扩展；验过完整路径却读取攻击者追加叶的扩展，仍会得出错误硬件证明。

| 扩展字段 | 能帮助判断什么 | 不能单独证明什么 |
|---|---|---|
| attestationSecurityLevel / keyMintSecurityLevel | 证明签名与业务密钥实现的安全级别 | 所有授权都由相同硬件执行 |
| hardwareEnforced / softwareEnforced | 各约束由哪一侧执行 | 软件约束也抵抗 Android 全面失陷 |
| RootOfTrust | 启动 key、locked 状态、VerifiedBootState、适用版本的 boot hash | 系统不存在漏洞或当前所有操作合法 |
| OS/vendor/boot patch 信息 | 证明记录所绑定的版本状态 | 厂商确实正确修复每一个漏洞 |
| attestationApplicationId | 生成请求关联的包/版本/签名摘要集合 | 任意远端账户身份或一次交易同意 |

上表字段依据[证明扩展](https://source.android.com/docs/security/features/keystore/attestation)；它记录的状态有时间语义，旧证书不能当作设备此刻所有运行状态的连续监控。
Verified、SelfSigned、Unverified、Failed 不能仅按“签名能验过”合并；`deviceLocked` 也要与验证 key 和状态共同解释。
ID attestation 涉及硬件标识符的受限调用、生产写入值及隐私边界，不是向任意 app 开放读取序列号/IMEI 的替代接口。

## RKP 供应的是证明所需密钥和证书

RKP 自 Android 12 存在，Android 14 起把远程配置功能整合为 `com.android.rkpd` Mainline APEX。
模块包含 RKPD app 与 system_server 部分，仍依赖 `IRemotelyProvisionedComponent` 实现；旧版 RemoteProvisioner/Keystore 分工与新版模块不同。
[RKP 模块文档](https://source.android.com/docs/core/architecture/modular-system/remote-key-provisioning)给出这些版本和包边界，必须同时记录系统版本与活动 APEX 版本。

供应流程由安全组件生成 key pair，普通系统侧管理受保护 blob 和公钥；取得后端 challenge 后生成经认证的证书请求，后端验证并返回证书，RKPD 管理可用供应资源。
私钥不应作为普通网络下载内容交给 Android；协议中的设备根/DICE 派生身份也不能成为公开 API 的永久设备标识符。
这些约束来自[官方 RKP 设计](https://android.googlesource.com/platform/hardware/interfaces/+/refs/heads/main/security/rkp/README.md)；该 `main` 文档还包含演进阶段及 AVF 扩展，实施需换成目标 revision，不能假定所有设备采用完整同一阶段。

RKP 证明 key/证书用于给业务公钥及其属性出具证明，与应用自己创建的签名/加密密钥不同。
后端不可达、供应池不足、CSR/HAL 失败与业务 keyblob 丢失是不同故障；证明失败不自动证明已有业务密钥不可用，业务签名成功也不证明证明链可用。
诊断按请求链分层：应用创建/证明请求、Keystore 选用证明资源、RKPD 的模块与供应状态、IRPC 实例、安全组件和后端结果。
不能通过输出 keyblob、HAT 或设备派生秘密来补足日志。

## 结论必须绑定真实密钥和失败条件

| 结论 | 最低所需证据 |
|---|---|
| 两组件可合法共享系统密钥 | descriptor domain/namespace、双方 SELinux 权限、实际允许/拒绝 |
| 逐次认证绑定正确 | 当前 challenge、SID/type 验证、旧 token 和其他操作 token 的拒绝 |
| 受保护删除有效 | 可信删除元数据与旧 blob 恢复后的拒绝路径 |
| 证明满足业务要求 | 远端验证过的链、challenge、公钥、所需安全级别与授权字段 |
| RKP 故障已定位 | 活动模块、IRPC 与后端/供应阶段的具体失败，而非笼统“Keystore失败” |

本页描述机制与审查依据，不声称已验证任何具体设备的闭源 TA、证明后端或生产密钥。
