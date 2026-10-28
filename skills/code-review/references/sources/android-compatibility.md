# Android 兼容性规则溯源

下列官方正文均于 **2026-10-27** 实际打开读取。这里只归档采用的规则与边界，不是执行 Review 的前置链接目录。
本地专项为原创审查步骤；建议的负向输入、状态断言和矩阵是由契约推导的回归设计，不宣称是官方现成测试。
动态网页与具体发布分支可能不同；执行时记录目标版本，并到对应 checkout 确认 API、测试配置、模块和工具帮助。

## CDD 与兼容性判定

[Android Compatibility Definition Document](https://source.android.com/docs/compatibility/cdd)

- 已读：CDD 的职责、逐版本入口，以及测试不可能穷尽所有兼容要求的解释。
- 采用：先选目标 Android 版本的 CDD，再评价测试证据；CTS 通过不能代替全部兼容性审查。
- 边界：入口页面指向的当前版本不自动适用旧分支，不能用“最新 CDD”给任意旧设备增加要求。

[Android 16 Compatibility Definition](https://source.android.com/docs/compatibility/16/android-16-cdd)

- 已读：3.5 API Behavioral Compatibility、3.6 API Namespaces、9.5 Multi-User Support，以及设备 feature 条件的正文。
- 采用：签名以外继续查行为、权限语义与设备能力声明；支持多用户时核对数据隔离与其明确例外。
- 边界：以 Android 16 作版本化核验实例，不将该版本的章节条款、profile 例外或具体条件外推到所有发布版。
- 转化：新旧客户端、非法参数、拒绝权限、跨用户和 feature 缺席是本地提出的区分性回归，不冒充完整 CDD 合规清单。

## CTS 能力与结果边界

[Compatibility Test Suite overview](https://source.android.com/docs/compatibility/cts)

- 已读：CTS/Tradefed、自动测试、CTS Verifier、模块/计划、API 签名与行为测试覆盖说明。
- 采用：区分 API signature、运行行为与需人工观察的能力，读取真实断言后再声称覆盖。
- 边界：该页没有保证每个安全路径均已测试；单次通过不能推出不存在漏洞。

## 真实目标与调度规则

[Run tests (Atest)](https://source.android.com/docs/core/tests/development/atest)

- 已读：环境准备、模块/类/方法/路径选择、dry-run、TEST_MAPPING 与 host 选项。
- 采用：从目标分支的构建文件与测试源码取得实际标识，再用 dry-run 核对选择；执行和构建分别报告。
- 边界：dry-run 不是运行通过，host 运行也不能把需要设备的测试变成无设备测试。
- 工具版本：子目录展开等选项以分支 `atest --help` 为准，不将网页范例目标当项目必有模块。

[Test mapping](https://source.android.com/docs/core/tests/development/test-mapping)

- 已读：presubmit/postsubmit、imports、options、file_patterns、suite 构建属性、当前目录与祖先规则。
- 采用：同时审测试内容与是否被调度，核对路径过滤和 imports；TEST_MAPPING 名称使用真实模块/集成配置。
- 边界：网页新 schema/导入能力不保证旧分支支持；调度规则本身也不证明断言捕获本次风险。
- 版本差异：该页与 Atest 页对子目录选项写法存在差别，专项要求查分支帮助，未固定一种写法为通用事实。

## vendor 边界与 GSI

[Vendor Test Suite and infrastructure](https://source.android.com/docs/core/tests/vts)

- 已读：VTS 对 HAL/kernel 的范围、设备侧测试与 host harness，以及实例遍历示例。
- 采用：HAL/kernel/vendor 问题优先定位对应 VTS 与实现测试；不以 CTS 全绿替代接口专项证据。
- 边界：VTS 成功不能外推出 App 全部行为或业务授权正确。

[Generic system images](https://source.android.com/docs/core/tests/vts/gsi)

- 已读：参考 GSI 与 vendor 接口测试关系、CTS-on-GSI 的作用和随版本变化的 GSI 说明。
- 采用：仅在 vendor 独立兼容边界需要时安排 CTS-on-GSI，记录参考 system 与 vendor 的具体组合。
- 边界：不复制页面历史构建目标、刷机/解锁命令；GSI 测试不等同 OEM 完整镜像端到端验证。

## 稳定接口与行为门控

[Stable AIDL](https://source.android.com/docs/core/architecture/aidl/stable-aidl)

- 已读：structured/stable 区分、接口版本与冻结、默认值、构建跟踪 API/ABI 的范围。
- 采用：核对真实稳定承诺、冻结内容与新增字段默认语义，补充真实消费者的旧新组合。
- 边界：普通手写 Parcelable 不能自动获得 Stable AIDL 的跨版本保证；编译检查不能证明业务默认值正确。

[AIDL for HALs](https://source.android.com/docs/core/architecture/aidl/aidl-hals)

- 已读：稳定 HAL、VINTF、注册实例、HAL 策略与 Tests for HALs。
- 采用：先核对 manifest/实例与实际接口，再找本分支 HAL/VINTF 测试；检查返回错误与未知方法降级。
- 边界：文档中的示例目标必须先在目标 checkout 核实，不能直接作为所有产品的测试清单。

[Compatibility framework tools](https://developer.android.com/guide/app-compatibility/test-debug)

- 已读：按 change 隔离行为、targetSdk 默认门控、override/reset 和可切换限制。
- 采用：边界 targetSdk 客户端与默认发布配置都要测；隔离测试后恢复 override。
- 边界：并非所有变化都可切换，关闭门控不是发布修复；具体 change 及阈值从目标版本取得。

核验范围仅为上述正文；未对当前被审产品运行 CTS/VTS、验证认证状态或检查任何厂商镜像。
