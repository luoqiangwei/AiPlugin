# 编译优化、启动关键路径与性能归因

用于 native 编译 profile、R8、ART 预编译/设备编译、首启回归、启动耗时和调度抖动问题。核实日期：2026-10-28。
先固定平台分支、工具链、产品/release config、ABI、代码与 profile revision、运行产物、负载和测量区间。
下文“事实”来自所列官方正文；定位与修改建议是从这些契约推导的工程判断。官方旧机型参数不自动适用于当前设备。

定位：编译/profile/CLC 读第 1–6 节，启动与时序归因读第 7–8 节，安装/数据库/窗口缓存、Health、游戏与 NPU 读第 9–11 节。

## 1. 几种“profile”服务于不同编译阶段

| 机制 | 主要输入与执行阶段 | 不能混同的对象 |
|---|---|---|
| Native Clang instrumentation PGO | 插桩 native 二进制运行生成计数，合并后供 host 编译器使用 | ART 的方法/类 profile |
| Native AutoFDO | native 运行的采样数据，供 LLVM 优化代码布局与生成 | 不等于让所有模块固定最高优化级别 |
| R8 | 最终 DEX 目标的代码、资源、保留入口和 API 边界 | 不是设备上的 dex2oat |
| ART app profile | 与 DEX 匹配的方法/类信息，指导 JIT/AOT 与类加载优化 | native PGO 数据不可直接替代 |
| Boot image / system-server profile | 多个关键用户路径的系统代码使用情况，进入系统镜像 | 不是每个应用可随运行任意替换的全局 profile |

**工程判断**：先证明使用了什么优化输入，再比较收益。存在 `.profdata`、`.prof` 或 `optimize` 属性不等于目标产物实际使用了它。[PGO][pgo] [AutoFDO][afdo] [ART][art-config]

## 2. Native PGO：采集构建与发布构建分开

**事实**：官方平台 instrumentation PGO 集成文档适用于 Android 13 及以前，Android 14 起该功能已标记 deprecated。
Android 旧平台路径支持 LLVM IR instrumentation；不能因 Clang 支持 AST 和 sampling 就推断这些都受该旧 Soong 集成支持。[PGO][pgo]

其闭环是：

```text
指定参与模块和代表性 benchmark → 插桩编译/链接 → 运行负载产生 profraw
→ llvm-profdata 合并/加权 → 检入匹配 profile → 用 profile 重新编译 → 验证实际收益
```

- `pgo.benchmarks` 决定哪些 `ANDROID_PGO_INSTRUMENT` 采集构建会插桩该模块，`profile_file` 决定优化构建读取哪个文件；两者不是同一开关。
- 插桩 static library 的依赖链必须满足 profiling runtime 的链接要求；只给其中一个编译单元加标志可能产生链接失败或不完整采集。
- 同一库被多个 benchmark 使用时，需要聚合相应负载；计数加权应代表产品使用分布，不能让运行最久的合成负载无意主导优化。
- profile 应与代码一同版本化，使用分支预置的 `llvm-profdata` 处理。`-Wprofile-instr-out-of-date` 表明部分数据已不能可靠对应代码，需要重新采集。
- 缺失 profile 可能仅被记录到 dist 的 `pgo_profile_file_missing.txt`，使优化静默消失；构建成功不是 profile 已使用的证据。
- 插桩有运行开销，采集构建的耗时不能直接作为发布构建的性能结果。

**工程判断**：代码路径、新设备用途或训练负载改变后，应复核覆盖代表性与未覆盖路径的代价，不能仅以“有 profile”证明优化正确。
旧页面涉及的 build 变量、路径和链接闭包在旧分支复核，不将 deprecated 集成移植成新版本默认方案。

## 3. AutoFDO：采样对应产品真实行为

**事实**：Android 12 引入平台 AutoFDO 支持；它是 instrumentation PGO 的后继，以运行采样指导 native 优化。
官方列出 x86/x86_64/ARM/ARM64 采集支持，AOSP profile 位于 `toolchain/pgo-profiles/sampling`；具体规则通过 `afdo: true` 表达。[AutoFDO][afdo]

- AOSP 预置采样代表其采集时的手机/平板用途；本地修改的热点代码、新项目和独特产品负载需要自己的采样。
- profile 能跨架构使用不等于硬件结果可跨设备比较；采集来源、符号/代码版本、采样能力和产品负载仍要留存。
- 使用 `llvm-profdata`、官方 `afdo_summary.sh` 可审视最常执行函数；热点列表只证明被采样的执行分布，不证明所有关键低频路径已优化。
- Android 旧 PGO 页面中的“不支持 sampling”描述属于那一历史集成，不能拿来否定 Android 12+ 的 AutoFDO。

**工程判断**：验证时既比较代表性 CUJ 的时延/能量/代码大小，也保留没有出现在训练负载中的关键路径。
ETM、LBR 和 Profcollect 的具体采集部署尚需阅读目标架构与分支文档，本页不凭概览给出设备配置。

## 4. R8：可达性分析必须看得到真实入口

**事实**：Soong 对生成 DEX 的目标运行 R8，例如 `android_app`、`android_test` 和 `compile_dex: true` 的可安装 Java library。
静态 `android_library`/`java_library` 不直接执行最终 R8；它们可通过 `optimize` 和 `export_proguard_flags_files` 向下游传递 consumer rules。[R8][r8]

R8 的 shrinking、bytecode optimization、obfuscation 和 resource shrinking 是相关但独立的动作；实际默认值还受模块类型、release flag 和分支影响。
减少 DEX/资源可减少系统分区、编译产物及 demand paging 成本，但效果必须在实际产物与负载上测量。

### 动态入口和跨模块 API 是正确性边界

- Manifest、布局中的入口可由 AAPT2 产生保留规则；平台全局规则也覆盖部分注解、JNI native 方法等，但不能由此推断任意字符串反射都安全。
- `Class.forName`、反射成员名、JNI `FindClass`/`GetMethodID` 或资源名动态查找若未被分析表达，可能在 shrink/rename 后失效。
- 动态链接的 bootclasspath/system-server/shared Java API 要保留对外符号；调用者按 stub 编译成功不能保证被改名后的实现可解析。
- 外部 test APK 使用 `instrumentation_for` 直接访问目标内部代码时，目标混淆可能导致运行时 `NoSuchMethodError`/`NoClassDefFoundError`；测试能编译不是充分证明。

当前官方平台方案包括 declaration-site keep annotations、`protect_api_surface`、consumer rules，以及通过 `trace_references_from` 或 `allow_traced_references`/`trace_references` 从 DEX 消费者生成入口约束。
这些属性和自动生成的 Metalava/hidden-API 保留规则按目标 `build/soong/java/dex.go` 与 release flags 核实；旧分支未必具备。
同进程 self-instrumenting 测试、静态链接 `.impl` 也是不同的测试组织方式，不能为解除依赖报错盲目混用。

### 保留规则要最小且可解释

**工程判断**：审查每条规则保留了哪个动态入口/API/资源及其调用者，再选择删除冗余规则、声明处注解、导出 library rules 或精确手写规则。
`-keep class ** { *; }` 会大幅阻断优化；全部删除规则又可能破坏分析不可见的合法入口。
修改后验证真实反射/JNI、跨 APK 测试和资源路径，不写只复述 `Android.bp` 属性的测试。

R8 的 mapping 必须与实际产物匹配。当前 Soong 文档说明会生成 module dictionary、汇总 `proguard-dict.zip` 并记录 mapping 标识；排查混淆栈时保留匹配的字典，不能拿邻近构建 retrace。

## 5. Dexpreopt 的 class loader context 是有序依赖契约

**事实**：Android 12 的相关构建检查要求构建时和运行时 class loader context（CLC）一致。
CLC 描述共享 Java library 的类加载层次与查找顺序；重复类按先遇到的定义解析，因此依赖集合相同但顺序不同也可能改变语义。[CLC][clc]

```text
构建侧：Soong/Make 模块依赖 → dex2oat 的 CLC → 记录在 ODEX
运行侧：Manifest uses-library + 系统共享库 XML → PackageManager 的 CLC
                                      ↓
                            ART 比较上下文后决定接受预编译产物
```

- `uses_libs`/`optional_uses_libs` 应与 manifest 的 required/optional 库及相对顺序一致；不能把任意编译 `libs` 自动当成运行时共享库。
- 模块名与 manifest library 名不同，可能需要该分支的 `provides_uses_lib` 映射；长期应修正真实模块/API 组织，而非持续隐藏差异。
- ART 检测到 CLC mismatch 时可能拒绝 dexpreopt 产物并在设备 dexopt，首启 I/O、CPU 和耗时随之增加；“APK 已预编译”不证明实际加载了该产物。
- `RELAX_USES_LIBRARY_CHECK`、产品 broken-check 开关或关闭 dexpreopt 是临时减损手段。绕过检查无法证明上下文正确，且可能失去 AOT 收益。
- 自定义 class loader、动态加载另一个 APK 等情形并不一定能由构建图完整推断，需要核对目标 runtime 实际加载路径。

**证据**：保留 manifest、最终共享库配置、构建模块属性、ODEX 中的 classpath/CLC、首启 `ClassLoaderContext ... mismatch` 以及对应 dexopt 日志。
依赖修复后以同一首次启动条件验证，而不只比较已经在 `/data` 完成编译的后续启动。

## 6. ART profile、编译 filter 与设备资源

**事实**：dexpreopt 在构建主机执行；dexopt 在设备执行。bootclasspath 等依赖更新可能使构建产物失效。
`verify` 只校验，`speed` AOT 编译所有方法，`speed-profile` 根据 profile 编译方法并优化相应类加载；`quicken` 有 Android 11 及以前的适用范围。[ART 配置][art-config]

Android 14 起应用设备 AOT 由 ART Service 管理；Android 13 及以前使用 Package Manager 路径。
`pm.dexopt.<reason>`、filter 的 fallback、调度和 API 必须查对应管理者；仅设置旧属性无法证明现代 ART Service 已按预期运行。[ART Service][art-service]

- `.prof`/`.dm` 要与 APK 路径、文件名、二进制格式及 DEX checksum 匹配；请求 `speed-profile` 不保证实际使用成功。检查结果中的 `actualCompilerFilter` 与执行状态。
- cloud/local profile 有不同来源；共享给其他应用的代码还有隐私约束，不能随意用某应用的 local profile 指导其他应用。
- `pm.dexopt.<reason>.concurrency` 控制 dex2oat invocation 数；每个 invocation 的线程数是另一维度。二者乘积影响最大线程数量，CPU set/task profile 仍限制可运行资源。
- 扩大并发可能加快总完成时间，也可能产生 OOM、I/O 竞争与额外切换；不能仅看某个 dex2oat 进程更忙。
- ART Service 后台 dexopt 受 JobScheduler 的 idle、供电/资源与 thermal 条件约束；回调数量不必一一对应，不能用 start/done 计数自行推断整个 job 状态。

### Boot image 与 system-server profiles

**事实**：Android 11+ 可从 CUJ 应用 profile 中聚合 bootclasspath/system-server 方法与类使用信息。
boot profile、Zygote preloaded classes 和各 system-server JAR profile 是不同输出；boot profiles 进入镜像，不能在 OTA 之外任意替换。[Boot profiles][boot-profiles]

- 聚合必须是相同 boot image/bootclasspath 版本；保留 DEX checksum 和采集包来源。
- 多设备、多 CUJ 数据优于单一脚本的偶然路径；优先系统关键路径，也考虑低频但关键的 camera 等路径。
- 收录所有类/方法会增加成本，不能把更大 profile 当作更好覆盖。
- 比较时固定 app/profile 数据、冷/热缓存、编译状态和后台 job；否则首启、普通冷启动和编译后启动会被混成同一指标。

## 7. 启动优化沿关键路径归因

**事实**：官方 boot-times 主要使用 Android 8 与 Pixel 的案例，涵盖 bootloader、内核、I/O、init、boot animation 与 SELinux 标签成本。
案例中的 cfq、stune、具体 sysfs 路径和节省秒数属于历史设备，不能复制为现代产品设置。[Boot times][boot-times]

- bootloader/内核/用户空间有各自起止点；应带时间基准、阶段定义和正常启动/首启/OTA后启动条件。
- init 的慢 exec、builtin 或 property wait 会阻塞相应 action 路径；异步 service 可以并行工作，但依赖方必须以真实 readiness 条件 join。
- 系统日志中的慢 init command、`wait for service` 与 block/filesystem trace 可定位依赖和 I/O；删除 wait 或换成固定 sleep 都不能建立就绪契约。
- 非关键初始化可后移，但需证明它未被更早路径使用；ZRAM 的配置所有者在新版本可能是 `mmd`，不能照旧文章另加第二套 setup。
- boot-only boost、I/O/readahead 和暂时禁用的省电策略要在 boot complete、失败恢复及 charger 模式收敛，避免将启动收益变成持续耗电。
- 动画出现、退出信号、尾段动画完成、framework 就绪与可交互分别计时；缩短动画只能改变可见等待，不自动加快依赖初始化。

调试增加逐文件日志、内核 trace 或串口输出会改变负载。开发内核用的 trace 修改不能被误当成生产优化；保留诊断开销说明。

## 8. Capacity 与 jitter：热点、等待和 deadline 分开

**事实**：capacity 是一段时间内可提供的 CPU/GPU/I/O 等资源，jitter 是使关键工作不能及时运行的系统干扰。
更高频率可能增加 capacity，但不能消除固定时长的 I/O、关闭中断区段、锁等待或错误依赖。[Evaluate performance][eval] [Jitter][jitter]

| 证据 | 能说明什么 | 不能推出什么 |
|---|---|---|
| Simpleperf 的 CPU 样本与调用栈 | 被采样的实际执行热点 | 低样本函数没有造成等待 |
| `sched_wakeup` 到开始执行的 `sched_switch` | runnable 后等待 CPU 的时长 | 该线程此前阻塞的原因 |
| Binder/锁/I/O 与 blocked reason 时间线 | 关键路径依赖与等待 | 仅时间重合就有因果关系 |
| IRQ/softirq、preempt/irq-off 信息 | 调度线程被中断或不可抢占工作占用 | 所有时间都算该用户线程的业务 CPU |
| 最终 present/scanout 证据 | 是否在实际帧 deadline 前完成 | submit 或 queue 成功即用户看到 |

**工程判断**：沿输入→应用/UI→RenderThread→合成→最终呈现追踪同一帧，按实际刷新模式计算 deadline。
平均 FPS/总吞吐正常仍可能有明显 P95/P99 长尾；Binder/hwbinder 吞吐 benchmark 与 latency/deadline benchmark 回答不同问题。[VTS performance][vts-perf]

- 用稳定、轻量且连续的 UI 负载先暴露系统噪声，再验证真实 CUJ；合成分数不能代替用户感知性能。
- 高优先级 runnable 线程长期不能运行时，检查 IRQ/softirq、不可抢占段、CPU 约束和依赖，不先永久提高实时优先级。
- UI-critical 工作若被放入普通 workqueue，其可运行时间受其他任务竞争；应先明确执行上下文和实时性要求，再选择正确机制。
- thermal、频率、idle、内存 refault/回收与调度一起记录；固定低频等诊断实验只用于验证假设，不能直接成为产品配置。
- 标明 trace 数据源、缺失事件、buffer/丢失、权限、符号和采样工具开销；未采集到某事件不是证明它未发生。

## 9. 缓存优化有安装、数据库和窗口三种生命周期

### APK caching：历史 A/B 工厂预载方案

**事实**：Android 8.1 文档的方案使用新设备尚未被 OTA 使用的 `system_other`/B 分区保存预载内容，首启复制到 `/data/preloads/file_cache/<package>/`。
一旦 OTA 将新系统写入 B，原预载缓存不再可用；缓存不能靠该机制随 OTA 更新。[APK caching][apk-cache]

- 放在 B 的内容在 OTA 覆盖之前可跨 `/data` factory reset 再复制；直接放入工厂 userdata image 的内容则随 reset 丢失，两种实现的恢复能力不同。
- cache 是安装源/预载文件，不等于 APK 已安装、DEX 已编译或 app 已就绪；消费者还要正确完成实际安装和状态处理。
- 缓存访问具有 privileged/系统接口边界，低存储时需能回收，不能变成不可删除的永久占用。
- `preloads_copy`、目录创建和 SELinux 标签/域要一致；只把文件加入 image 不会自动完成首启复制。

该页面是历史特定 A/B 布局设计，不表示 Virtual A/B 的 snapshot 空间可被任意当 APK cache；现代设备需先确认分区和 OTA 所有者。

### Compatibility WAL：journal mode 与连接数不是同一设置

**事实**：Android 9 的 Compatibility WAL 让 `SQLiteDatabase` 使用 `journal_mode=WAL`，同时保持单数据库最多一个连接的兼容行为。
应用显式调用 enable/disable WAL 或明确指定 journal mode 后，不再由该兼容默认路径决定。[Compatibility WAL][wal]

- Room 默认完整 WAL 与 Compatibility WAL 是不同路径；不能看到 WAL 字样就推定连接并发语义相同。
- 收益取决于文件系统/负载。官方给出的 ext4/F2FS 结果是案例，不是所有存储的通用性能承诺。
- `db_compatibility_wal_supported` overlay 可控制平台兼容默认；修改前核对最终资源与应用显式配置，避免调整了未生效路径。
- `CtsDatabaseTestCases` 在合法关闭该模式时也可通过，CTS 通过不能证明设备实际启用了 WAL；还需实际 journal/连接行为和写入量/时延证据。

### Task snapshots：共享 GraphicBuffer 不等于应用已经绘出新帧

**事实**：Android 8 引入的 Task Snapshots 将 Recents thumbnail 与窗口恢复时的 saved surface 统一。
任务转后台时的 GraphicBuffer 可同时用于 Recents 和返回时的 starting window，应用首帧完成后再退出 snapshot；传递引用减少复制。[Task snapshots][snapshots]

- snapshot 是以前任务状态的视觉占位，不是当前应用完成初始化的证明，也不是可作为业务状态源的 live 内容。
- 内存中的 buffer 生命周期、磁盘 snapshot 恢复和真实 app 首帧要分别跟踪；不要把 snapshot 迅速显示计为真实冷启动完成。
- 磁盘可保存 high/low 两种缩放；先读低分辨率再替换高分辨率是加载时延与内存/清晰度的取舍。
- 调整 `config_highResTaskSnapshotScale`/`config_lowResTaskSnapshotScale` 需核对当前实现与最终 overlay；截图空白、低清和 first-frame 卡顿不是同一问题。
- 官方旧页面的源文件行号和“完全禁用”的做法属于历史实现；现代窗口安全/隐私与 snapshot policy 在目标 WindowManager 中另外核实，不能以清除标志恢复敏感内容预览。

## 10. Health HAL 与 trade-in mode：数据路径和信任结论分开

### Health 的角色与跨版本路径

**事实**：Android 13 引入 health AIDL，Android 13 首发及更新到相应目标 FCM 的 vendor image 有对应迁移要求；Health 2.1 文档保留作历史参考且已 deprecated。
不能用“设备当前是 Android 13”代替首发/vendor/FCM 条件。[Health overview][health] [Health 2.1 implementation][health21]

- BatteryService 接收 health 更新并向应用提供受控查询；应用不能因可访问 BatteryManager 就直接调用 Health HAL 或任意读 power_supply 节点。
- charger、recovery、framework 与 storaged 的运行环境不同；off-mode charging/recovery 成功不能只用完整 Android framework 下的查询验证。
- 历史 HIDL 的 `default` vendor 与 `backup` healthd 回退，以及 `libhealthloop`/`libhealth2impl`/`libbatterymonitor` 分工有具体版本条件；新 AIDL 实现不能照搬 backup 注册方案。
- sysfs 节点存在但权限/符号链接目标标签不正确时，默认实现也可能读失败；要验证实际 HAL domain 对最终目标的访问。
- 电流的符号、单位和充电状态必须一致：Health 2.1 要求电流以 μA 表达，充电正、放电负等条件应与电源连接状态相符；sysfs 电压 μV 与 HAL 历史 mV 转换要分清。
- 部分字段/节点可选不等于可伪造零值；检查默认 fallback 和对应 VTS 要求，不能从较宽松的旧测试推出数据契约可忽略。

**工程判断**：错误电流符号或量纲会使容量/充电归因失真；先证明 raw node→HAL→BatteryService→消费者各阶段的单位与更新时间，再修改 power profile。
本页未展开 health AIDL 全部实现与充电策略，具体接口/单位以目标冻结版本继续核对。

### Trade-in mode 的受限状态与可信诊断

**事实**：Android 16+ trade-in mode 面向满足 factory reset、无账号/连接/蜂窝服务、非 debug 等条件的设备，提供受限诊断；evaluation mode 再开放更完整评估能力。[Trade-in mode][tradein]

- `getstatus` 提供电池/存储/产品等健康信息，Android 17+ 还增加相机/UICC 字段；字段缺失可能是版本/能力差异，不等于硬件不存在。
- 设备就绪、获取普通 JSON、使用随机 challenge 的 attestation 和解析后信任判断是不同阶段；不要把普通字符串里的 IMEI/serial 视为已证明可信。
- attestation 的 challenge 必须与解析时一致；bootloader/verified boot、证书与报告属性共同决定信任，不能只检查存在 base64 certificates。
- evaluation 需要检查 FRP/防盗锁；custom setup wizard 需受权限保护的 receiver，并按状态检查、锁检查、provision、结束 setup 顺序集成。
- 退出 evaluation 发生 factory reset，测试 start/stop/wipe 也有明确状态与 build 前提；这些不是无副作用健康查询。本文只解释契约，不将命令示例当作执行授权。

## 11. 游戏状态 hint 与 NPU 调度是资源协调协议

### Performance Hint session：线程身份、目标与实际工作闭环

**事实**：Java `PerformanceHintManager` 从 Android 12/API 31 提供；NDK 的 get-manager/create-session、target/actual duration 和 close 等基础接口从 Android 13/API 33 提供。两套入口及后续新增接口的起始版本不能互换。[Java reference][hint-java] [NDK 头文件][hint-native]
应用为完成同一负载的线程组创建 session，报告 target work duration 与每轮 actual work duration，系统结合 SoC/DVFS/thermal 选择资源。[Performance Hint API][hint]

- 线程 ID 必须是 Linux native TID，而非 JVM 的 `Thread.getId()`；线程重建后旧 ID 不能继续代表新负载。
- 线程组改变时使用目标 API 支持的 set-threads 操作，低版本按相应生命周期重建 session；不能只修改应用的数组而不更新系统 session。
- actual duration 使用单调时间和纳秒单位，target 只在需求改变时更新；循环睡眠/等待不能无说明伪装成持续 CPU 需求。
- hint 是反馈请求，不是固定绑核/锁频保证；忙循环“骗” governor 会增加能量与温度成本。
- 验证包含线程归属、session 创建/更新/关闭、目标变化以及实际 deadline/能量；不能仅凭 API 调用成功或短期频率抬高声称产品收益。

具体 overload、set-threads 等新增接口及 preview 标记继续以目标 SDK/NDK reference、头文件引入级别与平台实现核实；不能把基础 session 的引入版本当作所有方法的起始版本。

### GAME 与 GAME_LOADING

**事实**：Android 14 的 GAME 表达前台游戏场景，Android 13 的 GAME_LOADING 表达加载状态，经 GameManager/PowerManager 传给 Power HAL。
两者提示的是场景，不是相同的永久 CPU boost。[Game boost][game-boost]

- Manifest game category、前台状态和游戏加载报告影响不同路径；loading 完成和场景退出必须收敛，不能留下永久状态。
- framework/CTS 测试能证明提示被转发，vendor HAL 是否改善加载/持续帧率仍需硬件实验；没有通用参考频率方案。
- 游戏稳态的能量、温度和 frame-time 目标与短时 loading deadline 不同，不能只测首秒峰值。thermal 保护边界仍以目标产品安全策略约束。

### Android 17+ NPU Manager

**事实**：NPU Manager 在 framework 端协调 model load reservation 和优先级，NPU scheduling AIDL HAL 向 driver 传递调度信息；它不是替代低层计算运行时的算子执行实现。[NPU Manager][npu]

- model-load 请求带 request ID、大小类别和优先级；异步获准后 client 真正加载完成才 `notifyModelLoaded`，卸载要求完成后才 `notifyModelUnloaded`。
- pending cancellation、系统要求卸载与 driver 的 completed/paused/failed/cancelled work lifecycle 分别处理，获准加载不等于模型已占用资源，暂停也不等于任务完成。
- app UID/实际调用归属、请求优先级与 effective priority 不可混同；后台请求不能仅靠自报高优先级绕过前台资源保护。
- `SchedulingConfig` 与 WorkInfo 的实例、UID、task/group、时间和原因应足以追踪 preemption/resume；debounce 会合并通知，回调少不能直接推断工作从未发生。
- feature declaration 和 VTS scheduling 测试只覆盖相应能力/接口，不证明特定模型速度、精度、thermal 或所有 driver scheduling policy。

驱动抢占粒度、各 workload 的 memory accounting 和硬件隔离仍需目标 vendor 实现证据；不能凭服务存在声称所有 NPU workload 都已受协调。

## 已读官方依据与仍需专项查询的范围

本页已提炼以下正文的机制。ETM/LBR/Profcollect 部署、完整 R8 注解语法、各版本 ART Service 全部 API，以及具体 SoC tracing/sysfs 参数仍是专项查询范围；没有在此声明已逐版本核实。

[pgo]: https://source.android.com/docs/core/perf/pgo
[afdo]: https://source.android.com/docs/core/perf/autofdo
[r8]: https://source.android.com/docs/core/perf/r8-optimization
[clc]: https://source.android.com/docs/core/runtime/art-class-loader-context
[art-config]: https://source.android.com/docs/core/runtime/configure
[art-service]: https://source.android.com/docs/core/runtime/configure/art-service
[boot-profiles]: https://source.android.com/docs/core/runtime/boot-image-profiles
[boot-times]: https://source.android.com/docs/core/perf/boot-times
[eval]: https://source.android.com/docs/core/tests/debug/eval_perf
[jitter]: https://source.android.com/docs/core/tests/debug/jank_jitter
[vts-perf]: https://source.android.com/docs/core/tests/vts/performance
[apk-cache]: https://source.android.com/docs/core/perf/apk-caching
[wal]: https://source.android.com/docs/core/perf/compatibility-wal
[snapshots]: https://source.android.com/docs/core/perf/task-snapshots
[health]: https://source.android.com/docs/core/perf/health
[health21]: https://source.android.com/docs/core/perf/health/implementation-2-1
[tradein]: https://source.android.com/docs/core/perf/trade-in-mode
[game-boost]: https://source.android.com/docs/core/perf/boost
[npu]: https://source.android.com/docs/core/perf/npu-manager
[hint]: https://source.android.com/docs/core/perf/performance-hint-api
[hint-java]: https://developer.android.com/reference/android/os/PerformanceHintManager
[hint-native]: https://android.googlesource.com/platform/frameworks/native/+/refs/heads/main/include/android/performance_hint.h
