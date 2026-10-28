# DDD Code Reviewer

DDD 代码审查 + 反模式检测 + 5 维度合规评分。验证代码是否遵循 DDD 最佳实践，输出结构化审查报告。

先按 [DDD 主流程](../../SKILL.md) 确认适用范围、现有架构和本次改动目标。以下反模式与 Java 工具示例是检查线索，不覆盖主文件的简化原则，也不自动决定问题等级。

## Workflow

DDD 代码审查三步走：

```
Step 1: 代码扫描 — 核实适用的依赖规则、业务不变式、实际调用与相关测试
Step 2: 问题验证 — 给出触发条件、行为后果和源码证据，按影响分级；需要评估时再做五维评分
Step 3: 报告输出 — 按严重程度列问题、位置、修复方向和验证缺口
```

报告深度随请求范围调整。局部代码审查直接反馈可操作问题；用户要求评分或完整架构评估时才补评分，不自动创建独立文档。

## When to Use

### 常见请求

`代码审查` `DDD review` `反模式检测` `anti-pattern` `贫血模型` `充血模型检查` `架构审查` `分层合规` `代码质量评分` `layering compliance` `rich domain check` `review my DDD code`

### 适用前提

| 条件 | 说明 |
|------|------|
| 项目已采用 DDD 思想 | 非 DDD 项目无审查基础 |
| 有可审查的源代码 | 需提供代码路径或片段 |
| 期望发现反模式 | 不只是格式检查，更关注领域模型健康度 |

### 不适用场景

| 跳过 | 改用 |
|------|------|
| 非 DDD 项目或简单 CRUD | 按正确性、安全性、性能和可维护性审查，不强制领域模型重构 |
| 项目尚未引入 DDD | 按当前架构审查；评估是否引入 DDD 时再读适用性模块 |
| 只有局部实现 | 审查可见变更，明确未覆盖部分，不要求先完成整个项目 |
| 需要架构选型 | `ddd-architecture-selector` |
| 需要架构健康度评估 | `ddd-architecture-evaluator` |

## Audience

This skill is designed for: **Backend developers** (implementing DDD architectures), **Software architects** (evaluating and selecting patterns), **Tech leads** (reviewing team implementations), and **DDD beginners** (learning domain-driven design fundamentals).

## Rules

1. Report demonstrated defects and meaningful architecture violations within the requested scope. Use scoring only when an assessment is requested or useful.
2. Determine severity from the concrete impact, affected users and trigger conditions; an anti-pattern name alone cannot block merge.
3. Verify the architecture's agreed dependency rules. A deliberately pure domain module should avoid implementation dependencies; Android platform components are not automatically pure domain modules.
4. Order findings by severity and include source locations, consequences and practical fixes. Use ArchUnit only when appropriate to the project stack.

## Anti-Pattern Checklist

先检查贫血模型、上帝 Service、跨聚合引用、实现依赖、循环依赖、可变值对象和重复领域规则是否造成实际问题。简单数据结构、必要的平台依赖、未使用领域事件或有证据支持的事务边界，不直接记为缺陷。

- **P0 — 紧急阻断**：有证据的严重安全绕过、广泛数据损坏或关键系统不可用；需说明触发条件及影响范围。
- **P1 — 高优先级**：可复现的核心不变式破坏、错误事务边界导致部分写入、实际构建失败或关键回归；修复后才能把相关能力报告为完成。
- **P2 — 普通改进**：有具体后果的规则重复、边界耦合或测试遗漏；说明改进收益。单纯命名或风格偏好按项目约定处理。

> 完整反模式速查表见 [references/checklist.md](references/02-checklist.md)，含 Java 代码示例和修复路径。

## Layered Compliance Matrix

先从项目模块、构建依赖和 ADR 确定允许依赖矩阵。下表是端口适配器式组织的示例，不强加给所有分层项目；Infrastructure 实现领域/用例接口，因此可以依赖内层：

```
    ┌─────────────────┬─────┬─────┬─────┬─────┐
    │ 层 / 可依赖     │ Infra│ Dom │ App │ Adap│
    ├─────────────────┼─────┼─────┼─────┼─────┤
    │ Infrastructure  │  ✓  │  ✓  │  ✓  │  ✗  │
    │ Domain          │  ✗  │  ✓  │  ✗  │  ✗  │
    │ Application     │  ✗  │  ✓  │  ✓  │  ✗  │
    │ Adapter         │  ✗  │  ✓  │  ✓  │  ✓  │
    └─────────────────┴─────┴─────┴─────┴─────┘
```

**采用纯领域模块时的 JVM 实现依赖检查示例**（发现后按实际影响分级）：
  - ✗ `import org.springframework.stereotype.Service`
  - ✗ `import javax.persistence.Entity`
  - ✗ `import org.apache.ibatis.annotations.Mapper`
  - ✓ `import java.util.Optional`
  - ✓ `import java.math.BigDecimal`

ArchUnit 完整配置见 [references/archunit-config.md](references/01-archunit-config.md)。

装配入口可以引用具体实现完成依赖注入。历史参考中的通用矩阵、P0 标签和零依赖模板需按本项目实际架构调整，不能直接作为全库门禁。

## Rich Domain Model Validation

有复杂领域规则时，检查规则是否集中、是否能通过不同入口一致执行，以及是否有不变式测试。仅有 getter/setter 不能证明模型错误；简单 CRUD、查询 DTO、平台协议结构可合理保留数据模型。不要仅因采用函数与数据结构组织行为而要求改成类方法。

> 完整代码示例和重构对比见 [examples/rich-model-refactoring.md](examples/04-rich-model-refactoring.md)，含 3 个实战案例。

## Scoring System

仅在需要架构评估时使用。评分用于定位改进方向，不代表生产就绪，也不自动阻断合并；不适用项标注 N/A 并调整总分。

### 5 维度评分

| 维度 | 权重 | 检查项 | 满分 |
|------|:----:|--------|:----:|
| **1. 分层合规** | 30% | Domain 零依赖、依赖方向、App 无 SQL、Controller 无业务逻辑 | 30 |
| **2. 领域模型质量** | 30% | 充血模型覆盖率、值对象使用率、聚合设计、领域事件 | 30 |
| **3. 命名规范** | 15% | 聚合根 = 业务名称、Repository = 标准命名、事件 = 过去式 | 15 |
| **4. 代码结构** | 15% | 包按聚合组织、类大小、圈复杂度 | 15 |
| **5. 测试覆盖** | 10% | Domain 层测试覆盖、聚合根行为测试、事件验证 | 10 |

各维度按“满分”列给分时，**总分 = 各维度得分之和**（已含权重，不再次加权）。

### 分数等级

| 范围 | 等级 | 含义 | 行动 |
|:----:|:----:|------|------|
| ≥ 85 | 🟢 A | 适用项表现良好 | 仍需通过行为、集成及发布验证 |
| 70-84 | 🟡 B | 基本合规，有改进空间 | 修 P1 问题 |
| 50-69 | 🟠 C | 存在明显反模式 | 规划重构 Sprint |
| < 50 | 🔴 D | 需要复核模型与架构适配性 | 先核实低分原因，按实际问题渐进修复 |

评分细则和计算示例见 [references/scoring-criteria.md](references/09-scoring-criteria.md)、[examples/scoring-example.md](examples/05-scoring-example.md)。

## Review Report Template

需要完整评估时可参考下列结构；局部审查可以省略评分和不相关项：

```markdown
# DDD Code Review Report

## Overall Score: 78/100 (🟡 B)

### 分层合规 (24/30)
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| Domain 零依赖 | ✅ | 无框架依赖 |
| App 层无 SQL | ❌ | OrderAppService L45 直接调用 Mapper |
| 依赖方向 | ✅ | 无反向依赖 |

### 领域模型质量 (22/30)
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 充血模型 | ⚠️ | User 实体仍为贫血模型 |
| 值对象 | ⚠️ | Money/Email 已用，Phone 仍为 String |

### 反模式清单
| 严重级别 | 反模式 | 位置 | 修复建议 |
|:------:|--------|------|---------|
| P1 | 支付状态检查与写入未形成原子操作，并发请求可重复扣款 | OrderService.java:45 | 使用项目支持的并发控制，并补并发支付回归测试 |

### 改进建议（按优先级）
1. [P1] 修复并发支付的原子性并验证扣款次数
2. [P2] 将多入口重复的定价规则集中，保留现有行为
3. 按实际消费需求评估领域事件，不为评分新增事件机制
```

完整模板见 [references/report-template.md](references/08-report-template.md)、示例见 [examples/review-report-example.md](examples/03-review-report-example.md)。

## Gotchas

常见审查陷阱见 [references/gotchas.md](references/06-gotchas.md)。

## FAQ

| 问题 | 回答 |
|------|------|
| 一次审查要多久？ | 小项目（1-2 聚合）约 30-60 分钟；大项目按模块分次审查 |
| 评分是主观的吗？ | 评分依赖适用性和权重选择；明确评分范围与证据，不能用总分替代缺陷分析。 |
| ArchUnit 检查必须自己写吗？ | JVM 项目可参考模板，按实际模块和允许依赖调整后验证，不直接复制为全库门禁。 |
| 找到了反模式，改不动怎么办？ | 先核实具体后果与等级。P0/P1 未解决时明确相关能力受阻，不能以评分或技术债条目代替修复；普通改进按范围安排。 |
| 审查频率建议？ | 代码审查推荐 PR 合并前做。架构级审查推荐每季度一次 |
| 与非 DDD 架构的审查区别？ | 都关注正确性、安全、性能和可维护性；采用 DDD 的部分额外检查统一语言、领域规则和一致性边界。 |

## Security & Safety

This skill is pure documentation. It contains no executable scripts, collects no user data, accesses no external services or networks.

## Keywords

DDD 代码审查、反模式检测、贫血模型、充血模型、上帝 Service、分层合规、依赖方向、ArchUnit、领域事件、值对象不可变、聚合设计、5 维度评分、代码质量门禁

## References

| 文件 | 用途 |
|------|------|
| [references/checklist.md](references/02-checklist.md) | 反模式速查表 — P0/P1/P2 分级 + 修复路径 |
| [references/scoring-criteria.md](references/09-scoring-criteria.md) | 5 维度评分细则 — 每项检查的权重和检测方法 |
| [references/archunit-config.md](references/01-archunit-config.md) | ArchUnit 完整配置 — Maven/Gradle 依赖 + 全套检查规则 |
| [references/report-template.md](references/08-report-template.md) | 审查报告模板 — Markdown + 快速摘要格式 |
| [references/clean-ddd-hexagonal-layers.md](references/03-clean-ddd-hexagonal-layers.md) | 四层架构结构详解 — Domain/App/Infra/Presentation |
| [references/clean-ddd-hexagonal-tactical.md](references/04-clean-ddd-hexagonal-tactical.md) | DDD 战术模式参考 — Entity/VO/Aggregate/Repository |
| [references/clean-ddd-hexagonal-testing.md](references/05-clean-ddd-hexagonal-testing.md) | 测试模式 — 单元测试/集成测试/架构测试 |
| [references/partme-15-boundaries.md](references/07-partme-15-boundaries.md) | 微服务边界理论 — 逻辑边界/物理边界/代码边界 |
| [references/gotchas.md](references/06-gotchas.md) | 审查常见陷阱 — 跨聚合引用、PO/DTO 混用等 |

## Examples

| 文件 | 用途 |
|------|------|
| [examples/review-report-example.md](examples/03-review-report-example.md) | 完整审查报告示例（62/100 🟠 C 级） |
| [examples/scoring-example.md](examples/05-scoring-example.md) | 评分计算全过程 + 修复 ROI 分析 |
| [examples/rich-model-refactoring.md](examples/04-rich-model-refactoring.md) | 贫血→充血模型重构：3 个实战案例 |
| [examples/anti-pattern-fix-guide.md](examples/01-anti-pattern-fix-guide.md) | 反模式修复路径速查 |
| [examples/archunit-compliance-test.md](examples/02-archunit-compliance-test.md) | ArchUnit 合规测试 — P0/P1/P2 门禁实现 |

## 相关参考模块

审查完成后，按实际需要补充读取：

- [架构评估](../ddd-architecture-evaluator/README.md) — 架构级健康与演进评估。
- 对应架构模块（[Layered](../ddd-architecture-layered/README.md)、[Hexagonal](../ddd-architecture-hexagonal/README.md)、[COLA](../ddd-architecture-cola/README.md) 等）— 修复目录和分层结构。
- [测试策略](../ddd-testing-strategist/README.md) — 提升测试覆盖率。
- [架构文档](../ddd-architecture-doc/README.md) — 输出架构文档。
