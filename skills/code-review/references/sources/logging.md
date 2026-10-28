# 日志审查资料来源

核验日期：2026-10-27。以下均实读官方正文；只归档本次实际采用内容，运行判断在 `common/logging.md`，无需执行前逐个访问。正文示例和审查流程为本技能原创归纳。

| 一手资料与已读范围 | 采用内容 | 限制与本地映射 |
|---|---|---|
| [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)：Purpose；Which events to log；Event attributes；Data to exclude；Customizable logging；Event collection；Verification；Attacks on Logs | 安全事件按风险选择、事件上下文、敏感数据最小化、编码防注入、默认可见性、日志故障和资源耗尽验证 | 是安全日志指南，不把所有输入拒绝定为 ERROR；映射到覆盖、字段安全、失效与验证。审计成功条件仍从项目契约取得 |
| [OpenTelemetry Logs Data Model](https://opentelemetry.io/docs/specs/otel/logs/data-model/)：Log and Event Record Definition；Trace Context Fields；Severity Fields；Attributes | 级别语义、原日志框架的语义映射、时间/关联上下文/事件属性的职责区分 | 核验页面标记 Stable，文档站显示 OTel 1.62.0。仅用作通用意图参照；不要求项目接入 OTel，也不将其数值级别强加给仓库 |
| [Python Logging HOWTO](https://docs.python.org/3/howto/logging.html)：When to use logging；Advanced Logging Tutorial；Exceptions raised during logging；Optimization | DEBUG 至 CRITICAL 的用途、handler/过滤影响可见性、普通日志故障隔离、参数格式化与昂贵参数求值的区别 | 核验入口显示 Python 3.15.2；只提炼上述通用机制，不规定其他运行时的默认级别或异常处理行为 |
| [Apache Log4j API](https://logging.apache.org/log4j/2.x/manual/api.html)：Introduction；Best practices | 显式/上下文字段、异常对象的诊断价值、稳定参数模板、延迟昂贵参数 | 对应拥有者所需上下文、cause 和构造成本；具体 Throwable 参数位置、supplier 与过滤行为需核对项目 API，不能跨框架照搬 |
| [Apache Log4j Performance](https://logging.apache.org/log4j/2.x/manual/performance.html)：Using Log4j API efficiently；Location information；Asynchronous logging | 栈位置成本、异步队列吞吐/异常传播权衡，以及日志属于业务审计时的可靠性交付差异 | 映射到热路径、队列饱和、sink 故障和强审计边界；不将异步或同步方式本身判为缺陷，不要求未经测量的优化 |

## 工程归纳的边界

- 从成功/失败/降级/恢复/取消/拒绝分支枚举事件，再追日志拥有者，是本技能的覆盖方法；来源没有要求每个函数都写日志。
- “同一最终失败由合适边界记录”用于避免重复栈和责任空洞；独立阶段、补偿和恢复事件可以各自记录，不能机械执行“一异常一日志”。
- 必须保留的事件由诊断与安全审计契约确定。指标、链路或统一审计能否替代，取决于它们的覆盖、采样、字段与可靠性，不能只凭名称认定。
- 级别表表达意图并服务于生产过滤和告警；普通取消/校验不自动是系统 ERROR，是否记录安全拒绝与选择什么级别是两项判断。
- 最终失败/恢复不被全部采样丢弃、限流键与索引基数有界、强审计失败策略服从契约，是结合可诊断性与资源预算的本地推导，不宣称为所有来源逐字要求。
- 后续审查遇到版本敏感的格式化、异常输出、队列或过滤语义，按仓库锁定版本复核；本次未把未读书籍、二手摘要或搜索结果列为依据。
