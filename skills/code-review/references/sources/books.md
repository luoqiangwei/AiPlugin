# 书籍内容到审查规则的提炼记录

本文件保存采用关系和阅读深度，不参与默认 Review 流程。实际指令、原创示例、反证与验证都在 `../common/quality.md`、`../common/security.md` 和专项资料。核验日期：2026-10-27；公开摘录不等于全书，工程推演不冒充作者原话。

| ID / 书籍 | 实际读取的材料 | 提炼进入的能力与适用边界 |
|---|---|---|
| BOOK-01 / Code Complete, 2nd，Steve McConnell | 出版社公开第 5 章 [Design in Construction](https://www.microsoftpressstore.com/articles/article.aspx?p=2222451) 与 [Key Design Concepts 正文](https://www.microsoftpressstore.com/articles/article.aspx?p=2222451&seqNum=2) | 接口设计与封装：用调用者需要同时理解多少约束衡量抽象，而不是用类/函数行数判质量。把“管理复杂度”转成查找约束外泄和调用次序失配；不采用年代相关的工具与固定尺寸建议。 |
| BOOK-02 / Refactoring, 2nd，Martin Fowler | [作者的重构说明](https://martinfowler.com/books/refactoring.html) 与 [修改接口的重构边界正文](https://martinfowler.com/bliki/IsChangingInterfacesRefactoring.html)；未将下载介绍页当作已读完整首章 | “兼容性与演进”与主流程：先识别可观察行为，再比较重构前后；内部签名变化须覆盖全部调用者，已发布接口本身也是行为。测试和回滚是工程推演，不复刻书中案例。 |
| BOOK-03 / The Pragmatic Programmer, 20th Anniversary，David Thomas、Andrew Hunt | 出版社 [DRY 公开摘录正文](https://media.pragprog.com/titles/tpp20/dry.pdf)，关于知识重复、偶然相似及派生数据的段落 | 重复代码与业务规则：用“是否因同一需求变化而一起修改”判断知识重复；追踪派生状态同步；保留独立变化的相似实现。例子与实际操作步骤为原创，不使用摘录中的示例代码。 |
| BOOK-04 / A Philosophy of Software Design, 2nd，John Ousterhout | [作者书籍说明](https://web.stanford.edu/~ouster/cgi-bin/book.php) 核实版本；实质采用作者 [Modular Design 讲义正文](https://web.stanford.edu/~ouster/cgi-bin/cs190-spring16/lecture.php?topic=modularDesign)，未将未成功读取的书籍 PDF 当已读 | 接口设计与封装：找接口向调用者泄漏的表示、顺序和清理责任，再定位失配；不把拆更多类或更短方法当作天然改进。讲义与第二版全书有区别，仅映射已核实的共同主题。 |
| BOOK-05 / Working Effectively with Legacy Code，Michael Feathers | 出版社公开 [第 4 章 The Seam Model](https://www.informit.com/content/images/0131177052/samplechapter/0131177052_ch04.pdf)，关于可替换行为与 enabling point 的段落 | 测试有效性：对难测存量代码先找依赖替换点，保持被测核心逻辑一致，在边界观察行为；不因缺少单元测试要求重写，也不以 mock 掩盖需要验证的真实框架边界。 |
| BOOK-06 / Software Engineering at Google，Titus Winters、Tom Manshreck、Hyrum Wright 编 | 官方公开 [Code Review](https://abseil.io/resources/swe-book/html/ch09.html) 与 [Testing Overview](https://abseil.io/resources/swe-book/html/ch11.html) 中的流程和测试动机部分 | 主流程与测试有效性：审查评论区分必要修复与信息，测试为行为和安全变更提供证据。采用概念并以原创步骤实现，不复制、翻译或改编受限章节的表达，不把 Google 组织流程强加给所有项目。 |
| BOOK-07 / Effective Java, 3rd，Joshua Bloch | 出版社公开 [Generics 样章](https://www.informit.com/content/images/9780134685991/samplepages/9780134685991_CH05.pdf)，实际读取 raw types、heap pollution 和泛型 varargs 的契约；第 50/76 条仅核实目录 | 类型安全：把 unchecked warning 当作需要证明的类型边界，追踪错误值如何进入容器及在哪里触发强转。“对象所有权与可变数据”主题的具体可变性推理另由 [Oracle Java Secure Coding 的 Mutability 正文](https://www.oracle.com/java/technologies/javase/seccodeguide.html) 支撑；不声称从未读的第 50/76 条正文提炼。 |
| BOOK-08 / Java Concurrency in Practice，Brian Goetz 等 | 作者网站 [第 6 章 Task Execution 样章](https://jcip.net/jcip-sample.pdf)，实际读取任务独立性、无限线程、执行策略及排队相关内容 | 异步任务、取消与资源释放：分别审查提交、执行、积压、拒绝和关闭，固定线程数不等于全部工作有界。“并发与同步”主题的具体交错/原子性推演结合平台契约，不把本样章当作全书内存模型章节。 |
| BOOK-09 / Rust for Rustaceans，Jon Gjengset | 出版社 [Foundations 样章](https://nostarch.com/download/samples/RustforRustaceans_Ch1.pdf)，实际读取值/位置/指针、共享/独占引用与内部可变性段落 | “对象所有权与可变数据”和 Rust 语言规则：追踪真实值的所有者与别名，依据编译器允许假设的契约，而不是一次运行结果推断安全。具体 unsafe API 与 FFI 按 Rust 官方契约补足，任务调度和取消另按实际运行库契约补足。 |
| BOOK-10 / Secure by Design，Dan Bergh Johnsson、Daniel Deogun、Daniel Sawano | 出版社公开 [第 4 章概述](https://www.manning.com/preview/secure-by-design/chapter-4) 与 [第 5 章概述](https://www.manning.com/preview/secure-by-design/chapter-5)，属于公开章节概述而非已读付费全文 | 输入校验与状态约束、对象所有权与可变数据、安全输入处理：验证尽量在副作用前、用受控构造维护合法状态、廉价资源限制保护昂贵解析。转换为绕过入口、别名和失败点检查；不把领域类型当成授权机制，也不强制每个 primitive 都封装。 |

## 多源知识的工程化组合

“失败原子性”“错误处理与恢复”和“性能与资源开销”中的故障前缀、失败类别和成本推导，是结合上述契约/行为/资源思想与 [规范来源](standards.md) 编写的原创操作方法，不对应某本书逐字逐条的摘抄。最终适用性由当前代码、目标平台与业务契约决定。

提炼规则采用标准：能描述触发条件、推导反例、区分已安全的情形，并给出修复后必须满足的事实与验证。仅有书目、目录或营销描述不足以支持具体语言/API 结论。
