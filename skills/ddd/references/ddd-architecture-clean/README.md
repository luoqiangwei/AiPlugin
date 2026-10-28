# DDD Architecture — Clean

> Clean Architecture by Robert C. Martin (Uncle Bob): UseCase-centric, strict dependency rule — source code dependencies must point only inward.

本模块是采用 Clean 组织方式时的参考，适用性与简化原则以 [DDD 主流程](../../SKILL.md) 为准。Clean、Onion、Hexagonal 的原则可以重叠，重点是清晰且一致的依赖规则；不因读取本模块而重组存量平台。下列 Spring/JPA/ArchUnit 示例只用于相应技术栈。

## Quick Start

直接说明你的需求，例如： "帮我建整洁架构项目骨架" / "订单模块实现 CreateOrder UseCase，从实体到控制器" / "检查项目依赖方向是否正确" / "从三层迁移到整洁架构，先迁订单"。

信息不足时我先给参考版本，再列出需要补充的具体信息。

## Workflow

### Step 1: 确认基础概念
确保团队对 DDD 实体、值对象、聚合根有一致理解。不清晰则先参考 `ddd-architecture-awesome`。

### Step 2: 定义 Enterprise Business Rules
识别聚合根 → 设计实体 + 值对象 → 实现业务规则 → 定义领域事件。参考 [01-core-entities](references/01-core-entities.md)、[order-entity example](examples/01-order-entity.md)

### Step 3: 定义 UseCase 端口
按调用方与用例契约定义内聚的 Input Port、需要的 Output Port 和数据边界，避免为每个类机械增加接口。参考 [02-usecase-ports](references/02-usecase-ports.md)

### Step 4: 实现 UseCase Interactor
编写 Interactor → 编排实体与端口调用 → 处理用例级流程和事务 → 按需要收集与发布领域事件。参考 [03-interactors](references/03-interactors.md)、[create-order example](examples/02-create-order-usecase.md)

### Step 5: 实现适配器层
Controller → Presenter → Repository Impl → Gateway Impl → DI 配置。参考 [04-adapters](references/04-adapters.md)、[05-framework-config](references/05-framework-config.md)

### Step 6: 验证与测试
Enterprise 单元测试 → UseCase 集成测试 → Adapter 集成测试 → ArchUnit 验证。参考 [06-dependency-rules](references/06-dependency-rules.md)、[07-testing-strategy](references/07-testing-strategy.md)

## When to Use / When NOT to

| ✅ 适用 | ❌ 不适用 |
|----------|-----------|
| 企业级核心系统（订单、支付、库存） | 临时脚本、小工具 |
| 业务规则独立于交付机制 | 前端重后端轻的简单 CRUD |
| 需要清晰的用例边界和模块依赖 | 抽象成本超过当前收益 |
| 微服务内部标准化架构 | 简单三层架构已足够 |
| UseCase 驱动的复杂业务编排 | 无复杂业务逻辑的管理后台 |

## Boundary

| 类别 | 能力 | 说明 |
|------|------|------|
| ✅ 擅长 | 依赖边界明确的业务系统 | 根据测试、变化和协作需要决定物理隔离 |
| ✅ 擅长 | UseCase 驱动设计 | 每个用例独立 Interactor + Port |
| ✅ 擅长 | 依赖规则自动化检查 | ArchUnit 全自动验证分层合规 |
| ✅ 擅长 | 多语言落地 | Java/Go/TypeScript/C# 均可实现 |
| ⚠️ 需条件 | 团队理解 Interactor 模式 | 否则学习成本高，需培训 |
| ⚠️ 需条件 | 抽象具有实际收益 | 小项目也可轻量使用，不按人数决定架构 |
| ⚠️ 需条件 | 业务规则适合领域建模 | Clean 本身不要求引入全部 DDD 战术模式 |
| ❌ 超出范围 | 简单 CRUD 项目 | 用 `ddd-architecture-layered` |
| 相关参考 | COLA 工程约定 | 按需读取 `ddd-architecture-cola`，不改变已选依赖规则 |
| 相关参考 | 同心层的表达 | 可参考 `ddd-architecture-onion` 的重叠原则 |
| 相关参考 | 端口适配器边界 | 可参考 `ddd-architecture-hexagonal`，避免重复接口层 |

## 受众说明

| 用户类型 | 使用方式 |
|---------|---------|
| **后端架构师 / 技术负责人** | 直接使用，选型并按照 Workflow 6 步落地 |
| **Java 开发者** | 参考 examples/ 代码模板，按步骤实现 UseCase |
| **DDD 初学者** | 先读 `ddd-architecture-awesome` 了解概念，再回来看本 Skill |
| **多语言团队（Go/TypeScript/C#）** | 架构规则通用，参考 references/ 中语言无关的部分 |

定制化：触发时说明你的技术栈（Java/Go/TS）、模块名称（如订单/支付），我会针对性地生成代码模板。

## 核心架构

```
Enterprise ← UseCase ← Adapter ← Framework
```

详细原理（四层结构、架构对比、数据流转）参考 [architecture-principles](references/09-architecture-principles.md)。目录结构参考 [directory-structure](references/12-directory-structure.md)。

## 开发规范

| 规范 | 说明 | 违规示例 |
|------|------|---------|
| Entity 零框架依赖 | 不可 import Spring/JPA/Jackson | `@Entity` 出现在 `core/entity/` |
| 端口按契约内聚 | 独立变化的调用方或用例分离，简单模块可直接调用用例 | 为所有用例添加无差别大接口或重复抽象 |
| Interactor 编排用例 | 可包含流程、授权和错误分支；领域不变式由领域对象负责 | 用例复制领域状态规则，出现不一致行为 |
| Output Port 在 UseCase 定义 | Repository 接口定义在 usecase 层 | Adapter 定义 Repository 接口 |
| 数据转换在 Adapter 层 | Controller DTO 不可穿越到 UseCase | `@RequestBody` DTO 直接传入 Interactor |
| 事务覆盖用例一致性边界 | 根据用例决定边界，由事务端口、装饰器或项目已有声明式事务实现 | 每次 Repository 调用单独提交，破坏用例原子性 |

详细规范请参考 [references/06-dependency-rules.md](references/06-dependency-rules.md)。

## Gotchas

| # | 陷阱 | 现象 | 正确做法 |
|---|------|------|---------|
| 1 | 用例复制领域规则 | 多处重复决定聚合是否合法转换 | 将领域不变式集中在 Entity/Domain Service，保留用例级编排 |
| 2 | Input Port 过大 | 不相关用例被同一接口绑定 | 按调用方与契约拆分，不机械要求一用例一接口 |
| 3 | Controller DTO 穿越层 | 框架 DTO 传入 UseCase 层 | Adapter 层完成 DTO ↔ Domain 转换 |
| 4 | Entity 上有 @Entity 注解 | JPA 注解泄露到 Enterprise 层 | 在 Adapter 层创建独立的 JPA Entity |
| 5 | Interactor 直接调 Adapter | 跳过 Output Port 调用实现类 | 通过 Output Port 接口调用 |
| 6 | Output Port 放在 Adapter 层 | UseCase 依赖 Adapter 包 | Output Port 接口定义在 UseCase 层 |
| 7 | UseCase 返回 Entity 对象 | Interactor 返回 `Order` 而非 DTO | 返回 UseCase 专属 Output DTO |
| 8 | 过度设计简单查询 | 读操作也走完整 Input→Interactor→Output | 简单查询直接走 Repository |
| 9 | 领域规则泄漏到 Adapter | 协议入口独立决定领域状态转换是否合法 | 领域规则交给领域模型，Adapter 保留协议、权限及映射分支 |
| 10 | 依赖边界缺少验证 | 模块反向依赖无法发现 | 按项目技术栈检查依赖，JVM 可使用 ArchUnit |
| 11 | 领域对象可变 | ValueObject 有 setter 方法 | 所有值对象不可变 (record/final) |
| 12 | UseCase 粒度不当 | 不相关业务目标与事务混在同一流程 | 按可验收的用例职责拆分，行数只用于定位线索 |
| 13 | 遗漏所需领域事件 | 已约定的业务事实没有通知消费者 | 按业务语义设计事件，无通知需求的状态变更无需发布事件 |
| 14 | 事务边界碎片化 | 多次 Repository 写入各自提交导致部分成功 | 由用例确定一致性边界；在外层装饰器或项目认可的应用层事务中实现 |
| 15 | 无效对象可被构造 | 构造入口绕过不变式 | 在构造函数或静态工厂验证约束，按实际需要选择 |

## FAQ

| # | 问题 | 回答 |
|---|------|------|
| 1 | Clean Architecture 和六边形架构有什么区别？ | 整洁架构以 UseCase 为组织核心，强调四层严格隔离；六边形以 Port/Adapter 为抽象，强调驱动/被驱动端口对称性。核心目标一致：内层不依赖外层。 |
| 2 | 什么时候用 Interactor vs Domain Service？ | Interactor 在 UseCase 层做编排（调 Entity + 调 Port）；Domain Service 在 Enterprise 层封装跨实体的业务规则（如 PricingService）。 |
| 3 | Service 在哪里写业务逻辑？ | Entity/DomainService 封装领域规则，Interactor 处理用例级流程、端口协调与异常；不能用是否出现 if/else 判断违规。 |
| 4 | 每个 UseCase 都要有独立的 Input Port 吗？ | 不必。按调用方和变化边界定义内聚契约，避免大而不相关的接口，也避免纯转发接口。 |
| 5 | 一个 UseCase 有多个输出怎么办？ | 每个输出独立为一个 Output Port。如 OrderRepository 为持久化，EventPublisher 为事件，PaymentGateway 为支付。 |
| 6 | Repository 接口放哪一层？ | 按接口所表达的领域或用例契约确定归属；本模块的示例放在 UseCase 层。实现层依赖接口层，不让内层依赖具体存储实现。 |
| 7 | 简单查询也走 UseCase 层吗？ | 不。纯读操作可以直接调用 Repository（查询不改变状态）。写操作必须走 UseCase。 |
| 8 | 如何组织多个 UseCase？ | 按业务聚合组织：`order/usecase/` 下放所有 Order 相关的 CreateOrder/PayOrder/CancelOrder。 |
| 9 | Interactor 中如何做事务？ | 用例定义原子性需求，外层事务装饰器可包裹调用；项目采用应用层声明式事务时遵循既有约定，领域对象不承担框架事务管理。 |
| 10 | JPA Entity 和 Domain Entity 要分开吗？ | 要。JPA Entity（@Entity）在 Adapter 层，Domain Entity（纯 POJO）在 Enterprise 层。通过 Converter 转换。 |
| 11 | 项目从三层架构迁移要多久？ | 根据耦合、测试基线和交付范围估计；先迁一个代表性用例验证收益和成本，不按项目大小承诺固定周期。 |
| 12 | 如何保证依赖规则不被破坏？ | 在 Framework 模块中写 ArchUnit 测试（参考 examples/04-archunit-test.md），CI 中每次提交自动检查。 |
| 13 | 值对象和实体的区别？ | 值对象不可变、无 ID、按属性相等（如 Money）；实体可变、有唯一 ID、按 ID 相等（如 Order）。 |
| 14 | 领域事件是同步还是异步发布？ | 按一致性和可靠性需求选择。外部可靠通知需避免提交前发布或提交后丢失；采用事务 Outbox 等机制时验证重复投递与幂等，不默认引入消息队列。 |
| 15 | 适配器层可以有多个实现吗？ | 可以。一个 Output Port 可以有多个 Adapter 实现：JPA/MyBatis/InMemory，通过 Spring Profile 切换。 |

## Keywords

Clean Architecture, 整洁架构, Robert C. Martin, Uncle Bob, Enterprise Business Rules, Use Case, Interactor, Input Port, Output Port, Interface Adapter, Dependency Rule, 依赖倒置, 接口隔离, DDD, 领域驱动设计, 分层架构, 严格分层, 用例驱动, 领域模型, 实体, 值对象, 聚合根, 领域事件, ArchUnit, 依赖规则检查

## References
### Internal

| 文件 | 内容 |
|------|------|
| [references/architecture-principles.md](references/09-architecture-principles.md) | 四层结构、依赖规则、架构对比、数据流转、目录结构 |
| [references/01-core-entities.md](references/01-core-entities.md) | Enterprise 层实体、值对象、领域事件、异常模板与测试 |
| [references/02-usecase-ports.md](references/02-usecase-ports.md) | Input/Output Port 定义、DTO 设计、端口设计规则 |
| [references/03-interactors.md](references/03-interactors.md) | Interactor 实现模板、复杂编排、查询 Interactor、测试 |
| [references/04-adapters.md](references/04-adapters.md) | Controller、Repository Impl、Gateway 适配器实现 |
| [references/05-framework-config.md](references/05-framework-config.md) | Spring DI 配置、Security、Persistence、多 Profile |
| [references/06-dependency-rules.md](references/06-dependency-rules.md) | 依赖规则矩阵、ArchUnit 全量测试集、CI 集成 |
| [references/07-testing-strategy.md](references/07-testing-strategy.md) | 分层测试策略、Test Doubles、覆盖率目标 |
| [references/08-migration-guide.md](references/08-migration-guide.md) | 三层→整洁架构迁移指南、Strangler Fig 模式 |
| [examples/01-order-entity.md](examples/01-order-entity.md) | 完整 Order 实体代码 + 状态机 + 单元测试 |
| [examples/02-create-order-usecase.md](examples/02-create-order-usecase.md) | 完整 CreateOrder UseCase 实现 + 测试 + Test Doubles |
| [examples/03-repository-implementation.md](examples/03-repository-implementation.md) | Repository Adapter JPA 实现 + 集成测试 |
| [examples/04-archunit-test.md](examples/04-archunit-test.md) | 完整 ArchUnit 依赖规则测试套件 |
| [examples/05-domain-event-handling.md](examples/05-domain-event-handling.md) | 领域事件定义、发布、消费完整实现 |
| [examples/06-monolith-simple.md](examples/06-monolith-simple.md) | 单体 Clean 简单版：单模块包级四层，目录树+依赖方向+ArchUnit |
| [examples/07-monolith-complex.md](examples/07-monolith-complex.md) | 单体 Clean 复杂版：多聚合+多 Interactor，共享内核+领域隔离 |
| [examples/08-monolith-multi-module.md](examples/08-monolith-multi-module.md) | 单体 Clean 多模块版：Maven 模块级分层，编译期强制依赖方向 |
| [examples/09-microservice-simple.md](examples/09-microservice-simple.md) | 微服务 Clean 简单版：包级四层+事件总线+Kafka 适配器 |
| [examples/10-microservice-complex.md](examples/10-microservice-complex.md) | 微服务 Clean 复杂版：CQRS + Saga + Outbox + 多子域 |
| [examples/11-microservice-multi-module.md](examples/11-microservice-multi-module.md) | 微服务 Clean 多模块版：6 模块+API 契约独立发布 |
| [examples/12-microservice-complex-multi.md](examples/12-microservice-complex-multi.md) | 微服务 Clean 复杂多模块：8 模块+全模式矩阵+子域编排 |

### External

- [The Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html) — Robert C. Martin (2012)
- [Clean Architecture: A Craftsman's Guide](https://www.oreilly.com/library/view/clean-architecture-a/9780134494272/) — Robert C. Martin (2017)
- [Domain-Driven Design: The Blue Book](https://www.domainlanguage.com/ddd/blue-book/) — Eric Evans (2003)
- [Get Your Hands Dirty on Clean Architecture](https://reflectoring.io/book/) — Tom Hombergs
- [thombergs/buckpal](https://github.com/thombergs/buckpal) — Java Reference Implementation
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/) — Alistair Cockburn
## Security & Stability

- 所有代码模板为教育用途。生产环境请用环境变量替换占位凭证。
- 依赖规则可减少领域与 I/O 实现的耦合，但不代替权限检查、输入验证或安全边界测试。
- Interactor 模式确保每个 UseCase 可独立测试，无需框架或数据库依赖。
- 不包含可执行脚本。本 Skill 仅提供架构指导和代码生成模式。
