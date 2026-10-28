# SELinux 的分区归属、策略接口与升级组合

用于平台/vendor policy 拆分、framework-only OTA、public type 演进、vendor_init 和策略装载故障。
资料核实于 2026-10-28；先固定 system/system_ext/product/vendor/odm 镜像版本、vendor API level、策略版本与设备首发条件。
Android 8 起的拆分、Android 11 起的 system_ext/product 扩展与旧单体策略不可混用；官网也保留不少只适用于历史 HIDL/Treble 阶段的例子。
基础 default deny、neverallow 与 denial 分析见[安全模型](security.md)，本页补充独立更新所需契约。

## Public policy 是跨分区接口

平台 public policy 暴露给 vendor 编写策略，private policy 是平台实现细节，允许随 framework 更新改变。
vendor 依赖 private type/attribute，即使同一套源码能构建，也可能在只更新 system 时无法组合。
public type 和 public attribute 的兼容处理不同：type 被转换为版本化 attribute；原本的 public attribute 不做相同版本化，新增成员可能自动获得既有 attribute 规则的权限。
[Policy compatibility](https://source.android.com/docs/security/features/selinux/compatibility)解释其 API 性质，具体暴露集合应查目标分支的策略快照。

| 策略来源 | 作用 | 发布时需确认 |
|---|---|---|
| system public/private | 平台接口与内部实现 | vendor 引用只落在受支持的 public 表面 |
| vendor/odm policy | 设备组件与硬件职责 | 使用的 public 策略版本、对象归属与所需镜像 |
| system_ext/product public/private | Android 11+ 的附加分区接口与实现 | 导出者维护对受支持旧 vendor 的映射 |
| compat mapping | 旧 vendor 所见符号到当前具体 type 的关系 | 每个受支持旧版本的映射实际进入新镜像 |

当前[构建说明](https://source.android.com/docs/security/features/selinux/build)列出相应构建目录与变量。
`BOARD_SEPOLICY_DIRS`、ODM/public/private 目录的含义要结合分支，不应只复制旧版本根目录 `sepolicy` 文件的布局。

## 标签归属比增加 allow 更早决定权限

对象在最终系统中只有一个具体 type；平台与 vendor 对相同路径或服务各自套用标签，可能发生后写覆盖、访问丢失甚至启动失败。
碰撞不只存在于文件，还包括 property、Binder service、socket 等受标记对象；为 vendor type 加 `vendor_` 前缀只能避免声明名碰撞，不能解决对象归属冲突。
[兼容规则的对象归属部分](https://source.android.com/docs/security/features/selinux/compatibility)说明 system、vendor、procfs、sysfs 等有各自约束，需按对象类别和版本检查。

新增对象时先确定它由哪一分区维护、是否构成跨分区稳定接口，再选择 context 来源和 type。
例如 vendor 给平台 `/system` 文件设置独有标签，会使新 system 镜像无法独立维护其对象语义；为未知 denial 重复添加两边标签不是兼容修复。
平台 public attribute 的成员变化也要审查授权影响，不能只看新增 type 自身没有新增 allow。

## Versioned attributes 与 mapping 怎样保留旧 vendor

假设旧 vendor 基于策略版本 V 构建，引用平台 public type `sysfs`。
构建系统把 vendor 对平台 public type 的依赖转换为 `sysfs_V` 等 attribute；vendor 自己不应手写当前新平台的具体 type 来逃避版本化。
新 system 携带的 mapping 将这些旧 attribute 关联到当前具体 type，最终与新平台和旧 vendor CIL 组合。
这允许更新平台而保留已经发布的 vendor 策略；仅把 vendor 源码也重编成新版本，验证的是另一种组合。

官方[兼容示例](https://source.android.com/docs/security/features/selinux/compatibility)使用 202504 vendor 与 202604 平台：

```text
旧平台：/sys/usb 的 type 是 sysfs
旧 vendor 的转换后规则依赖 sysfs_202504
新平台：/sys/usb 改为 sysfs_usb
新 system 的旧版本 mapping：
    (typeattributeset sysfs_202504 (sysfs sysfs_usb))
```

这里保留旧 attribute 对所代表旧对象集合的访问语义，映射本身不是凭空新增一个业务授权入口。
新 public type 应在受支持旧版本的 `.cil` 中有对应映射，或在 `.ignore.cil` 声明没有对应旧类型；ignore 不能用来掩盖旧 vendor 真正需要的访问。
映射多个新 type 到一个旧 attribute 会把旧规则应用到这些 type，应判断拆分前哪些对象原本就属于旧标签，避免扩大旧 vendor 权限。
示例的版本号不是产品支持矩阵；实际以目标策略版本、打包映射和 OEM 承诺支持的升级组合为准。

## 验证的单位是镜像组合

至少区分以下组合；是否支持更旧或更宽组合由产品发布契约决定。

| 镜像组合 | 所验证的性质 | 不能替代它的结果 |
|---|---|---|
| 旧 system + 已发布旧 vendor | 原基线确实可启动和完成场景 | 新源码编译通过 |
| 新 system + 原封不动旧 vendor | 新平台对既有 vendor 的兼容映射、标签与装载正确 | 新 system + 重编新 vendor |
| 新 system + 新 vendor | 新接口与新设备策略协同正确 | 仅 framework-only OTA 成功 |
| 新 system_ext/product + 受支持旧 vendor | 附加分区导出者维护的映射正确 | system 自己的 mapping 正确 |

记录每个镜像的 revision/版本、旧 vendor 所针对的策略版本、最终 contexts、CIL/mapping 和运行策略。
如果 OEM 的 system_ext/product public policy 是 vendor 的依赖，相关分区的旧版本 mapping 也由该导出者负责维护；平台 `system` 的映射不会自动覆盖它们。
GSI 等组合中缺少 OEM system_ext/product 时，还要检查该分支对相应 vendor 规则和缺失 type 的处理，不能仅凭自家整包成功推断通用组合成立。
这些组合依据[策略构建和分区映射说明](https://source.android.com/docs/security/features/selinux/build)；具体可支持矩阵必须落到产品目标。

## 构建和装载不是同一个阶段

Android 8+ 将多分区策略转换、版本化并组合为可装载二进制；早期 init 必须能取得所需分区中的策略材料。
支持 precompiled policy 的分支会校对其输入匹配信息，不匹配时可能改走设备侧编译路径；应核对真实启动路径，而非只寻找某个文件名。
contexts 还分别被 init、属性服务、服务管理器等使用，加载 binary policy 不证明每类对象都得到预期标签。
[Build SELinux policy](https://source.android.com/docs/security/features/selinux/build)解释历史单体构建与现代拆分组合，启动具体路径以目标 init/sepolicy 构建规则为准。

策略合成失败、policy version 不匹配、缺少 mapping、context 不存在、运行时合法性拒绝，是不同故障。
把全部错误都转成运行时 allow 可能根本改变不到失败阶段。
验证应同时检查策略构建约束、实际装载结果、per-domain permissive 状态及真实业务拒绝；global enforcing 不能排除某个域仍被单独设为 permissive。
[Validate SELinux](https://source.android.com/docs/security/features/selinux/validate)提供 denial 字段与策略分析办法；诊断能力及内核审计 tracepoint 有具体版本条件。

## Vendor init 不能借完整 init 权限访问平台内部

init 读取 vendor 脚本，但并非所有命令都以完整 init 域执行。
vendor_init 子进程使用受限 SELinux 域；文件系统等标记为需要 vendor 子上下文的 builtin 在该上下文执行，影响 init 内部状态的某些命令仍在主进程执行并做相应权限处理。
因而“rc 由 init 执行”不能作为 vendor 脚本访问平台 private 文件或属性的授权依据。
[Vendor init](https://source.android.com/docs/security/features/selinux/vendor-init)描述该拆分，具体命令标记与脚本来源判断要查目标分支 init builtin 表。

定位时应连接脚本所在分区、触发器、builtin、真实 scontext、目标 label 与服务启动定义。
vendor_init 执行命令与被启动 daemon 最终获得什么域是两个问题；修改前者 allow 不会自动完成后者的正确域转换。
如果旧产品借用了不稳定平台内部对象，应修正接口或对象归属，再验证支持的旧/新镜像组合，不能把共享文件路径变成永久豁免。

## 审查输出

应能说明：谁拥有对象；vendor 依赖哪个 public 版本；新 type 如何映射旧对象集合；哪些分区提供哪些 compat 文件；已发布旧 vendor 与新平台如何组合；在哪一阶段观察到允许或拒绝。
没有 denial 可能只是场景未触发、审计被限流或域处于 permissive，不能单独证明升级兼容。
本页未运行设备测试，也不为任意版本组合声明兼容；它给出需要由实际镜像、构建和运行证据验证的不变式。
