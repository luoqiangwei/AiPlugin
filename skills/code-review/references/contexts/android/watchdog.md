# system_server Watchdog

用于修改系统服务锁、Handler、Binder/HAL 调用、Monitor、启动或关机流程时；先读 AOSP 场景。这里的 Watchdog 检测 system_server 部分执行路径的存活性，与应用 ANR、kernel soft/hard lockup 和硬件喂狗机制分别判断，不能互换阈值或恢复语义。

机制基线实读 `frameworks/base` 的 `android16-release`；目标产品的 manifest revision、厂商补丁、构建类型与运行配置才是审查契约。旧分支的 monitor 执行线程、half 阶段、注册限制可能不同，不能按类名套模板，也不默认用“加长超时”修复。

## 先确定到底监测谁

**触发**：新增/移动 Handler、`addThread`、`addMonitor`、Monitor 内容或工作队列变化。

- 对每个受影响路径记录 `注册点 → Handler/Looper 所在线程 → checker → monitor 顺序 → 实际锁/远端依赖`。区分 Watchdog 调度线程、执行 checker 的线程、业务 Binder 线程和 HAL 线程。
- 此基线 `addThread(handler)` 检查该 Looper 能否执行 checker；不是扫描服务的全部线程。`addMonitor` 排入 monitor checker，在专用 `watchdog.monitor` 线程串行调用；新增 monitor 要到可安全调度时才并入执行列表。
- 逐个读 `monitor()` 的函数体。拿锁即返回只探测该锁的可获取性；空实现不证明业务完成。此分支 `StorageManagerService.monitor()` 调用 `mVold.monitor()`，不能误写为探测 Java 服务锁。
- 监测表中还要列未注册的 Handler、后台 executor、native 工作线程、暂停中的 checker、未覆盖的锁和远端。未触发 Watchdog 不等于这些路径没卡死；有进程被加入 dump 列表也不等于它受 checker 监测。

**确认条件**：变更让关键等待路径从监测链中消失、永久暂停，或新增 checker 会依赖已停止/尚未就绪的线程；需指出调用点及可达生命周期。
**反证**：工作有独立的有界完成/故障恢复契约，或故意不纳入该 Watchdog，不能仅凭未注册报告缺陷；仍须核对关键服务可用性。

## Looper 的进展与业务队列积压

**触发**：受监测线程新增长任务、同步等待、锁、native 调用或消息调度策略。

- 从当前 dispatch 追踪锁等待、`Future.get`/latch/join、同步 Binder、HAL 和文件/设备 I/O；找出谁能使它返回，是否必须向同一 Looper 投递后续工作。
- 此基线 checker 投递在队首，且无 monitor 的空闲 polling Looper 可直接判完成。普通队列很长不能单独证明 checker 被堵；当前消息长期不返回、不可调度或队首竞争要分别取证。
- 反过来，checker 能运行不证明普通业务消息及时完成。队首任务反复插队、无界生产、执行时间增长仍可让业务积压，按队列年龄、长度与完成速率审查。
- 多次 checker 调度没有完成时，要核对计时起点是否被保留；不能通过反复重置起点、吞异常或伪造完成掩盖停止进展。

```text
风险：受监测 Looper H 执行任务 → 等待 latch；
      释放 latch 的任务已经排到 H → H 不能返回当前 dispatch。
反证：完成者在独立且可进展的执行器，等待有实际生效的边界与失败处理。
```

**确认条件**：指出自等待或持续超过目标预算的可达工作，补全完成者与调度条件；只看到一次 WAITING 栈不够。
**修复与验证**：移除同 Looper 同步等待，拆出有界工作并保留顺序/失败语义；同时断言 checker 和真实业务消息都持续进展。

## Monitor 等锁与持锁跨边界

**触发**：Monitor 获取锁，或任意持有该锁的业务路径新增 Binder、HAL、native I/O、回调、第二把锁。

画等待图，箭头表示“等待其完成/释放”，为每条边标持有者、线程/进程、同步性和可达条件；再找环或没有上界的叶子。

```text
monitor checker → 服务锁 L → 持 L 的业务线程 → 同步 HAL reply
HAL reply → 另一工作线程发起的回调 → 服务锁 L
另查：线程 A 持 L 等 M；线程 B 持 M 等 L。
```

回调若是嵌套 Binder 事务，可能复用原事务线程；不能自动画成“等待新线程”。即使 Java 可重入锁避免了该锁环，回调仍可能看到半更新状态；native 非递归锁又有不同结果。
单个 Monitor 卡住会延后同 checker 后续 monitor；报告中的当前 monitor 是观察入口，锁持有者、远端池或 I/O 才可能是阻塞源。顺序累计开销也要纳入整轮预算。

```java
// 风险示意：业务持锁等待外部完成；回调可能再次读取或修改本服务。
synchronized (lock) {
    state.beginChange();
    result = hal.update(request); // 同步 Binder/native 等待，含潜在回调。
    state.commit(result);
}

// 修复方向示意：先准备不可变请求和版本，再释放锁。
synchronized (lock) {
    if (closed) return;
    generation = state.generation();
    request = state.immutableRequest();
}
result = hal.update(request); // 异常、超时、取消各自有失败/清理策略。
synchronized (lock) {
    if (closed || state.generation() != generation) {
        discardOrReconcile(result); // 仅本地有界处理；外部补偿放到锁外。
        return;
    }
    state.commit(result); // 所有冲突修改/销毁路径必须推进 generation。
}
```

generation 重查只防旧结果覆盖新状态，不能撤销已发生的 HAL 副作用；需按协议处理幂等、补偿与重复回调，不能无界重试。移锁时保证快照没有共享可变别名，回调不读半状态。
**确认条件**：给出锁持有者和闭环/无界叶子的实现证据，或受控延迟可使监测链停止进展。看到 `synchronized` 与 IPC 同时出现只是线索。
**反证**：不可达的锁顺序、不会执行的回调路径、独立有界完成者可排除对应推导；“HAL 正常很快”或一次健康 trace 不能排除慢设备情形。

## Binder 池耗尽与同池相互等待

**触发**：Binder 入口同步等工作、服务回调、批量 IPC、线程池配置变化。

列每个相关进程/驱动实例的可用池、在途事务及完成者。此基线 `BinderThreadMonitor` 等本进程 Binder 线程可用；它阻塞只能作为池压力入口证据，不能直接归咎于某个服务。
检查是否所有可服务线程都在等锁、远端或 Handler，而完成这些任务又需该池接收新事务；区分嵌套事务复用与另一线程/异步链发起的新事务。进程内本地调用也不保证会排队到 Binder 池。
`oneway` 不表示业务完成；同一 Binder 节点的异步事务仍会串行，改为 oneway 还要定义回压与完成协议。增加线程可能缓解有界负载，但不能消除锁环或无限积压。
**确认条件**：池占用和等待链同时成立，且关键新事务缺少可运行处理者；仅凭线程数多或一次 Binder 栈不能确认枯竭。
**反证与修复**：有剩余处理能力/独立完成路径时先查调度和锁；通过移出同步等待、隔离有界工作、回压和取消释放资源恢复进展，再评估池容量。

## 预警、超时与启动关机时序

- 从目标分支还原 checker 的完成、等待、预警、逾期条件与聚合方式。旧资料的 half/full 不能直接套用：此基线虽保留 `waitedHalf` 名称，预警按 `PRE_WATCHDOG_TIMEOUT_RATIO` 计算，不保证“半程”；计时使用 uptime。
- 核对默认设置、`addThread` 自定义值、硬件超时倍率和暂停范围；此基线自定义值覆盖默认策略，不能只改全局值就认为所有 checker 一起变化。不得写固定通用超时数值。
- 逾期、写报告、杀 system_server 是不同观察点。核对 debugger 当前/近期连接、activity controller、allowRestart、user/userdebug/eng、调试开关和崩溃循环配置；不能以调试环境未重启断言没有超时。
- 按实际调用链排列服务对象/锁/native handle 就绪、monitor/Handler 注册、Watchdog start/init、服务发布和 boot phase。此基线运行中可排队注册 monitor，不能沿用旧分支“必须 start 前注册”的限制；init 前缺少 DropBox 依赖也不能当作没监测。
- 对 shutdown、用户停止、daemon 死亡重连，找等待者、完成回调、Looper quit 与资源销毁顺序。禁止在将处理完成回调的线程上 join/drain；已注册 Handler 停止后 checker 如何处理必须有目标实现依据，不能假定自动注销。
- `pause/resume` 核对调用线程、嵌套配对与异常路径；有期限暂停检查覆盖范围和恢复后的再检测。长期合法慢操作也应先证明边界与恢复契约，再评估局部预算，不能全局放宽或删除 Monitor 掩盖锁环。

**区分性验证**：在可恢复测试环境按产品实际预算注入受控慢 HAL/native I/O，分别低于预警、跨预警后恢复、持续至逾期，核对状态、日志和构建策略。调试器与禁止重启配置单列预期；修复后有界慢操作应完成，永久故障仍应被检测。
用真实跨进程回调立即查询/取消，覆盖另一线程回调、并发销毁、HAL 死亡、延迟旧 generation；断言无锁环、无旧状态提交且资源只释放一次。再施加有界 Binder 池压力，记录事务完成率与队列年龄，释放压力后必须恢复，不能只测单进程 mock。
覆盖冷启动依赖未就绪、部分初始化失败、关机回调迟到、退出 Looper 与暂停异常。同步采集同次事件的多时刻 Java/native 栈、锁持有者、Binder 事务、调度/CPU 与 I/O 证据；trace 会扰动时序，一次 trace 或某 Monitor 的线程栈不能独立证明根因。

来源与分支复核：[规则溯源](../../sources/android-watchdog.md)。
