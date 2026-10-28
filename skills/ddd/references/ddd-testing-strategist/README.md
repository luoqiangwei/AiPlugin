# DDD Testing Strategist
DDD testing strategy — from value object unit tests to end-to-end validation across all DDD architectures. Covers the DDD test pyramid, layer-specific test patterns, mock strategies by architecture, Test-Driven Domain Design (TDDD), CI/CD pipeline integration, and N+1 query detection.

适用范围与完成定义遵循 [DDD 主流程](../../SKILL.md)。按改动风险和实际技术栈选择测试，以下 JVM 示例及比例仅供参考；无数据库、Repository 或事件机制时跳过对应项。

## Workflow
```
用户输入 → 场景分类 → 输出测试策略 + 代码模板

Step 1: 按用户问题场景分类（金字塔/AR/Repository/Mock/CQRS/TDDD/CI-CD/覆盖率）
Step 2: 检查项目已有测试命令与设施，再从 references 按需获取对应测试模板
Step 3: 按架构类型调整 Mock 策略
Step 4: 输出风险对应的验证方案；要求实现时运行相关测试并报告结果，覆盖率目标按项目约定选择
```
什么时候用：用户询问 DDD 测试策略、聚合根测试、Repository 测试、Mock 策略、CQRS 测试、TDDD、CI/CD 测试集成时触发。
## Boundary
### ✅ 擅长处理
1. DDD 测试组合：核心规则单元测试、接口和存储集成测试、关键端到端验证与依赖检查
2. 各层测试策略：Value Object / Aggregate Root / Domain Service / Repository / Application / Adapter
3. 按架构类型差异化测试（Layered / Hexagonal / Clean / COLA / CQRS / Event Sourcing）
4. 测试驱动领域设计（TDDD）方法论
5. Mock 策略选择（Mock Ports / Capture Events / Real DB）
6. CI/CD 三阶段流水线 + N+1 查询检测 + ArchUnit 架构测试
7. 测试覆盖率目标设定 + 分支覆盖率检查
### ⚠️ 需要条件
1. 已有 DDD 项目代码或正在设计领域模型
2. 使用项目已有测试框架；JUnit / Mockito / Spring Test / Testcontainers 是 JVM 项目的选项
3. 理解 DDD 战术模式（Entity / VO / Aggregate / Repository / Domain Event）
### ❌ 超出范围（不适用场景）
1. 非 DDD 项目测试 — 标准测试框架（JUnit / pytest / Jest）
2. 纯前端测试 — Cypress / Playwright / Vitest
3. 性能 / 负载 / 安全测试 — JMeter / k6 / OWASP ZAP
4. 语言特定测试教程 — 概念和模式语言无关
5. 非 DDD 项目的 CI/CD 配置

## Audience

This skill is designed for: **Backend developers** (implementing DDD architectures), **Software architects** (evaluating and selecting patterns), **Tech leads** (reviewing team implementations), and **DDD beginners** (learning domain-driven design fundamentals).

## Rules

1. Prioritize critical invariants, state transitions and failure paths; do not enforce a fixed test-count ratio.
2. Exercise the real domain behavior under test. Use test doubles at external boundaries when isolation is useful; do not mock away the rule being verified.
3. Verify storage adapters against the actual storage mechanism. Database integrations need a representative real database; Testcontainers is optional. In-memory, file-backed and platform storage implementations need their own contract and persistence tests.
4. Event Sourcing projects must verify event replay and historical event compatibility; test projections when used.
5. Check agreed architecture boundaries using stack-appropriate tools; use ArchUnit where suitable for JVM projects.

## DDD 测试金字塔
以便宜、稳定的规则测试覆盖核心行为，再补真实边界与端到端验证。下面是组织示意，项目无需满足固定比例：
```
         ╱           E2E Tests           ╲
        ╱──────── API Integration ────────╲
       ╱────── Storage Integration ─────────╲
      ╱─────── Application Service ─────────╲
     ╱──────── Domain Service Tests ──────────╲
    ╱────────── Aggregate Root Tests ───────────╲
   ╱──────────── Value Object Tests ──────────────╲
```
## 各层测试策略
### ① Value Object 测试（纯函数）
```java
@Test void money_should_prevent_negative_amount() {
    assertThrows(IllegalArgumentException.class, () -> new Money(-1.0, "CNY")); }
@Test void money_add_should_sum_same_currency() {
    assertEquals(new Money(30.0, "CNY"), new Money(10.0, "CNY").add(new Money(20.0, "CNY"))); }
```
覆盖：构造验证、运算逻辑、等值比较、不变式。
### ② Aggregate Root 测试（核心业务逻辑）
```java
class OrderPayTest {
    @Test void pay_changes_status_to_paid_when_draft() { ... }
    @Test void pay_emits_orderPaidEvent() { ... }
    @Test void pay_fails_when_already_paid() { ... }
    @Test void pay_fails_when_cancelled() { ... } }
```
覆盖：每个状态转移独立测试类 → happy path + 边界条件 + 不变量 + 事件。
### ③ Domain Service 测试（Mock Repository，Capture Event）
```java
@Test void pricing_service_applies_vip_discount() {
    when(orderRepository.findById(order.getId())).thenReturn(Optional.of(order));
    pricingService.calculatePrice(order.getId());
    assertEquals(new Money(90.0, "CNY"), order.getTotalAmount()); }
```
Mock 原则：保留被测规则的真实实现；可在 Repository / Gateway 等外部边界使用测试替身。
### ④ Application Service + ⑤ Repository + ⑥ Adapter 测试
```java
@Test void place_order_creates_and_saves() {
    var orderId = handler.handle(new PlaceOrderCommand("cust-123", ...));
    assertNotNull(orderId); }
@SpringBootTest @Testcontainers
class OrderRepositoryImplTest {
    @Test void persists_and_retrieves_complete_aggregate() { ... } }
@SpringBootTest(webEnvironment = WebEnvironment.RANDOM_PORT)
class OrderControllerTest {
    @Test void post_orders_returns_201() { ... }
    @Test void post_invalid_product_returns_400() { ... } }
```
应用单元测试可替换外部端口，集成测试验证真实装配。数据库 Repository 使用代表性的真实数据库；HTTP Adapter 按契约测试需要选择 MockMvc 等项目工具，无需每个接口测试都启动数据库。
## Mock 策略矩阵
| 测试目标 | Repository | Gateway | EventBus | External |
|---------|:--------:|:-------:|:-------:|:--------:|
| Value Object | N/A | N/A | N/A | N/A |
| Aggregate Root | N/A | N/A | Capture | N/A |
| Domain Service | Mock | Mock | Capture | Mock |
| Application Service | Mock | Mock | Mock | Mock |
| Repository Integration | Real storage | N/A | N/A | N/A |
| API Integration | 按测试边界选择 | 按需替换 | 按需替换 | 按需替换 |
| E2E | 实际使用的存储 | Real | 使用时 Real | Real |
矩阵是默认选择的示例，不要求项目新增这些端口。测试被测行为时保留其真实实现；使用领域事件时可捕获事件验证内容，真实投递能力由集成测试验证。
## 各架构测试差异
| 架构 | 测试重心 | 差异说明 |
|------|---------|---------|
| **Layered** | 规则与使用的 Repository | 按业务规则和存储风险覆盖 |
| **Hexagonal** | Port Mock + Adapter Integration | Mock 接口即 Mock 整个外部 |
| **Clean** | Entity + UseCase Interactor | UseCase 层 Mock 输出端口 |
| **COLA** | Domain + App Service | 验证约定的领域依赖；使用 CQRS 时再测读写分流 |
| **CQRS** | Command + Query Read Model | 写模型用聚合测试；读模型直接查视图 |
| **Event Sourcing** | Event Replay + Projection | 聚合重放测试（必测）；投影读模型测试 |
## Test-Driven Domain Design（TDDD）
四步工作流：RED → GREEN → REFACT → REPEAT
```java
@Test void tddd_order_should_not_allow_paying_twice() {
    Order order = Order.create(customerId, items);
    order.pay(mockGateway);
    assertThrows(OrderException.class, () -> order.pay(mockGateway)); }
public void pay(PaymentGateway gateway) {
    if (this.status == OrderStatus.PAID) throw new OrderException("Already paid");
    this.status = OrderStatus.PAID;
    addDomainEvent(new OrderPaidEvent(this.getId())); }
```
## 测试覆盖率目标

下表是复杂 JVM 业务模块可参考的目标，不是通用门禁。采用项目已约定的阈值，或根据基线和风险协商目标；不适用项标注 N/A，不为达到比例补写镜像实现的测试。
| 层 | 目标 | 关键覆盖点 |
|----|:---:|-----------|
| Value Object | ≥ 95% | 构造验证、运算逻辑、等值比较 |
| Aggregate Root | ≥ 95% | 状态转移（每个路径）、领域事件 |
| Domain Service | ≥ 90% | 跨实体编排、外部数据计算 |
| Application | ≥ 80% | Use Case 完整路径 + 异常路径 |
| Repository | ≥ 80% | 聚合完整性、N+1 查询 |
| Adapter (API) | ≥ 70% | 协议转换、错误映射 |
可追踪分支覆盖率辅助寻找遗漏，优先验证关键行为；高覆盖率不能替代存储、协议或设备的真实集成验证。
## Gotchas — 常见陷阱
1. **只测 App Service 不测 Domain** — DDD 核心是 Domain 层。
2. **Mock 掉被测规则** — 测试替身不能替代本次需要验证的领域行为。
3. **聚合根只测 Happy Path** — 必须覆盖不变式违反和边界条件。
4. **把 Repository 测试当作 E2E** — Repository 只验证持久化。
5. **事件溯源缺少重放测试** — 使用事件作为事实源时，验证历史事件兼容和状态重建。
6. **测试与实现耦合** — 测试行为而非内部细节。
7. **遗漏已设计的领域事件** — 对需要发出事件的行为验证事件内容和时机，不要求每个方法产生事件。
8. **用 Mock 证明存储正确** — 存储集成测试使用真实机制；数据库可由现有测试设施或 Testcontainers 提供。
9. **CQRS 不测 Query 端** — Command 和 Query 端策略完全不同。
10. **查询放大未验证** — 使用 ORM 或存在查询放大风险时，检测相关查询次数与数据规模。
11. **E2E 测试重复且不稳定** — 覆盖关键旅程与集成风险，数量由场景决定。
12. **依赖规则缺少检查** — 按项目工具和实际架构验证关键依赖边界。
## FAQ
| 问题 | 回答 |
|------|------|
| 聚合根测试需要 Spring 吗？ | 不需要。纯 POJO，直接用 JUnit + AssertJ。 |
| Repository 应 Mock 还是真实 DB？ | 用例单元测试可替换端口；存储集成测试验证真实实现，使用数据库时用代表性的真实数据库。 |
| CQRS 怎么测 Query 端？ | 直接访问读模型，不需要 Mock。 |
| Event Sourcing 的必要测试？ | Event Replay：给定事件序列 → 重放 → 验证状态。 |
| 怎么避免 N+1 查询？ | 集成 SQLStatementCountValidator。 |
| TDDD 和传统 TDD 的区别？ | TDDD 以"领域行为/状态转移"为单元。 |
## Keywords
DDD testing, test pyramid, aggregate root test, value object test, domain service test, repository test, application service test, adapter test, CQRS testing, Event Sourcing test, TDDD, mock strategy, Testcontainers, ArchUnit, N+1 test, domain event test, branch coverage, CI/CD testing, integration test, E2E test, event replay test
## References
| 文件 | 用途 |
|------|------|
| [references/testing.md](references/09-testing.md) | 测试金字塔 + 各层 TypeScript 示例 |
| [references/mock-integration-patterns.md](references/06-mock-integration-patterns.md) | Mock 实现 + Java 集成测试 |
| [references/clean-ddd-hexagonal-testing.md](references/03-clean-ddd-hexagonal-testing.md) | Clean/Hexagonal/DDD 多层测试 |
| [references/unit-testing-strategies.md](references/10-unit-testing-strategies.md) | VO/AR/DS 单元测试 + 状态转移 |
| [references/integration-test-strategies.md](references/05-integration-test-strategies.md) | Repository/API 集成测试 + N+1 |
| [references/cqrs-event-sourcing-testing.md](references/04-cqrs-event-sourcing-testing.md) | CQRS + ES 重放/投影/快照测试 |
| [references/test-coverage-targets.md](references/07-test-coverage-targets.md) | 覆盖率目标 + 分支覆盖率 + JaCoCo |
| [references/ci-cd-test-stages.md](references/02-ci-cd-test-stages.md) | CI/CD 三阶段 + GitHub Actions |
| [references/architecture-testing-comparison.md](references/01-architecture-testing-comparison.md) | 各架构测试差异 + 项目阶段策略 |
| [references/test-driven-domain-design.md](references/08-test-driven-domain-design.md) | TDDD 四步工作流 + 完整案例 |
## Examples
| 文件 | 用途 |
|------|------|
| [examples/domain-test-examples.md](examples/05-domain-test-examples.md) | VO + AR + DS 完整测试示例 |
| [examples/app-adapter-test-examples.md](examples/01-app-adapter-test-examples.md) | App Service + Adapter + E2E |
| [examples/cqrs-es-test-examples.md](examples/04-cqrs-es-test-examples.md) | CQRS + ES 重放/投影/快照测试 |
| [examples/builder-mock-patterns.md](examples/03-builder-mock-patterns.md) | Builder + Mock Repository/EventPublisher |
| [examples/architecture-test-examples.md](examples/02-architecture-test-examples.md) | ArchUnit 架构测试（分层/聚合隔离） |
## Security & Safety

This skill is pure documentation. It contains no executable scripts, collects no user data, accesses no external services or networks.

