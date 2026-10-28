# Spring

先确认 Framework/Boot/Security/JDK 解析版本、Servlet/Reactive 栈、代理模式、profile、事务管理器和部署入口。注解和 starter 声明是线索；结论取决于真实调用经过哪些容器机制。HTTP/浏览器边界组合 Web 模块。示例省略无关装配，修复使用项目版本支持的 API。

## 检查入口字典

| 审查主题 | 进入条件 | 必须回答的问题 |
|---|---|---|
| 安全过滤链、方法与对象授权 | HTTP/方法安全变化 | 请求选中哪条链与规则，最终由谁对对象和租户授权？ |
| 事务边界、异步事件与投递 | 多步写入、异常、重试、事件 | 事务是否生效、何时结束、回滚哪些状态，外部副作用如何恢复？ |
| 请求字段绑定、类型反序列化 | 表单、JSON、消息解码 | 输入能控制哪些字段/类型，是否超过用例授予的能力？ |
| Reactive 执行与取消 | WebFlux、阻塞调用、线程切换 | 工作在何时/何处执行，主体跟随哪个订阅，取消后谁清理？ |
| 查询与表达式、持久化查询 | 查询、表达式、关联、分页 | 输入是否扩展解释器语义，SQL/锁/结果规模是否符合用例？ |
| CSRF 配置、管理端点 | 凭证、管理端点配置 | 生效配置是否暴露未计划的能力，异常路径是否同样受保护？ |

## 安全过滤链与方法授权

1. 按真实 `@Order` 排所有链，列每条 `securityMatcher`；将 URL、方法、Servlet 路径和 dispatcher 代入，**只沿首个匹配链**继续。
2. 在选中链查 `requestMatchers` 与兜底授权；链内 `anyRequest` 仅覆盖已选中该链的请求，不保护范围外路径。
3. 无匹配链时标为“未被这些链保护”，再查其他可靠授权与端点用途，不直接把公开静态资源判漏洞。
4. 沿 controller→service→repository 查对象/租户约束；方法安全须启用、bean 受管、调用实际经过代理，不能搜到 `@PreAuthorize` 就停止。

```java
// 风险假设：/internal/export 应受保护，但仅有这个范围内的链
http.securityMatcher("/api/**")
    .authorizeHttpRequests(a -> a.anyRequest().authenticated());
// 修复方向：给 /internal 明确策略，或以最后一条未限定范围的链兜底。
// catch-all 中按契约声明公开入口，其余 denyAll/authenticated/特定权限。
```

- **确认缺陷**：给出实际敏感入口及选链结果，证明匿名/低权限绕过所需控制；不用“无 catch-all”代替入口与影响证据。
- **反证**：可信网关覆盖所有入口且无源站旁路、服务方法完整授权，或端点本来公开。网关身份头须证明被替换，不能由客户端伪造。
- **回归**：真实 Security 配置下，匿名/普通/授权主体覆盖匹配边界、未知路径、不同方法、转发/错误分派、管理端口与源站。controller mock 不能证明过滤链或方法代理生效。

## 事务提交与异步事件

**先写不变式**，如“转账成功两端同时改变；失败均不改变”。画出 `调用者→代理→事务方法→数据库→异常→代理提交/回滚`，标真正提交点。

```java
// 风险：默认代理模式下，自调用未触发 move 的事务拦截
public void transfer() { this.move(); }
@Transactional public void move() { debit(); creditMayFail(); }

// 选择之一：完整用例是从外部调用的受管 bean 方法；也可用显式事务
@Transactional(rollbackFor = TransferFailure.class)
public void transfer() throws TransferFailure { debit(); creditMayFail(); }
```

- **先找反证**：入口已有有效事务、使用 AspectJ 或显式事务时，自调用不表示用例无事务；不机械拆 bean 或给每个方法加注解。
- **再查失败**：拦截器最终看到什么异常/结果？catch 后返回成功可能提交；unchecked/checked、显式规则、全局策略按版本确认，不声称“所有异常回滚”或“checked 永不回滚”。
- **查边界**：哪个事务管理器；传播是否独立提交；异步/线程切换是否脱离事务；Reactive 事务是否绑定实际返回的 publisher。两次 repository 各有事务不等于组合原子。
- **查外部事件**：数据库事务不能回滚已发送消息/外部扣款。仅需提交后执行可用提交后事件；要求崩溃不丢投递则需可恢复记录、可靠交付与幂等消费；提交后监听器本身不持久可靠。
- **确认缺陷**：给具体失败点/交错，证明不变式被破坏；注解缺失或 self-invocation 只是一部分证据。
- **回归**：通过真实代理和数据库在两次写入中间抛错，另起查询查最终状态。测试自身事务可能掩盖生产边界；覆盖成功提交、指定 checked 异常、吞错、提交后投递失败和重复消费，断言状态而非 mock 次数。

## 请求字段绑定与反序列化

1. 区分 `@ModelAttribute` 绑定、`@RequestBody` 消息转换和其他反序列化，不能用同一个 binder 配置笼统防护。
2. 从字段追到赋值和持久化，列服务端决定的 owner、tenant、role、price、审批状态，检查嵌套路径与更新映射。
3. 核对构造器/DTO/允许字段/映射的实际能力；`@Valid` 常只验证值，不表示调用者有权修改字段。

```java
// 风险：客户端 owner/role 直接进入持久化
update(@RequestBody Account entity) { repository.save(entity); }
// 修复示意：输入只表达用例允许的修改
record RenameAccount(String displayName) {}
update(id, RenameAccount input, Principal who) {
    Account account = loadAuthorizedForUpdate(who, id);
    account.rename(input.displayName()); // owner/role 不取自请求
}
```

- **确认缺陷**：用额外/嵌套字段证明调用者能改用例权限外状态。直接绑定 entity 风险高，但构造与映射真正限制能力时先验证反证。
- **最小修复**：专用输入加显式赋值；表单 binder 可收紧允许字段，但不会自动限制 JSON 转换器；denylist 容易被新增字段绕过。
- **类型反序列化**：若输入可选类/类型，再查允许类型、可调用构造器/方法与类路径。普通 JSON 不自动等于 RCE；字段越权按 mass assignment，不混称不可信反序列化。
- **历史漏洞提炼**：框架可遍历的对象图可能超出业务表面字段；安全升级与应用输入能力限制分别验证，危险字段黑名单不能代替维护者补丁。
- **回归**：正常改名成功；owner/role/tenant、嵌套内部属性、多态标记不能改内部状态；额外输入按契约拒绝或忽略。走真实 HTTP 转换后查询持久化，不只测 DTO validator。

## Reactive 的组装、执行与取消

```java
// 风险：just 参数在组装时已执行；scheduler 搬不走已发生的阻塞
Mono.just(jdbc.find(id)).subscribeOn(worker);
// 确需阻塞依赖：推迟到订阅，放到容量受控的合适执行环境
Mono.fromCallable(() -> jdbc.find(id)).subscribeOn(blockingWorker);
// 主体/租户随订阅读取，KEY 值须来自已验证的入口
Mono.deferContextual(ctx -> repository.findForTenant(ctx.get(KEY), id));
```

- **进入条件**：链中有 JDBC/JPA/文件 I/O、`block()`、ThreadLocal、调度切换、手动 `subscribe()` 或资源获取。
- **执行检查**：标出副作用在组装还是订阅、线程、重订阅/重试次数；查阻塞是否占 event loop，隔离是否只把无界压力搬到别的队列。Servlet 同步栈不机械改 Reactive。
- **上下文检查**：Context 属于订阅，不是全局变量；查写入位置、传播与读取。已配置且验证有效的官方 ThreadLocal 传播是反证，不因出现 ThreadLocal 就判串租户。
- **取消检查**：返回链能否等待任务和观察失败；脱离链手动订阅可能绕过取消/上下文/事务。对完成、错误、取消分别查资源释放；确需后台工作时应有明确队列、所有权和恢复契约。
- **确认缺陷**：证明阻塞在受影响线程、主体串用或取消后资源/副作用违反契约；混用 Mono 与同步 API 本身不是 finding。
- **回归**：两租户同线程/跨 scheduler 交错，多次订阅/retry、慢依赖、超时、客户端取消；查身份、查询次数、连接池与回收。StepVerifier 验信号，真实服务/数据库验线程与资源。

## 其余规则：按实际能力和成本判定

| 审查主题 | 执行判断 | 反证与验证 |
|---|---|---|
| CSRF 配置 | 先判浏览器自动携带会话/Basic 等凭证，再查防护/忽略范围；stateless、仅移动端不是证明 | 仅显式且攻击站点不可得的令牌前提不同；过真实链测缺失/错误 token 与合法请求 |
| 查询与表达式 | 跟 SQL/JPQL/SpEL 来源，参数化数据，动态语法用固定映射；不可信表达式查可达对象与副作用 | 固定表达式/正确绑定是反证；SimpleEvaluationContext 不是任意表达式的安全沙箱 |
| 持久化查询 | 查真实 SQL 次数、行数、fetch、分页/排序与序列化触发访问；并发写查版本/条件/数据库约束 | 没 EntityGraph 不等于 N+1；查询要给规模与成本。代表数据下断言增长、边界和并发最终状态 |
| 管理端点 | 从 profile、HTTP/JMX exposure、管理端口、代理/安全链确定可达能力；自定义链可能改变自动保护 | 可靠网络隔离与公开口不同，脱敏不等于匿名许可；测真实入口匿名/普通权限 |

用已有 wrapper、解析依赖树和针对性集成验证；不能装配时列明代理、profile、数据库和运行线程未验证。仅核验版本契约或公告时使用 [来源与提炼映射](../sources/spring.md)。
