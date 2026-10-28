# DDD CQRS Architecture

CQRS (Command Query Responsibility Segregation) — read/write model separation, optional storage separation, independent Event Sourcing assessment, and event reliability.

本模块服从主 [DDD Skill](../../SKILL.md) 的任务范围和简化原则。CQRS、读写存储分离、Event Sourcing 和独立部署是不同决策，不构成统一成熟度阶梯。旧示例保留 `L1/L2/L3` 文件名以保持链接，但这些只是各篇历史标签；以实际模型、存储和一致性设计为准。

## When to Use This Skill

**Trigger keywords**: CQRS, 读写分离, Event Sourcing, 事件溯源, Command Bus, Query Model, 领域事件, domain event, 幂等, idempotency, eventual consistency, projection, materialized view

## Workflow

```
Step 1: 判断是否需要 CQRS → 确认读写模式是否显著分化
Step 2: 分别决定 → 是否分离模型 / 是否分离存储 / 是否采用 Event Sourcing
Step 3: 设计命令模型 → Command → Handler → 领域行为（按需产生领域事件）
Step 4: 设计查询模型 → Query → Handler → DTO
Step 5: 若有独立读模型 → 定义更新、延迟、恢复和必要的可靠投递策略
Step 6: 按现有架构集成 → 明确职责与依赖，不要求更换架构
```

## When to Use CQRS

### 适用场景
- **读写模式显著分化**: 写操作与读操作用不同数据结构和优化策略
- **独立优化需求**: 现有查询、索引和单模型优化仍无法满足读写需求时评估分离
- **复杂多视图**: 同一数据的查询形态与写入行为明显不同；仅有多个页面不足以证明需要 CQRS
- **审计追踪要求**: 独立比较审计日志与 Event Sourcing，审计需求本身不必引入 CQRS
- **能力与成本**: 只有采用异步投影时才需要相应的事件处理、延迟和恢复能力

### 独立决策
```
读写模型需要分离？       → 否：保持单模型；是：CQRS，可共享数据库
读存储需要独立优化？     → 否：共享表/视图；是：评估独立读库及同步成本
事件历史必须是事实源？   → 独立评估 Event Sourcing，可搭配或不搭配 CQRS
需要独立部署？           → 由发布、扩展和所有权需求决定，与以上决策分别评估
```

### 不适用场景
| 场景 | 替代方案 |
|------|---------|
| 简单 CRUD，读=写 | 单模型，不引入 CQRS |
| 原型/一次性项目 | 跳过 CQRS |
| 团队不具备异步投影运维能力 | 可先共享数据库，不默认引入异步事件 |
| 必须读取最新提交结果 | 优先同步查询或定义 read-your-writes 策略，评估异步投影是否适用 |

## CQRS Core Principles

| 维度 | 命令侧（Write） | 查询侧（Read） |
|------|----------------|----------------|
| 职责 | 处理状态变更，执行业务规则 | 返回数据视图，无业务逻辑 |
| 模型 | Command Model（命令对象+聚合根） | Query Model（DTO+物化视图） |
| 存储 | 按写入约束选择，可与查询共享 | 可直接查询共享表、视图或独立读库 |
| 一致性 | 按业务不变式确定事务边界 | 共享库可读已提交状态；异步投影需明确延迟与恢复 |
| 输出 | 用例结果；按需产生领域事件 | DTO / View Model |

## 实现选择与历史示例

### 模型分离（旧例标签 L1）
成本最低：仅代码层分离 Command/Query Service，共享数据库。适用于读写数据结构相同但逻辑分离的场景。
参考示例: `examples/06-order-l1-model-separation.md`

### 存储分离（旧例标签 L2）
中等成本：分离 Command DB 和 Query DB，通过领域事件同步。适用于读负载高、独立优化策略需求的场景。
参考示例: `examples/07-order-l2-db-separation.md`

### Event Sourcing（旧例标签 L3，独立于 CQRS）
以事件流作为权威事实源，通过重放重建状态，按需投影读模型。需要明确事件版本兼容、重放、快照和恢复成本；可直接评估，不要求先实施存储分离。单纯保留审计日志未必需要这种持久化方式。
参考示例: `examples/08-order-l3-event-sourcing.md`

## Event Lifecycle

```
领域行为 → 按需构建 DomainEvent → 持久化状态及必要的可靠发布记录 → 发布
                                        → 本地处理器 (同步)
                                        → MQ 外发 (异步, 跨服务)
```

### 发布策略
- **轮询发布（定时扫表）**: 延迟 1-5s, 低复杂度, 中小流量
- **CDC（Debezium binlog）**: 延迟 <100ms, 中复杂度, 高流量低延迟
- **事务提交回调**: 可触发本地处理或唤醒发布器；单靠内存回调无法保证崩溃后投递，不替代需要可靠投递时的 Outbox 或等效持久化机制

详细参考: `references/02-cqrs-events.md`

## 幂等设计

| 策略 | 开销 | 可靠性 | 场景 |
|------|:----:|:------:|------|
| **事件去重表** | 中 | ★★★ | 金融级关键事件 |
| **状态机守卫** | 低 | ★★★ | 状态驱动事件 |
| **Redis + TTL** | 低 | ★★☆ | 非关键通知 |
| **业务幂等** | 低 | ★★★ | 简单操作 |

详细参考（含代码示例）: `references/07-event-governance.md`

## 各架构 CQRS 集成模式

| 架构 | 集成点 | 目录结构 |
|------|--------|---------|
| **Layered** | Application 层 Command/Query Service 分离 | `app/service/command/` + `app/service/query/` |
| **Onion** | Core 层 Command/Query UseCase 接口 | `core/application/command/` + `core/application/query/` |
| **Hexagonal** | Port 层 Command Port + Query Port | `domain/port/command/` + `domain/port/query/` |
| **Clean** | UseCase 层 Command Interactor + Query Interactor | `usecase/interactor/command/` + `usecase/interactor/query/` |
| **COLA** | App 层 Command + Query 子模块 | `app/command/` + `app/query/` |

详细参考: `examples/04-multi-architecture-integration.md`

## Gotchas

- **把方案当升级阶梯**: 按需求独立选择模型分离、存储分离和事件持久化，不要求逐级实施
- **混淆存储边界**: 共享库时 Query 可以直接读共享表；已承诺独立读模型时，应明确读取写库的例外、权限及一致性语义
- **忘了事件幂等**: 消费者必须实现幂等（at-least-once 投递）
- **事件版本不兼容**: 修改事件结构必须向后兼容
- **投影延迟的交互处理**: 采用异步投影时按体验要求选择确认信息、read-your-writes、轮询或推送
- **过大的聚合**: 事件溯源聚合应保持小聚合原则

## FAQ

| 问题 | 回答 |
|------|------|
| CQRS 一定会引入最终一致性？ | 不会。是否有延迟由存储及投影更新方式决定，共享库模型分离可同步读取已提交数据 |
| Event Sourcing 和 CQRS 绑定？ | 否，可独立使用 |
| 何时需要 Outbox 模式？ | 需要可靠事件发布时，避免双写问题 |
| CQRS 和微服务关系？ | 正交，可在单体内部署或跨微服务 |
| 查询模型复杂到何种程度？ | 可跨聚合/服务组装，反范式化物化视图 |

## Rules

| 规则 | 说明 |
|------|------|
| Command 侧需验证权限 | 执行命令前必须鉴权 |
| 事件体不能含敏感数据 | 密码、PII 等不应出现在事件中 |
| 查询侧不能修改状态 | Query Handler/Service 不能有写操作 |
| 需要可靠外发时原子记录状态与待发布事件 | 采用 Outbox 或等效机制，避免双写丢失 |
| 按业务不变式定义一致性边界 | 通常保持小聚合；跨聚合事务或最终一致性应根据实际约束记录决策 |

## Skill Boundary

### ✅ 擅长处理
1. 读写模式显著分化的系统（报表 vs 交易）
2. 需要事件驱动架构的项目
3. CQRS 模型分离、可选的存储分离与独立的 Event Sourcing 取舍
4. 与 5 种 DDD 架构的集成模式
5. 领域事件全生命周期治理（发布/订阅/幂等/补偿）

### ⚠️ 需要条件
1. 理解现有模块职责与依赖约束，不要求从指定架构清单重新选型
2. 采用异步投影时，团队具备延迟、重试、恢复和重建能力
3. 业务场景确实需要读写分离（非简单 CRUD）

### ❌ 不该用（超出范围）
1. 简单 CRUD（读=写） → 不适用 CQRS
2. 原型/一次性项目 → 不应该使用 CQRS
3. 无法承担异步投影成本 → 优先共享库模型分离或保持单模型
4. 已使用 CQRS 框架（如 Axon） → 遵循现有框架约定，继续审查模型、契约和一致性，不重复搭建框架

## Security & Stability

- Code templates are educational — replace URLs/credentials with env vars.
- Command handlers must validate authorization. Never trust caller is authorized.
- Event payloads must not contain sensitive data — events are stored and replayed.
- 最小权限原则：Command API 和 Query API 应使用不同的访问权限控制

## Keywords

`CQRS`, `读写分离`, `Event Sourcing`, `事件溯源`, `Command Bus`, `Query Model`, `Command Model`, `领域事件`, `Domain Event`, `最终一致性`, `Eventual Consistency`, `Outbox Pattern`, `Transactional Outbox`, `Materialized View`, `Projection`, `Event Store`, `Idempotency`, `幂等`, `L1/L2/L3`, `Clean Architecture CQRS`, `Hexagonal CQRS`, `COLA CQRS`

## References

### Architecture CQRS Patterns
- `references/architecture/01-clean-ddd-hexagonal-cqrs.md` — CQRS & Domain Events：Commands, Queries, Read Models, Event Dispatcher, Outbox
- `references/02-cqrs-events.md` — CQRS 领域事件：事件分类、事件存储、投影策略、版本管理
- `references/03-cqrs-mindmap.md` — CQRS 思维导图：适用场景、实施策略
- `references/04-ddd4j-cqrs-mindmap.md` — CQRS 思维导图：核心理念、架构模式、组件

### Domain Events & Event Governance
- `references/07-event-governance.md` — 事件治理：Outbox DDL、幂等、重试/死信/补偿/对账
- `references/domain-events/01-domain-events-deep.md` — 领域事件深入：事件驱动设计原则
- `references/06-domain-vs-integration-events.md` — 领域事件 vs 集成事件：边界划分
- `references/08-partme-06-domain-events.md` — 领域事件实操：保险承保案例

## Examples

- `examples/06-order-l1-model-separation.md` — L1 模型分离完整示例
- `examples/07-order-l2-db-separation.md` — L2 数据库分离 + 事件同步
- `examples/08-order-l3-event-sourcing.md` — Event Sourcing 完整示例（历史文件名保留，不是 CQRS 第三级）
- `examples/04-multi-architecture-integration.md` — 5 种架构 CQRS 集成对比
- `examples/03-inventory-cqrs.md` — 库存 CQRS + 幂等策略实现
