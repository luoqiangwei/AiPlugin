# JavaScript 来源与提炼边界

以下规范与正式参考已于 **2026-10-27** 读取；运行模块给出完整判断，来源只用于后续维护。

| 实际读取的资料 | 提炼用途 |
|---|---|
| [TC39 ECMAScript：抽象操作](https://tc39.es/ecma262/multipage/abstract-operations.html) | 类型转换、真值与比较算法；区分值域约定和隐式转换 |
| [TC39 ECMAScript：表达式](https://tc39.es/ecma262/multipage/ecmascript-language-expressions.html) | 字符串/数值二元操作分支，以及 Number 与 BigInt 算术混用的异常 |
| [TC39 ECMAScript：数据类型与值](https://tc39.es/ecma262/multipage/ecmascript-data-types-and-values.html) | Number 的 binary64、整数表示边界与舍入基础 |
| [TC39 ECMAScript：Number 内置对象](https://tc39.es/ecma262/multipage/numbers-and-dates.html) | isInteger 与 isSafeInteger 的区别，以及安全整数上下界 |
| [MDN 正式参考：Promise.prototype.then](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise/then) | 返回值/异常决定新 Promise 状态，异步处理器及独立链的等待关系 |
| [MDN 正式参考：async function](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/async_function) | 首次 await 之前同步运行，后续代码分段恢复 |
| [MDN 正式参考：await](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/await) | 拒绝恢复为抛出、已兑现或普通值也暂停继续执行的语义 |

TC39 页面是持续更新的语言规范；这里未引入提案阶段特性。MDN 页面中的宿主定时器、网络与浏览器示例仅帮助理解，本库没有把它们的特定运行顺序推广为 ECMAScript 保证。精度、链遗漏和交错的示例为原创推导，只有破坏实际契约时才形成 finding。
