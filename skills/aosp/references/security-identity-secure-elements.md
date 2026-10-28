# Identity Credential、OMAPI 与 Secure Element 访问

用于身份文档安全存储、读卡器会话、SE applet 与 vendor HAL 访问控制。核实日期：2026-10-28。
固定 Framework API、Identity HAL/feature version、SE/TEE 实现和实际 applet；硬件上存在 SE，不代表所有身份文档、Keystore 密钥或 NFC 交互都由它保护。
当前官方 API reference 已将部分 Identity 类标记为 API 37.2 弃用；以下解释实际提供该机制的分支，不能把弃用标记当作旧设备数据已迁移或 HAL 已移除的证据。

## Identity HAL 负责安全存储，文档协议另有所有者

[官方架构](https://source.android.com/docs/security/features/identity-credentials)是应用 API → `credstore` → Identity Credential HAL → 安全硬件。
`IIdentityCredentialStore` 不规定发行机构和验证设备的全部通信语义；凭据应用仍负责相应文档的签发、呈现与验证协议。
因此 HAL 返回成功既不证明发行者可信，也不证明读卡器业务身份已获准取得所有字段。

[AIDL 契约](https://android.googlesource.com/platform/hardware/interfaces/+/refs/heads/main/identity/aidl/android/hardware/identity/IIdentityCredentialStore.aidl)把凭据拆成 document type、namespace 下的 CBOR 名值项、访问 profile、CredentialKey 和用于呈现的签名密钥。
创建时的 StorageKey 保护可外部保存的凭据内容；CredentialKey 用于向发行方认证该凭据，其证明链用于验证硬件与装载状态。
安全硬件不必为所有文档内容提供内部持久存储：Android 保存受保护 blob 与“所有明文都存进 SE”是两种实现。
test credential 使用已知的测试 HBK 并在回执中标识，不能作为生产凭据保护的证据。

`default` 实例明确用于常规访问；若实现 `direct_access`，它是独立实例，通常需要分别配置凭据。
不能由常规 store 存入成功推出关机或低电量 NFC 路径可用；低功耗取数协议本身也超出该 HAL 的规定范围。

## 数据项访问同时受用户、读卡器和会话约束

Personalization 把每个 namespace/name/value 与访问 profile ID 关联；profile 可要求用户认证、认证有效期以及匹配的 reader certificate。
默认 profile 要求用户认证且 timeout 为零，即每次读卡器会话都需要认证；指定 reader certificate 时，应与读卡器给出的证书链匹配。
这些条件来自[访问 profile API](https://developer.android.com/reference/android/security/identity/AccessControlProfile.Builder)，具体组合和授权结果仍按目标 HAL 的逐项返回值处理。
HAL 定义“数据项没有任何 access profile”为不可访问，不能把空列表理解成公开读取。[IIdentityCredentialStore](https://android.googlesource.com/platform/hardware/interfaces/+/refs/heads/main/identity/aidl/android/hardware/identity/IIdentityCredentialStore.aidl)

呈现会话还绑定临时公钥、session transcript、读卡器请求及其签名。无效认证 token、无效 reader 签名、请求未覆盖的数据项、缺失临时公钥和 transcript 不一致有不同失败状态。
**工程推导**：用户刚解锁手机、某张读卡器证书受信和当前会话所请求的字段获准，是独立事实。
不能因为身份 UI 显示“允许”就去掉安全侧 profile；不能把上个会话的 transcript、认证 token 或读卡器请求直接套到本次连接。
业务应根据每个数据项的授权结果选择披露范围，避免一次部分成功后仍发送未获准字段。

## 呈现签名密钥有签发与更新生命周期

[IdentityCredential API](https://developer.android.com/reference/android/security/identity/IdentityCredential)把动态 authentication key 与 CredentialKey 分开：动态密钥由凭据生成，公钥凭据交给发行者认证，再保存对应的 static authentication data；私钥留在安全硬件。
“已生成密钥”与“已有发行者认证数据”之间存在待认证状态。可用 key 数量、使用次数与有效期共同影响呈现结果，耗尽、过期和未认证也不能视为同一种错误。

在支持 feature version 202101 或以上的实现中，`update()` 成功会删除原动态认证密钥，需要生成替代密钥并重新向发行者认证；应用不能继续用旧 key 的 static authentication data 表示更新后内容。
HAL 的 `credentialData` 也可能随 feature version 变化，契约要求支持早期 feature version 创建的数据。
**工程推导**：OTA 后“旧凭据不能解密”应先区分 blob 兼容、硬件绑定、凭据内容更新和认证密钥补充，不应通过重新创建空凭据掩盖旧数据丢失。
API level、HAL 版本与 feature version 分别表达不同能力，不能只检查当前 OS 版本就调用所有新方法。

## OMAPI 把 Android 身份映射到 SE applet 访问规则

应用路径通常是 `SEService` → `Reader` → `Session` → `Channel`，在选中的 AID 上交换 APDU。
[Session API](https://developer.android.com/reference/android/se/omapi/Session)区分 applet 不存在/不能选择、调用者无访问权、会话已关闭、通信 I/O 失败和 channel 资源不可用。
能枚举 reader 或建立 session 不代表可以访问任意 AID；AID 是 SE 应用标识，Android 包名/签名是调用方标识，两端要由访问规则关联。
channel 与 session 应归属于实际连接，关闭后对象不可继续使用；无可用逻辑 channel 的 `null` 也不是授权失败的替代码。

**官方机制**：[OMAPI vendor stable interface](https://source.android.com/docs/security/features/open-mobile-api)从 Android 13 起允许 vendor HAL 经 OMAPI 服务访问 SE，既有应用接口不因此改变。
HAL 没有 APK 包名和签名证书，因此 vendor 配置把 Linux UID 映射到 16 字节 UUID；OMAPI 按标准补 `FF` 到 20 字节，作为 SE 访问规则中的 device application reference，再与 AID 规则配合。
这是可信配置建立的映射，不是 HAL 在请求中自报一个任意 UUID。

映射文件以 `hal_uuid_map_` 加 `ro.boot.product.hardware.sku` 的值命名，服务按官方规定从 `/odm/etc/`、`/vendor/etc/`、`/etc/` 寻找。
产品默认未启用该 vendor 接口；需要相应 `secure_element_vintf_enabled` 资源配置、服务注册、UID/UUID 映射和 SE 端已部署规则一致。
接口服务名为 `android.se.omapi.ISecureElementService/default`，可在官方 [service_contexts](https://android.googlesource.com/platform/system/sepolicy/+/b8e41c33da479cdb4134c01cca2a9ae029e9a1de/private/service_contexts) 核对；SELinux 对服务发现的允许仍不代替 SE 的 applet 访问规则。

**工程推导**：共享 UID 会共享该映射所表达的主体，SKU 配置选错会使合法 HAL 无权或使错误主体获得访问。
如果只有 `service_manager find` 放行，而 SE 没有相应 UUID/AID 规则，连接服务成功后仍应拒绝访问。
反过来，扩大为所有 HAL 共用一个允许任意 AID 的 UUID，会把 applet 的业务边界退化为一个过宽的 vendor 访问域。
“Android Ready SE”描述可在 SE 上承载的能力，不保证目标设备已把 KeyMint、Identity 或 RKP 的所有实现都迁入 SE。

## 从失败层区分根因

| 现象 | 解释所需证据 |
|---|---|
| 凭据存在，个别字段取不到 | namespace/name、profile ID、当前用户认证、reader 链及逐项状态 |
| 更新后无法呈现 | feature version、内容更新是否成功、动态 key 待认证/耗尽/过期状态 |
| HAL 能找到 OMAPI，但打不开 AID | 实际 UID、SKU 选择的 UUID 映射、SE 上的 device/app reference 与 AID 规则 |
| 偶发无法开 channel | SE/reader 状态、channel 耗尽、非 multiselect applet 会话与关闭时刻 |
| 常规身份 API 可用，低电量路径失败 | 是否存在 direct_access 实例及该实例是否独立完成凭据配置 |

本页已解释 Identity 数据/密钥生命周期和 OMAPI 授权映射；未穷举 ISO mdoc 全部报文、GlobalPlatform 规则编码、SE 固件/证书配置及每个厂商 applet 的 APDU 协议。
