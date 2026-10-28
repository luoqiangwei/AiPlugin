# 共享存储访问、卷发布与磁盘计量

核实日期：2026-10-28。本页细化 Core/Storage 的 FUSE、scoped storage、SDCardFS、卷配置、adoption 与 faster stats。
FBE/CE/DE、metadata encryption、备份与通用数据生命期见 [storage-data.md](storage-data.md)；硬件包裹密钥使用专门安全页，不在此重复。
版本判断至少包含 OS、target SDK、设备首发版本、内核、MediaProvider 模块及实际文件系统。

## 路径可达不等于调用方有权读取

内部私有目录、模拟共享存储、app-specific external 目录、portable 与 adopted volume 的访问路径不同。
`/sdcard` 是按用户提供的主共享存储语境，不能当成永远固定的块设备或全用户共享目录。
排查时需同时记录调用 UID/user、volume UUID、mount namespace、实际挂载和访问 API。[存储配置][config] [传统存储][traditional]

Android 10 的 scoped storage 与 Android 11+ 路径访问机制不同；Android 11+ 对 target API 30+ 应用要求 scoped storage。
MediaProvider 的 FUSE 可在 direct file path/NDK 文件操作中执行 allow/deny/redact，因此“没调用 ContentResolver”并不表示绕过媒体隐私。
内部 `/data/data` 并非此 FUSE 共享媒体挂载，Android/data 与 Android/obb 也有性能专门路径，不能把所有 I/O 延迟都归因同一 FUSE daemon。[Scoped storage][scoped]

读取其它应用媒体、修改媒体、访问其它 app external data、使用用户授予 URI 与 MANAGE_EXTERNAL_STORAGE 有不同条件。
scoped 页面中的 READ_EXTERNAL_STORAGE 是其所述历史基线，Android 13+ 媒体细分权限及后续部分照片访问应看权限专题和目标版本。
root/shell 可读、MediaStore 行可见、URI 授予存在与应用直接 open 成功是不同证据，不能相互替代。

## FUSE passthrough 优化的是受控打开后的数据通道

普通路径包含应用 → VFS/FUSE driver → userspace daemon → lower filesystem，会增加切换和传递成本。
passthrough 让 daemon 在处理某次 open/create-and-open 时，确定该文件/调用方可使用快路径，再把已打开 lower file 的引用交给 kernel。
后续适用 read/write 可直接转给 lower filesystem，避免每次往返 daemon；这不取消打开时的访问判定，也不把整个挂载点变为无限权限通道。[Passthrough][passthrough]

FUSE request ID、`/dev/fuse` connection、lower file FD 与 ioctl 成功结果必须属于同一次合法打开。
引用关联错误会把授权用于另一文件；lower FD/connection 的关闭与在途 I/O 也需有明确生命期。
需要 redaction 或不能提前确认完整访问权的情况，不能只为 benchmark 强行打开 passthrough。
性能评估需区分 metadata、顺序大块、随机小块、缓存命中与真实存储设备吞吐，不能用一个顺序读结果宣称所有 FUSE 成本消失。[快路径][passthrough]

官方 Android 12 文档将支持绑定到 Android 12 首发与相应 android12-5.4/5.10 等内核，升级设备的冻结内核不因此自动取得支持。
MediaProvider 是相关 Framework 实现位置，模块更新也不能凭空补出缺失的 kernel 功能。
这些是文档的引入条件，后续内核分支应核对其实际 backport/接口；仅运行 Android 12+ 不是充分条件。[版本条件][passthrough]

## SDCardFS 迁移同时涉及权限、casefold 与 quota

SDCardFS 原来提供模拟存储的访问控制、大小写不敏感及部分统计。
替代机制由 filesystem 原生 casefold、project quota、必要 bind mount 和新 FUSE 协同完成，不能只卸载 sdcardfs 就获得全部能力。
Android 11+ 首发且 kernel 5.4+ 的设备不能挂载 SDCardFS；更旧内核/升级路径有历史例外与支持边界。[SDCardFS][sdcardfs]

`emulated_storage.mk` 的原生 casefold 配置不能机械用于 Android 10 及以前首发设备，其既有 FBE 格式与该方式不兼容。
迁移的危险不是“缺一个速度优化”而是改变磁盘名字/加密/权限语义；失败时不能将已有用户卷重新格式化当成兼容修复。
两个只在大小写上不同的文件名、用户隔离、目录权限和统计都应保持目标分支承诺，不能只测一次文件拷贝成功。[迁移条件][sdcardfs]

## 介质发现、挂载与对应用发布

StorageManagerService 持有 Framework 卷状态，vold 负责介质准备/挂载等；fs_mgr/fstab 描述块设备与挂载配置。
discovery、检查文件系统、密钥可用、mount、用户目录准备和对应用发布是不同状态，不能因 sysfs 节点出现就发出“存储就绪”。
移除介质后应停止新操作并处理在途 FD、Provider 视图和挂载状态；重新插入依 GUID/UUID 识别，不应只按插槽号复用旧数据身份。[配置][config]

官方 config 页横跨多个历史版本：≤4.2 的 vold.fstab、4.3 之后统一 fstab、5.x 的 storage_list.xml 与 Android 6 动态卷模型不能混用。
Android 6 移除旧静态列表/EMULATED_STORAGE 环境变量及设备 init 硬编码 FUSE 服务，由 vold 动态处理相关挂载。
旧 traditional 页面里的 Zygote bind mount/环境变量解释可帮助理解用户 namespace，但不能作为当前分支精确实现路径。
诊断应读当前 fstab、vold/Framework 状态与 `/proc/<pid>/mountinfo` 所见对象，不能靠旧路径名推断。[配置演进][config] [历史模型][traditional]

## Adoptable storage 绑定的是设备与卷身份

Android 6 引入 adoption，将介质格式化/加密并绑定本设备，可以存应用和多用户私有数据；portable 则保留可移动文件盘语义。
adopted 分区 GUID 关联保存于设备内部的密钥，换到另一设备不能简单挂载；恢复出厂/原设备密钥丢失也不等于介质本身没有数据。
应用还需声明适合的 installLocation 才能迁移；ejected 时记住包与“当前可运行”是不同状态。[Adoptable][adoptable]

Android 7.0–8.1 的 FBE 不能与 adoptable 共用，Android 9+ 才支持相应组合；实际 FBE/metadata 格式仍需按设备条件配置。
采用的 filesystem 需 POSIX permissions 与 xattrs，不能任意以便携盘格式替换。
适合 adoption 的位置应稳定连接；TV 固定 USB 盘与手机上随手拔出的 USB 盘有不同风险，不能只因都能枚举就提供相同默认方案。
介质性能 benchmark 是体验筛选，不能证明断电一致性、耐久或加密安全。[Adoptable 条件][adoptable]

迁移主共享数据涉及源/目标卷、剩余空间、包路径和中断恢复，成功回调不代表所有持有旧 FD 的进程已经改用新卷。
损坏、缺钥、文件系统不兼容和暂时 I/O failure 都可能表现为 mount failed，应保留区分，不能默认询问格式化或把未知卷当空白盘。

## Faster statistics：计量加速不等于任意存储限额

Android 8 官方方案利用 filesystem quota 让 installd 快速取得磁盘用量，不支持时回退为手动计算；公开统计结果应在两条路径下都正确。
启用 quota 需要 kernel、filesystem 与 fstab 支持；旧文档明确验证基线是 ext4/Linux 3.18+，不能把其中的 ICE/fstab 示例当成现代所有产品通用配置。[Faster stats][stats]

quota accounting、project ID/UID 的归属、缓存预算和磁盘保留策略是不同对象。
统计值应说明是 code/data/cache、共享 external 类别、逻辑大小还是已分配空间，并绑定 user/package/volume 与采样时间。
一个 app 的名义缓存额度不等于无法超出的写入硬限制；页面的磁盘/inode 全局保护也不能替代每个 API 的配额契约。
删除目录、释放 open-but-unlinked 文件、更新计量和可用块回收有不同时间点，不能以 `du` 与 Settings 的单次差值直接判断 quota 错误。

quota 开关变化可能触发首次 fsck/结构更新，第一次启动较慢不一定是系统卡死。
若统计差值接近特定测试文件大小，应从内部 data、external cache 等被测类别追溯 UID/project 归属，而非只改 UI 四舍五入。
新 filesystem/内核组合需真实统计与 fallback 对照；统计快并不能证明 volume 空间不足或 cache eviction 的行为正确。[统计验证][stats]

## 主要分支与诊断归属

| Storage 分支 | 本页的判断依据 | 深度边界 |
|---|---|---|
| Scoped storage / FUSE passthrough / SDCardFS | 授权路径、快路径与首发/内核条件 | 逐个 open/read/write ioctl 与全部 MediaProvider 内部缓存策略 |
| Device configuration / examples / traditional | 卷状态、namespace、fstab 历史和发布顺序 | 各设备控制器/文件系统的全部配置字段 |
| Adoptable | GUID/密钥、迁移、包可用性与热拔插 | 全部厂商介质和故障恢复实现 |
| Faster statistics | accounting/fallback、计量对象和 quota 条件 | 每个 quota limit、缓存淘汰算法与 block-level 量测 |
| Encryption / backup | `storage-data.md` 及安全专题 | 本页不重复密钥派生、硬件 wrapped key 或备份协议 |

定位需连接实际失败调用、errno、调用方/namespace、volume 状态与对应 daemon，而不是只截一张文件管理器图。
不确定 lower filesystem 与 FUSE 哪层出错时，应在同一授权语境下对比操作路径，避免拿 root lower-path benchmark 直接证明普通 app 的体验。

## 官方依据

[config]: https://source.android.com/docs/core/storage/config
[traditional]: https://source.android.com/docs/core/storage/traditional
[scoped]: https://source.android.com/docs/core/storage/scoped
[passthrough]: https://source.android.com/docs/core/storage/fuse-passthrough
[sdcardfs]: https://source.android.com/docs/core/storage/sdcardfs-deprecate
[adoptable]: https://source.android.com/docs/core/storage/adoptable
[stats]: https://source.android.com/docs/core/storage/faster-stats
