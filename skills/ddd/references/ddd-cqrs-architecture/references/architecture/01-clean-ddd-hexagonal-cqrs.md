# CQRS Core Principles — Architecture Integration

本文的 L1/L2/L3 是旧示例标签：模型分离、存储分离、Event Sourcing 是独立决策，不是逐级升级。模型分离允许共享数据库并直接查询共享表；下图只展示独立读库的一个方案。Event Sourcing 不要求预先实施存储分离，详见 [模块入口](../../README.md)。

## 核心分离原则

传统 CRUD 与 CQRS 对比：

```
传统 CRUD：                     CQRS：
         ┌──────────┐          ┌──────────┐     ┌──────────┐
         │   CRUD   │          │ Command  │     │  Query   │
         │  Service │          │  Model   │     │  Model   │
         └────┬─────┘          └────┬─────┘     └────┬─────┘
              │                     │                  │
         ┌────┴────┐            ┌───┴───┐          ┌───┴───┐
         │   DB    │            │ Write │          │ Read  │
         └─────────┘            │  DB   │          │  DB   │
                                └───────┘          └───────┘
```

## L1 — Model Separation Code Example

```java
// 写侧
@Service
public class OrderCommandService {
    private final OrderRepository orderRepository;

    @Transactional
    public OrderCreatedResult createOrder(CreateOrderCommand command) {
        Order order = Order.create(command);
        orderRepository.save(order);
        return OrderCreatedResult.from(order);
    }
}

// 读侧
@Service
public class OrderQueryService {
    private final OrderReadRepository orderReadRepository;

    public OrderDetailDTO getOrderDetail(String orderId) {
        return orderReadRepository.findDetailById(orderId)
            .orElseThrow(() -> new OrderNotFoundException(orderId));
    }

    public Page<OrderSummaryDTO> listOrders(OrderQuery query, Pageable pageable) {
        return orderReadRepository.findByCriteria(query, pageable);
    }
}
```

## L2 — Database Separation Code Example

```java
// 领域事件
public class OrderPaidEvent extends DomainEvent {
    private final String orderId;
    private final BigDecimal totalAmount;

    public OrderPaidEvent(String orderId, BigDecimal totalAmount) {
        super(orderId);
        this.orderId = orderId;
        this.totalAmount = totalAmount;
    }
}

// 事件处理器 → 同步到 Query DB
@Component
public class OrderPaidEventHandler {
    private final OrderReadRepository readRepo;

    @EventListener
    @Async
    public void on(OrderPaidEvent event) {
        OrderDocument doc = OrderDocument.from(event);
        readRepo.save(doc);   // 写入 Elasticsearch / Query DB
    }
}
```

## Event Sourcing Code Example（旧标签 L3，独立于 CQRS）

```java
// 事件溯源聚合
public class Order extends EventSourcedAggregate {
    private OrderStatus status;

    public void pay() {
        apply(new OrderPaidEvent(this.id));
    }

    @EventHandler
    private void on(OrderPaidEvent event) {
        this.status = OrderStatus.PAID;
    }
}

// 投影
@Component
public class OrderProjection {
    private final JdbcTemplate jdbc;

    @EventListener
    public void on(OrderPaidEvent event) {
        jdbc.update(
            "UPDATE order_projection SET status = ? WHERE id = ?",
            "PAID", event.getOrderId()
        );
    }
}
```

## 落地步骤

```
Phase 1: 评估（1d）
  → 分别评估模型分离、存储分离和 Event Sourcing 的必要性

Phase 2: 命令模型设计（1-2d）
  → 设计 Command 对象 → 实现 CommandHandler → 发布领域事件

Phase 3: 查询模型设计（1-2d）
  → 设计 Query 对象 → 实现 QueryHandler → DTO 组装

Phase 4: 事件同步（仅在选择异步投影或可靠事件外发时需要，按实际范围估算）
  → Outbox 表 → 事件发布器 → 投影更新
  → 幂等策略实现 → 重试/死信机制

Phase 5: 集成测试（1-2d）
  → Command → 领域事件 → Query DB 同步 → 验证最终一致
```
