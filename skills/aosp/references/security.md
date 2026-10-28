# Android 信任边界与平台安全机制

涉及具体认证与密钥行为时，继续读[认证链](security-authentication.md)、[密钥/attestation/RKP](security-keystore-attestation.md)；策略跨版本问题读[SELinux 兼容](selinux-compatibility.md)，APK 身份与 native 防护读[签名与内存安全](signing-memory-hardening.md)。本页保留整体信任模型。

Trusty/DICE 见[可信执行](security-trusted-execution.md)，Identity/OMAPI 见[身份与安全元件](security-identity-secure-elements.md)，Safety Center/Private Space/蜂窝保护见[平台安全服务](security-platform-services.md)，wrapped/FBE 密钥交接见[加密生命周期](encryption-key-lifecycle.md)。

用于权限、IPC 授权、SELinux、启动信任链、密钥与加密存储，以及安全补丁适配。安全边界应从攻击者能控制的输入与状态解释，而不是从目录或组件名称解释。
“事实”对应已读官方资料；“工程推导”是实现判断。核实于 2026-10-28，要求与默认行为必须按目标发布、设备能力和分支确认。

## 1. 身份、隔离与授权是不同问题

**事实**：Android 利用 Linux UID、进程隔离及文件权限构建应用沙箱，native 代码也处于相应沙箱中；SELinux、seccomp 等进一步形成纵深防御。[S1][]
沙箱不表示应用之间永不通信，而是通过受控组件和接口共享能力。

**工程推导**：信任边界至少区分外部应用、跨用户/profile、系统服务、vendor/HAL、kernel 和安全执行环境。
请求携带的包名、UID、路径、对象句柄和目标用户都是需验证的数据，不能仅因来自 Binder 参数就视为可信身份。
调用身份来自可信执行上下文；把操作派发到其它线程或清理 Binder identity 后，不能再假设读取到的仍是原调用者。
服务代表调用者执行操作时，要避免“代人调用”的权限扩大：自身有权限并不意味着可以替任意调用者使用该能力。

| 问题 | 所需证据 | 常见误推 |
|---|---|---|
| 调用者是谁 | 可信 UID、签名/身份映射、委托链 | 请求中的包名就是调用者 |
| 可访问谁的数据 | 用户/profile 作用域和对象所有者 | 系统服务可跨用户就可以任意共享 |
| 可做什么 | 权限、操作状态、服务端授权 | UI 隐藏入口就已禁止操作 |
| 数据去了哪里 | 返回值、日志、文件、回调接收者 | 只检查写入权限便没有泄漏 |

## 2. 平台权限不是一张“系统应用白名单”

**事实**：危险权限的运行时授予、角色分配及特权权限配置有不同作用；权限控制组件也随发布演进。[S2][]
签名或安装身份不能替代其它层的用户授权、操作限制和 SELinux 约束。

**工程推导**：从权限声明追踪到授予条件和服务端 enforcement，而不是只核对 manifest 中有名称。
正常调用路径应验证对象归属与目标用户；后台、锁屏、profile、工作策略及用户撤销权限可能改变合法操作条件。
新增授权判断要明确发生在信任边界的哪个位置，以及是否早于身份清理和异步派发。
为内部调用增加绕过入口时，要证明该入口不能被外部借道触发；仅用注释标“internal”没有隔离效果。
具体权限级别和允许列表规则按目标分支查看，不把某个发布对系统/非系统应用的授予规则推广到全部版本。

## 3. SELinux：从软件责任推导最小策略

**事实**：SELinux 对包括 root 进程在内的对象访问施加强制控制，默认拒绝；enforcing 阻止违规访问，permissive 只记录。[S3][]
Android 策略用域、类型、属性与规则表达边界；新增 daemon 通常需要相应域、执行文件标签与访问规则。[S4][]
neverallow 表达禁止出现的授权关系，不是运行时出错后应删除的噪声。[S4][]

**工程推导**：拒绝日志先回答主体、目标、对象类别、操作、路径/服务和触发用例，随后判断软件是否本来就该访问。
错误标签、错误分区、错误架构路径和真正缺少规则，会产生不同修复；不能把每条 denial 都转成 allow。
策略改变应对应软件职责改变。扩大通用域、授予默认标签或绕过 neverallow，可能把一个功能问题变成系统级暴露。
Binder 服务、属性、文件、套接字等对象的标签来源不同，不能只改 `.te` 文件就假设其它配置已正确。
开发时的临时诊断状态不等于交付状态；最终验证须在目标 enforcing 策略下进行。

**定位证据**：相关 `*.te`、context 文件、实际进程/对象标签、拒绝日志、构建约束及对应功能调用。
官方页面保留的旧策略路径和示例编号只解释机制；具体 platform/vendor 策略布局和兼容要求查目标源码。

## 4. AVB：验证镜像来源、完整性与回退条件

**事实**：Android 8 起提供 AVB 参考实现，支持启动时验证、不同分区的信任委托及 rollback protection；bootloader 需正确实现信任根和回退元数据等平台接口。[S5][]
AVB 与镜像构建、签名、分区元数据和设备启动状态有关，不是运行在应用内的一次签名校验。

**工程推导**：镜像内容变化会影响相应签名/哈希链与更新组合；只重编一个二进制不能保证可部署镜像仍匹配。
回退计数、信任状态、槽位与版本组合要在更新方案中一起解释，不能只记录文件版本号。
签名有效证明来源与完整性，不证明镜像没有漏洞；启动成功也不能证明完整性和回退保护按发布要求工作。
不能把关闭验证当成产品修复，或假设开发解锁设备的行为等同于生产锁定设备。

## 5. TEE、Trusty、KeyMint 与 Keystore 的职责

**事实**：Trusty 是一种 TEE 操作系统，与 Android 隔离；Android 也支持其它 TEE 实现，所以 TEE 不等于 Trusty。[S6][]
AndroidKeyStore 是应用侧访问方式；Keystore daemon 管理访问与 keyblob；KeyMint HAL 将敏感操作交给安全环境中的实现。[S7][]
KeyMint/历史 Keymaster、Gatekeeper 与认证 token 共同支持受认证条件约束的密钥操作，但属于不同组件。[S7][]

**工程推导**：使用 Keystore API 不能单独证明某把密钥由指定硬件安全级别保护；须核实实际安全级别、授权条件和设备实现。
密钥不可导出不等于可任意使用。攻击者若能借用合法服务执行签名/解密，仍可能突破应用的意图边界。
keystore alias、UID/namespace、grant 和用户状态需要共同追踪；只知道 alias 不代表拥有使用权。
TEE 隔离也不免除 RPC 长度、共享内存和状态机验证；新增可信功能还会扩大可信计算基。

## 6. FBE 与 Direct Boot：可访问不等于无敏感性

**事实**：FBE 为不同文件/用户使用可独立解锁的密钥；CE 存储在相应用户解锁后可用，DE 存储可供 Direct Boot 阶段使用。[S8][]
Direct Boot 改变组件在解锁前后的可用数据与生命周期；一个用户解锁不能替代另一个用户或工作 profile 的状态。[S8][]

**工程推导**：启动前必需状态与用户隐私数据应分开存储；将所有数据移到 DE 来消除启动失败，会扩大解锁前暴露面。
DE 不是公开存储，也不代表跳过权限；CE 当前可用也不意味着可以跨用户访问。
写入、迁移、备份、删除和恢复都需要按数据所属用户与密钥状态解释，不能只验证一次解锁后的读写成功。
FBE 保护与元数据加密、应用级端到端加密不同，不从一种机制推出其它机制已经存在。

## 7. 版本绑定与补丁状态影响密钥和安全声明

**事实**：Keymaster/KeyMint 的版本绑定把密钥与可信系统/补丁版本联系起来；升级时可能需要升级 keyblob，回退后密钥可能不可用。Treble 引入按分区追踪的版本信息。[S9][]
安全公告的修复来源包括 AOSP、上游内核和 SoC 厂商；仅更新 framework 并不能代表其它受影响组件都已修复。[S10][]

**工程推导**：升级/回退异常需核对真实启动版本、system/vendor/boot 补丁信息、可信环境获得的信息以及 keyblob 升级结果。
禁止通过伪报安全补丁级别来“修复”版本绑定错误；版本声明应反映实际实现和补丁覆盖。
处理公告时从当期条目确认组件、受影响版本、补丁和依赖，结合目标分支判断是否适用、已合入或需要 backport。
不能仅按 CVE 名称或提交标题做机械 cherry-pick；回移后仍需验证补丁所依赖的不变式与失败场景。
本文件不固定“最新”补丁月、漏洞清单或支持周期，执行时重新核实对应公告。

## 8. 安全结论应描述实际边界

| 变化 | 应证明的性质 | 合适证据 |
|---|---|---|
| 新 Binder 入口 | 非授权调用被拒绝，合法委托未扩大 | 身份/权限路径及正反调用 |
| 新路径或 daemon | 标签与最小访问符合职责 | enforcing 行为、contexts、策略构建 |
| 密钥功能 | 所有者、认证与安全级别符合要求 | 实际密钥属性、失败行为、用户状态 |
| 存储迁移 | 解锁前后及跨用户边界不泄漏 | CE/DE 路径、生命周期和恢复测试 |
| 安全补丁 | 目标分支确实消除相同根因 | 补丁差异、依赖分析、针对性回归 |

**工程推导**：没有崩溃、没有 denial 或使用了安全组件，都不能独立证明安全；应说明被拒绝的能力、可信输入与残余假设。

## 已读官方来源

- [S1 应用沙箱](https://source.android.com/docs/security/app-sandbox)：UID、进程与纵深隔离。
- [S2 平台权限](https://source.android.com/docs/core/permissions)：权限控制、角色与版本演进。
- [S3 Android SELinux](https://source.android.com/docs/security/features/selinux)：强制访问控制及 enforcing。
- [S4 SELinux 定制](https://source.android.com/docs/security/features/selinux/customize)：域、标签、最小策略与 neverallow。
- [S5 AVB](https://source.android.com/docs/security/features/verifiedboot/avb)：镜像信任、分区委托与回退保护。
- [S6 Trusty](https://source.android.com/docs/security/features/trusty)：TEE 隔离及其它实现的边界。
- [S7 Hardware-backed Keystore](https://source.android.com/docs/security/features/keystore)：Keystore、KeyMint、认证和访问域。
- [S8 FBE](https://source.android.com/docs/security/features/encryption/file-based)：CE/DE、Direct Boot、多用户密钥。
- [S9 密钥版本绑定](https://source.android.com/docs/security/features/keystore/version-binding)：版本、分区补丁与 keyblob 升级。
- [S10 Android 安全公告](https://source.android.com/docs/security/bulletin/asb-overview)：当期公告与各类修复来源。

[S1]: https://source.android.com/docs/security/app-sandbox
[S2]: https://source.android.com/docs/core/permissions
[S3]: https://source.android.com/docs/security/features/selinux
[S4]: https://source.android.com/docs/security/features/selinux/customize
[S5]: https://source.android.com/docs/security/features/verifiedboot/avb
[S6]: https://source.android.com/docs/security/features/trusty
[S7]: https://source.android.com/docs/security/features/keystore
[S8]: https://source.android.com/docs/security/features/encryption/file-based
[S9]: https://source.android.com/docs/security/features/keystore/version-binding
[S10]: https://source.android.com/docs/security/bulletin/asb-overview
