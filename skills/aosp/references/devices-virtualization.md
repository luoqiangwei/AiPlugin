# 设备形态、虚拟设备与隔离执行

Cuttlefish 实例/恢复/宿主边界见[Cuttlefish host/guest](cuttlefish-host-guest.md)，TV 的 TIF/Tuner/CAS/CEC 见[TV 集成](tv-device-integration.md)。

基线核实日期：2026-10-28。虚拟设备、受保护虚拟机和面向用户的设备形态属于不同维度。
本页用于识别可被某种环境证明的行为；可运行不等于具备目标硬件能力或安全保证。
API、架构支持、内核配置和设备要求均应在目标分支、产品和对应版本 CDD 中复核。

## Cuttlefish 与 Android Emulator

Cuttlefish 面向平台开发，强调与目标 AOSP Framework 的行为一致性，可配置和并行运行虚拟设备。
Android Emulator 主要服务应用开发；它的宿主工具、系统镜像与应用开发集成有不同目标。[虚拟设备定位][cuttlefish]
两者都能运行 Android，不代表其内核、虚拟 HAL、设备模型或快照行为相同。

| 需求 | 适合的证据环境 | 证据边界 |
|---|---|---|
| 自定义 Framework 的权限、进程和 API 行为 | 对应源码构建的 Cuttlefish | 不证明真实 SoC 的 HAL 实现 |
| 应用在公开 API 下的交互 | 对应版本 Android Emulator 或设备 | 不证明产品私有系统修改 |
| 调度、热量、功耗、无线与物理传感器 | 目标硬件及匹配镜像 | 虚拟设备数据不能代替量测 |
| 可重复的大规模平台回归 | 固定镜像与配置的虚拟设备 | 需记录虚拟硬件与宿主差异 |

失败可能来自 Android guest、虚拟设备后端或宿主，三者日志不能混在同一个故障归因中。
宿主架构、KVM、CPU 特性、图形后端和镜像版本共同决定能否启动与可用功能。
“adb 连接成功”只证明 transport 可用，不证明 Framework 完成启动或各 HAL 已就绪。

## AVF 解决的隔离问题

AVF 提供比普通应用沙箱更强的隔离执行环境，关键目标是受保护 guest 的机密性和完整性。
VirtualizationService 管理 VM 生命周期；crosvm 承担 VMM 与虚拟设备后端职责；pKVM 提供受保护隔离。[AVF 定义][avf]
这些组件不是可互换的名称，进程隔离、容器和 pVM 也不能混用为同一安全承诺。

参考实现主要面向 ARM64；官方架构文档也列有 x86_64 非保护 VM 测试支持。
因此测试模式可用不能推出 protected VM 在该硬件上得到支持。[架构边界][avf-architecture]
目标设备还需要对应内核、固件、产品包和权限支持，不能只添加一个 Java 调用就启用保护。

## pKVM、内存与可用性

pKVM 通过 EL2 的隔离约束限制宿主访问 protected guest 内存。
显式共享页仍是接口的一部分，共享的数据和缓冲区需要按不可信输入处理。
VM 销毁后的内存清除、固件验证和实例状态绑定共同维持隔离语义。[安全模型][avf-security]

重要的不变式是宿主不能任意读取受保护内容，而非宿主必须随时让 VM 继续运行。
宿主可以影响 guest 的执行和资源可用性；pVM 不提供对恶意宿主的无限可用性保证。
仍需信任架构假定中的硬件、供应链和相应启动根，不能把 pVM 当作消除所有信任的机制。

审查共享内存或 RPC 时，关注共享范围、所有权转移、边界校验和 guest 端授权。
客户端持有一个 Binder 句柄，不代表它应当获得 guest 中的任意功能或秘密。

## pvmfw、DICE 与实例身份

pvmfw 在 pVM 的启动链中验证初始内容，并参与派生与实例关联的秘密。
DICE 使用启动阶段的测量和配置等输入派生身份材料，形成后续验证所依赖的链。
它不是“生成一个与所有代码版本无关、永不变化的通用密钥”。[启动架构][avf-architecture]

镜像、调试状态或 payload 身份变化，可能影响秘密派生和实例可继续启动的条件。
实例磁盘、镜像签名和验证元数据需要一致，复制一个磁盘文件不自动复制合法实例身份。
证明应同时解释请求者如何验证 attestation，以及它把哪个测量结果视为可信。
只有证书链而没有验证策略，不能证明所执行的 payload 符合业务预期。

## Microdroid 的能力范围

Microdroid 是面向隔离 payload 的精简 Android guest，不是缩小屏幕的完整 Android 产品。
它提供 Bionic、部分 NDK 能力、Verified Boot、SELinux 和 Binder RPC over vsock 等机制。[Microdroid][microdroid]
标准的 SystemServer、Zygote、图形 UI 和一般 `android.*` Java API 不是其默认能力。
部分 Java 核心能力的可用性取决于 ART APEX 等具体配置，不能据此假定完整 Framework 存在。

宿主通常负责 UI 与 VM 管理，guest 执行需要隔离的 payload。
跨 VM 的接口应保持窄且清楚，避免把宿主路径、FD、参数或结果当成可信事实。
调试配置与生产保护配置的保证不同，调试日志不能泄漏设计中应受保护的资产。
APK/APEX 更新及实例状态兼容需要专门判断，不能直接沿用普通应用热更新的假设。

## TV、Watch 与其他形态

设备形态改变的是产品能力、输入输出、资源与兼容性条件，不只是屏幕尺寸。
TV 的 TIF 连接 TV App、输入管理、输入服务、节目数据及可选硬件能力；TIF 本身不实现所有地区广播标准。[TV 架构][tv]
调谐器、HDMI 输入、CEC、CAS 和 OTT 播放是不同链路，不能用一种播放成功证明另一种输入正常。

Watch 类产品还受小屏交互、输入方式、传感器、续航和资源限制影响。
面向 Watch 的 Android 兼容性条件与 Wear OS 的特定服务或产品要求不能等同。
不同形态的必选、可选和条件要求，应读取对应 Android 版本 CDD 的设备类型条款。[形态要求][cdd]
不要将某个手机的 HAL 集合、物理按钮或持续网络连接假设推广到所有 Android 设备。

## 传感器机制与测量语义

Android sensor 是 HAL 暴露的数据能力，物理芯片与逻辑 sensor 不必一一对应。
相机、麦克风、指纹等有各自接口，不属于 Android Sensors 列表中的同一种报告机制。[传感器定义][sensors]
虚拟和组合 sensor 仍需满足它声明的事件语义，而不只是数值看起来合理。

Batching 把事件暂存在 sensor hub 或 FIFO 后再上报，以减少处理器唤醒。
采样周期与最大报告延迟分别影响采集和交付，不能把一次批量回调的间隔当成传感器采样周期。[批处理][batching]
事件时间、交付时间、FIFO 容量、flush 完成和 wake-up 行为需分别验证。
缓冲溢出、休眠恢复和 sensor 激活/取消是定位丢数或耗电的关键边界。

## 诊断证据与常见误推

| 现象 | 有区分力的证据 | 常见误推 |
|---|---|---|
| Cuttlefish 启动失败 | host 日志、VMM 日志、kernel/Android 启动阶段 | 所有失败都来自 Framework |
| pVM 创建失败 | VM 配置、权限、内核能力、固件与验证日志 | 换一个 APK 权限就能开启 pKVM |
| guest 更新后不再启动 | payload 身份、签名、实例状态与验证错误 | 关闭验证即可证明功能正常 |
| TV 有画面但遥控异常 | 输入设备路由、焦点、CEC 与应用处理链 | 视频成功意味着电视集成完成 |
| sensor 间歇丢数 | 事件时间序列、FIFO、flush、休眠和订阅状态 | 提高线程优先级即可解决 |
| 虚拟设备性能良好 | 宿主负载与配置、目标硬件重复量测 | 可直接发布相同功耗和延迟结论 |

选择验证环境时，应明确要证明 API 行为、设备集成还是隔离属性。
缺失某类硬件时，可以报告已验证的软件路径及剩余硬件证据，不把模拟输入升级为实车或物理量测结论。

## 官方依据与版本复核

以下页面已阅读；示例 `main` 或当前网页的架构说明不固定交付版本。
AVF 保护模式、Microdroid API、虚拟硬件配置及 CDD 条件均以目标分支和设备声明复核。

[cuttlefish]: https://source.android.com/docs/devices/cuttlefish
[avf]: https://source.android.com/docs/core/virtualization
[avf-architecture]: https://source.android.com/docs/core/virtualization/architecture
[avf-security]: https://source.android.com/docs/core/virtualization/security
[microdroid]: https://source.android.com/docs/core/virtualization/microdroid
[tv]: https://source.android.com/docs/devices/tv
[cdd]: https://source.android.com/docs/compatibility/16/android-16-cdd
[sensors]: https://source.android.com/docs/core/interaction/sensors
[batching]: https://source.android.com/docs/core/interaction/sensors/batching
