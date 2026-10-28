# Android SELinux 规则溯源

下列官方正文均于 **2026-10-27** 实际打开读取。规则已在专项内展开，来源仅用于争议、版本和术语复核。
本地的风险链、反证和回归矩阵是原创归纳，不是将官方示例宏或历史规则当作可直接应用的产品补丁。
对象 owner、宏展开、contexts 合并结果、公共接口版本和 neverallow 必须以目标 Android 分支核对。

## AVC 与模式验证

[Validate SELinux](https://source.android.com/docs/security/features/selinux/validate)

- 已读：全局/每域模式、AVC 字段含义、日志及其限流、需要时收集用户态/内核调用链。
- 采用：从 scontext、tcontext、class 和 permission 还原访问，并关联真实入口和身份；comm 只作线索。
- 采用：同时检查全局 enforcing 和实际编译策略的 permissive 域，不以 getenforce 一项证明完整强制执行。
- 边界：调用链工具受内核/分支支持；页面中的 root、日志开关等命令不是 Review 默认执行动作。
- 转化：无 AVC 可能是未覆盖路径或日志缺失，专项要求实际结果与正负向断言，而非只统计日志。

## 对象映射与标签生效

[Implement SELinux](https://source.android.com/docs/security/features/selinux/implement)

- 已读：file/genfs/property/service/seapp/mac_permissions 等关键文件、标签管理组件与应用时点。
- 采用：按对象类型选择映射文件；文件上下文、服务注册和 property set 不能互相替代。
- 采用：区分路径期望标签与已存在对象的实际标签，并检查映像、restorecon、升级及挂载路径。
- 边界：官方提及的自动升级重标范围不能泛化到所有分区/恢复程序；具体生命周期须追目标实现。
- 转化：首次创建、inode 复用、rename、恢复与 OTA 的组合回归是根据标签生命周期推导的本地审查步骤。

## 新域、错标与过度授权

[Write SELinux policy](https://source.android.com/docs/security/features/selinux/device-policy)

- 已读：core service 错标例子、新 init daemon 域、audit2allow 局限、否定集合、调试权限与 dac_override。
- 采用：错标优先修 label，合法需求才加 allow；新 daemon 的启动域和职责须明确。
- 采用：检查否定集合遗漏 isolated/new domains；宏和 attribute 要按实际成员评价，而非只看源文件行数。
- 边界：不照搬历史设备 bringup 的 permissive/刷机流程；进入发布要求仍以实际 user enforcing 验证。
- 转化：最小正向域集合与相邻敏感对象的负向用例用于检验权限是否只覆盖需求。

[Customize SELinux](https://source.android.com/docs/security/features/selinux/customize)

- 已读：最小权限、neverallow、Android 8+ policy placement、system_ext/product public/private 与 GSI 注意事项。
- 采用：neverallow 冲突促使检查架构/标签/归属，不通过删约束、关闭检查或发布 permissive 绕过。
- 采用：平台 public 是 vendor 可依赖的导出接口，private 为实现；system_ext/product 公开接口由产品维护兼容性。
- 边界：页面示例明确带有历史版本，规则编号和片段不是当前分支事实；不为满足示例将代码任意搬分区。
- 转化：debug 构建成功与发布必需权限分开判断，检查 userdebug_or_eng 是否掩盖 user 路径缺权。

## Treble、owner 与公开类型版本

[Policy compatibility](https://source.android.com/docs/security/features/selinux/compatibility)

- 已读：object ownership、标签/类型冲突、public 类型 versioned attributes、mapping/ignore、public attribute 非版本化。
- 已读：system_ext/product 的映射责任，以及 property/service/hwservice/vndservice contexts 的分离说明。
- 采用：查同一对象是否被 platform/vendor 竞争标签；旧 vendor 与新 system 组合要保持公开边界和标签语义。
- 采用：给 attribute 增加成员可能扩大旧规则权限，重映射也必须审新对象是否继承过多访问。
- 边界：页面含 Android 8 等历史说明；不可据此断言现代 vendor AIDL 全部只能经 HwBinder。
- 转化：专项要求追实际服务管理器与目标版本，既检查升级丢权，也检查旧权限扩散到新类型。

## AIDL/HIDL 服务对象区别

[AIDL for HALs](https://source.android.com/docs/core/architecture/aidl/aidl-hals)

- 已读：SEPolicy for AIDL HALs、服务实例名、hal client/server attributes 与 service_manager 的注册/发现控制。
- 采用：AIDL HAL 的 service_contexts 与 HIDL 的 hwservice_contexts 分开；find/add、Binder call、方法授权分别证明。
- 边界：例子里的类型、实例和宏必须在本分支存在并符合设计，不将示例服务当作产品固定命名。

## 属性与 UID 的独立约束

[Add system properties](https://source.android.com/docs/core/architecture/configuration/add-system-properties)

- 已读：property context、读/写宏、exact/prefix 与值类型、跨分区稳定性和 vendor 命名范围。
- 采用：按真实写入者/读取者评价属性权限，相邻 prefix 和非法值用于负向验证；命名与稳定性分开检查。
- 边界：不把 `getprop/setprop` 的 shell 身份结果当 daemon 证据；具体前缀和构建宏以目标分支为准。

[SELinux concepts](https://source.android.com/docs/security/features/selinux/concepts)

- 已读：MAC 与 DAC、root 受策略约束、类型/attribute 展开、context/categories 的用途。
- 采用：SELinux、Unix owner/mode、UID/用户及 Binder 业务鉴权分开证明，allow 不构成业务授权。
- 边界：类别与 App 域随版本变化，不靠简化示例断言跨用户数据已经隔离。

上述核验只涉及文档读取；未编译或加载任何产品策略，也未执行设备、OTA、CTS/VTS 回归。
