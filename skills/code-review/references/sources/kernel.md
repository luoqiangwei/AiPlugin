# kernel 规则溯源

本文件仅用于追溯与版本核验；执行审查先使用专项资料中的判定步骤。外部资料不需要在每次 Review 中逐个打开。

## 历史漏洞：CVE-2022-0847 / Dirty Pipe

这是审查案例，不是受审项目的既成发现。发现者披露：受影响内核中，复用 pipe buffer 的状态与 page-cache 页面交互，使无特权进程可能改写只读文件内容；利用还受页面/偏移等条件限制。[KERNEL-S12]

上游修复 `9d2231c5d74e13b2a0546fee6737ee4446017903` 在 `copy_page_to_iter_pipe()` 和 `push_pipe()` 创建 `pipe_buffer` 时初始化 `flags`。审查启发是检查**所有创建路径和复用状态**，不能只看到最初分配清零就判安全。[KERNEL-S13]

处理：核对目标树两条初始化路径、后续 merge 行为及 vendor backport；依据设备供应方的实际修复状态升级或回补。回归思路是在隔离环境构造 pipe buffer 复用与文件页交互，确认不可改变只读文件，并覆盖正常 pipe/splice 行为。这个案例不提供“高于某版本永远安全”的判断规则。


## 权威来源字典

以下入口均于 **2026-10-27** 实际读取；`latest/master` 是动态入口，执行 review 时优先查受审树同版文档。每项来源只支撑对应契约；表中的风险组合与验证方案是本技能的审查归纳。

| 来源 ID | 标题与链接 | 用途 |
|---|---|---|
| KERNEL-S01 | [Submitting patches](https://docs.kernel.org/process/submitting-patches.html) | 补丁范围、用户影响、维护者与下游上下文 |
| KERNEL-S02 | [Linux Kernel patch submission checklist](https://docs.kernel.org/process/submit-checklist.html) | Kconfig、ABI 文档、checkpatch/sparse 与提交前检查 |
| KERNEL-S03 | [Lock types and their rules](https://docs.kernel.org/locking/locktypes.html) | 上下文、锁嵌套及 PREEMPT_RT 差异 |
| KERNEL-S04 | [Linux kernel memory barriers](https://docs.kernel.org/core-api/wrappers/memory-barriers.html) | 屏障、配对与 LKMM 边界 |
| KERNEL-S05 | [refcount_t API compared to atomic_t](https://docs.kernel.org/core-api/refcount-vs-atomic.html) | 引用计数与内存排序差异 |
| KERNEL-S06 | [What is RCU?](https://docs.kernel.org/RCU/whatisRCU.html) | 发布、读者与延迟回收 |
| KERNEL-S07 | [Memory Management APIs](https://docs.kernel.org/core-api/mm-api.html)、[upstream uaccess.h](https://github.com/torvalds/linux/blob/master/include/linux/uaccess.h) | 用户内存访问与复制契约；以目标树源码为准 |
| KERNEL-S08 | [Linux kernel coding style](https://docs.kernel.org/process/coding-style.html) | 集中式错误清理、局部复杂度及代码可读性 |
| KERNEL-S09 | [Kernel Testing Guide](https://docs.kernel.org/dev-tools/testing-overview.html) | KUnit/kselftest、sanitizer 与动态验证边界 |
| KERNEL-S10 | [ioctl based interfaces](https://docs.kernel.org/driver-api/ioctl.html) | uAPI、结构布局、兼容与信息泄漏 |
| KERNEL-S11 | [Security bugs](https://docs.kernel.org/process/security-bugs.html) | 精确版本/commit、问题证据与 reproducer 要求；不授权自动对外报告 |
| KERNEL-S12 | [The Dirty Pipe Vulnerability — original disclosure](https://dirtypipe.cm4all.com/) | 发现者的一手漏洞说明、触发条件 |
| KERNEL-S13 | [Upstream fix: initialize flags in new pipe_buffer](https://github.com/torvalds/linux/commit/9d2231c5d74e13b2a0546fee6737ee4446017903) | 已读取补丁的两处初始化修复 |
