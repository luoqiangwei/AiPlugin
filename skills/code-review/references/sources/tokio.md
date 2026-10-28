# Tokio 规则来源

以下是任务调度与取消规则实际采用的一手资料，核验日期为 2026-10-27。Rust 语言语义与其他运行时行为不由这些 API 文档定义；实际审查需匹配项目锁定的 Tokio 版本。

| 资料 | 提炼用途 |
|---|---|
| [Shared state](https://tokio.rs/tokio/tutorial/shared-state) | 区分短同步临界区、跨等待持锁和异步锁；按实际竞争与等待链判断 |
| [Select tutorial](https://tokio.rs/tokio/tutorial/select) | 以 Future 被停止轮询或销毁时的状态分析取消；不推导自动回滚 |
| [select! API](https://docs.rs/tokio/latest/tokio/macro.select.html) | 具体操作的取消安全契约、已产生进度与重试；使用时切换到依赖版本 |

任务能否丢弃、需要何种恢复由业务交付契约决定；取消相关测试不得强加并不存在的可靠交付要求。
