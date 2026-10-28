# 企业设备管理：管理身份、策略解析与数据作用域

核实日期：2026-10-28。设备管理 API 的调用资格、管理模式和冲突规则随 Android 版本演进。
对应版本 CDD、产品 feature 声明、目标分支实现及具体 API 文档共同决定适用范围。
本页解释平台机制，不把云端 EMM 控制台或某个 DPC 产品当成 Android 平台本身。

## 管理身份不等于普通权限

EMM 提供管理解决方案，设备上的 DPC 经合法 enrollment 获得相应管理身份。
Device Owner 管理设备级能力，Profile Owner 管理指定 profile；可调用的 API 取决于管理模式。[管理模型][overview]
预装、平台签名、管理员用户或持有危险权限，都不自动成为 Device Owner。

| 身份或对象 | 作用 | 不能推出的权力 |
|---|---|---|
| Device Owner | 对受管设备实施适用的设备策略 | 以任意 UID 读取所有应用数据 |
| Profile Owner | 管理指定 profile 的应用、数据与策略 | 无条件读取个人 profile 内容 |
| 传统 active admin | 使用仍受支持的设备管理能力 | 等同于现代 owner 或管理角色 |
| 新版本管理 role holder | 按角色和 API 获得特定管理能力 | 自动获得所有 owner API |
| Delegated package | 使用 owner 委托的 scope | 拥有 owner 的全部管理权 |

Android 用户、profile、账号、包与管理 component 分别有不同生命周期。
相同包安装在个人与工作 profile 中，是不同用户空间的应用实例。[用户与 profile][users]
管理状态应绑定正确用户及可信 component 身份，不能仅以包名字符串判断。

## Provisioning 建立可持久的管理关系

Managed provisioning 处理告知、建立受管用户、必要应用配置以及 owner 设置；DPC 随后完成合规配置。
需要的 `device_admin`、`managed_users` 等产品能力由实现和兼容要求决定，不是声明后就已具备完整支持。[平台实现][implement]
setup UI、系统组件和 DPC 的协作必须覆盖中断、失败和恢复，避免留下半配置用户。

Device Owner enrollment 有严格的初始状态条件，不能对已有个人数据的设备任意提升管理权。
QR、NFC、云或 DPC-first 的具体流程及 intent 在各版本不同，旧示例不应当作固定协议。[Provisioning][provision]
Android 12 起部分 provisioning intent 与回调流程变化，迁移需核对 mode 选择和 compliance handler。
合规回调发生在哪个用户，会影响账号、包和策略实际配置的对象。

owner 身份设置成功、DPC 完成策略配置与用户可开始使用，是不同状态。
测试设备上的开发设置方法不能替代产品的告知、合法 enrollment 与状态约束。

## Work profile 的隔离与共享

Work profile 以独立用户空间隔离应用数据和账号，同时可与父用户共享部分系统设置和展示入口。
Launcher 徽标、通知或共享界面不表示底层数据已经合并。[工作资料][profiles]
一份 APK 在多个用户下可共享安装代码，但应用数据、凭据和策略作用域仍应区分。

- 服务处理请求时核对调用用户、目标 profile、父用户关系与具体能力，不将它们都视为 user 0。
- 跨 profile intent、剪贴板、文件、联系人与应用启动需分别经过对应策略和 API。
- 显示来自工作 profile 的内容，不自动授权个人应用读取原始数据或凭据。
- 组织所有设备上的 profile 可能有特定父用户/设备级策略例外；这些例外按具体 API 核实。

`getParentProfileInstance` 一类入口只开放文档列明的策略能力，不能被理解为任意个人数据访问通道。
“Profile Owner 绝不影响任何全局设置”与“组织拥有设备就能读取全部个人数据”都是过度概括。

## 多用户服务与管理状态所有权

系统组件可以选择每用户实例或由一个实例提供服务，两种结构都要明确请求和数据归属。
跨用户权限控制、组件标志和实际路由决定是否允许调用。[多用户应用][multiuser-apps]
单实例服务代表多用户工作，不意味着它可以把所有用户的策略和缓存合成一份。

用户停止、profile 暂停、解锁和删除时，应清理订阅、回调及相关授权缓存。
政策来自某个管理 agent，不代表它设置的状态必然是设备当前最终执行状态。
同一操作经 Settings、系统 API 或后台任务触发，均需到达拥有策略的可信执行边界。
UI 隐藏入口只是呈现，不能替代服务端限制或证明策略已真正生效。

## 策略冲突按每类规则解析

Android 14 起的 resolution framework 支持多个符合资格的管理 agent 对部分策略施加要求。
这不表示同一设备可以任意拥有多个 Device Owner，也不表示所有 API 都参与多 agent 解析。[策略解析][resolution]
实际策略由受管理对象、来源及对应解析机制共同决定。

| 机制 | 解析含义 | 典型误推 |
|---|---|---|
| MostRestrictive | 执行更严格的限制 | 任一 agent 撤销便立即解除全部限制 |
| MostRecent | 按规定执行最近设置 | 所有安全限制都采用最严格值 |
| StringSetUnion | 合并各来源集合 | 一般列表都该求交集或取最后值 |
| TopPriority | 按管理角色优先级选择 | 最后调用者总能覆盖之前设置 |

上述类名与 API 对应关系按版本及 `PolicyIdentifier` 文档核实，不凭数据类型猜规则。
设置值、设置结果和 resolved/enforced state 应分开记录。
设置回调可报告冲突或硬件失败，后续其它来源变化又可能使结果改变。
清理某个 agent 时移除该来源贡献，再重新解析；不能直接将全局值恢复默认而覆盖其余来源。

## Delegation 是可撤销的按用户能力

owner 可通过 `setDelegatedScopes` 将一组 `DELEGATION_*` 能力授给指定包。
委托 scope 是 per-user 状态，持续到显式撤销或委托包卸载，并非一次请求的临时许可。[委托 API][delegation]
证书安装、权限授予或应用限制等 scope 彼此不同；拥有其中一个不能代替另一个。

委托包需使用 API 规定的调用方式，不能因为没有 admin component 就自行绕过调用资格判断。
变更、撤销和卸载后，缓存与正在进行的异步工作需按实际授权语义收敛。
不能信任调用者自己传来的委托包名，也不能把某次 UID 对应关系永久缓存到下一次安装。
owner 对委托的管理责任不会因为把工作交给另一个应用而消失。

## 解锁、撤管与数据生命期

工作 profile 可有独立解锁状态；父用户已解锁不证明工作 CE 数据可访问。
FBE 的 CE/DE 区分可用时机，DE 仍然需要应用和用户访问控制。[数据密钥边界][fbe]
不应为让开机策略可用而把工作凭据和敏感数据全部搬入 DE。

暂停 profile、移除工作 profile、清除某应用数据和 factory reset 的效果不同。
撤管时需要明确删除的用户、owner/委托、策略贡献及工作数据，不能通过普通卸载假定全部清理完成。
profile 删除后的外部副本、日志、已共享内容或远端服务状态不一定自动消失。
受管身份迁移或重注册时，必须重新确认策略来源和授权，不能只复用旧包名或账号。

## 从现象判断失效边界

| 现象 | 应关联的证据 | 不充分的判断 |
|---|---|---|
| DPC 调用被拒绝 | owner/role、component、调用用户、API 版本与 scope | manifest 已声明权限就应成功 |
| 设置后 UI 仍受限 | 本 agent 值、其他来源、解析策略与执行值 | setter 返回后必然覆盖全局 |
| 工作数据出现在个人应用 | profile/UID、跨界 API、URI/intent 授权与接收者 | 同一包名意味着同一数据空间 |
| 撤管后限制仍在 | 剩余 agent、持久策略及重新解析结果 | 直接清空设备全部限制 |
| 重启前后管理状态不同 | provisioning 完成状态、持久来源和用户解锁 | 增加一次开机广播即可修复 |

实现判断以授权、状态所有权与最终执行语义为依据，避免仅验证管理应用页面显示成功。

## 已读官方依据与版本复核

官方平台正文用于机制，官方 API 用于调用资格与委托契约；具体版本需映射目标分支及对应 CDD。
旧页面中的 primary user、固定 UID 算式与 provisioning 示例不能代替当前用户模型和 API。

[overview]: https://source.android.com/docs/devices/admin
[implement]: https://source.android.com/docs/devices/admin/implement
[provision]: https://source.android.com/docs/devices/admin/provision
[profiles]: https://source.android.com/docs/devices/admin/managed-profiles
[users]: https://source.android.com/docs/devices/admin/multi-user
[multiuser-apps]: https://source.android.com/docs/devices/admin/multiuser-apps
[resolution]: https://source.android.com/docs/devices/admin/device-policy-resolution
[delegation]: https://developer.android.com/reference/android/app/admin/DevicePolicyManager#setDelegatedScopes(android.content.ComponentName,%20java.lang.String,%20java.util.List%3Cjava.lang.String%3E)
[fbe]: https://source.android.com/docs/security/features/encryption/file-based
