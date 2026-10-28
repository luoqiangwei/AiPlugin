# 兼容性、稳定接口与模块化发布

真实设备环境、CTS-V/ITS、音频/传感器/SE 等测量与结果边界见[兼容性设备验证](compatibility-device-verification.md)。

用于系统定制、平台升级、HAL 演进及发布判断。兼容性描述多个实现/版本是否仍满足契约，不能缩减为“能编译”“能启动”或“某套测试全绿”。
“事实”对应文末已读资料；“工程推导”用于选择实现和验证边界。资料核实于 2026-10-28，目标发布的 CDD、接口及测试版本具有优先适用范围。

## 1. CDD、源码与测试分别提供什么

**事实**：CDD 按 Android 发布列出兼容要求；官方明确没有测试套件可以穷尽所有兼容性，因此通过 CTS 不能替代 CDD 的全部要求。[C1][]
兼容计划要求实现满足相应 CDD 并通过 CTS；硬件、功能、设备形态和版本等条件影响具体要求的适用范围。[C1][][C2][]

**工程推导**：先固定设备形态、首次出厂版本、当前系统版本、vendor/内核版本和声明的能力，再查对应条款。
当前 SDK、应用 target SDK、设备 launch level 与 HAL/FCM 版本不是同一坐标，不能通过修改一个版本号消除其它义务。
源码说明实际实现，规范说明必须满足的行为；已有代码不自动构成豁免，最新概览也不能倒灌旧发布。
功能声明会影响消费者与测试发现，不能为绕过失败简单隐藏本应具备的能力或伪报硬件属性。

| 依据 | 主要回答 | 不能独立证明 |
|---|---|---|
| 目标 CDD/规范 | 哪些行为和能力必须满足 | 当前实现已经满足 |
| 目标源码和配置 | 代码实际怎样运行 | 所有现有行为都符合规范 |
| 自动测试 | 被执行条件下的断言结果 | 未覆盖能力和全部设备组合正确 |
| 设备/人工验证 | 特定硬件和用户可见行为 | 所有版本与所有更新组合兼容 |

## 2. CTS、CTS-V、平台回归与 VTS

**事实**：CTS 包含 API 签名和行为、权限、资源等兼容检查；CTS Verifier 包含需要人工执行的测试。[C3][]
平台测试可以依赖实现细节和特权环境，用于开发回归；CTS 与平台测试不互斥。[C4][]
VTS 主要测试 HAL 和 kernel，包括相应 native、内核及 host 驱动的用例。[C5][]

**工程推导**：对公开行为改变，要看是否违反既有应用预期；对服务内部修复，要增加能触发原根因的平台回归；对 HAL/kernel 改变，再选择相应 VTS/子系统测试。
不默认每个补丁都跑完整 CTS/VTS，但发布要求也不能仅由少量本地回归替代。
“测试通过”需要区分实际执行、跳过、未找到测试、环境失败和功能失败；总命令成功不表示每个预期模块都运行。
缺陷修复若只能看到成功日志，应补结果断言或可复现行为证据；无 crash 不能证明权限、数据、性能及升级语义正确。

## 3. VINTF 是双方能力与需求的匹配

**事实**：device manifest 描述设备向 framework 提供什么；framework compatibility matrix 描述 framework 需要什么。
framework manifest 与 device compatibility matrix 则描述相反方向的提供和需求；两组都需匹配。[C6][]
device manifest 可合并 vendor、ODM 及相关 fragments，实际生成结果不一定等于某一个源 XML 文件。[C7][]
匹配涉及版本、实例与 FCM 等规则，并在构建、OTA、启动及相关兼容测试阶段使用。[C8][]

**工程推导**：修改 HAL 声明时应同时核对实现注册、客户端期望、实际合并清单和目标矩阵。
manifest 记录的“已提供”必须对应真实可用服务；改 XML 并不会生成缺失实现。
实例名、服务版本与消费者发现方式不一致时，服务运行正常也可能无法被合法发现。
FCM 不是一个“越高越兼容”的数字；随意增加 target-level 或删矩阵条目可能改变整个接口义务。
`optional`、版本范围和 fragment 合并等规则在不同发布可能变化，使用目标 `libvintf` 及对应文档验证，不照搬旧 XML 模板。

## 4. 稳定接口需要行为兼容

**工程推导**：接口兼容至少区分源码、二进制、传输格式、行为和更新兼容。
方法签名没变，默认值、错误映射、权限、回调顺序或超时含义改变，仍可能破坏使用者。
Stable AIDL 保护的接口演进范围见 [architecture-ipc.md](architecture-ipc.md)；内核 KMI 的受限范围见 [kernel-native.md](kernel-native.md)。
它们不能替代持久化 schema、应用公共 API、native 库 ABI 或实际硬件行为的兼容验证。

| 组合 | 应解释的行为 |
|---|---|
| 旧客户端 → 新服务 | 原有调用、权限、结果与错误仍可解释 |
| 新客户端 → 旧服务 | 新方法/能力缺失时明确降级或拒绝 |
| 部分模块更新 | 稳定边界之外不偷用新内部实现 |
| 更新失败或回退 | 数据、密钥与接口版本能否恢复或安全拒绝 |

表中组合按产品实际支持范围选择；不支持的组合应明确拒绝，不靠未定义行为“碰巧可用”。

## 5. Mainline、APEX 与 APK 不能等同

**事实**：Mainline 将部分系统组件模块化，采用 APK 或 APEX，可经 Google Play 系统更新机制或合作方 OTA 分发。[C9][]
APEX 是承载较底层系统模块的容器与安装机制，并不是所有 APEX 都自动属于某一 Mainline 发布集合。[C9][][C10][]
APEX 具有版本、验证和激活过程，常见 staged 更新在后续启动激活；具体模块是否支持其它模式应查目标规则。[C10][]

**工程推导**：模块内的编译依赖不等于模块外承诺的稳定 API。独立发布需要限制跨边界依赖，并确认新旧模块组合。
模块包已安装、已验证、已激活和当前进程加载新实现是不同状态；诊断时核对真正生效的版本。
更新代码可回滚不代表数据 schema、缓存、密钥或外部副作用自动回滚，必须单独设计恢复语义。
模块包签名、APEX payload 信任及整机镜像签名各有配置，不能混用“签名正确”概括所有验证。
Mainline 模块名单、支持周期及提供能力会演进，不在知识文件中固定“最新全部模块”或假设只看 SDK_INT 就能识别所有能力。

## 6. AOSP、Android 兼容与 GMS 的边界

**事实**：AOSP 可被下载和修改；达到 Android 兼容后，可以考虑 Google Play/GMS 许可及相应商标使用，兼容性本身不授予这些许可。[C2][]
Mainline 文档还区分 Google 签名的模块与 AOSP 签名的包配置，不能假设非 GMS 系统具有相同更新来源。[C9][]

**工程推导**：架构设计应明确依赖的是 AOSP 能力、公开 Android API，还是另需提供方授权与服务的组件。
不能把某个 GMS 设备上可用的云服务、认证或更新机制当成纯 AOSP 固有能力。
闭源接口、授权流程和额外验收要求若未提供，不凭通用文档猜测；将其作为产品依赖单独说明。

## 7. 兼容失败的定位证据

| 失败 | 先核对 | 避免的“修复” |
|---|---|---|
| CTS API/行为 | 测试版本、实际 API、应用可见行为 | 改测试期望或隐藏本应支持的能力 |
| VINTF 不匹配 | 双方清单/矩阵、实例、版本、合并产物 | 只删 required 项而不解释契约 |
| VTS HAL 失败 | 实例、调用错误、硬件状态、接口行为 | 把注册成功当作功能通过 |
| 模块更新失效 | 签名、安装/激活、依赖与运行版本 | 只替换文件而不核对更新语义 |
| 回退后数据失效 | schema、版本绑定、恢复边界 | 伪报版本或忽略迁移失败 |

**工程推导**：一个合格结论应说明违反哪条契约、什么组合触发、补丁如何恢复，并保留未执行检查的范围。
临时为工程实验选择较窄验收不等于可宣称整机兼容；是否达到发布标准须按完整发布要求判断。

## 已读官方来源

- [C1 CDD](https://source.android.com/docs/compatibility/cdd)：按发布的要求与测试不能穷尽的边界。
- [C2 Android 兼容计划](https://source.android.com/docs/compatibility/overview)：兼容要求、AOSP 与 GMS 许可关系。
- [C3 CTS](https://source.android.com/docs/compatibility/cts)：兼容范围、自动测试及 CTS Verifier。
- [C4 平台测试](https://source.android.com/docs/core/tests)：CTS 与实现回归的职责区别。
- [C5 VTS](https://source.android.com/docs/core/tests/vts)：HAL/kernel 验证和测试组成。
- [C6 VINTF](https://source.android.com/docs/core/architecture/vintf)：双方提供/需求模型。
- [C7 VINTF manifests](https://source.android.com/docs/core/architecture/vintf/objects)：vendor/ODM/fragments 与实际清单。
- [C8 VINTF matching rules](https://source.android.com/docs/core/architecture/vintf/match-rules)：版本、实例及 FCM 匹配，规则随发布核对。
- [C9 Mainline](https://source.android.com/docs/core/ota/modular-system)：独立模块、更新渠道及包集合。
- [C10 APEX](https://source.android.com/docs/core/ota/apex)：容器、验证、安装与激活机制。

[C1]: https://source.android.com/docs/compatibility/cdd
[C2]: https://source.android.com/docs/compatibility/overview
[C3]: https://source.android.com/docs/compatibility/cts
[C4]: https://source.android.com/docs/core/tests
[C5]: https://source.android.com/docs/core/tests/vts
[C6]: https://source.android.com/docs/core/architecture/vintf
[C7]: https://source.android.com/docs/core/architecture/vintf/objects
[C8]: https://source.android.com/docs/core/architecture/vintf/match-rules
[C9]: https://source.android.com/docs/core/ota/modular-system
[C10]: https://source.android.com/docs/core/ota/apex
