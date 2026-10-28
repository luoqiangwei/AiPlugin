# 权限状态、AppOps 与隐私可见性

用于平台权限授予/撤销、前后台数据访问、PermissionController、角色与受限读取。它补充 [安全模型](security.md) 的状态机制，不把“已授予权限”当成永久可用能力。
“事实”对应已读官方资料；“工程推导”是实现与定位判断。核实于 2026-10-28，系统版本、target SDK、用户/profile、模块版本与产品策略分别核对。

## 1. 有效访问是多维状态，不是单个 grant 位

**事实**：危险权限采用运行时模型，预装应用同样受其约束；系统只为符合规定的默认能力等提供例外，不是所有系统应用自动预授予。[P1][]
hard-restricted 与 soft-restricted 权限还有安装方/角色等允许列表条件；用户同意不能独自覆盖这些平台限制。[P1][]

**工程推导**：分析一次敏感访问时，应组合以下事实，而非只截图 Settings 中的开关。

| 维度 | 要区分的状态 |
|---|---|
| 身份与作用域 | 实际 UID、用户/profile、包与归因链 |
| 权限 | 请求声明、授予状态、用户/策略固定标记与限制条件 |
| AppOps | 原始 mode、当前状态下求得的有效结果 |
| 生命周期 | 组件/进程、前后台、持续会话与临时授权期限 |
| 策略与数据 | 设备开关、用户限制、具体对象和数据粒度 |
| 透明性 | 实际访问归因、使用记录、指示器与用户可撤销入口 |

这些不是可直接照抄的服务端数据结构；应在目标权限与数据服务实现中找到真实所有者及检查点。

## 2. 授予、拒绝和撤销各自改变什么

**事实**：运行时申请由系统呈现决策，拒绝后能否再次显示请求取决于权限状态及版本规则；调试可检查 `USER_SET`、`USER_FIXED` 等标记。[P10][]
Android 11 起，位置、相机、麦克风等支持一次性授权，持续时间受活动可见性、前台服务及用户行为影响。[P10][]
Android 13 起的主动放弃权限 API 是异步流程，生效时会终止相关 UID 的进程；调用返回不能直接宣称权限已经撤销。[P10][]

```text
未授权 → 合法请求 → 系统决策 → 持续授权 / 临时授权 / 拒绝
                         ↓
               用户撤销、临时到期、自动重置或策略变化
                         ↓
                   重新计算可访问状态
```

上图是工程状态摘要；请求资格、对话框和授予组合由平台规则决定，不能新建一套私有流程代替。
**工程推导**：权限检查是当时的快照。异步工作、持续会话和进程恢复时应按数据提供方契约处理状态变化。
部分撤销会导致进程终止，不能依赖应用“收到一次通知后清理一切”；服务也须有客户端死亡与资源收尾路径。
权限组的 UI 汇总不一定等于单个权限位，不能只根据组开关判断一个特定 API 的授权。
测试要覆盖初始拒绝、受限重试、授予、使用中撤销和进程恢复，不用开发环境的强制 grant 代替用户流程。

## 3. AppOps 约束操作，并记录实际使用

**事实**：AppOps 不同 mode 有不同语义；`MODE_DEFAULT` 要走默认安全判断，`MODE_IGNORED` 与 `MODE_ERRORED` 的失败方式不同。[P2][]
`MODE_FOREGROUND` 是条件模式；raw 查询与历史预检 API 的结果不等于当前允许访问，实际 `noteOp`/`startOp` 按适用前后台状态求值。[P2][]
瞬时访问与持续访问的记录不同：持续操作应使用匹配的开始/结束 API，身份和归因参数须保持一致。[P2][]

**工程推导**：敏感数据提供方要在正确边界联合执行权限、AppOps 和具体对象策略；应用通常通过该提供方访问，不应靠自行记一条 op 绕过服务端授权。
不能把 raw mode 缓存成能力票据，也不能只因一次 `checkOp` 允许就无限期继续投递数据。
`MODE_ALLOWED` 仅说明该 op 判断允许，不证明跨用户、文件对象、其它权限或设备隐私开关也允许。
正确区分“拒绝”“降级/空结果”和基础设施错误，保持目标 API 的契约；把所有拒绝都吞成正常数据会误导调用方。
使用 `noteOp` 的真实访问记录不应被无目的轮询污染；持续会话失败、取消或客户端死亡时也要结束相应记录。

## 4. 前台、后台与定位权限

**事实**：Android 10 的三态定位区分拒绝、使用期间允许与始终允许；之后发布的请求流程和相关能力继续演进。[P3][]
后台定位提醒是透明性机制，可能延迟、限流或对特定访问不展示，不能作为一次定位是否发生的完备日志。[P7][]

**工程推导**：前台是平台定义的状态及具体权限判断，不是“进程还在运行”。前台服务也不应被无条件视为顶层可见活动。
后台授权、前台授权、精度选择、实际定位开关和调用 API 的粒度须分别确认，不能用“定位开关已开”概括全部条件。
系统升级后的权限迁移和应用 target SDK 变化可能改变请求路径；旧版三态对话框不是所有新版本的固定 UI。
对持续更新，观察转入后台、回到前台、用户切换和授权变化后的投递，而不只测试注册回调时的结果。

## 5. PermissionController 与角色

**事实**：PermissionController 管理权限 UI、授予/管理、使用追踪与 roles；其代码位置、打包形式和模块边界随发布变化。[P4][]
自动撤销未使用应用的运行时权限是相应版本的功能，默认启用条件及豁免须结合目标发布确认。[P4][]
角色是关联特定资格、权限和特权的系统名称；不同 role 对组件能力、用途及分配方有不同要求，不是任意可授予的权限包。[P5][]

**工程推导**：role 请求 → 资格校验 → 持有者变化 → 派生授权/默认行为更新，是应追踪的一组状态变化。
失去 role 后应重算相关能力，但不能盲删用户另行授予或其它策略仍要求的全部权限。
默认处理应用变化后，需要确认旧持有者、新持有者、每用户状态及数据服务是否一致；改一个包名资源未必完成迁移。
定制权限 UI 不能改变同意语义、抹去拒绝/撤销能力或绕过模块稳定接口；源码和运行中模块版本需一起定位。

## 6. 隐私指示器依赖正确归因和会话边界

**事实**：指示器通过 AppOps 使用记录及系统组件协作呈现访问；SystemUI 和 PermissionController 分别承担相应展示与使用信息职责。[P6][]
相机/麦克风与位置指示器的引入版本、active/recent 时间窗口和显示条件不同，不能固定成全平台共用的一组时长。[P6][]

**工程推导**：代理访问要保留合法调用者和 attribution；全部归到系统服务自身，会让用户无法理解谁实际使用数据。
没有指示器不自动证明没有访问，有指示器也不证明授权路径完全正确；应对照服务检查、数据交付及记录。
开始/结束记录与真实会话需一致，避免资源已关指示器仍常亮，或会话仍运行但记录提前结束。
数据不可用、全局开关变化及用户切换时，UI 应反映实际状态，不能因取不到使用信息而崩溃或展示旧用户的信息。

## 7. 受限读取不是“放进 priv-app 即解决”

**事实**：Android 10 收紧屏幕缓冲读取，单凭 privileged 身份不能继续获得相关静默捕获能力；无对应签名权限的路径应使用需要用户同意的 MediaProjection。[P8][]
不可重置设备标识符的读取也有特定权限、身份与例外条件，且旧 target SDK 不自动绕开系统版本的限制。[P9][]

**工程推导**：按实际 API 检查签名、允许列表、运营商/设备管理资格、target SDK 与返回契约，不泛化为“所有系统应用都能读”。
读不到时可能是预期拒绝、占位数据或不支持；不要用反射、私有文件或旁路服务恢复本应禁止的读取。
屏幕捕获同意不是永久后台授权；当前捕获范围、会话有效性和受保护内容还需按目标 MediaProjection/显示规则核实。

## 8. 权限故障的定位证据

| 现象 | 需要关联的证据 |
|---|---|
| grant 为真仍无数据 | 具体权限、AppOps 有效状态、用户与对象策略、开关 |
| 同前台可用、后台失败 | UID 状态转换、授予粒度、持续会话和目标 API 条件 |
| role 变化后行为残留 | 资格、旧/新持有者、派生授权和默认处理路径 |
| 指示器归因错误/常亮 | UID/包/attribution、开始结束、客户端死亡 |
| 升级后状态异常 | 迁移前后权限 flags、target SDK、PermissionController 版本 |
| 受限读取失败 | 实际调用 API、身份/例外条件、期望拒绝类型 |

**工程推导**：保留测试前后状态与真实调用结果；开发者强制授予、修改 AppOps 或清 flags 会改变实验条件，不能据其成功宣称标准授权流程正确。

## 已读官方来源

- [P1 Runtime permissions](https://source.android.com/docs/core/permissions/runtime_perms)：预装应用、限制条件、授予与撤销模型。
- [P2 AppOpsManager](https://developer.android.com/reference/android/app/AppOpsManager)：mode、前台求值、note/start/finish 与归因 API；重载及弃用条件按版本确认。
- [P3 Tristate location](https://source.android.com/docs/core/permissions/tristate-perms)：Android 10 定位三态及历史适用范围。
- [P4 PermissionController](https://source.android.com/docs/core/ota/modular-system/permissioncontroller)：权限逻辑、roles、auto-revoke 和模块演进。
- [P5 Android roles](https://source.android.com/docs/core/permissions/android-roles)：资格、用途与分配边界。
- [P6 Privacy indicators](https://source.android.com/docs/core/permissions/privacy-indicators)：记录、归因、展示和版本不同的时间窗口。
- [P7 Background location reminder](https://source.android.com/docs/core/permissions/background-location-access)：提醒与真实访问的区别。
- [P8 Restricted screen reading](https://source.android.com/docs/core/permissions/restricted-screen-reading)：特权/签名边界与用户同意。
- [P9 Immutable device IDs](https://source.android.com/docs/core/permissions/immutable-device-ids)：受限标识符、身份及版本条件。
- [P10 Request runtime permissions](https://developer.android.com/training/permissions/requesting)：拒绝 flags、一次授权、撤销与自动重置。

[P1]: https://source.android.com/docs/core/permissions/runtime_perms
[P2]: https://developer.android.com/reference/android/app/AppOpsManager
[P3]: https://source.android.com/docs/core/permissions/tristate-perms
[P4]: https://source.android.com/docs/core/ota/modular-system/permissioncontroller
[P5]: https://source.android.com/docs/core/permissions/android-roles
[P6]: https://source.android.com/docs/core/permissions/privacy-indicators
[P7]: https://source.android.com/docs/core/permissions/background-location-access
[P8]: https://source.android.com/docs/core/permissions/restricted-screen-reading
[P9]: https://source.android.com/docs/core/permissions/immutable-device-ids
[P10]: https://developer.android.com/training/permissions/requesting
