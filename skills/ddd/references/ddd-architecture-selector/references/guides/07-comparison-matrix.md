# DDD Architecture Comparison Reference

## Quick Decision Matrix

| Dimension | Layered | Onion | Hexagonal | Clean | COLA |
|-----------|:--:|:--:|:--:|:--:|:--:|
| **Learning Cost** | ★☆☆ | ★★★ | ★★★ | ★★★ | ★★☆ |
| **Business Complexity Fit** | ★☆☆ | ★★★ | ★★★ | ★★★ | ★★★ |
| **CRUD Efficiency** | ★★★ | ★☆☆ | ★☆☆ | ★☆☆ | ★★☆ |
| **Infrastructure Replaceability** | ★☆☆ | ★★★ | ★★★ | ★★★ | ★★☆ |
| **Test Friendliness** | ★☆☆ | ★★★ | ★★★ | ★★★ | ★★★ |
| **Chinese Community** | ★★★ | ★☆☆ | ★☆☆ | ★☆☆ | ★★★ |
| **Code Generation Support** | Good | Poor | Poor | Poor | Excellent |
| **Coordination Focus** | Layer responsibilities | Domain-centered dependencies | Adapter contracts | Use-case/module boundaries | Java engineering conventions |
| **Origin** | Martin Fowler | Jeffrey Palermo 2008 | Alistair Cockburn 2005 | Robert C. Martin 2012 | Alibaba 2018 |

## Architecture Selection Flowchart

```
Existing project/platform constraints?
├── Existing organization meets the task → Preserve it; isolate the changed behavior locally
└── A real boundary is missing
    ├── Simple behavior → Simple layers or existing conventions
    ├── External protocols impede testing → Consider ports/adapters
    ├── Use-case dependencies need enforcement → Consider Clean/Onion principles
    └── Java engineering conventions are required → Evaluate COLA tooling
```

## Architecture Selection by Scenario

| Scenario | Recommended | Why |
|----------|-------------|-----|
| REST API + Simple CRUD | Layered | Minimal overhead |
| Core domain logic heavy | Hexagonal / Onion | Best domain isolation |
| Chinese enterprise backend | COLA | Ecosystem + Chinese docs |
| Multi-entry (REST+CLI+MQ+gRPC) | Hexagonal | Cleanest adapter isolation |
| Strict module boundaries needed | Clean | Physical module isolation |
| Frequent DB/MQ changes | Hexagonal / Onion | Easy adapter swap |
| Rapid prototyping → Production | Layered → COLA | Progressive evolution |
| Service implementation conventions | Primary organization plus clear adapter contracts | Avoid duplicate abstractions for overlapping principles |

Team size affects coordination cost, not pattern eligibility. Bounded contexts default to logical modules; independent deployment needs its own justification. CQRS and Event Sourcing are independent of these named architectures.
