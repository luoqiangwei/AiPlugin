# C 来源与提炼边界

以下一手入口已于 **2026-10-27** 读取；本文件用于核验，日常审查所需判断已写入语言模块。表中名称是官方资料名，不是本库的规则编号。

| 实际读取的官方资料 | 提炼用途 |
|---|---|
| [SEI CERT：有符号运算溢出](https://cmu-sei.github.io/secure-coding-standards/sei-cert-c-coding-standard/rules/integers-int/int32-c/) | 普通有符号溢出的未定义行为、运算类型、极值与运算前检查；不把回绕观察当语言保证 |
| [SEI CERT：整数类型转换](https://cmu-sei.github.io/secure-coding-standards/sei-cert-c-coding-standard/rules/integers-int/int31-c/) | 隐式/显式转换丢值、符号变化与大小参数的范围证明 |
| [SEI CERT：分配足够对象空间](https://cmu-sei.github.io/secure-coding-standards/sei-cert-c-coding-standard/rules/memory-management-mem/mem35-c/) | 元素大小、乘法上界与实际分配字节数保持一致 |
| [SEI CERT：对象的存储期](https://cmu-sei.github.io/secure-coding-standards/sei-cert-c-coding-standard/rules/declarations-and-initialization-dcl/dcl30-c/) | 自动对象地址逃逸及对象生存期结束后的使用 |
| [SEI CERT：读取未初始化内存](https://cmu-sei.github.io/secure-coding-standards/sei-cert-c-coding-standard/rules/expressions-exp/exp33-c/) | 自动标量、动态分配区的首次读取与路径完整初始化 |

资料中的规范引文与工具列表不等于本库已独立核验所有标准版本或检测器。语言模块以实际目标标准、类型范围与编译契约判定；原始资料中的历史风险评级不直接成为 finding 的优先级。示例和确认/反证是结合语言机制的原创审查归纳。
