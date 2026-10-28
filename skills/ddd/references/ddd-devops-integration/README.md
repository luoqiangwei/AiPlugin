# DDD DevOps Integration

DevOps for DDD projects — project-specific architecture gates, dependency-aware builds, and optional JVM container, storage, event delivery and monitoring examples.

本模块提供 Java/Spring 服务端的可选交付示例，受 [DDD 主流程](../../SKILL.md) 的适用性和简化原则约束。只采用项目实际使用的构建、存储、事件和部署机制；下列模板不是所有 DDD 项目的交付清单。

---

## Workflow

### Step 1: Code & Build — Use the project's build graph and standard targets; compile dependencies before their consumers. Check domain dependencies explicitly rather than inferring purity from build order.
### Step 2: Unit Test — Per-module unit tests run independently.
### Step 3: Architecture Validate — Check the agreed dependency rules with stack-appropriate tools. Block on demonstrated correctness issues or agreed mandatory gates; phase in advisory rules separately.
### Step 4: Integration Test — Test changed module interactions and the storage or messaging mechanisms actually used.
### Step 5: Package — Follow the existing delivery format; use Docker images only for container deployments.
### Step 6: Deploy — Use the simplest supported deployment and rollback path; use K8s templates only when the project deploys to K8s.
### Step 7: Monitor — Select logs, health checks and metrics for the actual failure modes; add event delivery metrics when such delivery is used.

Architecture gates run during development and CI. The project's release policy determines whether a failed mandatory gate blocks merge or release; a naming preference alone is not a production incident.

---

## Boundary

### ✅ 擅长处理
- 为 DDD 项目配置 ArchUnit 质量门禁（P0/P1/P2），集成到 CI/CD Pipeline
- 多模块 DDD 项目增量编译优化（Maven/Gradle）、并行构建加速
- 架构类型感知的 Dockerfile 生成（单体/CQRS/六边形架构）
- K8s 部署模板：Per-BC Namespace、DB 迁移 initContainers、领域健康探针
- 事件驱动数据库迁移：Event Store、Outbox 表创建与索引策略
- 领域事件健康监控：Prometheus 指标暴露与告警规则配置

### ⚠️ 需要素材
- **项目结构**：Maven/Gradle 模块列表、依赖关系图 → 自动生成 ArchUnit 规则
- **部署环境**：K8s 集群版本、Ingress 策略 → 生成适配的 YAML 模板
- **数据库方案**：采用 Layered/CQRS/Event Sourcing 何种模式 → 定制迁移策略

### ❌ 超出范围（不适用）
- 通用 CI/CD 配置（非 DDD 项目不适用）→ 使用通用 DevOps 工具
- 容器编排基础（K8s 入门教程）→ 参考官方文档
- K8s 集群运维（节点管理、RBAC 配置）→ 使用专业运维工具
- 通用数据库管理（备份、恢复、性能调优）→ 使用 DBA 工具
- 基础设施监控（CPU、内存、网络）→ 使用 Prometheus + Grafana

---

## Audience

This skill is designed for: **Backend developers** (implementing DDD architectures), **Software architects** (evaluating and selecting patterns), **Tech leads** (reviewing team implementations), and **DDD beginners** (learning domain-driven design fundamentals).

## Rules

1. Verify agreed dependency boundaries with the project's tools; ArchUnit is one option for JVM projects.
2. Package by actual deployable units and runtime needs. Architecture names and CQRS do not require separate images or processes.
3. When events must be delivered reliably, validate delivery failures, retries and consumer idempotency and monitor the relevant failure modes.
4. Add an event store only for an event-sourced design. Add a transactional outbox only when it is the chosen reliable publication mechanism; neither is required merely because the system emits events.

---

## CI/CD Pipeline

```yaml
stages:
  - build
  - unit-test
  - architecture-check    # DDD gate
  - integration-test
  - containerize
  - deploy
```
此流水线是容器化 JVM 服务的示例；不使用容器时去掉 `containerize`。`architecture-check` 只执行已确认适用的依赖规则，问题等级根据实际影响确定。采用独立纯领域层时，可用 ArchUnit 检查 Spring/JPA/MyBatis 等实现依赖和模块循环；不要求所有平台代码零框架依赖。Full guide: [references/ci-cd-archunit-setup.md](references/01-ci-cd-archunit-setup.md)

---

## 多模块构建策略

```
ddd-project/
├── domain/ (zero framework deps) → application/ (depends on domain only) → infrastructure/ (implements domain interfaces)
├── adapter/ (REST/event adapters) → start/ (boot entry)
```
Maven 项目可按依赖图使用模块选择和并行构建，例如 `mvn verify -pl <changed-module> -am`；同时覆盖受影响的下游回归测试。缓存键应包含依赖和工具链输入，不能以缓存命中代替测试；不要按架构层名称跳过关键模块。性能收益以本项目测量为准。纯领域模块可按已确认规则使用 Maven Enforcer 检查依赖。Full config: [references/multi-module-build-config.md](references/09-multi-module-build-config.md)

---

## 容器化部署

**Monolith** — Multi-stage fat JAR:
```dockerfile
FROM eclipse-temurin:17-jdk-alpine AS builder
COPY . . && RUN mvn clean package -DskipTests
FROM eclipse-temurin:17-jre-alpine
COPY --from=builder start/target/*.jar app.jar
HEALTHCHECK --interval=30s CMD curl -f http://localhost:8080/actuator/health
```
**CQRS** 可在同一应用中实现。只有读写负载、交付或隔离需求证明有收益时，才独立构建和部署；JVM 参数根据实际测量设置。已使用 K8s 时，再按运维边界选择 Namespace、迁移任务、HPA 和 NetworkPolicy，不将限界上下文机械映射成 Namespace。Templates: [dockerfile-patterns.md](references/04-dockerfile-patterns.md) | [k8s-ddd-reference.md](references/07-k8s-ddd-reference.md)

---

## 数据库迁移（事件驱动）

以下 SQL 只演示事件存储及 Outbox 所需的数据结构，不要求两者同时使用。普通领域事件无需新增事件存储表；不使用数据库的模块跳过本节。实际迁移应使用项目数据库方言，并验证兼容性与回滚策略。

```sql
CREATE TABLE domain_event_store (id UUID PRIMARY KEY, aggregate_id VARCHAR(36) NOT NULL,
    event_type VARCHAR(200) NOT NULL, event_data JSONB NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL, published BOOLEAN DEFAULT FALSE);
CREATE INDEX idx_events_pending ON domain_event_store(published) WHERE published = FALSE;
CREATE TABLE outbox_message (id UUID PRIMARY KEY, event_id UUID UNIQUE NOT NULL,
    payload JSONB NOT NULL, status VARCHAR(20) DEFAULT 'PENDING',
    retry_count INT DEFAULT 0, created_at TIMESTAMPTZ DEFAULT NOW());
CREATE INDEX idx_outbox_pending ON outbox_message(status) WHERE status = 'PENDING';
```
Strategy: 共享数据库沿用项目迁移工具；读写存储分离时分别管理 schema 并验证同步；事件溯源时维护事件版本、投影及兼容性；独立服务各自负责拥有的数据。Full scripts: [flyway-migration.md](references/05-flyway-domain-event-migration.md) | [db-strategies.md](references/02-database-migration-strategies.md)

---

## 监控与告警

Bus metrics: `domain.events.published` (Counter), `domain.events.processing.duration` (Histogram p50/p95/p99), `domain.aggregate.load.duration` (Histogram), `domain.outbox.depth` (Gauge).

Alert rules: DomainEventBacklog (rate > 100 for 2m, critical), OutboxQueueGrowing (depth > 1000 for 1m, critical), EventProcessingErrorRate (> 5% for 2m, warning). Full config: [ddd-observability-config.md](references/03-ddd-observability-config.md)

---

## Gotchas

1. **把架构偏好当作阻断门禁**: 先确认规则适用范围和现有违规基线；新增强制规则前评估真实影响。
2. **为 CQRS 强行拆部署**: 读写模型分离不要求容器或进程分离，先验证负载和交付需求。
3. **领域事件监控遗漏**: Event 投递延迟、Outbox 堆积、Consumer Lag 是事件驱动架构中最易忽略的可靠性指标。
4. **单体打成微服务镜像**: 先评估 BC 是否需要独立部署，过度拆分失去聚合内强一致性优势。
5. **数据库迁移未考虑事件存储**: 添加 Event Store 表时需同步考虑回填、索引、清理策略。
6. **ArchUnit 不检查充血模型**: 需结合 ddd-code-reviewer 做领域模型质量审查。

---

## FAQ

**Q: ArchUnit CI 失败但代码正确？** A: 先核实规则是否适用于当前架构和模块，再修复实际依赖违规；不要把平台实现层误当成纯领域层。
**Q: Monolith vs 微服务 DDD 部署策略？** A: 优先清晰的逻辑模块。只有独立扩缩容、交付或所有权需求足以抵偿运维成本时再拆分，团队人数不是硬阈值。
**Q: 如何监控领域事件而不增加延迟？** A: 异步指标（Micrometer Timer 百分比采样）+ 采样追踪（1/100 OpenTelemetry）。绝不阻塞事件发布。
**Q: CQRS 读写应共享同一 pipeline？** A: 跟随实际部署单元；同一应用可共用流水线。独立部署时也需覆盖共享契约、兼容性和端到端回归。
**Q: Event Sourcing schema 如何管理？** A: 事件追加写入不代表无需演进。管理事件版本、反序列化兼容、投影迁移和历史重放；底层存储 schema 也按需迁移。
**Q: Bounded Context 金丝雀发布如何实现？** A: 先确认它是否独立部署。使用现有流量控制工具和项目设定的观察窗口逐步放量，不为此默认引入 Service Mesh。

---

## Security & Safety

This skill is pure documentation. It does not collect user data, does not access external services or networks, and contains no executable scripts.

## Keywords

ddd devops, ddd ci/cd, archunit ci, domain event monitoring, ddd docker, ddd kubernetes, ddd outbox, ddd database migration, ddd build optimization, ddd quality gate, ddd deployment, ddd alerting, ddd observability, cqrs deployment, event sourcing infrastructure

## References

- [CI/CD ArchUnit Setup](references/01-ci-cd-archunit-setup.md) — ArchUnit CI/CD integration guide
- [Dockerfile Patterns](references/04-dockerfile-patterns.md) — Dockerfiles by DDD architecture type
- [K8s DDD Reference](references/07-k8s-ddd-reference.md) — K8s deployment for bounded contexts
- [Flyway Domain Event Migration](references/05-flyway-domain-event-migration.md) — Event store and outbox scripts
- [Monitoring & Alerting](references/08-monitoring-alerting-reference.md) — Prometheus metrics and alerting rules
- [Multi-Module Build Config](references/09-multi-module-build-config.md) — Maven/Gradle build optimization
- [DDD Observability Config](references/03-ddd-observability-config.md) — Micrometer/OTel/Logback configuration
- [GitLab CI Pipeline Reference](references/06-gitlab-ci-ddd-pipeline-reference.md) — GitLab CI complete pipeline
- [Database Migration Strategies](references/02-database-migration-strategies.md) — Event-driven migration strategies

## Examples

- [GitHub Actions Pipeline](examples/02-github-actions-pipeline.md) — Complete GitHub Actions workflow with ArchUnit
- [GitLab CI ArchUnit Pipeline](examples/03-gitlab-ci-archunit-pipeline.md) — GitLab CI with architecture validation
- [K8s DDD Deployment](examples/05-k8s-ddd-deployment.md) — K8s manifests for bounded context deployment
- [Flyway Domain Event Migration](examples/01-flyway-domain-event-migration.sql) — Complete migration SQL scripts
- [Grafana Domain Health Dashboard](examples/04-grafana-domain-health-dashboard.md) — Domain event monitoring dashboard
