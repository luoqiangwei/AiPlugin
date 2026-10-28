# 存储密钥交接、Hardware-wrapped keys 与历史格式

本页补充 FBE 密钥的持久化/解锁关系、硬件包装、Adiantum、adoptable 与更新恢复。核实日期：2026-10-28。
CE/DE 和 metadata encryption 的基本启动模型见[存储与数据](storage-data.md)，LSKF、synthetic password 与可信限速见[认证链](security-authentication.md)。
先固定设备首发版本、当前 Android/内核分支、磁盘已有格式、文件系统与安全硬件；这些维度共同决定密钥能否继续使用。

## 密钥可用性是依赖图

[FBE 官方实现](https://source.android.com/docs/security/features/encryption/file-based)由 `vold` 管理密钥，除 per-boot key 外均加密保存在磁盘。
密钥文件本身往往放在另一个加密类别中，因此“文件已存在”不代表 `vold` 此时能读取并解封。

| 密钥类别 | 官方存放关系 | 解锁依赖的含义 |
|---|---|---|
| system DE | `/data/unencrypted` | 先有启动可信状态与相应保护密钥；该目录在启用 metadata encryption 时仍受其保护 |
| 内部 user DE/CE | system DE 下的 `vold/user_keys` | system DE 可读后才有相应 blob；CE 仍有额外凭据保护 |
| adoptable user DE | 内部 user DE 下，按 volume UUID 保存 | 外置介质已插入不能替代内部用户 DE 可用 |
| adoptable user CE | 内部 user CE 下，按 volume UUID 保存 | 内部用户 CE 未解锁时，外置 CE 的密钥记录也不可读 |
| per-boot | 不持久化 | 重启后无需恢复旧内容的临时数据具有独立寿命 |

目标路径的完整表格见官方 FBE 文档，不将上表作为可跨分支硬编码的路径 API。
KeyMint 需在 `post-fs-data` 前能够处理初始密钥请求，因此官方要求早期 HAL 启动；把它依赖的数据或服务放到尚未解锁的 CE 中会形成依赖环。
内核 `fscrypt` 接受 class/master key 后负责目录策略；密钥 blob 解封、安装到内核和上层发布“用户可用”是不同阶段。

## 换锁屏凭据与换文件加密密钥不是同一事件

内部 CE key 由从用户 synthetic password 派生的 AES-GCM key 保护；synthetic password 是每用户随机生成的高熵稳定秘密。
`LockSettingsService` 管理其由 LSKF、Weaver 或 Gatekeeper 等构成的保护绑定。
LSKF 变化时，删除的是旧凭据到 synthetic password 的绑定信息；不能由换 PIN 推出所有文件内容需要重新加密，也不能只改 UI 密码记录就认为旧路径已失效。[FBE key protection](https://source.android.com/docs/security/features/encryption/file-based)

其它 FBE 密钥的外层保护通常使用不离开 TEE 的 Keystore key，并请求 rollback resistance；设备支持时，删除可抵抗恢复旧 blob。
不支持时，`secdiscardable` 是尽力而为的补充，不能声明与可信防回放删除等价。
**工程推导**：用户删除或重置失败要沿“保护记录、Keystore/Weaver 资源、内核已安装 key、volume 对应记录”解释；只观察一个文件被 unlink 不能证明所有恢复路径都消失。
屏幕重新锁定也不等于 CE key 已从内核移除，状态解释应绑定实际用户生命周期。

## Hardware-wrapped keys 缩小原始内容密钥的暴露面

[Hardware-wrapped keys](https://source.android.com/docs/security/features/encryption/hw-wrapped-keys)从 Android 11 起在支持硬件上提供：原始 storage key 仅专用硬件掌握，Android 和内核持有包装后的值。
硬件从 storage key 分别派生并隔离 `inline_encryption_key` 和 `sw_secret`：前者直接装入 inline crypto keyslot 加解密文件内容，后者返回软件用于文件名、key identifier 等不能由块加密引擎完成的工作。
所以该机制没有消除软件中的全部加密秘密；保护结论必须区分内容密钥与其它子密钥。

包装有不同寿命：long-term wrapping 使用硬件持久秘密，供磁盘保存；ephemeral wrapping 使用每启动随机的硬件秘密，交给内核使用。
磁盘保存的长期包装值外面仍有 Android 自身绑定启动状态/适用凭据的保护层，两层目的不同。
从 RAM 泄露的 ephemeral wrapped 值不能在设备重启后继续使用；这不等于运行时完全控制 OS 的攻击者无法利用当下已授权的数据访问。

inline crypto 的 keyslot 数有限，控制器 reset 还可能丢失槽内容。系统必须能用包装值重新编程槽位，不能把唯一可恢复密钥仅保存在槽中，也不能要求每次 I/O 错误恢复都让用户重新输入 PIN。
硬件的 KDF 应对两个用途使用不同 label/context；若两者相关到可由软件子密钥推回内容密钥，就失去这一层隔离目标。
同主 CPU 上纯 TEE 软件包装不自动获得专用硬件对 cold-boot 等攻击的同样收益。

## 新旧 wrapped 格式不能只改配置名

| 条件 | 接口与格式关系 |
|---|---|
| `wrappedkey_v0`，Android 11+ 的旧方案 | 经 KeyMint 的 storage-key/convert-to-ephemeral 能力，非标准磁盘格式 |
| `wrappedkey`，Android 17+ 当前方案 | 经内核生成/导入/准备 key 的 ioctl 路径，兼容 mainline Linux 的方案 |
| 已以 v0 首发的设备 | 官方要求继续 v0 以保留向后兼容，不能在普通 OTA 中改成新名字 |

这些版本条件来自[当前官方说明](https://source.android.com/docs/security/features/encryption/hw-wrapped-keys)，不从 Android 大版本推测旧 BSP 已有所有内核回调。
FBE 与 metadata encryption 的配置是两个位置；支持一种用途不自动证明另一种已启用。当前方案只用于内部存储，不能加到 adoptable 卷配置上。
内核加密验证通过仍须确认 wrapped-key 用例实际执行；官方指出能力未检测到时相关用例可能 skip 而总体显示 passed。
密文/IV/KDF 一致性可以由导入的测试 key 检验，但这不证明厂商硬件秘密永不泄露。

## Adiantum 改变算法，不改变 CE/DE 授权

[Adiantum](https://source.android.com/docs/security/features/encryption/adiantum)适用于 Android 9+、缺少 AES 加速指令的 CPU；有 ARMv8 crypto extensions 或 AES-NI 时，官方建议使用更快的 AES。
它可用于 FBE 内容/文件名及相应 metadata encryption；用户凭据、synthetic password 与可信限速的关系仍存在，不能把算法选择当成另一套用户隔离模型。

算法能力、fscrypt、块加密与 metadata 路径需要配套，且 Android 9/10 与 11+ 首发配置不同。
旧属性名中的 `fde` 有时配置的是 adoptable 的 metadata encryption，并不能据此判断整台设备使用 FDE。
32 位 ARM 的 NEON 加速关系到实现性能；日志中的算法实现名、实际文件系统策略与 dm 层配置可解释“配置写了 Adiantum 却仍然很慢”，单个属性不能证明数据真的使用该算法。
算法和 flags 确定磁盘格式，不能在已有数据卷上当作可随 OTA 随意翻转的性能参数。

## Adoptable 的恢复仍依赖原设备和原用户

[Adoptable storage](https://source.android.com/docs/core/storage/adoptable)为每个采用的介质生成随机密钥，保存在内部存储并与采用分区 GUID 关联；因此拔卡带走不获得一块可在另一台机器挂载的普通盘。
FBE 设备的 adopted 卷同时使用 FBE 和 metadata encryption，密钥又受前述内部 user CE/DE 的依赖关系约束。
Android 7.0～8.1 不支持 FBE 与 adoption 并用，Android 9+ 才支持；旧文档提到的非 FBE/FDE adopted 路径不能推广为新产品内部存储的允许方案。

**工程推导**：介质、GUID、内部密钥记录和用户状态构成同一绑定；复制文件系统镜像、重建一个相似 UUID 或插入同容量卡都不能恢复该绑定。
临时移除使应用/数据不可用，不等于用户已删除这些内容。重新插入失败应区分缺钥、GUID 不符、I/O 损坏及加密格式不支持，不能自动重新格式化。
内部密钥记录丢失时，即使外置盘物理完好也可能无法恢复；这与存储介质的坏块检测是不同问题。

## 历史 FDE 的启动约束为何不同

[Full-disk encryption](https://source.android.com/docs/security/features/encryption/full-disk)只适用于 Android 9 及更早首发设备；Android 10～12 仅保留由这些旧设备升级的支持，Android 13 删除 FDE 支持。
其 `dm-crypt` 在块层保护整个 userdata，需先建立解密映射再挂载真实 `/data`，无法提供 FBE 的逐用户 CE/DE 解锁划分。

旧实现为显示凭据 UI 临时在 `/data` 挂 tmpfs，解密后需停止所有持有临时文件引用的相关进程，再切回真实卷并重启服务。
所以历史 `vold.decrypt`、main/late_start 和 cryptfs 属性描述的是那套启动状态机，不能贴到当前 FBE 系统里“修复挂载”。
历史换密主要重包裹 disk master key，不是重写全部用户数据；而 inplace 首次加密被中断会进入部分加密失败状态，不能按“密码错误”解释。
本节仅用于识别旧产物和日志，不把旧命令/默认算法作为当前产品配置建议。

## OTA、recovery 与 Resume-on-Reboot 各自恢复什么

`fileencryption` 定义的磁盘格式不能通过普通 OTA 随意改变；未启用 wrapped keys 时，`inlinecrypt` 的增减通常只改变执行实现，不能把这个例外推广到 wrapped 格式转换。[FBE configuration](https://source.android.com/docs/security/features/encryption/file-based)
recovery 无法读取 userdata 上的 DE 存储，官方因此推荐 A/B 更新让 OTA 在正常运行时处理。
历史非 A/B 方案若确需 recovery 读取包，使用专门不受 FBE 保护的最小目录与限定访问策略；启用 metadata encryption 时还需考虑该层，不能将其解释为 recovery 已能读全部用户数据。

[Resume-on-Reboot](https://source.android.com/docs/core/ota/resume-on-reboot)在准备好的 OTA 重启后恢复 CE 可用性，系统锁屏状态并不因此等同于用户当前在场。
Android 11 的 reboot escrow HAL 路径与 Android 12+ 的 server-based 路径有不同条件。后者以一次性随机秘密和 TEE 保护共同恢复 synthetic password；服务端不保存用户 PIN，材料在使用后丢弃。
这不是把 CE key 永久搬入 DE，也不允许任意重启复用已准备的状态。

**工程推导**：OTA 应用成功、进入正确槽位、可信侧接受 keyblob、恢复 CE、恢复 SIM 连通性是不同事实。
server-based RoR 取回材料失败时，应解释为数据仍等待合法解锁，而不是损坏后直接清除；普通重启、准备被取消和材料过期也不能落入同一“自动解锁”分支。
SIM-PIN replay 另有绑定 SIM 身份、一次使用和短时效条件，CE 恢复成功不能独立证明蜂窝通信已恢复。

本页未穷举所有 fstab 参数、IV 模式、SoC 包装算法、RoR 后端与异常恢复状态；设备上的密钥保留/清除和真实断电恢复仍须目标实现证据，本文不声称已运行设备测试。
