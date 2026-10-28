# ART 执行、DEX 格式与运行时状态

核实日期：2026-10-28。DEX 的有效性、类解析、解释/JIT/AOT 执行和 native/JNI 行为是不同边界。
进程/服务总览见 [runtime-framework.md](runtime-framework.md)；profile、dexpreopt 与 ClassLoaderContext 使用已有专题，本页不重复其配置手册。

## 执行模式不能从一个文件名推断

ART 的方法可处于解释、JIT 或 AOT 状态。JIT 使用运行时类型信息，支持 OSR，生成代码不必与 AOT 完全相同。
`.oat` 存在不证明它包含本方法的编译代码；存在代码也不保证适用于当前依赖和运行状态。
JIT code cache 会因内存压力回收，profile 快照也不承诺记录所有曾 JIT 的方法；缺少一个 profile 条目不证明该方法从未运行。[JIT][jit]

| 失败位置 | 需要观察的证据 | 不应直接采用的修复 |
|---|---|---|
| DEX 解析/验证 | magic、结构/指令约束、具体方法和 dex PC | 清除所有缓存来掩盖无效字节码 |
| 类加载/解析 | loader、依赖、访问性与初始化异常 | 只调 JIT 阈值 |
| 执行/反优化 | 方法模式、OSR/deopt、运行时异常 | 仅以 oat 文件存在认定已全 AOT |
| native/JNI | 进程 ABI、引用生命期、tombstone、GC 交互 | 认定所有 heap corruption 都是 GC bug |
| 性能 | 同场景编译状态、分配率、暂停/调度与 I/O | 全设备强制 speed 后当作通用产品策略 |

GC 的职责是回收不可达对象，不是把所有进程 RSS 立即还给内核。
官方 GC 调试页描述 Android 8 的 Concurrent Copying、Android 10 起的 generational CC 与 CMS 历史配置；具体 collector/default flag 必须看目标 ART，不能永久宣称所有新版本仍用同一计划。
并发 GC 仍会有暂停、读屏障与 CPU 成本；高分配率、长时间保留对象或 native 内存压力可产生不同现象。[GC][gc]

GC verification 检查 roots、可达引用和 allocator 记账，可帮助定位堆破坏发生在 GC 前后哪个阶段。
verification/追踪会改变时序与开销，诊断构建的性能不能直接代表发布构建。
观察 GC pause、total duration、freed bytes、allocation/throughput 与线程 trace；一次 GC 恰好靠近卡顿并不构成因果证据。

## DEX 索引、字符串和容器

DEX 存储类定义和 string/type/proto/field/method 等索引表；定义与引用是不同对象。
多数表有特定排序/去重约束，class_defs 还受依赖顺序约束，不能拼接两个文件的表而不重写引用。
string_data 使用 MUTF-8，长度字段按 UTF-16 code unit 计数；它不等于 UTF-8 字节数，不能直接用 strlen/strcmp 处理所有有效字符串。[DEX][dex]

header、map、offset/size、对齐与不重叠关系共同约束结构；LEB128 是有限长度的变长整数，不可无界读取直到找到结束位。
checksum 和 DEX header 的 SHA-1 signature 用来检查格式内容，不等同于 APK 签名、发布者身份或 Verified Boot 信任。
因此重算 checksum 只能让某类完整性字段一致，不能使无效指令、错误类型或未授权 APK 成为有效可信代码。[格式][dex] [约束][constraints]

DEX version 与 Android/API 条件需配套：037/038/039/040 分别涉及默认方法、invoke-custom/polymorphic、method-handle/type、名字规则等变化。
当前官方说明 Android 16 对 041 container format 的支持仍为实验用途，不应作为生产代码格式。
041 的 header/container_size、跨 header offset 与 ≤040 的单文件假设不同；解析器不能把较大版本号简单当成 035 的同布局。[版本][dex]

## Code unit、寄存器与指令变体

Dalvik 是寄存器机，方法 frame 的寄存器数固定；普通值按 32 bit 使用，64 bit 值占相邻寄存器对，不要求偶数对齐。
方法参数放在 frame 的末尾寄存器，wide 参数占两个；instance 的第一个参数是 this。
插入局部寄存器或改参数时需要重新解释这个布局，不能只加 registers_size 而保留全部 v/p 引用假设。[bytecode][bytecode]

指令流以 16-bit code unit 为单位，指令长度、branch offset 与 dex PC 不能一律按 byte 计算。
格式 ID 的首位说明 code unit 数，寄存器位宽可能只有 4/8/16 位；合法的 frame 寄存器号不代表任意 opcode 都能编码它。
高寄存器、较大常量池索引和 range invoke 需选择合适变体或 move，不能静默截断字段。
例如将局部寄存器扩到 v20 后，仍用只能编码 v0–v15 的变体，即使文本看似合理也不合法。[指令格式][formats] [bytecode][bytecode]

switch/fill-array-data payload 是数据伪指令，需对齐且不可从正常控制流进入；插入 nop、移动 payload 或指令会影响跳转/异常/debug 信息。
修改方法必须同步调整 branch target、try 范围、handler、debug address 与相关长度，不能把十六进制替换当成语义不变的补丁。

## 校验约束的层次

| 约束层 | 关键不变式 | 失效推导 |
|---|---|---|
| 文件完整性 | 合法 header/section、范围、对齐、map 不重叠 | 文件可被 ZIP 解出不证明可加载 |
| 静态 bytecode | 有效 opcode、长度、索引、寄存器与 branch 边界 | 跳进一条指令中间或 payload 仍不合法 |
| 结构/数据流 | 先赋值后读、类型兼容、wide pair、初始化状态 | 单条指令都合法，合流后的类型仍可能非法 |
| 调用/结果 | 参数与原型匹配；move-result 紧随对应调用；move-exception 位于 handler 首位 | 插桩插进结果/异常协议会改变有效性 |

构造器中的未初始化实例有专门限制，不能当作普通对象任意传递或读字段。
return、field store、invoke receiver 等需满足类型兼容，字节码验证不是仅“指令能解码”。
排查 VerifyError 应记录完整异常、class/method、dex PC 与生成/转换工具版本，再映射到对应约束层。[约束][constraints]

## ART TI 与 Zygote 的授权和继承边界

Android 8+ ART TI 经 JVMTI plugin 暴露能力；agent 可观察分配、GC、栈与类重定义，但不等于 Java instrumentation 的完整桌面接口。
重定义使用只含单个类定义的 DEX，API 能力还随版本变化。[ART TI][ti]

运行时 attach 同时由 ActivityManager 的包信息和 ART 启动时保存的 debuggable 状态检查，普通生产应用不能由任意 attach 命令插桩。
agent 的 dlopen 还受文件权限与 SELinux 约束；找得到路径不等于可加载。
手动 dalvikvm 启动时加载 agent 的测试路径与从 Zygote fork 的正常 app 不同；Zygote 不允许加载这种 agent，不能以测试 runtime 成功推出 system_server 可任意 attach。[ART TI][ti]

Zygote 预加载、fork、specialize 与 USAP 影响启动时延和共享页；新增预加载对象会被后续进程继承，写入又可能触发 copy-on-write。
FD 白名单用于明确哪些打开资源可被子进程继承；不应为了绕过异常而放行含凭据或未定义生命期的 FD。
ABI 对应 Zygote、WebView Zygote 与普通 app Zygote 的职责不同；64 位设备不证明每个进程都用相同 ABI。[Zygote][zygote]

## Signed Config 与 soft restart 的历史条件

Signed Config 从 Android 10 支持，在 APK metadata 中携带 base64 JSON 与 ECDSA-p256 签名，允许可信来源调整指定 non-SDK 限制配置。
它不是任意 APK 把 Settings.Global 当自由配置入口；签名校验和内建信任根是功能的一部分，官方不支持 OEM 自由定制密钥/机制。
应区分 APK 自身签名和嵌入 config 的签名，不能因 APK 已安装便认定配置已应用。[Signed Config][signed]

soft/userspace restart 从 Android 11 用于部分需重启的用户空间更新，Android 15 已弃用。
它只重启 data 挂载后启动的相应进程，CE 仍可保持解锁，kernel/早期进程未必重启；与冷启动不同。
init 需要重置状态、停止进程、reset volume、卸载 APEX、回到 bootstrap mount namespace，并按 checkpoint 能力恢复；失败可能回退为硬重启。
这类历史特性不能作为当前所有 APEX/安全更新免整机重启的承诺，`boot_completed` 也不能证明经历了硬件 reset。[Soft restart][soft]

## Runtime 分支归属与未展开内容

执行/JIT/GC/ART TI、DEX format/bytecode/instruction formats/constraints、Zygote、Signed Config、soft restart 由本页承接。
ART Service、compiler filter、profile 与 CLC 交给现有运行时/性能专题；RRO、资源覆盖及故障定位见 `runtime-framework.md`、`system-configuration.md`。
未逐表复制 DEX opcode、encoded_value、debug state machine、每个 verifier 条款或 collector 的全部内部算法；涉及二进制解析/生成时仍需目标版本规范与实际 verifier 证据。

## 官方依据

[jit]: https://source.android.com/docs/core/runtime/jit-compiler
[gc]: https://source.android.com/docs/core/runtime/gc-debug
[dex]: https://source.android.com/docs/core/runtime/dex-format
[bytecode]: https://source.android.com/docs/core/runtime/dalvik-bytecode
[formats]: https://source.android.com/docs/core/runtime/instruction-formats
[constraints]: https://source.android.com/docs/core/runtime/constraints
[ti]: https://source.android.com/docs/core/runtime/art-ti
[zygote]: https://source.android.com/docs/core/runtime/zygote
[signed]: https://source.android.com/docs/core/runtime/signed-config
[soft]: https://source.android.com/docs/core/runtime/soft-restart
