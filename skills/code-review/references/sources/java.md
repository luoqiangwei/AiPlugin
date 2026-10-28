# Java 一手依据

核验日期：2026-10-27。仅归档实际读取的官方契约；语言模块的风险场景、修复与反证为基于契约的审查推导。
Java 依据固定为 Java SE 25；用于其他版本时先确认相关语义与所用 API 是否存在。

## 对象相等与哈希

- [JDK Object：equals / hashCode](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Object.html#equals(java.lang.Object))。
- 已读：方法签名、相等关系五项约束、默认引用相等、相等对象 hash 一致要求。
- 支撑规则：只重载 equals 不改变集合经 Object 调用的语义；相等实现与 hashCode 必须一致。
- 判断边界：hash 相同不推出对象相等，不要求所有不同对象都有不同 hash。
- 审查应用：使用跨静态类型、独立实例与实际集合查找作区分性证据。

## 可变 key 的契约

- [JDK Map：接口说明](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/Map.html)。
- 已读：可变 key 注意事项、equals 比较受修改影响时的未指定行为、hash 优化许可。
- 支撑规则：追踪影响相等关系的存储期修改；不能用一次 containsKey 成功证明安全。
- 判断边界：不参与相等的字段修改不直接触发此契约；具体身份集合需按其自身语义解释。
- 审查应用：选择稳定 key，或在修改前移除并于修改后重新插入。

## 类型擦除与堆污染

- [JLS 类型擦除与运行时可表示类型](https://docs.oracle.com/javase/specs/jls/se25/html/jls-4.html#jls-4.6)。
- [JLS 引用类型变量与堆污染](https://docs.oracle.com/javase/specs/jls/se25/html/jls-4.html#jls-4.12.2)。
- 已读：参数化类型擦除、reifiable 类型范围、raw type 与泛型 varargs 的污染示例。
- 支撑规则：外层 List 检查不验证元素；泛型数组经超类型数组别名写入仍可破坏类型约束。
- 判断边界：unchecked 不等于已发生污染；封闭写入口可为局部 cast 提供证明。
- 审查应用：从真实写入追至失败读取；不把 SafeVarargs 注解当作实现安全证据。

## 资源关闭和异常优先级

- [JLS try-finally 执行](https://docs.oracle.com/javase/specs/jls/se25/html/jls-14.html#jls-14.20.2)。
- [JLS try-with-resources](https://docs.oracle.com/javase/specs/jls/se25/html/jls-14.html#jls-14.20.3)。
- 已读：finally 突然完成覆盖先前原因；资源初始化失败、逆序关闭与 suppressed 异常规则。
- 支撑规则：区分已注册资源与获取函数内部未返回资源；避免清理控制流覆盖主失败。
- 判断边界：自动清理覆盖资源声明中的成功初始化项，不自动清理任意外部获取的对象。
- 审查应用：组合初始化、业务和 close 失败，检查关闭顺序及主异常。

## 发布与 final 字段

- [JLS happens-before](https://docs.oracle.com/javase/specs/jls/se25/html/jls-17.html#jls-17.4.5)。
- [JLS final 字段语义](https://docs.oracle.com/javase/specs/jls/se25/html/jls-17.html#jls-17.5)。
- 已读：同一 monitor、volatile、线程启动的同步关系；正确构造时 final 与普通字段的可见性差别。
- 支撑规则：构造期 this 逃逸破坏使用前提；final 引用不覆盖被引用对象的后续可变状态。
- 判断边界：正确构造的不可变对象具有 final 初始化安全保证，不能泛化成所有普通引用传递都破坏 final 值。
- 审查应用：分别证明发布、构造后修改和引用及时可见性；不以压力测试未复现排除合法错误执行。
