# Android SELinux 策略与升级边界

适用于 `.te`、contexts、init daemon、服务注册、属性和分区策略变更；语言错误、Binder 业务鉴权另读对应场景。
固定 Android/内核分支、product、user/userdebug、plat/vendor policy 版本、分区来源和设备首发/升级路径。
下面给出可离线执行的推导步骤；宏、构建变量、policy 版本格式和限制的精确行为以目标分支源码为准。

## 从 AVC 还原操作意图

**风险**：把 AVC 当需求，直接采纳 audit2allow；攻击输入触发的越界访问被写成永久合法权限。

1. 保存事件的 `scontext → tcontext → tclass → denied permissions`、时间、PID/comm、路径/实例及操作来源。
2. `comm` 只是线索；从实际进程域、init 配置和调用栈确认执行者，避免把 shell 复现的身份当发布 daemon。
3. 将拒绝关联到业务动作：正常启动必需访问、错误路径、探测 fallback、恶意请求，还是已经应被上层拒绝的操作。
4. 查对象真实 label 和设计 owner；落到 `device`、泛化数据类型等默认 label 时，先追错标/创建路径，再考虑 allow。
5. 按先后因果定位：目录 search 被拒可能遮住后续 open/read；日志无后续 AVC 不证明后续操作本来合法。
6. 若日志不能确定入口，按目标内核/工具支持采集调用链；缺权限或缺设备时标记待确认，不把所有拒绝批量放行。

**修复/判定**：不该发生的访问修代码/协议；主体或对象错误修 domain/context；合法需求才给具体类型、class 和最小操作。
**反证**：预期被拒的攻击/可选探测不要求加 allow；已有更早 DAC/业务拒绝时，不能只凭缺 AVC 推断策略授权正确。
**正向回归**：enforcing 下走真实合法操作并断言结果；**负向回归**：同入口请求越界对象/动作，被拒且无副作用。
日志用于解释结果，不能以“日志清净”替代功能和拒绝断言；丢失、限流或未走到路径都可能没有日志。

## 按对象找到真正执行标签的组件

**风险**：用文件 allow 处理服务发现错误，或把 find、Binder call 和业务方法授权合成一条“服务可访问”。

| 对象 | 先查映射和执行者 | 必须分开证明的操作 |
|---|---|---|
| 普通文件/设备节点/目录 | `file_contexts`、创建者、文件系统 xattr；实际 `ls -Z` | 父目录搜索、创建/名称变动、读写/执行和 relabel |
| proc/sysfs 等对象 | `genfs_contexts`、挂载配置及目标文件系统支持 | 节点精确路径、class、挂载/重启后是否生效 |
| Binder/AIDL 服务 | `service_contexts` 与实际 servicemanager、服务完整实例名 | 注册 add、查找 find、进程间 Binder 调用及业务授权 |
| HIDL/HwBinder 服务 | `hwservice_contexts` 与 hwservicemanager | 注册/发现权限、client/server attributes 和实际 HAL 实例 |
| vendor Binder 服务 | 实际使用的 vndservicemanager 与 `vndservice_contexts` | 仅在采用该机制的目标分支核对注册/发现，不能套到所有 vendor AIDL |
| 系统属性 | `property_contexts`、init/property service、精确键或 prefix | 读和 set 分开，命名 owner、值类型与稳定性分别核对 |
| App 进程/数据 | `seapp_contexts`、签名/seinfo 与 mac_permissions 配合 | UID/用户/categories 与 domain、数据 label 的匹配 |

这些文件是映射入口，不是“改了即生效”的证明；核对产品合并后的安装文件、实际对象和管理进程读取时点。
AIDL HAL 可由普通 servicemanager 管理，不能沿旧 Treble 文章概括为 vendor/system 必须全部使用 HwBinder。
**修复/判定**：补正确对象映射和对应的最小 client/server 规则；注册实例字符串必须与 VINTF/运行服务一致。
**反证**：服务能 find 不证明敏感方法可调用，find 被拒也不等于文件 label 错；先确认 AVC 的 class 和管理组件。
**正向回归**：批准 server 注册、client 发现并完成合法调用；**负向回归**：未批准 domain 注册冒名实例、发现/调用敏感服务失败。
属性另测允许键读写、相邻 prefix 和不合法值；不能用 shell `setprop` 成功替代真实写入者身份。

## daemon 域、路径迁移和标签生命周期

**风险**：手工 relabel 后成功，重建、数据恢复或 OTA 仍错标；移到新分区的 daemon 沿用错误执行类型和大域权限。

- 沿 `init service → 可执行文件路径/exec label → domain transition → 运行 domain` 核对，脚本/包装程序和重启路径也要跟到最终进程。
- 新 daemon 需与职责对应的域；不为绕过限制复用 init、shell 或权限过大的已有域；先确认确实具备所需启动转换。
- 数据文件沿首次 mkdir/create、临时文件、rename、恢复和重建路径查 label 来源；查 type_transition、创建上下文与 restorecon 的时序。
- `file_contexts` 描述路径期望值；移动/复用已有 inode 不保证自动获得新路径的期望类型，不能只审首次空盘创建。
- 对 OTA 指明哪些镜像/目录自动重标、哪些须由受控 init/恢复流程处理；按该分支挂载与加密解锁时序验证。
- `chcon` 或临时 permissive 可供获准实验定位原因，不能当可交付修复；也不能无条件递归重标不归本组件所有的数据。

**修复/判定**：正确划定 exec/data 类型和 owner，在实际生命周期应用标签；放权前证明创建与恢复结果一致。
**反证**：已有正确 type_transition/restorecon 路径且所有迁移形态覆盖，不因缺少新的一次 relabel 调用报错。
**正向回归**：干净启动、daemon 重启、文件重建与真实 OTA/恢复后操作成功，核对进程和对象标签。
**负向回归**：相邻私有目录、替换路径/链接、另一 daemon 创建的文件不能获得额外能力；原标签文件升级后不被错误共享。

## 宏、attribute 和 neverallow 的真实授权面

**风险**：一行宏/attribute 扩展给所有现有及未来成员；`{ domain -untrusted_app }` 仍可能放过 isolated_app 和新 App 域。

展开本分支宏及 attribute 成员，比较变更前后 `主体集合 × 对象集合 × class/permissions`，尤其是默认 label、通配和否定集合。
给 attribute 增加成员同样是授权变更；不只看本次 `.te` 是否新增 allow，public attribute 的新成员还可能继承旧 vendor 权限。
优先正向列出需要的域和专用对象类型；大范围文件读写、执行、ptrace、重标或 capability 逐项说明必要性。
遇到 neverallow 先追为何设计冲突：错误分区、错域、任意可写代码执行或跨边界私有依赖；修架构/标签/组件归属。
删除 neverallow、关闭检查、加宽例外或把发布域改 permissive 不能作为通过构建的修复；userdebug_or_eng 也不能承载发布必需权限。
**反证**：共享只读对象或已有精确语义的宏可以合法覆盖多个域；规则宽度必须结合对象敏感度和真实成员判定。
**正向回归**：user enforcing 的发布功能通过；**负向回归**：代表性非成员、App/isolated 域及相邻类型保持拒绝。
验证实际编译策略的 permissive 域列表和 neverallow/策略检查；`getenforce=Enforcing` 只说明全局模式，不能排除单域 permissive。
策略编译成功只证明语法和所执行约束通过，不能证明业务应当获权、实际标签正确或负向隔离仍成立。

## plat/vendor 公共接口与版本映射

**风险**：vendor 引用 platform private 类型或抢标 system 对象，当次整包成功，framework-only OTA/GSI 时丢权限或启动失败。

1. 为 type、attribute、属性、服务和文件路径确认 owner 及所在分区，查是否两方重复声明或给同一对象竞争 label。
2. platform public 是导给 vendor 的 policy 接口，private 是系统实现细节；设备策略目录与构建变量须符合目标版本的分区归属。
3. 公开类型变更要核对旧 vendor API 对应 mapping/ignore 处理及语义，不能仅消除编译错误；重映射也可能把旧权限扩给新对象。
4. system_ext/product public 的兼容映射由产品维护；参考 GSI 下 OEM 类型/规则可能缺席，不能把它们当 vendor 的永远可用依赖。
5. 用支持的旧 vendor + 新 system、正常整包和必要 GSI 组合核对合成策略、标签和功能；只编译当前双端不能证明分区独立升级。

**修复/判定**：维护公开稳定边界与精确映射，或调整组件/接口归属；不能为了 vendor 访问随意公开整个 private 策略。
**反证**：纯 vendor 内部类型无跨分区依赖时无需导出；并非所有类型都要加入历史 mapping，按真实兼容承诺处理。
**正向回归**：受支持升级组合能启动并完成跨分区服务；**负向回归**：旧权限不扩散到新敏感类型、重复注册/标签碰撞被检查捕获。

## 与 UID、DAC 和 Binder 鉴权分别交付

SELinux 控制域与对象的操作关系；DAC/UID、Binder 权限、AppOps、用户和对象归属仍须独立正确，允许 Binder call 不能替代方法授权。
同域不同 UID/用户可能有不同业务权限；root 也不自动越过 SELinux。遇到 dac_override 拒绝先查 Unix owner/mode，而非顺手加 capability。
正向验证获准 UID/domain 的业务；负向分别选同域未授权 UID、不同域和跨用户对象，确认各层拒绝都不产生副作用。
交付写明策略编译/neverallow、实际 user enforcing 功能、负向及升级组合各自结果；测试目标从本分支取得，缺设备的运行与 OTA 明标未验证。

来源与版本复核：[SELinux 规则溯源](../../sources/android-selinux.md)。
