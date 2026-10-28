# Kotlin 语言与标准库审查

本模块覆盖语言与标准库语义，按项目的 Kotlin 版本和目标平台解释；Java 互操作部分适用于 JVM。框架状态、调度和任务生命周期由对应场景模块判断。

## 平台类型把空值证明留在互操作边界

**进入条件**：调用 Java 接口、依赖空值注解或使用 `!!` 把输入收窄为非空。
Java 未提供有效空值信息时，推断值可能是平台类型 `T!`，编译器允许把它当作 `T` 或 `T?`。声明成 `String` 或调用成员不证明 Java 真会返回非空；运行时可能在赋值、传参或解引用处抛 NPE，集合元素和泛型也要追踪。

```kotlin
val name: String = legacy.name // 编译通过；Java 返回 null 仍会失败
// 若 null 是合法“未提供”，在边界保留 nullable 后按契约处理。
val nameOrNull: String? = legacy.name
```

风险→修复：可空输入经 `!!` 进入稍后才失败的业务路径 → 在取得值时执行有业务含义的拒绝、默认或缺省分支；能维护 Java API 时提供项目编译配置实际识别的空值注解。

**关键反证**：真实 Java 契约保证非空且调用始终满足前提时，非空接收可以正确；不要因平台类型本身要求所有调用都加 `?.`。

## 相等运算符依赖 equals 的实际实现

**进入条件**：去重、缓存匹配、数组比较或把普通类改为 data class。

`a == b` 调用空值安全的 `equals(Any?)`；普通类没有自动按属性生成相等，`equals(other: Foo)` 重载也不改变 `==`。`===` 检查引用身份，不适合作为一般内容比较。

```kotlin
val a = intArrayOf(1, 2)
val b = intArrayOf(1, 2)
check(a.contentEquals(b)) // 按元素；a == b 不承诺此语义
```

风险→修复：内容相同的独立实例被当成不同项 → 明确值相等或身份相等契约，覆盖正确签名并同步 hashCode；数组按需要选择 `contentEquals` 或嵌套数组的 `contentDeepEquals`。

**验证**：独立构造的相同内容、不同内容、null 与实际集合操作；共享同一实例的测试不能区分身份比较与值比较。

## data class 的生成范围与 copy 都不是深快照

**进入条件**：修改主构造器属性、在类体增加状态、复制可变数据。

自动生成的 equals、hashCode、componentN 和 copy 以主构造器属性为依据；类体属性不自动参与。把版本号从主构造器移到类体，可能让不同版本被去重，copy 后类体属性也会重新按构造过程初始化。

```kotlin
data class Draft(val lines: MutableList<String>) { var revision = 0 }
val first = Draft(mutableListOf("a")).also { it.revision = 7 }
val next = first.copy() // lines 指向同一列表；revision 重新为 0
```

风险→修复：将 copy 当成独立编辑草稿 → 明确复制参与的状态，并复制实际需要隔离的可变层；`val` 只禁止重新赋值，不能阻止上述列表被修改。

**关键反证**：共享部分已不可变或契约明确要求共享时，浅拷贝可以正确；显式 equals/hashCode 或父类 final 实现会改变自动生成行为，应先查看实际声明。

## inline lambda 的 return 可能退出外层函数

**进入条件**：forEach、run 等 inline 调用内新增 return，或把循环改成高阶函数。
可内联 lambda 的裸 `return` 可直接退出外层命名函数；`return@forEach` 才只结束该次 lambda。风险：遇到一条无效记录就跳过剩余处理与后续提交 → 若契约是继续遍历，使用明确的局部标签或普通循环。

**关键反证**：找到目标即退出搜索正需要非局部返回。标为 crossinline/noinline 的参数与匿名函数有不同控制流限制，不因看到 lambda 就假定裸 return 可用；直接检查声明和编译结果。

## runCatching 捕获范围包含控制异常

**进入条件**：使用 runCatching / getOrElse / recover，把失败改成默认结果。

标准库 runCatching 捕获所有 Throwable；inline 本身不会把捕获范围缩成业务异常。CancellationException 同样会变成 Result.failure；若调用契约要求取消传播，后续默认值处理可能把中止信号变成继续执行。

风险→修复：只想恢复解析失败却捕获了所有异常 → 对已知可恢复类型定向 catch；需要传播的取消或其他控制异常在转换为默认值前重新抛出。把异常封装并随后 getOrThrow 仍可传播，单用 runCatching 不能证明吞取消。

**验证**：各选一个约定可恢复异常和必须传播的异常，检查最终结果及之后的副作用。具体取消检查点、父子任务和资源生命周期按运行库契约审查，不从 runCatching 语法推断。

出处与适用边界见 [Kotlin 一手依据](../sources/kotlin.md)。
