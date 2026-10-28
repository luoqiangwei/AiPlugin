# rust 规则溯源

本文件仅用于追溯与版本核验；执行审查先使用专项资料中的判定步骤。外部资料不需要在每次 Review 中逐个打开。

## 历史漏洞：CVE-2024-24576 / Windows batch 参数注入

Rust 官方公告指出：Windows 上使用 `std::process::Command` 向 `.bat/.cmd` 传入不可信参数时，旧的转义处理可被绕过；其他平台和不满足该调用条件的用法不受这份公告影响。公告列出的历史修复版本是 **1.77.2**，不是本技能推荐的“当前最新版本”。[RUST-S10]

修复增强转义，并对不能安全转义的参数返回 `InvalidInput`。审查时追踪输入→依赖→实际 Windows batch 调用，核对构建时工具链/std，而非只看 `Cargo.lock`。升级到项目支持且包含该修复的工具链，重新构建和分发产物；不要建议用 `raw_arg` 作为通用修复，因为那会绕过标准库转义。[RUST-S10]

回归思路：在隔离 Windows 环境验证含元字符参数不会产生额外命令；确认合法参数仍可用、`InvalidInput` 被正确处理，并覆盖依赖中的间接调用。历史案例只有在受审构建和可达路径满足条件后，才能转化为当前 finding。


## 权威来源字典

以下入口均于 **2026-10-27** 实际读取；表中风险组合与验证方案是技能的审查归纳，不应冒充来源逐条强制要求。

| 来源 ID | 标题与链接 | 用途 |
|---|---|---|
| RUST-S01 | [Rust Reference: Behavior considered undefined](https://doc.rust-lang.org/reference/behavior-considered-undefined.html) | UB、safe 抽象 soundness 与模型尚未完全确定的边界 |
| RUST-S02 | [Rustonomicon: How Safe and Unsafe Interact](https://doc.rust-lang.org/stable/nomicon/safe-unsafe-meaning.html) | unsafe 与 safe 客户端的责任边界；具体规则以同版 Reference/API 为准 |
| RUST-S03 | [Rustonomicon: FFI](https://doc.rust-lang.org/nomicon/ffi.html) | ABI、布局、所有权、回调与 unwind |
| RUST-S04 | [Rustonomicon: Exception Safety](https://doc.rust-lang.org/nomicon/exception-safety.html) | panic 期间保持内存安全和清理不变式 |
| RUST-S05 | [Rustonomicon: Send and Sync](https://doc.rust-lang.org/nomicon/send-and-sync.html) | unsafe trait 与跨线程安全 |
| RUST-S07 | [Rust API Guidelines checklist](https://rust-lang.github.io/api-guidelines/checklist.html) | API 契约、错误、类型安全、文档和兼容性审查 |
| RUST-S08 | [RustSec Advisory Database](https://rustsec.org/) | Cargo.lock 已知漏洞检查与公告来源 |
| RUST-S09 | [cargo-deny official documentation](https://embarkstudios.github.io/cargo-deny/) | advisories、licenses、bans、sources 策略的配置边界 |
| RUST-S10 | [Rust Security Response WG: CVE-2024-24576](https://blog.rust-lang.org/2024/04/09/cve-2024-24576/) | Windows batch 漏洞条件、历史修复与错误语义 |
| RUST-S11 | [Miri official repository](https://github.com/rust-lang/miri) | 可发现的 UB、执行/平台/FFI 限制及不能证明 soundness |
| RUST-S12 | [std::slice::from_raw_parts Safety](https://doc.rust-lang.org/std/slice/fn.from_raw_parts.html) | 2026-10-27 补核零长度指针、单一分配、有效范围、借用存活期与初始化前提；使用时选择目标工具链文档 |
| RUST-S13 | [String::from_utf8_unchecked Safety](https://doc.rust-lang.org/std/string/struct.String.html#method.from_utf8_unchecked) | 2026-10-27 补核 String 的 UTF-8 不变式及后续内存安全影响；不是“任何错误输入立即崩溃”的证明 |
| RUST-S14 | [std::mem::replace](https://doc.rust-lang.org/std/mem/fn.replace.html) | 2026-10-27 补核用有效值替换字段并取出旧值的所有权语义；用于对比临时无效字段跨 panic 点的风险 |
