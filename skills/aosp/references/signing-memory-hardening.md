# APK 签名与 native 内存硬化

核实日期：2026-10-28。签名建立包身份及更新关系，内存硬化约束代码运行时行为；二者不能互相充当安全证明。

## 包身份、证书与升级

Package Manager 验证 APK 签名和与已安装包的更新关系。Android 应用证书不要求像 Web TLS 一样经过公有 CA 验证。[应用签名](https://source.android.com/docs/security/features/apksigning)
同包名不代表相同签名身份，相同签名也不自动让不同包共享 UID。signature 权限、历史 shared UID、数据继承和包升级各有检查，不能靠重签名后“能安装”推定这些关系全部正确。

**工程推导**：系统应用重签、证书轮换或替换预装包时，分别核对包身份、已有数据、权限、共享 UID 和依赖包；不通过卸载清数据掩盖产品要求的原地升级失败。
镜像、AVB、APEX payload 与 APK 的签名属于不同验证层，某层校验通过不保证其他层匹配。

## v1/v2/v3/v3.1/v4 的能力不同

| 机制 | 主要约束 | 不能推导的结论 |
|---|---|---|
| v1/JAR | 历史系统的 APK 签名兼容方式 | 不能代替所有新签名块的完整性语义 |
| v2 | Android 7 起的整体 APK 保护和签名块验证 | 签名后重打包、修改受保护内容仍合法 |
| v3 | 支持 SDK 条件及 proof-of-rotation | 换了密钥就自动继承所有历史授权 |
| v3.1 | Android 13 起支持按 SDK 定向轮换，与旧平台签名选择兼容 | 老系统会识别新块并采用同一新签名 |
| v4 | 流式安装相关 Merkle tree 和独立 `.idsig` | 独立替代 v2/v3 的包签名 |

上述机制依据：[v2](https://source.android.com/docs/security/features/apksigning/v2)、[v3](https://source.android.com/docs/security/features/apksigning/v3)、[v3.1](https://source.android.com/docs/security/features/apksigning/v3-1)、[v4](https://source.android.com/docs/security/features/apksigning/v4)。
v3 的轮换谱系表达新旧 signer 关系，具体权限和更新行为仍取决于平台版本、验证实现和谱系能力。不能把一个证书 hash 永久写死为所有版本唯一有效身份，也不能无条件信任调用者自报的证书链。

**工程推导**：验证最终交付 APK 的签名方案、signer、lineage 与各目标版本的安装/升级结果；使用与产物匹配的 `.idsig`。只检查构建目录中的旧包会漏掉打包或重签步骤造成的差异。

## 新签名方案的版本边界

当前官方 v3.2 文档描述 Android 17 起的传统算法与 PQC 混合签名，要求新的密钥材料、共同签名谱系和相应的隐式轮换；旧 Android 忽略该块并使用已有方案。
它不是在任意旧方案中放入单个 PQC signer，也不是复用旧密钥就自动完成迁移。[v3.2](https://source.android.com/docs/security/features/apksigning/v3-2)

**工程推导**：对具体产品先确认目标分支、apksig/验证器、更新链及兼容设备，不以官网已经有新格式证明量产镜像已经支持。
需要检查拒绝降级/剥离后的行为、旧设备回退路径和更新身份，而不只验证一个新包首次安装。

## 检测、缓解与代码正确性

| 工具或机制 | 主要作用 | 解释结果时的边界 |
|---|---|---|
| ASan / HWASan | 通过插桩及运行时信息定位内存越界和生命周期错误 | 需要触发受覆盖路径；无报告不证明不存在错误 |
| MTE | 对指针与内存 tag 做硬件检查 | 硬件、内核、进程模式和分配器共同决定实际覆盖 |
| GWP-ASan / KFENCE | 对部分分配做低成本采样检测 | 采样未命中不能证明同一请求安全 |
| Scudo | 硬化 native 堆分配并拒绝部分异常 | 是缓解层，不能替代完整内存错误检测器 |
| CFI | 约束受保护的控制流转移 | 不检查全部数据不变式，也不自动修复 UAF |
| ShadowCallStack | 隔离受保护的返回地址 | 不保护所有程序数据与前向间接调用 |

工具应按目标架构、用户态/内核、构建模式和问题选择，不能仅因都带“sanitizer”就混用内核配置与用户态选项。

## MTE：模式决定报告含义

SYNC 在 tag 不匹配处同步中止，能较精确地关联访问及地址；ASYNC 在之后的内核入口等时点报告，不能把收到 signal 时的 PC 当成最初错误访问位置。
支持的模式及 ASYMM 能力随硬件和版本变化。[MTE](https://source.android.com/docs/security/test/memory-safety/arm-mte)

- 先从 tombstone 的 signal code、MTE mode、分配/释放记录与实际映射确认机制，区分同步与异步报告。
- 从异步发现切到适用的同步诊断可提高定位精度，但模式改变也可能改变时序；保留原运行环境。
- 只在某个进程开启检查不证明所有 native 库及非受覆盖分配都已验证。
- 不以清除指针 tag、关闭检查或修改 signal 处理作为缺陷修复。

## HWASan、采样和符号

HWASan 使用指针/内存标记与插桩，在适用的 AArch64 平台中报告堆、栈和释放后访问；它与依赖硬件 MTE 的检测不是同一机制。部分标记检测存在概率性漏检，单次零报告不构成穷尽证明。[HWASan](https://source.android.com/docs/security/test/hwasan)
它能定位 JNI/native 中的内存问题，不能直接检测 Java 堆中所有逻辑错误。是否支持单独目标、libc 和非 HWASan 镜像，按相应平台/NDK 文档核实。

GWP-ASan 与 KFENCE 分别面向用户态和内核的采样分配；报告、终止或继续执行语义不能互换。[采样检测](https://source.android.com/docs/security/test/memory-safety/gwp-asan-kfence)
保留故障输入、架构、Build ID、分配/释放栈、工具模式和 revision；错误符号可以产生看似合理的假定位。

## 控制流与分配器硬化

CFI 需要匹配的编译/链接配置；历史 LLVM CFI 使用 LTO 获取类型与调用信息。错误的跨语言函数指针、类型擦除或未按契约连接的库可能触发检查。[CFI](https://source.android.com/docs/security/test/cfi)
出现 CFI abort 时，先验证真实目标与类型契约，不用扩大 allowlist 或移除插桩掩盖错误调用。

ShadowCallStack 在相应 AArch64 实现中使用保留寄存器维护独立返回地址栈；不兼容的同进程旧代码/汇编若改写该寄存器，会破坏机制。[SCS](https://source.android.com/docs/security/test/shadow-call-stack)
Scudo 检测到堆异常而 abort 的位置可能是首次发现点；破坏通常发生得更早。[Scudo](https://source.android.com/docs/security/test/scudo)

**工程推导**：同时确认哪些目标编入保护、哪些库实际加载、运行开关是否生效，以及测试是否走到原缺陷路径；“构建启用了某选项”不足以替代这些证据。

## 指针标记和零初始化的误区

TBI 允许硬件忽略指针高字节，并不授权应用把高位当任意存储。截断标记、把指针转浮点后还原或跨 FFI 改写高位，可能在释放或受标记检查时失败。[Tagged pointers](https://source.android.com/docs/security/test/tagged-pointers)
临时兼容开关不会修复被依赖库错误的指针表示假设。

平台栈/堆零初始化的范围按版本、进程和构建核实；零值不是业务有效值，也不保证初始化顺序、对象生命周期或全部共享内存语义正确。[零初始化](https://source.android.com/docs/security/test/memory-safety/zero-initialized-memory)
去掉初始化来改善性能前，证明相应路径的赋值、失败和信息泄漏边界，不能仅比较热点 benchmark。

## GPU IOCTL 过滤与驱动契约

Android 16 QPR2 的 `set_xperm_filter` 使用 SELinux 扩展权限，将目标设备 IOCTL 分为普通应用允许、生产限制和仅 shell/debuggable app 可用的 instrumentation 集合。适用范围还受 appdomain 例外和 target SDK gate 控制；它与进程 seccomp syscall 过滤不是同一配置。[GPU syscall filtering](https://source.android.com/docs/security/features/gpu-syscall-filtering)

厂商需按实际驱动版本分类 IOCTL，不能把页面中的示例数字当作真实 Mali/其他 GPU 接口。验证既包含普通应用合法操作仍可执行，也包含未授权应用不能调用受限/调试 IOCTL；userdebug 成功不能替代量产 appdomain 的允许/拒绝结果。放宽整个 GPU device 的权限会破坏细粒度控制。

## 尚需目标证据的部分

此页提供格式与检测机制，不替代发布密钥管理、具体供应商固件验证、全内核硬化配置或产品安全认证。APK 签名成功、sanitizer 无报告和兼容套件通过各自只提供相应范围的证据。
