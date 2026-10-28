# Android 系统与 AOSP

本文件处理 Android 系统服务、native daemon、HAL/AIDL、SELinux 与分区接口。具体实现语言另读语言资料；修改实际驱动才补内核场景，修改 APK 组件与界面才补 Android 应用场景。先固定 repo manifest 与受影响仓库 revision、product/架构、Android 分支、system/vendor/APEX、user/userdebug 和设备补丁。

多仓库平台不能由单个 HEAD 推断完整依赖；系统版本与补丁日期也不能证明厂商分支包含修复。以下规则直接作用于调用链、身份和编码契约，外部来源仅用于版本复核。

按 [场景索引](../index.json) 的 `aosp.checks` 进一步选择兼容性、SELinux、并发、ANR 和 system_server Watchdog 专题。系统接口变更要追到受影响调用者与真实测试；服务端阻塞既可能拖住 App 造成 ANR，也可能卡住系统被监测线程，两条等待链分别证明。

新增服务注册、关键操作失败、HAL 重连、降级和恢复路径时也进入日志专题：必要事件不能仅在调试构建打印，日志级别与内容必须反映真实结果；锁内、Monitor 和高频 Binder 路径的日志另核频率与执行成本。

BPF 变更按索引的 `aosp.checks.bpf` 进入专题；高频路径先查 helper/Map 冗余、循环放大、拉包/复制、输出及策略计费，再按改动补查构建、加载、pin/attach、权限和更新。目标分支能力与实际消费者优先；平台加载权限不能直接推给普通 App。

## Binder 身份与授权

**触发**：Binder 入口、`clearCallingIdentity`、异步投递、代理调用、跨用户操作或包名/UID 验证变化。

1. 找真正外部 Binder 入口，记录该处调用 UID、目标 user、对象所有者和操作。PID、请求中自报包名、WorkSource 都不能代替可信 UID 授权。
2. 标记 `clear/restoreCallingIdentity`、Handler/Executor、回调与进程边界。Binder 身份属于线程/事务上下文，不因闭包保留自动传播。
3. 包名须与调用 UID 绑定；跨用户分别检查目标 user 与跨用户权限。“系统 App”“同 appId”“拥有角色”不能自动推出任意对象权限。
4. 在正确身份下验证权限与对象归属；clear 后调用 `callingOrSelf` 一类 API 可能检查服务自己。若撤权必须立即生效，异步任务还须带可信身份和目标按执行时策略重校验，不能把入口检查当永久授权。
5. 查本地直接调用：没有新 Binder 事务时身份语义可能不同。可信内部 API 与外部 IPC 入口分别定义责任，不能允许任意路径自报 UID。

```java
// 风险：工作线程取到的执行身份不能代表原调用者。
handler.post(() -> {
    enforceAllowed(Binder.getCallingUid(), targetUser, objectId);
    performPrivilegedOperation(objectId);
});

// 在入口捕获和验证，只向内部任务传可信身份与目标。
final int callerUid = Binder.getCallingUid();
final Target target = resolveAndAuthorize(callerUid, targetUser, objectId);
final long token = Binder.clearCallingIdentity();
try {
    enqueueInternalTask(callerUid, target); // 是否重校验由执行时/撤权契约决定。
} finally {
    Binder.restoreCallingIdentity(token);
}
```

`resolveAndAuthorize` 必须实现服务端策略，不能只是格式校验。若队列提交/同步工作无需 clear，不为模板加入 clear；需要时缩小范围、所有异常路径恢复。应用权限、AppOps、用户和对象授权不能互相替代。

**反证**：有意公开的无特权操作，或具有可证明的可信内部入口，不因缺少某个权限 API 就报漏洞。捕获 UID 只证明身份保存，不证明访问策略正确。

**修复后不变式**：检查者针对原始主体，用户/对象/操作与该主体绑定；服务自己的权限不能把拒绝变为允许；异常后身份恢复。

**区分性验证**：不同 UID、同角色不同对象、伪造包名、不同用户、撤权后队列执行、授权抛错、本地和远程调用。断言拒绝请求无副作用、异常后下一请求不继承错误身份；只测系统签名调用者会漏过此类错误。

## Parcel 编解码契约

**触发**：Parcelable、自定义 Parcel、`onTransact`、集合/长度、FD/对象引用和接口版本变化。

为每个字段列 `写入条件 → 字节/对象布局 → 读取条件 → 读取后位置`，逐个比较两侧分支。至少覆盖 null、空和非空，不能只确认字段类型相同。

```text
风险写端：writeInt(count)
          if (items != null) writeList(items)
风险读端：count = readInt()
          if (count > 0) readList()

items 非 null 但为空时，写端仍有 list 编码，读端不消费；
后续字段被错位读取。空值不只是边界数据，它改变了解码位置。

修复：定义一致的 null/空/非空协议，双端按同一条件消费；
      若保留 count + list 两层长度，校验两者一致且有界；
      保持既有格式或按版本演进，不能只改一端。
```

继续检查：

- 长度/计数在乘加、分配和循环前限制；覆盖负值、截断、位宽转换、嵌套深度与总预算。
- 解包后校验不变式；能解码不代表有权引用该对象或 FD。
- FD/句柄的访问能力与借用、转移、关闭责任明确；错误/取消不能漏关或重复关。
- 客户端可手工构造 Parcel，不能以生成客户端“正常不会发送”排除恶意输入。结构化 AIDL 降低手写协议风险，但不替代权限和预算。

**反证**：null 与空编码不同可以合法，只要双端一致且兼容。不能脱离目标版本/协议，仅凭缺少某个 Parcel 检查方法推导可利用。

**修复后不变式**：合法编码恰好消费对应字段；非法编码拒绝且不改变状态；解析有界，失败释放已获取资源。

**区分性验证**：改动字段后放固定哨兵，分别 round-trip null/空/单元素/多元素并校验值与读取位置；再测截断、负/超大长度、不一致计数、重复句柄和嵌套。只比较正常非空对象相等会漏掉错位。旧/新端组合同时验证；fuzz 命中最小化后保留为回归。

## Binder 重入与锁

**触发**：锁内 IPC、跨进程回调、客户端死亡、oneway 或线程池变化。

1. 从同步出站调用画等待链：本地持锁、对端线程、对端可回调的本地方法。单线程池不证明不会重入；同线程也不证明状态满足原假设。
2. 查 IPC 前是否处于半更新状态。没有死锁时，回调仍可能读到破坏中的不变式。
3. 优先移出锁：锁内捕获不可变请求/版本，锁外调用，再持锁检查版本和对象存活后提交。不能只删锁制造竞态。
4. oneway 只代表调用语义，不等于业务完成；需要确认时有明确响应协议。队列、客户端死亡和重复回调各有清理责任。

```text
风险：持 lock → callback.onChanged() → 对端同步回调本地查询 → 等 lock。
修复：lock 内计算 snapshot + generation → unlock → callback；
      若要写回，再 lock，确认 generation 与对象状态匹配才提交。
```

**反证**：出现 synchronized 和 Binder API 不足以证明死锁；须给可达锁顺序、回调或半状态证据。快照仍持有共享可变集合时，形式上移出锁也未隔离状态。

**修复后不变式**：重入不见半状态，异步/死亡只清理自己资源，旧回调不覆盖新一代对象。

**区分性验证**：真实跨进程客户端在回调立即重入查询/取消；并发注册注销、服务重启、客户端死亡、延迟旧回调。断言完成期限、状态和资源次数，单进程 mock 不能代替 Binder 重入行为。

## SELinux 标签与访问策略

daemon、访问路径或策略变化时，先确认主体域、对象标签与业务允许的操作，再决定是否添加权限。AVC 不等于应放行，策略编译成功也不证明权限正确。标签创建与恢复、对象管理器、属性与服务权限、分区策略兼容、neverallow 及正负向验证统一按索引中的 SELinux 专题执行。

## 兼容、构建与资源补充规则

| 审查主题 | 审查必须证明 | 有区分力的验证 |
|---|---|---|
| AIDL 接口演进 | 冻结快照未改；默认值、nullable、枚举和错误码在旧端有确定行为；新方法有降级策略 | 旧 client/新 service、新 client/旧 service，含未知字段/枚举、UNKNOWN_TRANSACTION、错误返回；只构建当前双端会漏掉兼容问题。 |
| HAL 与分区兼容 | system/vendor 可分别升级；稳定接口、支持 backend、VINTF、实例名、启动和死亡恢复一致 | HAL/VINTF VTS、分区版本矩阵、服务重启；不把迁移所有 HIDL 当默认修复。 |
| 产品构建与依赖 | visibility、vendor/APEX 可用性、依赖和 ABI 符合实际隔离；生成物、产品 flag 契约一致 | 受影响 product/ABI 构建、API/依赖检查和 user smoke；单仓 HEAD 或 userdebug 成功不证明完整产品兼容。 |
| 系统 API 兼容 | SDK/System API 的权限、异常、默认值和语义满足对应发布契约 | 旧调用者/新系统、权限变化、受影响 CTS；可观察到的内部改动仍需评估兼容。 |
| 原生资源与内存 | 不可信长度的 checked arithmetic 对应真实分配；指针/FD 生命周期覆盖回调与失败 | 创建、注册、取消、死亡、关闭点注入失败，选相关 sanitizer/fuzz；没有 native 可达路径时不泛化内存漏洞。 |
| 错误处理与资源清理 | 失败不被吞成成功、重试/日志有界、秘密不入日志；清理与注册责任成对 | 抛错、满队列、部分初始化、重复注销、发布日志；风格交既有 preupload，不以个人偏好阻断。 |

## 验证与交付

从本分支 `TEST_MAPPING`、真实 target 和模块构建开始，按影响扩展 CTS/VTS、接口兼容、策略与 native 动态检查。只用实际存在的目标，不为 Review 自动刷机、解锁或放宽策略。报告精确 revision、product、构建类型、身份和验证边界；缺少设备、厂商代码或多仓库环境时明确限制。

来源、版本事实与原始漏洞记录仅在需要复核时读取：[规则溯源](../sources/aosp.md)。
