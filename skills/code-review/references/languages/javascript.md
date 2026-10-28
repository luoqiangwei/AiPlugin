# JavaScript：转换、数值与 Promise 执行语义

本文件适用于 ECMAScript 语言与标准内置对象；DOM、Node.js I/O、宿主定时器及框架生命周期按实际运行场景继续审查。通用输入约束、资源预算和并发不变式沿用公共规范。

## 转换规则应与允许的数据类型一致

遇到混合类型的 `+`、宽松相等、真值判断或默认值，写出实际值和类型。`+` 可能拼接字符串，`==` 会按算法转换，`||` 会把合法的 `0`、`false`、空字符串也当作缺省；它们不等同于领域解析。

```javascript
const next = "9" + 1;      // "91"，不是 10
const retries = supplied || 3; // supplied 为 0 时也得到 3
// 只把 null/undefined 视作缺省时：const retries = supplied ?? 3;
```

**确认条件**：可达类型/值被转换成不同业务含义，且改变判断或结果。**反证**：接口明确允许并验证该转换，或 `value == null` 有意同时匹配 `null`/`undefined`；不机械禁止所有宽松相等。修复须明确允许格式与类型，不能只加 `Number()` 后忽略空字符串、`NaN` 等结果。

## Number 的整数与小数精度都有限

遇到标识符、计数、精确金额或位运算，追踪值在解析前是否已经损失精度。Number 使用二进制双精度；安全整数范围为 `-(2**53-1)` 至 `2**53-1`，范围内的整数结果也仍需检查运算后是否安全。小数不能因绝对值小就假定精确。

```javascript
Number("9007199254740992") === Number("9007199254740993"); // true
0.1 + 0.2 === 0.3; // false
```

**确认条件**：需求要求区分的值会合并，或舍入改变实际比较/累计；`Number.isInteger` 不能证明安全整数。**修复**：按契约保留字符串、从原始文本构造 BigInt 或使用所需精度的运算，避免先转 Number 再补救；BigInt 与 Number 算术混用会抛异常。**反证**：上下界与全部中间结果有证明，或误差明确在可接受预算内；不因使用浮点就报告缺陷。

## Promise 链只等待返回或显式等待的工作

遇到 `.then`、`async` 与 `try/catch`，检查每个回调的返回值和每个新 Promise 的去向。处理器抛出的异常拒绝它返回的新 Promise；未返回的异步工作不会被外层链等待。`try/catch` 只能捕获当前同步抛出或在其中 `await` 恢复出的拒绝。

```javascript
return ready.then(() => { persist(); }); // persist 返回的 Promise 脱离此链
// 要让调用者等待并观察失败：return ready.then(() => persist());
```

**确认条件**：外层提前成功或遗漏可达拒绝，破坏调用方的完成/失败契约。**反证**：工作确需独立执行，且独立链有明确失败处理；不要求把全部后台工作串行等待。检查拒绝处理器正常返回是否有意把后续链变为成功；宿主如何展示未处理拒绝须转实际运行场景核实。

## async 不会把函数体一次性变成异步任务

调用 `async` 函数时，首个 `await` 之前的代码立即运行；`await` 之后的继续执行会让出当前调用，即使等待的值已经兑现或只是普通值。`.then` 处理器也异步执行；两个独立链不会自动等待彼此。

```javascript
const events = [];
async function run() { events.push("start"); await 0; events.push("end"); }
const done = run(); events.push("caller"); await done;
// events 为 ["start", "caller", "end"]
```

**确认条件**：依赖错误的同步/异步顺序，导致某个实际交错读到过期状态或提前使用结果。**反证**：代码已通过返回的 Promise、明确链式依赖或不可变值保证所需顺序。给出具体交错并验证观察结果；不能从语言 Promise 顺序推断不同宿主的定时器、I/O 或渲染顺序。

出处与适用边界见 [JavaScript 来源](../sources/javascript.md)。
