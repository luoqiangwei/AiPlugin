# TypeScript 来源与提炼边界

以下 TypeScript 官方 Handbook 入口已于 **2026-10-27** 读取；模块中的风险判断是结合真实数据流与可变别名的审查归纳。

| 实际读取的官方资料 | 提炼用途 |
|---|---|
| [The Basics](https://www.typescriptlang.org/docs/handbook/2/basic-types.html) | 类型注解擦除与有效严格性设置；不把注解当运行时行为 |
| [Everyday Types](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html) | any 的传播、类型断言与非空断言的静态性质 |
| [More on Functions](https://www.typescriptlang.org/docs/handbook/2/functions.html) | unknown 需要收窄，适合作为尚未证明类型的数据边界 |
| [Narrowing](https://www.typescriptlang.org/docs/handbook/2/narrowing.html) | 控制流收窄、类型谓词与可辨识联合所表达的静态信息 |
| [Object Types](https://www.typescriptlang.org/docs/handbook/2/objects.html) | readonly 不改变运行时行为、不代表深度不可变，可经可变别名改变 |

Handbook 为持续维护资料；具体诊断与类型推断以项目锁定的 TypeScript 版本、配置和真实检查命令为准。“类型未生成校验”不表示所有 TypeScript 语法都被擦除，也不要求在可信内部调用中重复解析。共享值的失效风险须证明实际变更路径，不能仅从 readonly、回调或 await 的存在推断。
