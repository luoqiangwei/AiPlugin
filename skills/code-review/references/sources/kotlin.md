# Kotlin 一手依据

核验日期：2026-10-27。以下均为实际读取的 Kotlin 官方文档；示例与缺陷判断是基于这些契约的审查推导。
语言指南是移动入口；标准库页面当日显示 2.4。执行时按项目版本、目标平台及空值注解配置核对。

## Java 互操作与平台类型

- [Calling Java from Kotlin：空值安全与平台类型](https://kotlinlang.org/docs/java-interop.html#null-safety-and-platform-types)。
- 已读：T! 的含义、推断与显式 nullable / non-null 接收、生成的运行时断言、注解对类型的影响。
- 支撑规则：编译允许解引用平台类型不证明运行值非空；检查泛型和集合元素的真实来源。
- 判断边界：本规则针对 JVM 的 Java 互操作，不把所有 Kotlin 非空类型都归为不可靠。
- 审查应用：在边界恢复明确空值契约，避免把必有值的 API 机械改成静默忽略。

## 结构相等与数组

- [Equality](https://kotlinlang.org/docs/equality.html)。
- [Arrays：数组比较](https://kotlinlang.org/docs/arrays.html#compare-arrays)。
- 已读：== 转换为 equals(Any?)、普通类默认行为、错误重载签名、===、数组内容比较。
- 支撑规则：== 不是任意对象的自动逐字段比较；数组比较须选择合适的内容比较函数。
- 判断边界：值与身份语义由调用契约决定；不因使用 === 本身就报告缺陷。
- 审查应用：以独立构造的同内容实例区分身份与结构语义。

## data class 的生成成员

- [Data classes：主构造器、类体属性与复制](https://kotlinlang.org/docs/data-classes.html)。
- 已读：自动生成成员范围、显式或继承 final 方法的例外、类体属性不参与、copy 的浅复制。
- 支撑规则：移动属性会改变相等与复制语义；copy 共享引用，不复制类体可变状态。
- 判断边界：共享不可变内容可以正确，不要求无条件递归复制。
- 审查应用：同时检查去重结果、copy 后类体默认值和嵌套可变引用。

## inline 与非局部返回

- [Inline functions：非局部跳转与 crossinline](https://kotlinlang.org/docs/inline-functions.html#non-local-jump-expressions)。
- 已读：可内联 lambda 裸 return 的外层函数退出语义、标签返回、noinline 与 crossinline 限制。
- 支撑规则：循环与高阶函数互换时，逐条检查控制流目标。
- 判断边界：提前结束搜索是合法用途；不同参数修饰符须按实际声明解释。
- 审查应用：用首项不符合、后项符合的样例区分跳过本项与退出整函数。

## runCatching 的异常范围

- [标准库 runCatching](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin/run-catching.html)。
- [标准库 CancellationException](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin.coroutines.cancellation/-cancellation-exception/)。
- 已读：runCatching 捕获任意 Throwable 并包装为 failure；CancellationException 表示正常取消，JVM 实现为 Java 同名异常的 typealias。
- 支撑规则：捕获范围包含取消异常；只有实际转换与后续控制流才能证明取消被吞掉。
- 判断边界：包装后重新抛出仍传播；库级任务层次与取消检查点不由本语言模块推断。
- 审查应用：区分可恢复业务异常与契约要求传播的异常，检查默认值后是否继续副作用。
