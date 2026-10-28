# 内存资源：进程状态、回收、保护与终止

用于内存压力、缓存进程行为、重复冷启动、异常终止、系统进程预算和 ZRAM 集成。核实日期：2026-10-28。
区分设备 release/首发条件、内核分支与配置、cgroup 挂载/层次、AMS 状态及进程实例；新版框架存在某服务不等于旧内核已实现所需节点与 ioctl。
下文机制事实来自官方正文；调试顺序和修改建议是据此推导。数值与默认策略必须在目标分支复核。

## 1. 不同机制解决不同时间尺度的问题

| 机制 | 触发或控制对象 | 主要动作与结果 |
|---|---|---|
| Cached apps freezer，Android 11+ 支持 | 缓存状态进程 | 暂停线程执行，保留进程；并非 kill |
| App hibernation，平台机制 Android 12+ | 长期未使用的应用包及用户状态 | 停止后台活动、回收缓存/编译产物、权限重置等；不是短时冻结 |
| LMKD | 全机内存压力与进程重要性 | 终止相对不重要进程，缓解压力与 thrashing |
| Memory Limiter，Android 17+ | 应用进程、可见性与 RAM 档位 | cgroup `memory.high` 局部回收/节流和 `memory.swap.max` swap 约束 |
| System memory budgets，Android 17+ | 关键 daemon 与系统应用 | `memory.min` 保护地板、`memory.high` 工作集上限 |
| PMGD，Android 17+ | vendor 显式配置的目标进程 | 监视局部超限，等待回收或终止目标；不是全机 LMKD |
| mmd，Android 17+ | ZRAM setup 与已换出的页 | 重压缩、写回、进程写回/预取；不是 Java GC |

**工程判断**：进程消失、无回调或 CPU 突降不能只归为“系统杀后台”。先确认 freezer、force-stop、LMKD、PMGD、内核 OOM、crash 和 ANR 等真正原因。

### Cgroups 与 task profiles：先解析实际动作，再判断资源策略

**事实**：Android 10+ 用 `cgroups.json` 描述 controller、版本、挂载位置和权限，在 early-init 准备层次；`task_profiles.json` 则把资源意图映射为动作。
`Attributes` 将抽象名映射到 controller 文件，`Profiles` 组合 JoinCgroup/SetAttribute/SetTimerSlack 等动作，Android 12+ 的 `AggregateProfiles` 可复用多个 profile，但不能递归包含自身。[Cgroups][cgroups]

- Android 11+ 的 `SetTaskProfiles` 面向 TID，`SetProcessProfiles` 面向 UID/PID；选错范围可能只影响调用线程或限制错误对象。
- Android 12+ 使用 init `task_profiles` 替代相应 `writepid` 迁移方式，避免上层硬编码 cgroup 文件路径。
- 加载顺序是默认→API-level→vendor；同名 attribute/profile 被后者覆盖，新名字才是追加。只找到 system 默认文件不能证明有效动作。
- `Optional` controller 可让不支持的挂载错误被忽略；init 没有失败并不证明该资源限制有效。节点、API 返回值和任务真实归属需要验证。
- 需要路径时使用 controller/attribute 查询抽象；vendor 自行 mount 的组不自动成为 framework 已知策略。

**工程判断**：记录 profile 最终定义、展开动作、目标 TID/PID、cgroup membership 与实际属性值，区分“profile 被调用”与“底层限制成功”。CPU affinity、权重、容量请求和 memory reclaim 即使被放入同一 aggregate，也仍是不同控制维度。

## 2. LMKD：以压力和 thrashing 判断全机退化

**事实**：用户空间 LMKD 监控内存状态，按重要性等条件选择终止对象。
Android 10 支持 PSI 检测，Android 11 的新策略进一步考虑资源使用、swap 与 page-cache thrashing，不能把它简化成固定 free-memory 阈值。[LMKD][lmkd]

- PSI 衡量任务因内存不足而停顿的时间；它与“已分配多少 RAM”不同。旧 vmpressure 路径可能需要额外过滤，具体使用哪条路径取决于内核支持和 `ro.lmk.*`。
- Android 11 文档的 PSI、pidfd 和 memcg 需求分别有作用；只有 property 设置正确不证明内核功能存在。
- workingset refault 与 page-cache 大小关联可揭示 thrashing；大量缓存被反复回收又读回时，仅把 free RAM 提高无法证明用户体验改善。
- `oom_score_adj`/重要性、low-RAM 产品策略和 kill 反馈影响选择；“最大 RSS 必须先被杀”不是通用契约。
- kill 日志、进程退出原因、PSI、swap 使用、refault、reclaim 停顿和前台 CUJ 要按同一时间窗对齐。只统计 kill 次数可能漏掉更严重的卡顿。

**工程判断**：先解释压力来自匿名 heap、共享页、图形 buffer、不可换出页、文件缓存还是内核分配，再选择所有者修复。
放宽阈值、让所有服务不可杀或扩大 heap 可能把可恢复重启换成系统停顿，不是泄漏的修复。

## 3. Cached freezer：线程停止后，IPC 与任务也有状态约束

**事实**：freezer 使用 cgroup v2 冻结缓存进程；AMS 决定进程生命周期，CachedAppOptimizer 执行优化。
Android 14+ 官方描述包含进入缓存后的延迟冻结、在合法生命周期事件到来时解冻，以及配套的广播与内存处理；具体延迟和豁免是实现策略，不固定成跨版本 API。[Freezer][freezer]

- 冻结后所有线程不能执行，包括 GC 与 trim callback；不能依赖 frozen 进程收到回收回调后主动释放资源。
- Android 14+ 将 `TRIM_MEMORY_UI_HIDDEN` 等通知提前到适合执行的状态，冻结前也可能请求 GC；这些与后续 compaction/ZRAM 是不同阶段。
- context-registered 广播可在缓存期间排队，manifest receiver 可能触发解冻；不能把所有广播都当立即唤醒或全部丢弃。
- 进程提升到非缓存状态会解冻；持有会阻塞非缓存进程的文件锁、某些 `BIND_WAIVE_PRIORITY` 绑定等有版本相关豁免。
- 同一 app 的进程全部冻结后，系统可关闭其活动 TCP sockets；“进程仍在 RAM”不保证连接持续有效。

### Binder reference 不会替代有效生命周期

**事实**：向冻结进程发送同步 Binder 调用可使服务端因 freezer 机制被终止，调用者得到 `RemoteException`；持续 oneway 调用可能耗尽冻结进程的异步缓冲，同样触发终止。
官方举例是解绑服务后仍使用旧 `IBinder`，因为解绑后对方可能已变缓存并冻结。[Freezer][freezer]

**工程判断**：解绑后清除失去生命周期支撑的代理；不要靠捕获异常继续高频重试。
对长寿命远程 callbacks，要按 frozen 状态暂停、合并或限量排队，并在解冻后交付仍然有效的最新状态。
Android 16+ 提供 `IBinder.FrozenStateChangeCallback` 等公开 API；底层还要求 Binder driver freeze-notification 支持，注册失败/`UnsupportedOperationException` 需要定义降级行为。
`RemoteCallbackList` 的 frozen callee policy 以目标 API/实现核实，不推断所有旧分支已经具备。

固定频率任务在冻结期间积欠，解冻后可能连续补跑；对不要求补齐每个历史 tick 的工作，采用适合的 fixed-delay/调度模型，不能把这一波峰误认成新请求暴增。

**证据**：AMS 的 frozen 列表、cgroup freeze 节点、freeze/unfreeze 日志及 reason、`ApplicationExitInfo.REASON_FREEZER`、Perfetto `Freezer` track。
实验性 `am freeze/unfreeze/compact` 与实际 AMS 状态迁移不同，手动成功不能证明真实冻结策略完整正确。

## 4. Hibernation：以包使用与存储优化为目标

**事实**：平台 hibernation 从 Android 12 提供；UsageStats/PermissionController 中的策略判断与 AppHibernationService 的执行分工，允许模块化策略演进。
它面向长期未用包，包含 force-stop、缓存/ART 产物回收与权限 auto-reset 的协作，保持应用数据和重新进入能力。[平台 hibernation][hiber]

设备版本与 app target SDK 决定实际效果：当前 Android Developers 表明确列出 Android 12+ 设备上 target 12+ 的后台 jobs/alarms/push 限制、缓存清理与权限重置；Android 11 场景主要是权限 auto-reset。
低版本通过 Google Play services 的权限回退不是 AOSP Android 12 的平台服务。
平台旧页面含设计期措辞和容易混淆的 target 条件，不据此写出反向兼容结论；使用当前行为表和目标 PermissionController 源码复核。[当前行为与版本表][hiber-app]

- resumed Activity、widget/通知交互及某些被外部明确调用的组件可构成使用；自己定时跑 job、收隐式广播或设置 alarm 不自动重置长期未用计时。
- 用户重新使用后可恢复运行资格，但系统不会替应用重新授予 runtime permissions，也不会自动恢复以前所有 jobs/alarms/notifications；业务要重新建立调度并处理权限缺失。
- 工作 profile、DPC、运营商特权等豁免与用户选择按实际用户/包判断，不从个人 profile 的设置推断工作 profile。
- 厂商更短时的省电限制可与 hibernation 并存，但改变 usage 信号或非标准唤醒可能破坏准确性；不能把仅停止某进程当作完成 hibernation。

**工程判断**：测试应该验证权限、调度、缓存/编译状态和重新进入后的重建行为，而不只看设置开关。系统数据目录被保留也不代表旧授权与任务继续有效。

## 5. Memory Limiter：局部软上限不是 kill 阈值

**事实**：Android 17+ 的 Memory Limiter 随 AMS 进程生命周期与可见性改变应用 cgroup v2 的 `memory.high` 和 `memory.swap.max`。
`memory.high` 超限触发局部 reclaim 与节流；正常情况下进程继续运行。持续匿名分配且 swap 耗尽等极端情况仍可能分配失败并终止。[Memory Limiter][limiter]

- UI 可见性与“有 foreground service”不同：官方将前者分配 visible 档，foreground service 属于 not-visible；cached 还有冻结与充分回收路径。
- 默认监视 app UID 范围，core system 的通用豁免与系统应用显式预算是不同机制。预装/OEM app 不天然免于通用应用限制。
- 配置读取 `/system/etc/memory-limiter-config.xml`；RAM 档位基于 `/proc/meminfo` 的 `MemTotal`，不是广告标称 DRAM。
- 匹配区间是包含 floor、不包含 ceiling；硬件/固件 carve-outs 会使 MemTotal 小于标称容量。未匹配不等于自动采用最近档位。
- 正式配置不以按 app 的 allowlist 作为普遍豁免；临时 shell `ignore/manual` 属于诊断覆盖，不能误记为产品策略。
- `manual` PID override 只对应当前进程实例，重启后恢复状态计算；应记录 PID、开始时间和状态，避免 PID 复用误判。

**证据**：service status 的 monitoring/watch failures/limit events、活动 limit set、UID/PID cgroup 的 `memory.high`、`memory.swap.max`、`memory.current`、`memory.swap.current` 与 `memory.events`。
只看开关 enabled 无法发现节点写失败、配置未匹配或进程状态档位错误。

## 6. System memory budgets：保护地板和回收上限分开

**事实**：Android 17+ 将交互关键 daemon/系统 shell 的保护与长期后台系统应用的上限区分。
SystemMemoryBudgetManager 用 `memory.min` 保护工作集；系统 app 的 `<memory-budget>` 用 `memory.high` 主动回收冷页，两者与通用 limiter 协作。[System budgets][budgets]

### 动态保护需要完整的 cgroup 祖先授权

- 官方默认以 settled resident working set 的 90% 计算每进程 floor，并设总 RAM 10% 的全局 cap；这些是本机制的版本默认值，可由设备 overlay 调整，不推广到旧系统。
- 工作集计算扣除 unmapped file cache；将包扫描/一次性文件读取留下的缓存计入 floor，会挤占其他交互进程的 cap。
- cgroup v2 叶节点的有效 `memory.min` 受祖先约束：只设 PID 而 UID/slice 为零，保护可能无效；只给共享 UID/top slice 一个总额，又可能让非目标进程分走保护。
- 管理者刷新时同时写 slice、UID 和受管 PID，清理过期对象；新增 vendor daemon 应通过对应配置纳管，手动 init 写值可能被下一次刷新重置。
- SystemUI 与当前用户 Home 的主进程按实际解析结果保护，辅助进程和不同 form factor 不应靠固定包名猜测。
- MGLRU 上 `memory.low` 与 `memory.min` 的强度不同；旧内核嵌套保护还需要对应 backport。节点有数值不证明压力下真能保住工作集。

替代 PinnerService 的永久 `mlock` 还涉及开机 prewarming；只去掉旧 pinning 可能把 I/O 推回同步启动路径。
boot 后主动回收包扫描缓存需保留匿名 heap/映射代码；旧内核不支持 `memory.reclaim swappiness=0` 时不能随意退化为更激进的无参数回收。

### 系统应用预算的范围决定连带影响

- package-level budget 在 UID 层执行；共享 UID 或同包多角色进程需要 PID 层作用域，避免一个后台 provider 限制整个系统 UID 或 UI picker。
- RAM 档位、进程状态、display pixel scaling、clause 顺序共同决定最终预算；当前页面指定 last-matching-clause 规则，不能按第一条命中理解。
- 预算 XML 通过 Soong `additional_manifests` 合并时应核实 library manifest 的 `<uses-sdk>`：官方提示缺失 target SDK 会触发 manifest-merger 的旧版本兼容权限注入，不能只检查预算元素本身。
- 配额针对 cgroup 记账，不等于 `dumpsys meminfo` 的 PSS。Zygote 共享页、file cache、swap 和共享 UID 不可重复相加为“进程真正独占 RAM”。

**工程判断**：基于代表性活跃 CUJ 的 anon/file/swap、peak、refault 和时延校准，而非用 idle 快照向下压预算。
`memory.events:high` 很多、anon/file refault 暴增、活跃任务持续 swap 或 Binder/帧长尾退化，说明上限可能过低；冷文件缓存无界增长且没有回收则可能过高。
预算命中不是目标；目标是在保持工作集与交互时延的同时回收无用驻留。

## 7. PMGD：显式目标的局部失控保护

**事实**：Android 17+ PMGD 从必需的 `/vendor/etc/pmgd/config.json` 获取目标、task profile、匿名内存上限和 reclaim grace period；通过 `memory.events` 监视 high 事件。[PMGD][pmgd]

```text
目标 memory high 事件 → anon 已超 hard limit？ → 立即终止并记录
                              否
                              ↓
                         等待 reclaim grace
                              ↓
        memory.current 仍 ≥ memory.high 或 anon 超限？ → 终止 / 否则继续监视
```

- `target_cmd` 和可选 UID 决定匹配范围；省略 UID 可能匹配多个用户下同名进程，不能只凭一条 ps 输出验证配置。
- `mem_limit_profile` 必须实际设置预期 cgroup 上限；配置文件存在不证明 profile 已解析和应用。
- 监视权还受 SELinux 约束；新 vendor domain 若不可访问会出现监视失败，不能通过扩大所有目标权限掩盖错误匹配。
- PMGD 记录 statsd 和 `/data/misc/pmgd/history.json`，按设备 reboot 限制每目标的 PMGD 终止，避免循环重启；进程第二次未被 kill 不证明泄漏消失。

**工程判断**：系统关键进程被 PMGD 终止会触发其恢复链，验证必须包括服务恢复、数据完整性和全机可用性。PMGD 是失控兜底，不能替代内存泄漏修复。

## 8. mmd：初次 swap、重压缩和写回是多阶段生命周期

**事实**：Android 17+ `mmd_setup` 在 boot-complete 后配置 ZRAM，完成后启用持续维护 daemon。
`system_server` 决定何时请求，`mmd` 经 `IMmd` 执行具体策略；Java 生命周期调度与内核 swap 实现由此分离。[mmd][mmd]

```text
内核 reclaim/compaction：快压缩换入 ZRAM
→ idle tracking：识别冷页
→ recompression：用更高压缩率算法保留在 RAM
→ writeback：把足够冷的页写到 backing storage
→ app 恢复：按需 fault 或主动 prefetch
```

- `mmd.zram.enabled` 启用后，旧 `swapon_all` 的 ZRAM setup 变为 no-op，旧 overlay/`ro.zram.*` writeback 配置被忽略；vendor init 抢先占用设备还会阻碍 mmd setup。
- 多 ZRAM device 的逗号列表必须与 `num_devices` 一致，且设备应在 setup 触发前存在；不能认为系统会凭列表创建缺失设备。
- 全局维护由 JobScheduler 的 idle、battery-not-low 等条件控制，经 oneway Binder 异步请求；不是 `system_server` 同步等待整次扫描。
- `mm.zram.maintenance.*` 由 system_server 消费，`mmd.zram.*` 由 setup/daemon 消费；改错前缀可能没有预期作用。
- 单 worker 区分高/低优先级工作；prefetch 优先，维护与进程 writeback 属低优先级。维护请求已发送不等于已执行完。
- 缓存进程 compaction 后，可延迟发起按进程 writeback；pidfd 绑定进程实例，回调成功后才更新对应状态/指标。
- 用户重新启动造成的解冻可请求 prefetch，降低 backing storage major fault 的冷启动成本；进程写回成功不保证恢复完全没有 I/O。
- idle age、backoff、每轮/每日 writeback 限制与剩余存储共同限制工作量。recompression 不产生相同 flash 写入成本，不能把两者的预算互换。
- 内核 access-time tracking 支持不足时有软件 idle 标记回退；年龄信号与维护轮次的含义随实现不同，不把旧内核的采集结果当精确最后访问时间。

**证据**：`comp_algorithm`/`disksize`、`mm_stat`/`bd_stat`、backing device、mmd service 与日志、job 状态、cgroup/swap 指标和 app resume 时延。
`WritebackDailyLimitExceeded`、pidfd 对象消失导致的 `EBADF/ESRCH`、存储/队列不足导致的 `ENOSPC` 分别诊断；不能统一通过增大超时解决。

## 9. mm_events：保留压力发生时的历史，而非事后单张快照

**事实**：官方对 Android 12+ 首发设备说明 `mm_events` 在 kswapd、direct reclaim 或 compaction 活动触发后，按配置窗口采集 vmstat 与 ftrace，并集成 Perfetto/bugreport。[MM events][mm-events]

- 它记录压力区间里的 free/anon/file/refault、swap、scan/steal 和 reclaim/compaction 时间，不能从 bugreport 当下内存已恢复推断此前没有压力。
- `persist.mm_events.enabled` 需要在 `post-fs-data` 之前设置以准备 tracing instance；配置中触发名、唯一 session 和 bugreport score 决定是否真的启动并被打包。
- 高压力设备上采集可能长期活跃，开销不能按“事件式采集”自动视为零；保留实际频率、数据源与 trace buffer 配置。
- vmstat 时间线与 raw ftrace 事件展示位置不同；图形界面没有对应曲线不等于数据缺失。按实际 trace 内容验证。

## 已读官方依据与边界

本页提炼上述进程与内存服务契约；不固化所有 RAM 档位/属性默认表，不宣称已核对每个内核 backport、全部 manifest budget 属性或每个产品的 cgroup 路径。
这些实施细节需结合目标分支、合并配置与运行节点继续确认。

[lmkd]: https://source.android.com/docs/core/perf/lmkd
[cgroups]: https://source.android.com/docs/core/perf/cgroups
[freezer]: https://source.android.com/docs/core/perf/cached-apps-freezer
[hiber]: https://source.android.com/docs/core/perf/hiber
[hiber-app]: https://developer.android.com/topic/performance/app-hibernation
[limiter]: https://source.android.com/docs/core/perf/memory-limiter
[budgets]: https://source.android.com/docs/core/perf/system-memory-budgets
[pmgd]: https://source.android.com/docs/core/perf/pmgd
[mmd]: https://source.android.com/docs/core/perf/mmd
[mm-events]: https://source.android.com/docs/core/perf/mmevents-stats
