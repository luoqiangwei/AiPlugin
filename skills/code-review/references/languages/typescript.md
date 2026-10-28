# TypeScript：静态类型承诺与运行时值

先读取实际 `tsconfig` 与类型检查入口，尤其 `strictNullChecks`、`noImplicitAny` 的有效设置；JavaScript 运行时语义同时组合 JavaScript 模块。编译目标、模块装载和框架类型约定按实际构建/运行场景检查，通用输入与所有权规则沿用公共规范。

## 类型声明不会验证运行时数据

遇到反序列化、JavaScript 调用方、声明文件或泛型解析器，区分“编译器相信的类型”与实际执行的检查。类型注解、接口和类型参数不会自动生成运行时校验；声明一个 `parse<T>` 不能证明数据符合 T。

```typescript
function parse<T>(text: string): T { return JSON.parse(text); }
const config = parse<{ retries: number }>(' {"retries":"many"} ');
config.retries.toFixed(); // 静态通过；运行时值仍是字符串
```

**确认条件**：存在真实入口把不匹配值送入依赖该类型的操作；外部边界应把值作为 `unknown` 并由实际解析/验证建立类型。**反证**：值来自已验证且无法绕过的构造路径，或声明精确描述可信实现；不要求每个内部函数重复校验，也不把所有 TypeScript 特性都说成会擦除。

## 断言与非空标记只是向检查器作承诺

遇到 `as`、双重断言、`!`、`is` 谓词或断言函数，逐个追查它们承诺的前提。`as T` 和非空断言没有运行时检查；自定义类型谓词的返回类型也不会替作者验证函数体覆盖了全部承诺。

```typescript
const entry = entries.find(item => item.key === key)!;
return entry.value; // 没找到时 ! 不会创建对象或抛出专门的校验错误
```

**确认条件**：合法可达路径违背断言前提，或类型守卫仅检查一个字段却放行后续依赖的其他字段。**反证**：不可绕过的不变式已证明非空/类型，局部断言准确表达编译器无法获知的事实。修复应建立缺失前提或处理缺失分支，不能仅换一种断言来消除告警。

## any 会把未证明的值传播成已声明类型

遇到显式/隐式 `any`、遗留库和动态索引，追踪它流入的赋值、返回值与调用参数。给接收变量补注解不会检查来自 `any` 的值；`noImplicitAny` 也不会禁止作者显式写下的 `any`。

```typescript
const raw: any = { count: "many" };
const count: number = raw.count; // 注解没有恢复保证
count.toFixed();
```

**确认条件**：具体不匹配值能沿失去检查的路径到达错误操作。**修复与验证**：在信息未知处使用 `unknown`，收窄后再进入有类型的核心，验证错误样本不能穿透。**反证**：局部兼容层拥有完整的运行时约束并封闭不安全值；单独出现 `any` 不足以确认缺陷，不为消除告警改成同样无依据的强转。

## 收窄和 readonly 不冻结共享对象

遇到可选属性收窄后调用回调/等待，或将可变对象暴露为 `Readonly<T>`，检查别名是否还能修改被依赖的值。收窄表达静态控制流信息；`readonly` 只限制相应静态写法，不改变运行时属性，也不自动递归冻结内部对象。

```typescript
const shared: { name?: string } = { name: "ready" };
const view: Readonly<typeof shared> = shared;
if (view.name !== undefined) {
  delete shared.name;
  view.name.toUpperCase(); // readonly 别名没有保住刚才检查过的值
}
```

**确认条件**：存在检查与读取之间的实际变更路径，或调用方把 readonly 当作运行时不可变保证。**反证**：此值为独立不可变快照，或全部写入被有效约束；仅有异步函数不能证明它会改变对象。按契约在使用时重新检查、保存已验证的不可变字段或建立真正的所有权限制，并验证变更路径而非仅看编译通过。

出处与适用边界见 [TypeScript 来源](../sources/typescript.md)。
