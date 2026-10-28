# Spring 来源与提炼映射

本文件只用于出处核验与知识库维护；日常 Review 直接执行专项资料，不要求打开外链。资料核验日期：2026-10-27。

## 来源 → 审查能力

| 运行规则 | 原始依据 | 已提炼的决策能力 |
|---|---|---|
| 安全过滤链、方法与对象授权 | SPRING-01/02 | 执行首匹配链覆盖矩阵，再追最终对象授权；区分无链、公开入口和其他可信控制 |
| 事务边界、异步事件与投递 | SPRING-04/05 与原子性/故障恢复推导 | 证明代理、回滚与真正提交点；识别外围事务等反证，区分提交后执行和持久可靠交付 |
| 请求字段绑定、类型反序列化 | SPRING-06/12/13 | 把请求输入能力限制到用例字段；区分表单绑定、消息转换和任意类型实例化 |
| Reactive 执行与取消 | SPRING-10/11/14 | 分开组装、订阅、执行、上下文和取消；通过真实线程与资源行为排除误报 |
| 其他规则 | SPRING-03/07/08/09 | 从生效认证、SQL成本、表达式能力与管理端口实际入口判断风险 |

这里的流程与反例是工程归纳；框架 API、回滚策略和调度器容量按实际锁定版本复核。

## 历史案例证据

CVE-2022-22965（Spring4Shell）

**官方事实（SPRING-13）**：公告涉及 Spring Framework 数据绑定与 JDK 9+。其中公开的特定利用路径要求 Tomcat、WAR 部署及 `spring-webmvc` 或 `spring-webflux`；默认 Spring Boot executable JAR 不受该特定利用路径影响。官方同时明确漏洞本质更一般，不能由 JAR 部署推导为所有利用方式均不可能。公告列出的历史修复为 5.3.18、5.2.20.RELEASE。

**审查推导**：确认实际 Framework 版本、JDK、部署产物和数据绑定入口；进一步追踪绑定对象与允许字段。仅“使用 Spring”或 scanner 命中组件名称不是当前可利用证据。

**处理与验证**：升级到当前受支持且修复相关问题的版本，遵循对应公告的暂缓措施；历史最低修复版本不作为现在的推荐目标。回归覆盖不应绑定的嵌套/内部属性无法改变服务端状态、正常表单绑定仍可用，并保留真实依赖与部署证据。不得在生产执行可写文件或执行命令的历史利用脚本。

## 来源字典


以下来源均已于 **2026-10-27** 读取核验。Spring 与 Reactor 的无版本参考入口是移动入口，执行 review 时切换到项目版本。

| 来源 ID | 官方资料 | 用途 |
|---|---|---|
| SPRING-01 | [Spring Security Java Configuration](https://docs.spring.io/spring-security/reference/servlet/configuration/java.html) | 多链顺序、链选择与未匹配路径 |
| SPRING-02 | [Spring Security Method Security](https://docs.spring.io/spring-security/reference/servlet/authorization/method-security.html) | 方法授权启用、代理和表达式 |
| SPRING-03 | [Spring Security CSRF](https://docs.spring.io/spring-security/reference/servlet/exploits/csrf.html) | 默认保护、SPA 集成与测试 |
| SPRING-04 | [Spring `@Transactional`](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html) | 事务注解、代理模式和 self-invocation |
| SPRING-05 | [Spring Transaction Rollback](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/rolling-back.html) | 默认及自定义回滚语义 |
| SPRING-06 | [Spring MVC Data Binding](https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-data-binding.html) | 专用模型、构造器与允许字段 |
| SPRING-07 | [Spring Data JPA Query Methods](https://docs.spring.io/spring-data/jpa/reference/jpa/query-methods.html) | 参数、排序、fetch/load graph 与有界查询 |
| SPRING-08 | [Spring SpEL Evaluation](https://docs.spring.io/spring-framework/reference/core/expressions/evaluation.html) | 不可信表达式、EvaluationContext 与可达对象风险 |
| SPRING-09 | [Spring Boot Actuator Endpoints](https://docs.spring.io/spring-boot/reference/actuator/endpoints.html) | 暴露、访问控制、自动安全配置退让 |
| SPRING-10 | [Spring WebFlux Overview](https://docs.spring.io/spring-framework/reference/web/webflux/new-framework.html) | 线程、阻塞与背压模型 |
| SPRING-11 | [Reactor Context](https://projectreactor.io/docs/core/release/reference/advancedFeatures/context.html) | 订阅者上下文与 ThreadLocal 局限 |
| SPRING-12 | [OWASP Deserialization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Deserialization_Cheat_Sheet.html) | Java/JSON 等解码器的配置与信任边界 |
| SPRING-13 | [Spring 官方 CVE-2022-22965 公告](https://spring.io/security/cve-2022-22965/) | 历史受影响条件、修复和缓解入口 |
| SPRING-14 | [Reactor FAQ: Wrap a Synchronous, Blocking Call](https://projectreactor.io/docs/core/release/reference/faq.html#faq.wrap-blocking) | 2026-10-27 读取；用 fromCallable 推迟阻塞并在合适 scheduler 上订阅，不能用 just 包装已执行的调用 |
