# eBPF 执行规则来源

本文件供版本核验与争议溯源；可执行审查步骤已写入专题。以下页面于 **2026-10-28** 实际打开并读取相关正文，未把搜索摘要、目录或未读取的链接当作依据。

## 内核文档与采用范围

`docs.kernel.org` 是滚动文档，本次读取不是对任何 Android/vendor 内核的兼容承诺。遇到实现、配置和文字冲突时，回到受审内核 commit、同版 UAPI、加载器和真实行为；表中的风险组合、修复形状和测试矩阵是本技能的审查归纳。

| 已读取来源 | 本地采用的语义 | 限制 |
|---|---|---|
| [eBPF verifier](https://docs.kernel.org/bpf/verifier.html) | 寄存器/栈初始化、指针范围、nullable map value、direct packet access、程序类型限定 helper；把拒绝日志还原成访问和引用证明义务。 | 开头包含 DAG/禁止循环的历史概述；不据此判定目标不支持 bounded loop，也不从示例推导当前通用复杂度上限。 |
| [BPF maps](https://docs.kernel.org/bpf/maps.html) | map 创建、lookup/update/delete 的职责；BPF 与用户态围绕 map 交换数据。 | 概览中的简化生命周期和错误描述须结合 UAPI；FD 关闭仍有 pin/attachment 等引用时不保证对象销毁。 |
| [Hash maps with PERCPU and LRU variants](https://docs.kernel.org/bpf/map_hash.html) | hash 共享 value、per-CPU slot、LRU 驱逐、更新 flags、lookup NULL、跨 CPU 同步与删除期间遍历变化。 | LRU 内部回收算法不当稳定 ABI；原子替换不自动扩大为复合读改写事务。 |
| [Array and per-CPU array maps](https://docs.kernel.org/bpf/map_array.html) | array 预分配、原地 value 共享、per-CPU 用户态读取和 array 不支持 delete。 | 示例中的 `long`/数组写法不直接作为跨架构共享 ABI；缓冲区大小、slot 对齐须核对所用接口。 |
| [BPF ring buffer](https://docs.kernel.org/bpf/ringbuf.html) | 空间不足 reserve 非阻塞失败、预留记录需提交/丢弃、消费者与生产者共享容量，快照不能证明后续空间。 | 文档的概念名 `commit` 与目标 helper 名称分开；v6.12 UAPI 使用 `bpf_ringbuf_submit`。不保证全部事件可靠交付。 |
| [Running BPF programs from userspace](https://docs.kernel.org/bpf/bpf_prog_run.html) | `BPF_PROG_RUN` 与旧名 `BPF_PROG_TEST_RUN` 同值；按类型提供上下文/包，普通执行与真实 action、XDP live-frame 模式区分。 | 支持的类型和 flags 必须在目标树核验；普通模式不真实 drop/redirect，但程序仍可改变 maps，不转述为“无任何副作用”。 |
| [libbpf Overview](https://docs.kernel.org/bpf/libbpf/libbpf_overview.html) | open/load/attach/teardown 分阶段，CO-RE 借编译信息、libbpf 与目标 BTF 解析重定位，skeleton 反映对象内容。 | 仅用于采用 libbpf 的项目；便携性概述不证明缺失 helper/type/config 会被补齐，不推断 Android 默认采用。 |
| [BPF Type Format](https://docs.kernel.org/bpf/btf.html) | BTF 的类型、函数与行信息以及内核 API/ELF 信息边界，供重定位和诊断关联。 | BTF 可描述结构不表示对应 hook/kfunc 可用，类型匹配也不证明业务语义兼容。 |
| [API naming convention](https://docs.kernel.org/bpf/libbpf/libbpf_naming_convention.html) | 区分 sys_bpf 包装接口、ELF 对象和高层生命周期接口，避免同名 helper/用户态接口混淆。 | 错误返回按实际 libbpf 版本或其他加载库核验，不从命名前缀推断所有接口同一错误约定。 |
| [HOWTO interact with BPF subsystem](https://docs.kernel.org/bpf/bpf_devel_QA.html) | 同目标内核版本的 BPF selftests 优先、配置与编译依赖影响结果；LLVM/BPF 目标和新指令能力需配套。 | 文中的示例 LLVM/pahole 版本、测试数量和命令是历史说明，不当当前项目的固定最低版本或通过证据。 |
| [BPF Design Q&A](https://docs.kernel.org/bpf/bpf_design_QA.html) 与 [v6.12 原文](https://raw.githubusercontent.com/torvalds/linux/v6.12/Documentation/bpf/bpf_design_QA.rst) | helper/内核对象扩展、内部探针与类型不是稳定 UAPI、限制需结合目标实现；供兼容边界复核。 | bounded-loop 章节仍写“尝试支持”，且部分上限陈旧；明确不采用这些文字作现行功能判定。 |
| [BPF ABI conventions v1.0](https://docs.kernel.org/bpf/standardization/abi.html) | R0 的函数/程序返回职责与调用约定，辅助定位编译产物。 | 该文档自称信息性建议；hook 返回值的业务行为另由具体 program/attach 契约确定。 |

## 固定版本的源码补充

本次用上游 **Linux v6.12 tag** 作为可复核的语义样本，不把它当设备分支、当前最新版本或所有 Android 设备基线。

| 已读取源码 | 实际核验的内容 | 应用边界 |
|---|---|---|
| [v6.12 include/uapi/linux/bpf.h](https://raw.githubusercontent.com/torvalds/linux/v6.12/include/uapi/linux/bpf.h) | `bpf()` 原始错误约定；map flags；pin 保留/解除引用；program load 与 attach 分离；tail call 成功不返回、失败继续；`bpf_skb_pull_data` 使旧包指针检查失效；spin lock 限制；perf 输出初始化；ringbuf reserve/submit/discard；TEST_RUN 别名。 | 源码 helper 注释与可用性仍要和目标 `get_func_proto`、程序类型、配置及实现对应；不把 v6.12 的限制列表和数值硬编码成通用规则。 |
| [v6.12 kernel/bpf/verifier.c](https://raw.githubusercontent.com/torvalds/linux/v6.12/kernel/bpf/verifier.c) | `is_state_visited` 的 bounded-loop/迭代器与无限循环检查、`check_cfg` 及其回边处理路径；证实不能只复制文件开头/DAG 历史注释。 | 只采用“核对实际实现和能力”的判定方法；未声称已审计 verifier 本身安全，也未运行加载或 selftests。 |
| [v6.12 tools/lib/bpf/libbpf.c](https://raw.githubusercontent.com/torvalds/linux/v6.12/tools/lib/bpf/libbpf.c) | `validate_map_op` 以 possible CPUs 与对齐后的 value 大小检查 per-CPU 缓冲区；`bpf_link__disconnect` 注释区分库对象释放与实际资源存活；perf buffer 处理 lost 记录。 | 本文只要求核对对应 ABI 与生命周期，不把该版 libbpf 的实现强加于 Android 其他加载器。 |
| [v6.12 net/bpf/test_run.c](https://raw.githubusercontent.com/torvalds/linux/v6.12/net/bpf/test_run.c) | `bpf_test_run` 直接执行程序、返回 action；XDP 普通和 live 模式分支不同。由真实执行推导测试可能改变其引用的 maps，不能理解为只做静态校验或自动回滚。 | 用于澄清文档“无副作用”在 drop/redirect 上的范围；不承诺其他类型/flags 的通用行为，测试须隔离可变数据。 |

## 规则推演与验证边界

- 包解析、map 竞争、tail-call fallback、事件半初始化和升级旧 schema 示例均为原创简化审查形状，不代表已确认的项目缺陷。
- 多字段快照、发布/迁移窗口、容量预算、隐私字段和失败策略必须由产品契约确定；资料中的机制不能替项目选择 fail-open/fail-closed 或是否允许近似统计。
- 本次仅建立文档与来源，不编译、不加载、不 attach 真实 BPF，也未执行任何目标设备测试。后续报告应明确区分静态推导、加载证据、程序逻辑测试和真实 hook 的端到端结果。

## helper 成本与性能审查的补充核验

以下内容于 **2026-10-28** 读取相关函数和注释，用于将性能风险转成可确认的 Review 场景；没有据此编造 helper 耗时排名或“最常见问题”的统计结论。

| 已读来源 | 采用到审查中的判断 | 不应推出的结论 |
|---|---|---|
| [v6.12 net/core/filter.c](https://raw.githubusercontent.com/torvalds/linux/v6.12/net/core/filter.c) 的 `bpf_skb_pull_data`、`bpf_skb_store_bytes`、`bpf_skb_load_bytes` 与 `bpf_unclone_prologue` | pull 的范围、逐段拷贝与可写化应按实际包表示计入成本；`len=0` 使用 `skb_headlen`，`len=skb->len` 要求整个包范围。只读少量头却拉全包、筛选前拉包、循环反复读取/拉包是进一步取证入口。 | 不是每次 pull 都分配/复制，也不能把 `pull_data(0)` 说成全包线性化；直接写包可能已有自动 unclone 前导逻辑，必要 pull、错误处理和失效后的边界重建不能删。 |
| [v6.12 net/core/skbuff.c](https://raw.githubusercontent.com/torvalds/linux/v6.12/net/core/skbuff.c) 的 `skb_ensure_writable` | 先 `pskb_may_pull`，符合条件的非克隆/可写克隆走快路径，否则可进入 `pskb_expand_head(..., GFP_ATOMIC)`；解释 cloned/nonlinear 包为什么可能暴露不同成本。 | 不从一次线性、未克隆的微基准推导所有包成本；分配、拷贝和失败率须由目标实现与实际输入证明。 |
| [v6.12 UAPI helper 文档](https://raw.githubusercontent.com/torvalds/linux/v6.12/include/uapi/linux/bpf.h) 的 `bpf_trace_printk`、`bpf_perf_event_output`、`bpf_get_stackid/get_stack` | trace_printk 定位调试用途；事件输出和栈采集有实际格式化/数据传输/栈遍历工作。先判断是否需要、是否应在过滤/采样之后，再评估输出大小和消费速率。 | perf/ringbuf 更适合数据输出不等于逐次输出免费；栈 helper 的支持类型和采样用途须核对，不能要求网络程序使用未支持 helper，也不能以逐帧 probe-read 手写遍历作为通用优化。 |
| [BPF ring buffer](https://docs.kernel.org/bpf/ringbuf.html) 的输出 API 与通知策略 | output 需要额外拷贝；reserve 可直接填记录，容量不足可失败；强制通知与默认自适应通知的唤醒成本应结合批量消费评估。 | reserve 不自动消除初始化、竞争、输出字节或消费者唤醒成本；不能为了少拷贝牺牲支持的记录大小、verifier 条件或可靠性合同。 |
| [v6.12 include/linux/filter.h](https://raw.githubusercontent.com/torvalds/linux/v6.12/include/linux/filter.h) 的 `__bpf_prog_run` 与 [UAPI BPF_ENABLE_STATS](https://raw.githubusercontent.com/torvalds/linux/v6.12/include/uapi/linux/bpf.h) | 开启运行统计会增加时钟读取及计数维护；只在目标支持、权限允许时使用同窗口 `run_time_ns/run_cnt` 增量定位平均程序成本，并记录开关状态。 | 平均程序时间不是 helper 单项耗时、尾延迟、整条网络路径或功耗结论；统计默认关闭不能当零成本，不能无授权改变全局统计设置。 |
| Android14 固定 revision 的 [netd.c](https://android.googlesource.com/platform/packages/modules/Connectivity/+/bd692130a596b4e9bc1ea6778db72c423bb8ab6f/bpf_progs/netd.c) 与 [offload.c](https://android.googlesource.com/platform/packages/modules/Connectivity/+/bd692130a596b4e9bc1ea6778db72c423bb8ab6f/bpf_progs/offload.c) | 实读 `DEFINE_UPDATE_STATS`、`do_packet_tracing`、`do_forward6` 与 IPv4 NAT 更新段：trace gate 在读包/时间戳前，协议筛选在按需拉头前；建项后再次 lookup、原子计数、NAT checksum/store 均存在必要语义。 | 不能把所有重复 lookup、所有按包计数和所有 checksum helper 视为滥用；采样诊断不能顺带采样精确计费或安全策略。源码只是审查对照，不是目标产品已性能验证的证明。 |

上述性能场景是从实际工作量与执行频率推导的审查方法。确认缺陷需要指出可达高频分支中的无效/放大工作及影响证据，或列出尚需的基准；PPS、包长分布、非线性/克隆比例、map 命中率与 churn、多核竞争、消费者速度、CPU/丢包/延迟及受控功耗对照共同决定结果。未执行这些测量。
