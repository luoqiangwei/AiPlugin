# OTA 交付、动态分区与失败恢复

用于更新包适用性、super 容量、快照合并、userdata 一致性、DSU 和 vendor APEX。核实日期：2026-10-28。
slot/AVB/启动基本状态见[启动与更新](updates-boot.md)，启动容器、DT 与 fastboot 模式见[Bootloader 与设备树](bootloader-device-tree.md)。
以下机制需绑定首发/升级路径、分区布局、update_engine/recovery 版本、内核与实际源/目标产物；不能混合不同年代页面的配置示例。

## 一个更新包绑定明确的前置与目标状态

[OTA package tools](https://source.android.com/docs/core/ota/tools)以 `target-files.zip` 为输入；full 包提供目标状态，incremental 包描述从特定源状态到目标状态的差异。
增量包依赖生成时的真实源产物，不能由“版本号看起来相同”代替 source 分区内容一致。
签名后产物与未签名构建目录也可能不同；错误源镜像、调试 remount 或其它修改会导致哈希验证失败。
full 包虽较少依赖旧内容，仍须满足设备、签名、版本/回退、分区和接收端能力条件，不是通用救援镜像。

OTA metadata 的 pre-device、pre-build、pre-build-incremental 与 post 字段表达不同身份；Android 11+ 多 SKU 可以列出合法运行时 fingerprint 集合。
仅扩充元数据允许列表不能使本来不兼容的硬件镜像变成兼容；分发端与安装器也应理解同一套 SKU 条件。

[Release signing](https://source.android.com/docs/core/ota/sign_builds)中的 APK 更新身份、OTA 验证 key、APEX 容器签名/内部 payload key 以及 AVB 分区信任链有不同消费者。
签过 OTA ZIP 不表示里面所有 APK/APEX 已换成正确发行身份；只重签外层 APEX 也不代表内部 payload 的信任已匹配。
test keys 是公开测试材料，不能作为发行包所有权。签名、证书轮换及旧设备实际内置的信任根共同决定后续能接受什么更新。
历史 recovery sideload 仍验证签名；下载方式改变不自动绕过安装器的信任检查。

## 动态分区改变容量分配，不改变持久数据所属

[Dynamic partitions](https://source.android.com/docs/core/ota/dynamic_partitions/implement)由 super metadata 描述逻辑分区 extents，`dm-linear` 提供块视图，验证层可再叠加其上。
super 不是一个可随意写用户文件的大文件系统；userdata 等长期读写分区不应装进 super。
update group 为一组逻辑分区定义最大总量，组内某个镜像可增长不表示组上限、总 super 容量或对齐开销已满足。
普通 A/B、Virtual A/B、retrofit 与 non-A/B 的 group 容量约束不同，不能把所有情况都除以二。

[A/B dynamic update](https://source.android.com/docs/core/ota/dynamic_partitions/ab_launch)保留 source metadata/extents 供当前系统及差分读取；构建 target metadata 时不能把仍使用的 source 空间重新分给目标。
metadata slot 与 OS boot slot 有关联，但写好一份 metadata 不代表所有 target blocks、postinstall 和启动状态已完成。
错误清理旧 group 可能破坏正在运行的源系统，错误保留 target 残留又可能造成空间不足。

[Super sizing](https://source.android.com/docs/core/ota/dynamic_partitions/how_to_size_super)需要估计产品寿命内最大 OS 大小、最坏更新快照及可接受的 `/data` 借用量。
例如不借用 `/data` 时，至少需在所用机制下容纳最终 OS 加必要快照/另一份内容；工厂镜像大小本身不是长期容量预算。
压缩率是内容相关估算，已压缩 EROFS 还会减少进一步压缩收益。不能以某次增量包很小承诺未来所有 full 更新都能安装。
FactorySize 应按 unsparsed 分区大小统计；ZIP、sparse image、文件系统已用字节与真实逻辑分区容量不是同一口径。

## Virtual A/B 的恢复能力随阶段改变

| 阶段 | 当前依赖的读视图 | 中断/恢复的含义 |
|---|---|---|
| 下载/应用 | 旧系统仍运行；目标写向非当前物理 slot 或 COW | 失败需保留旧系统及可重试的更新状态，不能提前发布启动成功 |
| 首次进入新系统 | 基础分区加快照组成新视图 | 启动健康确认前仍需保留允许回退的源状态 |
| 已确认并开始 merge | 新读视图继续服务，基础内容逐步被覆盖 | 不能再把旧 slot 当作永远完整的备份 |
| merge 被重启打断 | COW/merge 元数据记录进展 | 按状态恢复合并，不是删掉快照重新挂基础分区 |
| merge 完成 | 读映射可回到基础 dm-linear/验证层 | 此时才可按机制回收快照资源 |

[Virtual A/B](https://source.android.com/docs/core/ota/virtual_ab)只为 bootloader 必需分区保留相应实体更新组织，动态分区使用快照，不能按逻辑 `_a/_b` 名字推断永久有两份完整存储。
Android 11 的 kernel COW、Android 12 的压缩格式过渡、Android 13+ 的 userspace merge 路径不同；具体升级设备是否启用仍依目标配置。
压缩 COW 中 replace/copy/zero/XOR 等操作描述目标块如何组成，用户空间 `snapuserd` 可能承担根文件系统读取与合并。

因此 `snapuserd` 停止或 SELinux 域切换异常可以表现为系统 I/O 卡死，而不只是“更新服务报错”。
官方 init 交接在暂时禁止分区 I/O 的窗口切换 daemon 上下文；在该窗口引入一次读取尚未恢复的文件会形成依赖死锁。
下载校验、payload 应用、postinstall、boot successful、merge complete 和空间回收都需单独解释，客户端显示百分之百不等于全部阶段结束。

## Non-A/B 与 block OTA 属于历史恢复模型

[Non-A/B](https://source.android.com/docs/core/ota/nonab)在 recovery 中应用更新；当前官方将其列为 Android 15 起 deprecated，不能由旧文档存在推出新产品应采用它。
[Block OTA](https://source.android.com/docs/core/ota/nonab/block)以整分区块状态而非逐文件内容为目标，使文件系统布局、元数据和 dm-verity 所需字节保持一致。
旧 file OTA 只保持类似文件内容的做法不能给出同样的目标分区 hash。

[Non-A/B dynamic partitions](https://source.android.com/docs/core/ota/dynamic_partitions/nonab)还需按先缩小/删除再扩大的顺序更新分区和 group，避免暂态超过容量。
扩展设备分区的 block differences 与 metadata 操作必须由同一包逻辑协调；手工修改已由该逻辑管理的分区会破坏输入/输出假设。
recovery updater、脚本和设备扩展本身也是更新消费者，不能拿新包生成器给旧安装器假定它支持所有新 operation。

[OTA size](https://source.android.com/docs/core/ota/reduce_size)不仅取决于业务代码改了多少：非确定的文件顺序、时间、路径、压缩输出或块分配会放大差分。
稳定构建和重压缩/差分算法减少无意义变化，但不能靠关闭完整性检查来接受不匹配 source，也不能只比较下载字节而忽略安装 RAM/临时空间。

## User Data Checkpoint 保护 OS 回退所需的数据一致性

[UDC](https://source.android.com/docs/core/ota/user-data-checkpoint)补充 A/B 无法自动恢复共享 `/data` 的问题：新 OS 若已修改 userdata，仅切回旧 slot 可能使旧代码不能解释数据。
F2FS 可由文件系统 checkpoint 提供能力，其它支持路径可使用 `dm_bow` 保存被覆盖的恢复数据；后者需要可用空块，磁盘满会影响策略。
它与 Virtual A/B 的系统分区 COW 不是同一个对象，也不是永久用户备份。

恢复/创建 checkpoint 发生在相应读写挂载前，提交后不能再依赖该 checkpoint 回到旧数据。
KeyMint 删除操作延迟到 checkpoint 提交，避免旧 OS 回退时需要的 key 已不可逆销毁。
**工程推导**：代码数据迁移、checkpoint commit、boot 健康确认与对外不可撤销操作需对齐；服务器已收取的一条记录或用户已看到的结果不会由本地块恢复自动撤回。
容量不足时选择提交或重启的行为是产品/分支策略，不能把一次测试的默认值推广到所有设备。

## DSU 是临时系统与独立 userdata 的启动选择

[Dynamic System Updates](https://source.android.com/docs/core/ota/dynamic-system-updates)在临时逻辑存储中安装 GSI/相应分区，启用时由早期启动选择替代视图，并给 GSI 独立 userdata 沙箱。
它不覆盖原系统镜像，但仍消耗真实空间、metadata 及安全硬件资源；“临时系统”不表示无需 AVB/密钥/版本验证。
锁定设备可启动哪些开发/OEM 镜像，取决于 ramdisk 中认可的验证 key；被撤销 key 或不满足 patch level/兼容要求的镜像不应因由 DSU 下载而获得信任。

多分区 DSU 自 Android 11 起有相应能力，数据文件系统、Weaver 槽位和 Gatekeeper 的用户标识范围也有条件。
**工程推导**：原系统和 GSI 的用户凭据资源必须可区分，空间分配失败与镜像签名拒绝不能统称为“GSI 不兼容”。
页面中旧 VNDK 字段和容量示例只解释对应年代 loader，当前能力应查目标实现；不能把 VNDK 的历史依赖倒灌已废弃它的新 vendor 模型。

## RoR 恢复 CE 可用性，vendor APEX 决定早期依赖

[Resume-on-Reboot](https://source.android.com/docs/core/ota/resume-on-reboot)是准备好的更新重启后恢复 CE 访问的机制，和选 slot、系统健康确认、快照 merge 各自独立。
Android 11 的 reboot escrow HAL 与 12+ server-based 路径条件不同；服务端不可用、准备取消或材料过期都不能解释成 userdata 已损坏。
密钥交接与一次性材料见[存储密钥生命周期](encryption-key-lifecycle.md)。自动恢复 CE 不表示当前用户在场，也不证明 SIM-PIN/网络已经恢复。

[Vendor APEX](https://source.android.com/docs/core/ota/vendor-apex)把 HAL、native 依赖、init/VINTF、固件和配置组织为一个 feature 单元。非稳定 native 依赖通常随包带入，稳定依赖由 manifest/linkerconfig 建立可见性，不能只复制二进制。
VINTF fragment 放在包内与在构建属性中声明的安装归属不同，服务声明应与实际激活版本一致。
包内 init action 只在激活后解析，不能依赖已经过去的早期事件；早期必需 HAL 可用 bootstrap APEX，但它只从预置位置激活，不能依赖尚未挂载 `/data` 的更新包。

Android 17+ 的 `init_dev_config` 可在 apexd-bootstrap 前按 SKU 选择/禁用 vendor APEX；持久属性位于 `/data`，因此开发用途的 persistent selection 不能承担生产早期选择。
**工程推导**：选择新版 HAL 包必须同时解释其库、固件、服务声明与内核依赖。能够单独安装 APEX 不代表硬件状态或外部组件自动与之原子更新。

本页未穷举 payload operation 编码、COW 每个格式版本、全套 recovery edify 扩展、分发服务器协议、DSU loader 全部字段或 vendor APEX 各 HAL 模板；未执行镜像构建、签名、刷写及设备恢复测试。
