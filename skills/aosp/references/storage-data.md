# 存储与数据：密钥、卷、文件访问和计量

网络流量的 UID/tag、VPN/464xlat、共享网络 offload、Data Saver 与网络配额见[网络数据计量与控制](network-data-accounting.md)。它们与本页的磁盘容量、文件系统配额是不同对象。

卷/FUSE/passthrough/scoped storage 的集成见[存储访问](storage-access-integration.md)，底层密钥格式和硬件保护见[加密密钥生命周期](encryption-key-lifecycle.md)。

本页用于卷管理、Direct Boot、存储权限、容量统计、网络用量及备份变更。核实日期：2026-10-28。
先记录目标分支、设备首发 API、内核、文件系统、加密格式和用户状态；当前运行版本不能替代首发版本条件。
以下机制用于定位和判断；实际 fstab、服务接口、路径及测试名必须回查目标树。

## 先确定对象与所有权

- 区分内部私有数据、内部模拟共享存储、便携介质和 adoptable 卷；“external”不等于物理 SD 卡。[1][]
- 标识数据时至少带 user、package/UID、volume UUID 和存储类别；不要默认 `/sdcard` 永远属于同一个用户或同一块盘。
- 文件存在、路径可见、权限允许、密钥可用和内容已持久化是不同事实。
- 先查访问者所在 mount namespace 和实际挂载，再比较 root、shell、system service 与应用观察结果。
- 容量、应用存储、网络流量和备份大小是不同口径；不得把它们相加后解释为同一种数据用量。

## FBE：CE/DE 是生命周期与安全边界

FBE 从 Android 7 提供；Android 10 及以后首发设备要求使用 FBE。[2][]
CE 是用户凭据保护的数据，默认应用数据应尽量保留在 CE；DE 可供 Direct Boot 阶段的有限功能使用。
Direct Boot 允许用户首次解锁前运行必要组件，不是让所有业务提前访问用户私有数据。
`vold` 管理多用户 CE/DE 密钥，内核 fscrypt 执行相应目录策略；KeyMint/Gatekeeper 与启动信任链参与密钥保护。
DE 不表示明文、不受权限约束或任意用户共享；其可用时间与访问授权是两条独立规则。

- 首次启动、用户启动、解锁、工作资料解锁、停止和删除用户都要明确密钥及目录状态。
- 不能根据“屏幕锁住”直接推断 CE 密钥不可用；检查实际用户解锁/密钥生命周期。
- `directBootAware` 只表示组件能在该阶段运行，不会自动修复其对 CE 数据库、Provider 或服务的依赖。
- 避免把完整用户数据库复制到 DE 来绕过解锁限制；只保存解锁前确实需要的最小状态。
- 延迟到解锁后的操作需要可重试、去重并绑定 user；不能消费另一个用户的延迟队列。
- 故障证据应包含 user 状态、挂载与策略、vold/KeyMint 错误及失败访问，而不是导出密钥。

## Metadata encryption 与启动顺序

FBE 保护文件内容和文件名等相应信息；metadata encryption 补充保护文件系统其他未被 FBE 覆盖的内容。[3][]
Android 9 引入该能力，Android 11 及以后首发设备要求内部存储启用；不能把“升级到 11”当作同一首发条件。
内部实现涉及 metadata 分区、KeyMint 保护的密钥及 `dm-default-key`；内核接口和 shipping API 选择会影响格式。
官方明确：内部 metadata encryption 在 data 初次格式化时设置，不是普通 OTA 可以直接切换的布尔开关。

- fstab、内核能力、init 排序和 vendor 加密实现必须配套，不能只添加一个属性后宣告支持。
- `mount_all` 阶段 init 等待 vold；vold/KeyMint 若又等待 init 的属性请求，可能形成启动死锁。
- 审查新增依赖是否让解密、挂载路径反向等待尚未可用的服务或存储。
- 不把旧设备数据卷送进新格式再“试着挂载”；设计明确的兼容条件、恢复路径与测试介质。

## 卷管理、文件系统与 adoptable storage

StorageManagerService 组织框架层卷状态，`vold` 负责介质准备与挂载；`MountService` 是 Android 8 以前的类名线索。[4][]
设备配置文档包含 Android 4.x/5.x/6.0 的历史示例，不能照搬旧 `vold.fstab`、资源列表或 init 服务。
内核支持某文件系统不代表 Android 产品栈支持它；还需加密、完整性、OTA、权限和测试支持。[5][]
选择 ext4/f2fs 等实现应遵循目标 GKI/产品约束，不通过随机更换文件系统解决未定位的 I/O 延迟。

Adoptable storage 将介质格式化并加密绑定到设备，支持相应的私有应用数据和多用户隔离；不是普通可移植文件盘。[6][]
Android 7.0～8.1 的 FBE 不能与 adoptable storage 共用；Android 9 起支持，格式仍受首发版本影响。
拔出、重新插入、介质损坏和 UUID 改变必须有明确状态转换，不能自动视为一块空白新盘。

- 物理介质存在不等于文件系统就绪；分开发现、检查、解密、挂载和对用户发布。
- 挂载失败不默认格式化；错误可能是缺钥、损坏、格式不兼容或临时 I/O 故障。
- 仅在适合稳定连接的介质位置考虑 adoption；热拔插造成的应用不可用与数据损坏需进入验收。
- 以真实 UUID 和用户目录管理迁移，不硬编码共享存储绝对路径。
- 修改持久化实现时，逐项确认写入完成、崩溃一致性、重启可读及失败清理；成功返回不能代替断电恢复证据。

## Scoped storage：路径 API 仍受策略控制

Android 11 起对目标 API 30 及以上应用要求 scoped storage；Android 10 的兼容路径不同。[7][]
MediaProvider 的 FUSE 处理可拦截共享存储文件操作，按策略允许、拒绝或脱敏；直接文件路径不是权限绕过通道。
内部应用私有数据与共享媒体不走完全相同的 FUSE 路径，不能把任意文件访问慢都归因 FUSE。
Android 13 媒体权限细分、Android 14 可提供部分照片/视频访问；权限推断需要同时看 OS 和 target SDK。[1][]

- 区分 app-specific 目录、共享媒体集合、用户授予的文档 URI 和广泛文件访问。
- 不把 `READ_EXTERNAL_STORAGE`、旧 write 权限或 system app 身份当作现代全部共享文件权限。
- URI 授权、实际调用 UID、用户及生命周期应共同验证；同一路径在 shell 可读不能证明 app 可读。
- 优化批量查询或随机 I/O 时先测真实操作形态，不能为了 benchmark 绕过隐私检查。
- 文件系统与 MediaProvider 视图应保持相应一致性；扫描完成之前的数据库视图不等于介质全部内容。

## 容量统计与网络用量：先统一计量口径

应用磁盘统计可以利用文件系统 quota，由 installd 处理；不支持时存在遍历回退，统计慢不必然是 UI 线程问题。[8][]
逻辑文件大小、分配块、缓存、共享/归属和卷总量可能不同；先写明报告口径与采样时间。
启用 quota 要核对文件系统、内核和 fstab；不能从旧 ext4 示例推断所有 f2fs/内核组合都已验证。
删除文件后仍被打开、延迟释放和统计更新不同步，都可能使“目录变空”与“可用空间增长”不同步。

网络用量由网络路径计量，eBPF 方案可按 socket UID、tag 和 interface 归属数据，不是文件系统容量计数。[9][]
官方 eBPF 文档描述了早期 netd/TrafficController 实现；当前所在模块和 map 所有者要回查目标树。
socket 标签、UID、VPN、tethering/offload 和接口切换会影响对照方式；不要直接等同运营商账单字节数。
采样区间、重启/计数器重置、持久化时间桶和前后台分类需保持一致，差分不能生成负流量或重复计数。
用网络策略限制流量与显示历史统计是不同职责；修复显示不能悄悄改变联网权限。

## 备份与恢复：证明数据可恢复，而不只证明任务结束

先区分系统协调、应用 BackupAgent、传输 transport、云备份和设备到设备迁移；AOSP 框架不等于某云服务产品。[10][]
Auto Backup 是文件型机制，key-value 备份由应用定义数据；启用与执行条件不是“应用装好后立刻完整备份”。
备份范围由 app 配置、OS、target SDK 与传输类型共同决定；Android 12+ 的 data-extraction-rules 与旧规则不同。
某些厂商设备上 `allowBackup=false` 对云备份与 D2D 的效果可能不同，不能把它当所有导出通路的统一开关。

- 明确哪些数据可重建、哪些必须保留、哪些敏感凭据应排除，避免恢复后复用已失效的认证状态。
- 备份需取得一致的数据视图；不能把正在写入的数据库逐文件复制当作正确快照。
- 恢复验证包含安装/版本兼容、用户与包身份、CE 可用性、schema 迁移和首次启动行为。
- 记录传输端、数据集、失败阶段及恢复结果；上传成功不证明目标设备可用。
- 不因备份需要降低原文件权限、挪到 DE 或暴露给其他用户。

## 证据与实现决策

| 现象 | 先保留的证据 | 错误推论 |
|---|---|---|
| 开机前访问失败 | 用户解锁、CE/DE 位置、实际访问者与依赖 | 一律加 directBootAware 就能读数据 |
| 存储未挂载 | UUID、fstab、内核文件系统、vold/密钥错误 | 自动格式化即可修好 |
| 应用读不到媒体 | OS/target、权限/URI、用户、FUSE/MediaProvider 结果 | shell 能读，所以是应用 bug |
| 容量/流量不一致 | 同时间区间、归属、采样与重置点 | 两种计数必须逐字节一致 |

选择最靠近实际所有权的修复层，保持用户隔离、密钥生命周期和失败恢复；不以关闭 SELinux/权限检查完成验收。
验证使用目标树已有测试与隔离样本，覆盖重启、锁定/解锁、空间不足、介质移除、取消及恢复；无设备时标出未验证状态。

## 已核实的官方深读入口

1. [Storage：类型、运行时视图与权限版本](https://source.android.com/docs/core/storage)
2. [FBE：Direct Boot、CE/DE 与密钥实现](https://source.android.com/docs/security/features/encryption/file-based)
3. [Metadata encryption：首发条件、格式与启动死锁](https://source.android.com/docs/security/features/encryption/metadata)
4. [设备存储配置与 vold/StorageManagerService](https://source.android.com/docs/core/storage/config)
5. [Android 内核文件系统支持](https://source.android.com/docs/core/architecture/android-kernel-file-system-support)
6. [Adoptable storage：绑定、加密和可移除性](https://source.android.com/docs/core/storage/adoptable)
7. [Scoped storage：FUSE、访问控制与性能边界](https://source.android.com/docs/core/storage/scoped)
8. [Faster storage statistics：quota 与回退](https://source.android.com/docs/core/storage/faster-stats)
9. [eBPF traffic monitoring：归属和数据路径](https://source.android.com/docs/core/data/ebpf-traffic-monitor)
10. [Android 官方 Auto Backup：范围与恢复语义](https://developer.android.com/identity/data/autobackup)

[1]: https://source.android.com/docs/core/storage
[2]: https://source.android.com/docs/security/features/encryption/file-based
[3]: https://source.android.com/docs/security/features/encryption/metadata
[4]: https://source.android.com/docs/core/storage/config
[5]: https://source.android.com/docs/core/architecture/android-kernel-file-system-support
[6]: https://source.android.com/docs/core/storage/adoptable
[7]: https://source.android.com/docs/core/storage/scoped
[8]: https://source.android.com/docs/core/storage/faster-stats
[9]: https://source.android.com/docs/core/data/ebpf-traffic-monitor
[10]: https://developer.android.com/identity/data/autobackup
