# DDD Architecture Selector

Architecture selection decision guide that evaluates 5 DDD architecture patterns (Layered, Onion, Hexagonal, Clean, COLA) against project context — team size, business complexity, tech stack, infrastructure change frequency, and ecosystem preference.

这些模式有重叠的目标和原则，不是严格互斥的五种产品。确定一种主要组织方式，并明确模块职责、依赖方向和检查方法；复用兼容原则时不重复增加同义层。已有平台或项目架构优先，不为套用模式而重组整个工程。本模块及其支持资料服从主 [DDD Skill](../../SKILL.md) 的适用性、任务范围和简化原则。

## Workflow

### Step 1: Collect Project Context
- Team size & DDD experience level
- Business complexity (simple CRUD / moderate / high)
- Technical stack (Spring Boot / Go / Node.js / .NET / Python)
- Infrastructure change frequency (low / medium / high)
- Multi-entry needs (REST + CLI + MQ + gRPC?)
- Test coverage requirements (unit / integration / E2E)
- Ecosystem preference (Chinese community / international)

### Step 2: Run Decision Matrix
- Compare 5 architectures across 7+ dimensions

### Step 3: Apply Decision Tree
- Existing constraints → domain complexity → dependency/test boundaries → feasible organization

### Step 4: Assess CQRS and Persistence Independently
- Decide whether read/write models need separation, whether storage needs separation, and whether events must be the source of truth. Event Sourcing is not a CQRS upgrade level.

### Step 5: Classify Domain Types
- Core / Generic / Supporting → Apply different architectures per domain

### Step 6: Suggest Microservice Splitting
- Default to logical modules; assess independent deployment only when operational and ownership needs justify it

### Step 7: Route to Specific Architecture Skill
- Link to detailed implementation guidance

## When to Use (and When NOT to)

| ✅ Use When | ❌ Skip When |
|------------|-------------|
| Starting a new project: need architecture decision | Architecture already decided → go directly to that skill |
| Comparing multiple DDD architectures | Just need DDD learning → use `ddd-architecture-awesome` |
| Team unsure which approach fits best | Need architecture evaluation of existing project → use `ddd-architecture-evaluator` |
| Planning microservice splitting strategy | Need domain modeling after selection → use `ddd-domain-designer` |
| Evaluating CQRS necessity | Non-DDD project evaluation (consider standard MVC) |
| Chinese enterprise team making tech decisions | Simple CRUD with no DDD needed → use standard MVC |
| Team size / DDD maturity unknown | Need code review of existing DDD code → use `ddd-code-reviewer` |

## Boundary

| Category | Description | Alternative |
|----------|-------------|------------|
| ✅ **Handles** | New project architecture selection (5 DDD architectures) | — |
| ✅ **Handles** | Architecture comparison for migration decisions | — |
| ✅ **Handles** | CQRS / Event Sourcing necessity assessment | — |
| ✅ **Handles** | Domain classification (Core / Generic / Supporting) | — |
| ✅ **Handles** | Microservice splitting based on bounded contexts | — |
| ✅ **Handles** | Team capability and ownership constraints | — |
| ⚠️ **Requires** | Basic project context: team size, business complexity, tech stack | — |
| ⚠️ **Requires** | Domain expert or product owner involvement for classification | — |
| ❌ **Out of Scope** | Architecture already decided | 直接读取对应架构模块：[Layered](../ddd-architecture-layered/README.md) / [Onion](../ddd-architecture-onion/README.md) / [Hexagonal](../ddd-architecture-hexagonal/README.md) / [Clean](../ddd-architecture-clean/README.md) / [COLA](../ddd-architecture-cola/README.md) |
| ❌ **Out of Scope** | Just need DDD learning & concepts | [DDD 入门与全景](../ddd-architecture-awesome/README.md) |
| ❌ **Out of Scope** | Evaluate existing architecture health & quality | [架构评估](../ddd-architecture-evaluator/README.md) |
| ❌ **Out of Scope** | Domain modeling / aggregate design after selection | [领域建模](../ddd-domain-designer/README.md) |
| ❌ **Out of Scope** | Code review for DDD compliance | [代码审查](../ddd-code-reviewer/README.md) |
| ❌ **Out of Scope** | Non-DDD / standard MVC projects — not use this skill | Use standard MVC guides (not DDD skills) |

## Audience

This skill is designed for: **Backend developers** (implementing DDD architectures), **Software architects** (evaluating and selecting patterns), **Tech leads** (reviewing team implementations), and **DDD beginners** (learning domain-driven design fundamentals).

## Rules

1. Evaluate existing constraints, domain complexity, dependency boundaries, testability and operating cost to the depth needed for this decision.
2. Never recommend Event Sourcing as default. Assess its value and event versioning/replay costs independently of CQRS and database separation.
3. Team size informs coordination cost; it does not determine architecture or require migration. Choose the smallest change that meets the actual constraints.

## 5-Architecture Decision Matrix

| Dimension | Layered | Onion | Hexagonal | Clean | COLA |
|-----------|:--:|:--:|:--:|:--:|:--:|
| **Learning Cost** | ★☆☆ | ★★★ | ★★★ | ★★★ | ★★☆ |
| **Business Complexity Fit** | ★☆☆ | ★★★ | ★★★ | ★★★ | ★★★ |
| **CRUD Efficiency** | ★★★ | ★☆☆ | ★☆☆ | ★☆☆ | ★★☆ |
| **Infrastructure Replaceability** | ★☆☆ | ★★★ | ★★★ | ★★★ | ★★☆ |
| **Test Friendliness** | ★☆☆ | ★★★ | ★★★ | ★★★ | ★★★ |
| **Chinese Community** | ★★★ | ★☆☆ | ★☆☆ | ★☆☆ | ★★★ |
| **Code Generation Support** | Good | Poor | Poor | Poor | Excellent |
| **Module Physical Isolation** | Low | Medium | Medium | High | High |
| **Evolution Path Clarity** | ★☆☆ | ★★★ | ★★★ | ★★★ | ★★★ |
| **Coordination Focus** | Clear layer responsibilities | Domain-centered dependencies | Adapter contracts | Use-case and module boundaries | Shared Java engineering conventions |
| **Origin** | Martin Fowler | Jeffrey Palermo (2008) | Alistair Cockburn (2005) | Robert C. Martin (2012) | Alibaba (2018) |

| Architecture | Best For | Avoid When |
|-------------|----------|------------|
| **Layered** | Simple CRUD, small teams, traditional MVC migration | Complex business rules, frequent infra changes |
| **Onion** | High test coverage, changing infrastructure | CRUD-heavy apps, teams with no abstraction experience |
| **Hexagonal** | Multi-entry systems, microservice standardization | Simple single-entry CRUD, quick prototypes |
| **Clean** | Explicit use-case boundaries and inward dependencies | Extra interfaces/modules have no demonstrated benefit |
| **COLA** | Java ecosystem with a need for its conventions and extension points | Non-Java stacks or existing conventions already meet the need |

## 3-Step Decision Tree

### Step 1: Assess Business Complexity

```
Business Complexity?
│
├── Simple CRUD / little domain behavior
│   └── Keep existing conventions or simple layers; do not add speculative DDD abstractions
│
├── Moderate (core business logic with rules)
│   ├── Chinese ecosystem / Spring Boot + MyBatis?   → COLA
│   ├── Value domain layer purity most?               → HEXAGONAL
│   ├── Multi-entry system (REST + CLI + MQ)?         → HEXAGONAL
│   ├── Infrastructure changes often?                 → HEXAGONAL / ONION
│   └── .NET / Python stack?                          → ONION
│
└── High (multiple contexts or complex rules)
    ├── Need use-case boundaries and inward dependencies? → Consider CLEAN
    ├── Need Java engineering conventions?                → Consider COLA
    ├── Multiple protocols or replaceable dependencies?   → Consider HEXAGONAL
    └── Existing platform constrains modules/lifecycle?   → Preserve platform structure; isolate rules locally
```

### Step 2: Check Delivery and Ownership Constraints

| Evidence | Decision to assess | Rationale |
|-----------|------------------------|-----------|
| Tight delivery budget | Fewer layers, ports and modules | Keep only abstractions that improve this task |
| Several owners change the same code | Explicit module contracts and dependency checks | Reduce coordination and unintended coupling |
| Framework dependencies obstruct tests | Isolate relevant rules and adapters | Enable focused tests without replacing the whole architecture |
| Independent release or scaling needs | Evaluate separate deployment and its cost | Distribution requires operational evidence |

**Evolution**: Change architecture when concrete constraints or measured problems change. Team growth alone is not a migration trigger, and no named pattern is a mandatory next stage.

### Step 3: Final Recommendation

| If you have... | Then choose... | Why |
|---------------|---------------|-----|
| Spring Boot + MyBatis + Chinese team | **COLA** | Ecosystem match, Chinese docs, scaffolding |
| Multi-entry (REST + CLI + MQ + gRPC) | **Hexagonal** | Adapter pattern handles multiple entry points |
| Strict module physical isolation, large enterprise | **Clean** | Entity → UseCase → Adapter enforced isolation |
| Infrastructure changes often (DB, MQ swap) | **Hexagonal** or **Onion** | Port/Adapter makes swapping trivial |
| Rapid prototype → evolve DDD later | **Layered** → upgrade | Lowest startup cost, clear evolution path |
| Complex business rules + TDD | **Hexagonal** | Domain layer independently testable |
| Team new to DDD, incremental adoption | **Layered** | Closest to traditional 3-tier, gentlest learning curve |
| Service implementation needs shared conventions | Choose a primary organization and explicit adapter contracts | Avoid duplicate layers for overlapping patterns |
| Read-heavy, complex queries | Assess queries/indexes first, then CQRS and storage separation | Separate stores only when independent optimization justifies synchronization cost |
| Need to reconstruct state from event history | Assess **Event Sourcing** independently | Compare replay/versioning costs with simpler audit records |

## Domain Partitioning + Microservice Splitting

### Domain Classification (Core / Generic / Supporting)

| Domain Type | Investment Strategy | Architecture Recommendation | Examples |
|-------------|-------------------|---------------------------|----------|
| **Core Domain** (核心域) | Max investment, build in-house | Hexagonal / Clean / COLA with rich domain model | Order management, Payment processing, Pricing engine |
| **Generic Domain** (通用域) | Purchase or open-source reuse | Layered or off-the-shelf SaaS | Authentication, Authorization, Notification |
| **Supporting Domain** (支撑域) | Outsource or low priority | Layered or simple CRUD | Reports, Admin dashboard, Data export |

**Key rule**: Investment follows domain value and actual constraints. Generic/supporting domains usually need simpler implementations, but adapters or dependency isolation may still be useful; a domain label does not prohibit an architecture.

### Microservice Splitting Rules

1. **Default**: Express bounded contexts as logical modules with explicit model ownership. A bounded context is not automatically a process, repository or microservice.
2. **Split when**: Different deployment cadence, different scaling needs, different team ownership
3. **Keep together or reconsider boundaries when**: Independent deployment adds little value, consistency requirements are difficult to satisfy across processes, or ownership and release needs remain shared.
4. **Start conservative**: Fewer services, split as needed (proven by need, not anticipation)
5. **Communication**: Choose in-process calls, RPC or events according to coupling, latency and consistency needs. RPC alone does not make cross-service updates atomic.

## CQRS and Persistence Decisions

| Decision | Description | Added cost | Architecture Support | When to Use |
|-------|-------------|------|---------------------|-------------|
| **No CQRS** | One suitable model for reads and writes | None from CQRS | Any | Existing model meets the use cases |
| **Separate models** | Separate command and query responsibilities; storage may be shared | More code/contracts | Any | Read and write behavior or data shape materially diverge |
| **Separate storage** | Dedicated read models/stores with an explicit synchronization strategy | Projection, lag and recovery handling | Any with clear boundaries | Measured query or scaling needs justify it |
| **Event Sourcing** | Persist events as authoritative state and derive current state | Event evolution, replay and operational tooling | Any with explicit persistence boundaries | Reconstructing state from history is valuable enough to justify the cost |

**Recommendation**: Decide these dimensions independently; shared-database CQRS may query shared tables directly through the query path. Event Sourcing can be used with or without CQRS and does not require a prior separate-database implementation. Historical `L0/L1/L2/L3` names in examples are local labels, not standard levels or a required progression; consult each example's actual topology.

## 架构参考模块

| 选型结果 | 参考模块 |
|----------|----------|
| Layered | [DDD 分层架构](../ddd-architecture-layered/README.md) |
| Onion | [洋葱架构](../ddd-architecture-onion/README.md) |
| Hexagonal | [六边形架构](../ddd-architecture-hexagonal/README.md) |
| Clean | [整洁架构](../ddd-architecture-clean/README.md) |
| COLA | [COLA 架构](../ddd-architecture-cola/README.md) |

按需补充：[CQRS](../ddd-cqrs-architecture/README.md)、[领域建模](../ddd-domain-designer/README.md)、[架构评估](../ddd-architecture-evaluator/README.md)。

## Gotchas

See [references/gotchas.md](references/guides/10-gotchas.md) for 15 pitfalls.

## FAQ

See [references/faq.md](references/guides/09-faq.md) for 15 Q&A.

## Security & Safety

This skill is pure documentation. It does not collect user data, does not access external services or networks, and contains no executable scripts.

## References

See [references/](references/) for deep comparisons, microservice/domain, clean+DDD+hexagonal, ddd4j analysis, gotchas, FAQ, external resources, and 5 case studies.
