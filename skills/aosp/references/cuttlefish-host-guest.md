# Cuttlefish 的 Host、Guest 与实例状态

用于虚拟设备实例、磁盘重置/快照、虚拟硬件、远程交互与混合镜像。核实日期：2026-10-28。
平台与 AVF/pVM 的定位见[设备与虚拟化](devices-virtualization.md)。本页讨论普通 Cuttlefish；多实例/容器隔离不等于 pKVM 对恶意宿主的机密性保证。

## Host package 与 guest images 共同定义设备

[Cuttlefish](https://source.android.com/docs/devices/cuttlefish)追求与相同 AOSP Framework 的功能一致性，差异主要集中在 HAL/硬件交互；虚拟射频、GPU 和传感器不能代替真实硬件性能或认证证据。
[启动条件](https://source.android.com/docs/devices/cuttlefish/get-started)涉及 Linux host、KVM、host CPU/权限及图形能力。仅发现 CPU 虚拟化 flag 不证明当前进程能访问 `/dev/kvm`，云端还可能需要对应虚拟化支持。
官方要求 host package 与 guest images 来自同一 build；混用可以造成虚拟设备协议或工具格式不匹配，而非 Android Framework 本身错误。

[Custom device](https://source.android.com/docs/devices/cuttlefish/custom-device)把产品继承/镜像与运行时 canonical JSON 分开；后者描述每个 VM 的 CPU、RAM、显示等配置。
旧平铺的 launch config 与新层次 JSON 不是同一种结构，不能仅把参数名称复制过去。
扩大虚拟显示/RAM 只是虚拟配置，不能推断真实设备的内存带宽、显示硬件或功耗行为。

## 多租户共享基线，修改进入各实例 overlay

[Multi-tenancy](https://source.android.com/docs/devices/cuttlefish/multi-tenancy)允许多个 guest 共享只读基线镜像，每个实例通过独立 COW overlay 保存 Android 分区变化。
guest 看见的完整磁盘与 host 实际增量占用不同；运行越久、写得越多，host overlay 就越大。
reset 回到的是这份基线，不能误以为原始磁盘文件可以在实例运行中随意替换。

实例号分配关联 host TCP、TAP 等资源，serial、instance number 与设备 UI ID 也有不同用途。
同一次多实例创建和多次独立创建要正确分配这些资源，避免端口或虚拟网络冲突；默认资源数量是 host 安装配置，不是 guest 的最大能力。
某些 stop/remove 操作针对整个实例组，restart/powerwash 又可指定单个实例；不能按一条 adb serial 推断 host 命令的作用范围。

**工程推导**：多租户有三层隔离要分别确认：磁盘写入是否只进本实例、host 资源是否唯一、虚拟无线介质是否按预期共享。
共享无线介质使设备互相发现是功能，不是磁盘 overlay 泄漏。Host 仍持有镜像、overlay、VMM 和远程控制端点的管理权，不能只由“独立 guest UID”证明宿主不可访问其状态。

## Restart、powerwash 与 snapshot 恢复的对象不同

| 操作 | 官方语义 | 对证据的影响 |
|---|---|---|
| guest `adb reboot` | Android 正常关闭、同步并重启，host 进程不参与重建 | 保留 guest 磁盘状态，适合解释正常关机恢复 |
| host `restart_cvd` | 非正常断电式重启 | 未同步写入可能丢失，不能当作正常 shutdown 的结果 |
| powerwash/reset | 停止实例、清除相对基线磁盘变化并启动 | 本次测试产生的应用/数据修改不再存在 |
| stop 后 resume | 保留可兼容的既有 overlay 再启动 | image、磁盘布局等不兼容变化可触发重建，不能承诺所有 flags 都可变 |
| snapshot/restore | 保存并恢复 vCPU、RAM 和设备状态 | 不只是保留 userdata，也不等同重新执行一轮干净启动 |

[Restart/reset](https://source.android.com/docs/devices/cuttlefish/restart)明确：内核、initramfs、磁盘镜像/格式和 VMM 等配置变化可能使旧 overlay 不兼容；检测到不兼容后会重建状态。
因此“替换内核后应用配置消失”可能来自虚拟设备基线兼容处理，不必然是 Android 数据清理 bug。
禁用 overlay 后，写入直接改变底层镜像，失去同样的快速 reset 语义；在两种模式间切换不能假设原状态能无损继续。

[Snapshot/restore](https://source.android.com/docs/devices/cuttlefish/snapshot-restore)自 Android 15 提供；当前文档限制 x86_64、禁用 VirtioFS，且只支持 guest SwiftShader 图形模式。
快照前需 suspend，停止 vCPU/设备并把 buffer 状态推入 VM；restore 时原实例必须已停止，并匹配相应实例编号条件。
快照包含 guest 内存中的状态，应按其真实内容管理，不能只当作无状态镜像缓存。
远端服务器、共享无线环境和宿主外部进程不因 guest 恢复自动倒退，故恢复某个 UI 不证明外部协议回到同一会话。

## GPU 与 WebRTC 是两个不同的图形边界

[GPU acceleration](https://source.android.com/docs/devices/cuttlefish/gpu)可把 guest 渲染命令交给 host GPU：GfxStream 转发 OpenGL/Vulkan，Virgl 经中间表示到 host OpenGL，文档明确 Virgl 不支持 Vulkan。
无适用加速时 SwiftShader 以软件执行图形 API；Android 版本、host driver 和具体 gpu_mode 都影响实际路径。
这改变性能与宿主依赖，不表示 guest 应用中的渲染、编码、浏览器传输是一个组件。

[WebRTC](https://source.android.com/docs/devices/cuttlefish/webrtc)提供浏览器远程画面、输入和可扩展的 camera/mic/sensor 数据通道，并支持 in-browser ADB。
信令页面可打开不表示媒体连接成功；默认 HTTPS 页面之外还涉及 TCP/UDP 媒体端口，实际监听和协商应按所用 host package 配置观察。
无画面可分别来自 guest 没产出帧、host 渲染失败、编码/传输异常或浏览器会话失败，不能统一归因于 SurfaceFlinger。

[Control panel](https://source.android.com/docs/devices/cuttlefish/control-panel)的按钮既可执行 adb shell，也可把按下/抬起事件传给 host action server。
后者是 host binary，经 socket 接收命令并维护可选状态；它有能力改变实例生命周期，不能把自定义按钮都理解为普通 Android touch 输入。
配置声明按钮与正确消费 `down/up` 事件是两件事，漏掉 release 可使模拟按键一直处于按下状态。

## 虚拟无线与环境控制

| 子系统 | 模拟对象与控制入口 | 可以证明与不能证明的内容 |
|---|---|---|
| [Wi-Fi](https://source.android.com/docs/devices/cuttlefish/wifi) | Wmediumd 传递模拟无线包，OpenWRT 提供虚拟 AP；Android 14+ 使用 WmediumdService/OpenwrtControlService | 可控制 SNR、位置、发射功率与抓包来解释上层连接；不证明真实天线/射频性能 |
| [Bluetooth](https://source.android.com/docs/devices/cuttlefish/bluetooth) | Rootcanal 建立模拟 controller/device/PHY 与远端连接 | beacon、键盘、sniffer 等可驱动协议行为；发现成功不代表真实 controller 固件互操作 |
| [NFC](https://source.android.com/docs/devices/cuttlefish/nfc) | Android 15+ 的 Casimir 模拟外部设备，注入 NFC-A/ISO-DEP APDU | 可验证 HCE 路径与 APDU 响应；不证明物理 SE applet 或 NFC 天线符合相同条件 |
| [Environment control](https://source.android.com/docs/devices/cuttlefish/control-environment) | `cvd env`/REST 按 device ID 定位服务、方法、proto 类型，再调用 GNSS/AP/Wmediumd/Casimir | RPC OK 说明控制服务接受请求，Android 消费事件/完成连接是后续状态 |

[多设备连接](https://source.android.com/docs/devices/cuttlefish/connectivity)区分同次多实例默认共享介质与多次启动时显式连接同一介质/避免重复 AP。
旧 connectivity 页仍展示旧 wmediumd_control 用法，Android 14+ 的专门 Wi-Fi 页以新服务为准，不能把两者当作同时必需的守护进程。
环境控制时，instance/user、station MAC、device ID 与服务端口必须对应，否则一次成功调用可能改变了另一台设备的环境。

## 多显示、内核和 bootloader 的虚拟集成

[Multi-display](https://source.android.com/docs/devices/cuttlefish/multi-display)在启动配置中创建多个显示；[hotplug](https://source.android.com/docs/devices/cuttlefish/display-hotplug)在运行时添加/移除显示，当前文档明确 hotplug 显示不支持输入。
显示 ID 应从当前设备状态取得，不能永久把“第二个配置”当作固定 ID 1；画面存在也不证明 Activity/task/输入落在正确 display。

[Kernel development](https://source.android.com/docs/devices/cuttlefish/kernel-dev)要求匹配架构的内核与 virtual-device 模块/initramfs；旧非 GKI 组合的启动参数又有不同条件。
[Bootloader development](https://source.android.com/docs/devices/cuttlefish/bootloader-dev)使用 Cuttlefish 的 U-Boot 配置，assembler 可按提供的 kernel/module 产物重包 boot images。
这能隔离通用启动逻辑问题，却不等于真实 SoC 初始化、存储协议或安全固件已验证；镜像容器契约继续见[Bootloader 与设备树](bootloader-device-tree.md)。

## Hybrid device 与 host 编排

[CHD](https://source.android.com/docs/devices/cuttlefish/create-chd)自 Android 15/API 35 起，将物理产品的 Framework 侧 target files 与 Cuttlefish vendor 侧 target files 合并后生成虚拟镜像。
所以它可提前运行产品 Framework，却继续依赖 CF HAL/虚拟硬件；不能把 CHD 中相机/基带表现当作该物理产品闭源 HAL 的结果。
合并必须处理真正的镜像/元数据组合，不是把一个 system.img 随意覆盖到任意 vendor 后就宣称同等设备。

[On-premises](https://source.android.com/docs/devices/cuttlefish/on-premises)把 Docker host 环境、Cloud Orchestrator 服务和客户端 cvdr 分成不同层；容器打包依赖不消除 KVM、CPU 架构或 GPU 条件。
并行实例的 CPU/RAM/磁盘与媒体开销要按真实组合计算，示例容量不能当作所有 guest 的承诺。
管理 API 返回“创建实例”与 guest 可 adb、Framework 启动完成、虚拟 HAL 就绪各有独立结果。

[CTS stable subset](https://source.android.com/docs/devices/cuttlefish/cts)是 CF 上当前稳定的虚拟设备计划，某些 CTS 依赖真实硬件而不在相同能力范围内。
因此报告需保留计划、build、实例配置和 skipped/assumption 状态；不能把 stable subset 通过写成“整机 CTS 和硬件能力全通过”。本资料未实际创建实例或执行 CTS。

本页覆盖 CF 侧栏的实例/控制/虚拟硬件/混合设备关系；未穷举所有 launcher flag、Cloud Orchestrator 部署与鉴权实现、VMM 设备协议、GPU host 驱动细节和无线 simulator 全命令集。
