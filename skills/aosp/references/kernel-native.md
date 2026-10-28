# Kernel、GKI/KMI、BPF 与 Native 边界

内核构建/ABI 工具/发布与模块类别见[内核构建与 GKI](kernel-build-gki.md)；16 KB、ELF/APK 对齐、Vendor API 与 VNDK 演进见[Native 页与 ABI](native-page-size-abi.md)。

用于内核/驱动、native 服务、JNI、内存与动态链接问题。用户态 API、内核 UAPI、KMI 和硬件寄存器协议不能混作同一个兼容层。
“事实”对应已读官方资料；“工程推导”用于实施与诊断。核实于 2026-10-28，内核分支、架构、工具链和产品布局必须单独确认。

## 1. GKI 的目标与 KMI 的保证范围

**事实**：Android Common Kernel（ACK）包含上游内核及 Android 相关补丁。GKI 将通用核心与硬件专有 vendor 模块分离，二者通过受控 KMI 交互。[K1][]
稳定 KMI 只覆盖特定 Android/LTS 分支、指定配置与工具链约束下的受监控符号；不是 Linux 任意内部符号的永久 ABI。[K2][]
`android-mainline` 不提供相同的稳定 KMI 保证；不同 Android/LTS 分支之间不能据“都是 GKI”假设二进制模块可互换。[K2][]

**工程推导**：模块兼容至少要对齐内核分支、配置、工具链、导出符号与 ABI 描述。
只在本地重编译驱动成功，不能证明它可加载到出厂内核；只看到符号名没变，也不能排除类型布局和配置导致的 ABI 变化。
改公共结构体、导出符号或影响 ABI 的配置时，应运行该分支实际的 KMI/ABI 检查，再讨论是否需要合法更新符号列表。
不能以扩大导出、删除 ABI 检查或强制加载未知模块替代兼容性分析。

| 层次 | 约束对象 | 不能推出的结论 |
|---|---|---|
| 用户态 API/ABI | 应用或库的调用契约 | 内核内部结构也稳定 |
| 内核 UAPI | ioctl、syscall、可见结构等 | 任意驱动私有协议可以随意改 |
| GKI KMI | 指定环境中的模块依赖符号 | 跨 Android/LTS 可直接加载同一 `.ko` |
| 硬件接口 | 设备协议、DMA 与中断等 | 编译通过等于时序和资源行为正确 |

## 2. 模块装载也是启动依赖

**事实**：挂载分区所需驱动可能必须由 first-stage init 从 ramdisk 装载；`modules.load`、依赖描述和目标镜像布局共同决定装载过程。[K3][]
vendor/GKI 模块所在 ramdisk、dlkm 分区或其它位置随发布和产品配置变化，不能把一张旧布局图当作全部设备的固定路径。[K1][][K3][]

**工程推导**：新增驱动不能只添加编译目标，还须说明设备何时需要它、届时模块是否已可访问，以及依赖是否先就绪。
“开机找不到设备节点”应区分驱动未装载、probe 延迟/失败、设备描述不匹配、固件/时钟/电源依赖和节点访问限制。
先收集装载/probe 错误、依赖关系和设备状态，再调整启动顺序；插入固定 sleep 不能证明依赖正确。
模块已装载也不表示外设初始化完成，消费者应遵循子系统的就绪、重试和错误语义。

## 3. 驱动的正确性取决于执行上下文与资源生命周期

**工程推导**：先列出进程上下文、IRQ/软中断、工作队列、定时器以及 suspend/resume、remove 路径。
每个共享状态需要明确保护机制；自旋锁、互斥锁、引用计数和等待队列解决的问题不同，不能只用“加锁”概括。
判断阻塞是否允许，要看实际上下文和持有的锁；判断释放是否安全，要看回调、DMA 和异步任务是否仍持有访问权。
probe 的部分失败清理必须与成功初始化步骤对应，remove 之后不能留下仍能触达旧对象的回调。
用户态输入、ioctl 长度、整数运算和拷贝边界属于信任边界；不能因调用者通常是可信 HAL 就省略必要验证。

**定位证据**：目标驱动及子系统 API、lockdep/内核诊断、设备树或 ACPI、probe 日志、引用与关闭时序。
这些判断必须落到目标内核支持的 API；不能把另一主线版本的锁、内存或设备管理规则直接搬来。

## 4. eBPF：程序、映射、加载和附着是不同状态

**事实**：eBPF 程序通过内核接口加载并附着到受支持的事件/挂钩。Android 提供 BPF 构建与启动加载机制，程序对象和 map 定义由平台配置管理。[K4][]
目标支持的 program type、helper、内核验证约束、加载路径和权限需要结合该内核及 bpfloader 实现确认。

**工程推导**：编译出对象、加载成功、附着成功和数据被消费者读取是四个不同的验收点。
map 的 key/value 结构、大小、对齐与版本是用户态/内核程序之间的契约；修改一端可能让另一端静默误读。
共享 map 更新不能天然组成跨字段事务；多 CPU 并发、计数溢出、丢事件和对象清理都需要按用途设计。
BPF verifier 接受程序，不代表业务统计含义正确或性能开销可忽略；要核对附着点、事件频率和数据解释。
不要把平台 eBPF 扩展与应用 seccomp 过滤混为同一个权限能力，也不能假设普通应用能自由加载平台 BPF 程序。

## 5. JNI：托管对象和 native 资源的寿命不同

**事实**：`JNIEnv` 与线程相关，不能在线程间共享；可通过 `JavaVM` 获取/附着当前线程，native 创建并附着的线程需按契约 detach。[K5][]
局部引用通常只在当前线程的调用范围有效；跨调用保存对象要使用恰当的全局引用，并承担释放责任。[K5][]
`Get*` 返回的字符串/数组原始缓冲区与对象引用不是同一种资源，需对应 `Release*`；JNI Modified UTF-8 也不是任意 UTF-8 输入。[K5][]

**工程推导**：把跨 JNI 的每个值标成“借用、复制、转移或持有”，并说明长度、失败与释放路径。
native 指针写入 Java 字段时须考虑位宽与对象销毁后的并发访问；仅使用 `long` 不能解决悬空指针。
异步 native 回调要同时保护 Java 引用、native 对象和目标组件生命周期；取消 UI 请求不等于 native 工作已结束。
异常挂起时继续执行 JNI 调用可能放大问题；检查异常/返回值，并按既有契约向正确一层传播错误。
减少跨语言细粒度往返，通常比用特殊快速调用注解更可靠；性能改动仍须用实测说明。

## 6. Native 内存、FD 与并发所有权

**工程推导**：RAII、明确所有权和有界缓冲有助于形成可审计的释放路径，但不能自动解决跨线程销毁竞态。
FD 可能通过复制或 IPC 交给其它组件；关闭一份引用不表示所有持有者都已释放，数字复用也可能让旧回调误操作新资源。
共享内存需要独立的大小验证、可见性、同步和关闭协议；映射成功不代表生产者已经写完。
错误返回与部分初始化都应纳入资源证明，尤其是 acquire 成功后下一个步骤失败的分支。

**事实**：HWASan 等工具可捕获越界和释放后使用等 native 错误，但有架构、系统/工具链支持和检测局限，不能把单次无报告当作内存安全证明。[K8][]
是否使用 HWASan、ASan 或其它诊断工具，应按目标构建和复现条件选择，不照搬文档里的历史设备命令。

## 7. 动态链接的可见性不由文件存在决定

**事实**：linker namespace 约束共享库搜索、可访问路径和跨 namespace 导出；`DT_NEEDED` 与 `dlopen()` 都受调用者 namespace 影响。[K6][]
库的间接依赖不因某个公共库已导出就自动对其它 namespace 可见；运行时加载依赖也可能在静态构建检查之外出现。[K6][]

**工程推导**：定位 `dlopen`/`UnsatisfiedLinkError` 时同时检查 ELF 架构、目标 ABI、依赖符号、namespace 与实际文件权限。
文件已复制进镜像不等于允许链接；修改全局库路径可能破坏隔离和加载顺序，应优先修正合法依赖与公开接口。
VNDK、linkerconfig 和库集合有明确历史版本边界，不把旧版 `ld.config.txt` 示例路径当成所有新产品的真相。
namespace 是链接组织机制，不是独立 Linux 进程或完整安全沙箱。

## 8. 从崩溃点追到错误来源

**事实**：tombstone 中信号、fault address、abort message 与调用栈有不同含义；栈顶在 libc 函数并不意味着 libc 是根因。[K7][]
例如字符串函数收到非法指针，调用者和对象寿命通常比最后一条访存指令更值得追踪。

**工程推导**：先匹配运行二进制、Build ID 和符号文件，再解释栈；错误符号可能制造看似合理的错误根因。
区分主动 abort、空指针、越界、释放后使用和栈破坏，按证据选择工具，不以捕获信号、返回空值或屏蔽断言遮盖根因。
内核问题还需对应内核日志与构建信息；用户态 tombstone 无法独立说明驱动中的并发或 DMA 故障。

## 已读官方来源与历史边界

- [K1 Kernel 概览](https://source.android.com/docs/core/architecture/kernel)：ACK、GKI、vendor/GKI 模块。
- [K2 Stable KMI](https://source.android.com/docs/core/architecture/kernel/stable-kmi)：分支、配置、工具链及受控符号范围。
- [K3 Kernel module support](https://source.android.com/docs/core/architecture/kernel/kernel-module-support)：first-stage init、装载依赖及历史构建规则。
- [K4 Android eBPF](https://source.android.com/docs/core/architecture/kernel/bpf)：程序、map、构建与加载；具体支持按分支确认。
- [K5 JNI tips](https://developer.android.com/ndk/guides/jni-tips)：线程、引用、缓冲区和字符串契约。
- [K6 Linker namespace](https://source.android.com/docs/core/architecture/vndk/linker-namespace)：搜索/导出机制；旧 VNDK 配置示例有版本边界。
- [K7 Native crash diagnosis](https://source.android.com/docs/core/tests/debug/native-crash)：信号、tombstone 与调用者定位。
- [K8 HWASan](https://source.android.com/docs/security/test/hwasan)：可检测错误、平台要求与工具局限。

[K1]: https://source.android.com/docs/core/architecture/kernel
[K2]: https://source.android.com/docs/core/architecture/kernel/stable-kmi
[K3]: https://source.android.com/docs/core/architecture/kernel/kernel-module-support
[K4]: https://source.android.com/docs/core/architecture/kernel/bpf
[K5]: https://developer.android.com/ndk/guides/jni-tips
[K6]: https://source.android.com/docs/core/architecture/vndk/linker-namespace
[K7]: https://source.android.com/docs/core/tests/debug/native-crash
[K8]: https://source.android.com/docs/security/test/hwasan
