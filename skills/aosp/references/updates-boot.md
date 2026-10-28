# 启动、可验证系统与更新状态

装载/DT/镜像布局见[Bootloader 与设备树](bootloader-device-tree.md)，OTA 包/super/merge/恢复见[OTA 交付](ota-delivery-recovery.md)，各模块的独立职责见[Mainline 契约](mainline-module-contracts.md)。

基线核实日期：2026-10-28。启动镜像布局、OTA 机制和 APEX 能力随首发版本与升级路径变化。
本页描述状态与信任关系；实际行为以目标 bootloader、内核、产品配置及源码 revision 复核。
不要按当前网页的一个机型示例推断所有设备的分区和 recovery 布局。

## 启动链的责任分配

Bootloader 初始化必要硬件、选择启动目标、检查镜像并向内核传递启动参数。
内核建立执行环境后，init 负责挂载、策略加载与用户空间服务启动。
Verified Boot、分区选择、文件系统挂载和服务可用性是不同阶段的成功条件。[Bootloader][bootloader]

| 阶段 | 核心约束 | 能定位该阶段的证据 |
|---|---|---|
| Bootloader | 合法镜像、header、锁状态、slot 与回滚索引 | 串口、启动错误、bootloader 状态 |
| 内核 / early mount | 驱动、fstab、块设备、ramdisk 与逻辑分区可用 | kernel log、pstore、挂载错误 |
| SELinux 与 init | 策略、标签、域转换、动作与服务定义一致 | init 日志、AVC、启动耗时 |
| Native / Framework | 服务依赖、APEX、Zygote 与系统服务就绪 | 服务状态、崩溃、watchdog、trace |

`boot`、`vendor_boot`、`init_boot` 或 recovery 的内容由版本及机型决定。
镜像名相似不代表可以交换；镜像 header、内核模块和 ramdisk 必须符合该产品契约。
看到开机动画不代表 kernel 重启；Framework 重启也可能重新显示动画。

## init 不是普通顺序脚本

`.rc` 包含 actions、commands、services、options 和 imports，触发条件与服务生命周期决定实际顺序。
文件导入顺序、property trigger 和 service class 可能让两段文本的出现顺序不同于执行先后。[init 语言][init]
服务依赖应由真实就绪条件表达，任意增加固定 sleep 只会隐藏启动竞态。

- `disabled`、`oneshot`、lazy interface 和重启设置改变何时启动及退出后行为。
- UID/GID、capabilities 与 SELinux domain 分别约束进程，不能互相替代。
- 可执行文件路径、标签和域转换不一致，可能使“二进制存在”仍然无法启动。
- APEX 中的服务还受包激活和 mount namespace 影响，不应盲目提前启动。

SELinux 在启动期间建立并执行访问控制；AVC 应结合 source/target context、class 与操作解释。
开发阶段临时诊断模式不能作为最终运行条件；enforcing 下的正确行为才是交付依据。[SELinux][selinux]

## AVB 与反回滚

AVB 将镜像完整性验证与可信密钥、vbmeta 描述和分区链关联起来。
dm-verity 验证读取到的块；它不是用户数据加密，也不是应用授权机制。[AVB][avb]
签名校验成功、允许该版本启动和用户空间健康是三个不同结论。

反回滚索引阻止退回已知脆弱版本；它与升级失败时回退到可用 slot 的机制需要共同设计。
“换成旧镜像能启动”不能推出正式产品允许降级；受保护的索引和密钥状态可能禁止它。
审查签名或镜像改动时，应核对整个验证链及更新/回退窗口，而不是只检查单个 image 的 hash。
关闭 verification 或解锁后成功，仅能提供诊断线索，不能证明锁定量产状态可用。

## A/B 的状态语义

Legacy A/B 把更新写向非当前 slot，以保留正在运行的系统。
slot 的 active、bootable 和 successful 各有含义；active 只表示下一次尝试选择它。
启动尝试耗尽或验证失败时，bootloader 和 boot-control 状态决定回退。[A/B 状态][ab]

`update_engine` 的 payload 应用成功不等于新系统已经通过启动后检查。
成功标记不能随意提前，否则可能失去自动回退的机会。
共享的用户数据不会随 OS slot 自动复制；不可逆数据迁移可能破坏回退后的旧代码。
需要区分下载失败、写入失败、postinstall 失败、启动失败和健康确认失败，避免重复下载掩盖根因。

## Virtual A/B、快照与合并

Virtual A/B 对动态分区使用快照/COW 表示新内容，确认新系统启动后再合并到基础分区。
它不是给所有逻辑分区永久保留完整 `_a` 和 `_b` 两份实体。[Virtual A/B][virtual-ab]
压缩和 userspace merge 的具体实现按版本核对；`snapuserd` 可能处在系统关键 I/O 路径。

合并是可跨重启恢复的状态过程，不能把一次重启视为自动完成全部 OTA。
空间不足需考虑 COW、metadata、`super` 和必要临时空间，不能只查看目标 image 大小。
合并期间清空状态、删除快照或混刷分区可能破坏当前读视图，应依据已确认恢复设计处理。
在开始合并前和合并后的回退能力不同，不能承诺“任何时刻切回旧 slot 都安全”。
启动中的 init、SELinux 转换与 `snapuserd` 交接有特殊约束，调整 early boot I/O 时必须核查。

## 动态分区与 recovery

动态分区把 `system`、`vendor`、`product` 等逻辑分区组织在 `super` 内，通过元数据描述布局。
逻辑分区大小可以随 OTA 调整，但仍受总容量、分组、对齐与设备布局限制。[动态分区][dynamic]
动态分区解决空间管理，不自行提供镜像信任、A/B 回退或数据加密。

Recovery 是特定启动与维护环境，其内核、ramdisk 和所在分区取决于设备方案。
旧式 non-A/B 通过 recovery 更新，不能把其分区清单及安装逻辑直接套到现代 A/B 产品。[旧更新机制][nonab]
bootloader fastboot 与 userspace fastbootd 处于不同执行环境；实际支持以产品实现为准。
恢复方案要保留必要的验证元数据与状态一致性，不能把 factory reset 当成通用 OTA 修复方式。

## APEX、Mainline 与模块更新

APEX 为不适合普通应用安装模型的低层组件提供容器与早期挂载能力。
APEX 的 payload 验证与外层包签名是不同层次；只替换一个证书不能代表完整签名链已匹配。[APEX][apex]
设备上的活动版本可能来自 `/data`，遮蔽内置版本；只查看 `/system/apex` 容易误判实际执行内容。

Mainline 是让选定系统组件独立于整机发布周期更新的模块化方案，可使用 APK 或 APEX。
APEX 格式本身不保证任意系统组件都能独立升级；模块边界与稳定接口才决定兼容性。[Mainline][mainline]
外部模块更新可能改变代码而不改变整机源码 revision，诊断需要同时记录活动包版本。
APEX 的 staged activation、重启后验证与失败恢复，应按目标模块安装链核实。
模块包回滚、OS slot 回退和 AVB 反回滚不是一个开关，且均需考虑持久数据的向后兼容。

## 证据如何支持修改判断

| 失败现象 | 高价值证据 | 不能直接采用的结论 |
|---|---|---|
| 更新后卡住早期启动 | slot/AVB 状态、kernel/init 与挂载日志 | Framework 新代码一定是根因 |
| OTA 报成功但仍运行旧版本 | payload 结果、active/successful、启动回退原因 | 更新客户端 UI 误报是唯一问题 |
| 合并后空间或 I/O 异常 | snapshot 状态、COW、dm 映射和 snapuserd 日志 | 删除 metadata 即可恢复 |
| 升级后单模块崩溃 | 活动 APEX 版本、依赖库、符号和历史数据 | 系统 fingerprint 足以锁定代码 |
| 旧版无法启动 | rollback index、密钥、镜像组合与数据迁移 | 禁用 AVB 是正式修复 |
| 新 native 服务未出现 | rc 导入、trigger、domain、依赖与重启日志 | 文件被打包就等于服务就绪 |

良好的修复应解释坏状态如何形成，以及中断、重试和回退后如何回到一致状态。
仅延长超时、强制写成功标记或关闭验证会改变失败表现，不能代替该解释。

## 官方依据与版本复核

以下页面已阅读。首发/升级设备条件、启动镜像布局及 OTA 状态接口必须在产品分支复核。
源码链接的 `main` 只用于定位机制；发布证据应指向实际 revision 与活动组件版本。

[bootloader]: https://source.android.com/docs/core/architecture/bootloader
[init]: https://android.googlesource.com/platform/system/core/+/refs/heads/main/init/README.md
[selinux]: https://source.android.com/docs/security/features/selinux/implement
[avb]: https://source.android.com/docs/security/features/verifiedboot/avb
[ab]: https://source.android.com/docs/core/ota/ab
[virtual-ab]: https://source.android.com/docs/core/ota/virtual_ab
[dynamic]: https://source.android.com/docs/core/ota/dynamic_partitions
[nonab]: https://source.android.com/docs/core/ota/nonab
[apex]: https://source.android.com/docs/core/ota/apex
[mainline]: https://source.android.com/docs/core/ota/modular-system
