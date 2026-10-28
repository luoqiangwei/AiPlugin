# Android BPF 规则来源与版本

本文件仅用于来源、版本争议与精确机制复核；执行规则在 Android BPF 专题。核验日期：**2026-10-28**。
以下官方页面已读正文；Gitiles 源码通过官方站点的 `?format=TEXT` 只读取得，并阅读与规则有关的构建定义、函数和测试断言。大文件不声明逐行完整审计。
归纳采用固定 revision 的 `android14-release` 作为可复核机制基线，另用 `android16-release` 证明 loader 架构已变化；这不是目标产品 manifest，也不是跨仓库组合已经构建/运行的证据。

## 官方概览与历史边界

- [Extend the kernel with eBPF](https://source.android.com/docs/core/architecture/kernel/bpf)：实读构建、启动加载、pin、用户态 attach/map 读取与诊断段落。采用其分阶段集成思路，不将示例省略的错误处理当生产实现。
- [eBPF traffic monitoring](https://source.android.com/docs/core/data/ebpf-traffic-monitor)：实读流量统计用途、权限/内核需求、验证与测试定位。其 Android9 迁移说明与旧 `system/netd` 路径只作历史材料，不能替代 Android14/16 实际代码。
- 基础页面仍以 `/system/etc/bpf/` 概括启动加载；固定 Android14 源码还处理 vendor/Tethering APEX 位置。页面的 program-type 表不能替代实际 attach type：cgroup 包路径与 socket create 分别核对。
- 不采用网页中关于 typedef/struct 的历史编译限制作为当前编码门禁；也不把文章列出的旧测试名直接推广到所有分支。

## 固定分支与仓库 revision

| 分支 | 仓库与固定 commit | 使用范围 |
|---|---|---|
| android14-release | [system/bpf](https://android.googlesource.com/platform/system/bpf/+/a0e21c637428e1e416df106a04bc59a6a7b00faf/) | C++ loader、metadata 解析、pin 复用、init 服务 |
| android14-release | [build/soong](https://android.googlesource.com/platform/build/soong/+/9387734632ba3bf381bd57a638ac1216108c59f4/) | bpf 构建、对象输出与安装选择 |
| android14-release | [frameworks/libs/net](https://android.googlesource.com/platform/frameworks/libs/net/+/7c4073f3f973e54ac8354cd949b4d0e0a3e7c37a/) | loader 元数据定义、map wrapper、loaded 等待 |
| android14-release | [packages/modules/Connectivity](https://android.googlesource.com/platform/packages/modules/Connectivity/+/bd692130a596b4e9bc1ea6778db72c423bb8ab6f/) | BPF 程序、APEX、netd 上下文、Java/native 消费者与测试 |
| android14-release | [system/sepolicy](https://android.googlesource.com/platform/system/sepolicy/+/7595d4f4c36d27150d247701f3f87fb512b68d18/) | loader、bpffs 标签与消费者授权 |
| android14-release | [packages/modules/NetworkStack](https://android.googlesource.com/platform/packages/modules/NetworkStack/+/44e87d4600f9f3f746de6940a13863110a60c452/) | TEST_MAPPING 与单元测试构建定义 |
| android14-release | [kernel/tests](https://android.googlesource.com/kernel/tests/+/b8cfaed612887680e2086b9fc8e6337fc92cf5b5/) | 内核 BPF 行为用例定位，未推定其 VTS 调度目标 |
| android16-release | [system/bpf](https://android.googlesource.com/platform/system/bpf/+/4447acd742bf443f9088c300bd69f96ede8eaeb1/) | Rust/legacy loader 与 libbpf release flag 差异 |
| android16-release | [packages/modules/Connectivity](https://android.googlesource.com/platform/packages/modules/Connectivity/+/627eb3c63e7c7cb3cb9f8ea319e4bb1676079c3a/) | NetBpfLoad、平台 rc/APEX override 与最终就绪信号 |

## 构建、对象协议与 loader

- [Soong bpf.go](https://android.googlesource.com/platform/build/soong/+/9387734632ba3bf381bd57a638ac1216108c59f4/bpf/bpf.go)：实读 Clang `--target=bpf`、BTF 处理、vendor/sub_dir 与 AndroidMk 安装路径。只据此判断该基线，BTF 存在不证明 CO-RE relocation 已支持。
- [Connectivity bpf_progs/Android.bp](https://android.googlesource.com/platform/packages/modules/Connectivity/+/bd692130a596b4e9bc1ea6778db72c423bb8ab6f/bpf_progs/Android.bp) 与 [Tethering APEX Android.bp](https://android.googlesource.com/platform/packages/modules/Connectivity/+/bd692130a596b4e9bc1ea6778db72c423bb8ab6f/Tethering/apex/Android.bp)：实读 `netd.o` 的 `sub_dir`、offload/BTF 变体与 APEX `bpfs` 列表；对象名/目录对旧 netd 的兼容注释是路径协议证据。
- [bpf_map_def.h](https://android.googlesource.com/platform/frameworks/libs/net/+/7c4073f3f973e54ac8354cd949b4d0e0a3e7c37a/common/native/bpf_headers/include/bpf/bpf_map_def.h) 与 [bpf_helpers.h](https://android.googlesource.com/platform/frameworks/libs/net/+/7c4073f3f973e54ac8354cd949b4d0e0a3e7c37a/common/native/bpf_headers/include/bpf/bpf_helpers.h)：实读 map/prog metadata、固定布局、loader/kernel 范围、权限/子目录及 critical/optional 宏；已交付协议不能任意重排。
- 此基线元数据文件实际名为 `bpf_map_def.h`，不是 `BpfDefs.h`；Android16 的另一套兼容宏见下文 `android_bpf_defs.h`。未用猜测的 BpfDefs.h 路径作为已读证据。
- [Android14 BpfLoader.cpp](https://android.googlesource.com/platform/system/bpf/+/a0e21c637428e1e416df106a04bc59a6a7b00faf/bpfloader/BpfLoader.cpp)：实读 `locations`、allowed domain/program type、`loadAllElfObjects`、启动检查与 `bpf.progs_loaded` 发布；版本跳过/optional 使 loaded 不能表示每个对象都有可用程序。
- [Android14 Loader.cpp](https://android.googlesource.com/platform/system/bpf/+/a0e21c637428e1e416df106a04bc59a6a7b00faf/libbpf_android/Loader.cpp)：实读 map 创建/复用、`mapMatchesExpectations`、program load/pin 和 metadata 门控；类型/尺寸/容量/flags 比较不覆盖同尺寸字段语义；复用分支跳过新对象的 chmod/chown。
- [bpfloader.rc](https://android.googlesource.com/platform/system/bpf/+/a0e21c637428e1e416df106a04bc59a6a7b00faf/bpfloader/bpfloader.rc) 与 [构建定义](https://android.googlesource.com/platform/system/bpf/+/a0e21c637428e1e416df106a04bc59a6a7b00faf/bpfloader/Android.bp)：实读 init 事件、root/capabilities/group、memlock、oneshot、APEX 时序与 reboot_on_failure。源码中的刷机/禁重启调试建议没有执行，也没有变成默认 Review 操作。
- [WaitForProgsLoaded.h](https://android.googlesource.com/platform/frameworks/libs/net/+/7c4073f3f973e54ac8354cd949b4d0e0a3e7c37a/common/native/bpf_headers/include/bpf/WaitForProgsLoaded.h)：实读带退避持续等待属性的实现。它等待 loader 信号，不证明后续 attach 或业务初始化成功。

## 访问边界与实际消费者

- [bpfloader.te](https://android.googlesource.com/platform/system/sepolicy/+/7595d4f4c36d27150d247701f3f87fb512b68d18/private/bpfloader.te)、[genfs_contexts](https://android.googlesource.com/platform/system/sepolicy/+/7595d4f4c36d27150d247701f3f87fb512b68d18/private/genfs_contexts)、[netd.te](https://android.googlesource.com/platform/system/sepolicy/+/7595d4f4c36d27150d247701f3f87fb512b68d18/private/netd.te)、[network_stack.te](https://android.googlesource.com/platform/system/sepolicy/+/7595d4f4c36d27150d247701f3f87fb512b68d18/private/network_stack.te)：实读 pin 文件、BPF object class、bpffs 子目录授权与 neverallow；不以 UID=root 或文件路径可读替代实际政策。
- [netd/BpfHandler.cpp](https://android.googlesource.com/platform/packages/modules/Connectivity/+/bd692130a596b4e9bc1ea6778db72c423bb8ab6f/netd/BpfHandler.cpp) 与 [netd/Android.bp](https://android.googlesource.com/platform/packages/modules/Connectivity/+/bd692130a596b4e9bc1ea6778db72c423bb8ab6f/netd/Android.bp)：实读 `init`、`initPrograms`、cgroup attach、map 初始化与 socket tagging 身份/类型/容量限制；该库进入 netd 上下文，不把 APEX 归属当进程身份。
- [BpfMap.h](https://android.googlesource.com/platform/frameworks/libs/net/+/7c4073f3f973e54ac8354cd949b4d0e0a3e7c37a/common/native/bpf_headers/include/bpf/BpfMap.h)：实读 init/RO-RW wrapper 与 key/value 尺寸验证；模板参数不构成字段语义与访问策略的证明。
- [BpfNetMaps.java](https://android.googlesource.com/platform/packages/modules/Connectivity/+/bd692130a596b4e9bc1ea6778db72c423bb8ab6f/service/src/com/android/server/BpfNetMaps.java)：实读 map 路径/结构、初始化默认值、UID 规则与权限移除、`swapActiveStatsMap` 的发布和 RCU 同步；不把用户态锁当作内核写者的互斥。
- [TrafficController.cpp](https://android.googlesource.com/platform/packages/modules/Connectivity/+/bd692130a596b4e9bc1ea6778db72c423bb8ab6f/service/native/TrafficController.cpp) 与 [BpfNetworkStats.cpp](https://android.googlesource.com/platform/packages/modules/Connectivity/+/bd692130a596b4e9bc1ea6778db72c423bb8ab6f/service-t/native/libs/libnetworkstats/BpfNetworkStats.cpp)：实读 socket destroy 清理、native map swap/RCU、inactive map 读取/清空与接口归并。并发及编号复用回归为基于这些协议的审查推导，不声称已有测试覆盖全部情形。
- [netd.c](https://android.googlesource.com/platform/packages/modules/Connectivity/+/bd692130a596b4e9bc1ea6778db72c423bb8ab6f/bpf_progs/netd.c) 与 [netd.h](https://android.googlesource.com/platform/packages/modules/Connectivity/+/bd692130a596b4e9bc1ea6778db72c423bb8ab6f/bpf_progs/netd.h)：实读 map 定义、权限类别、cgroup/xt_bpf 返回语义、配置/UID 策略、流量计数和 GSO 估算；CLAT、方向和 header 单位依实际路径推导。
- [BpfCoordinator.java](https://android.googlesource.com/platform/packages/modules/Connectivity/+/bd692130a596b4e9bc1ea6778db72c423bb8ab6f/Tethering/src/com/android/networkstack/tethering/BpfCoordinator.java)、[BpfUtils.java](https://android.googlesource.com/platform/packages/modules/Connectivity/+/bd692130a596b4e9bc1ea6778db72c423bb8ab6f/Tethering/src/com/android/networkstack/tethering/BpfUtils.java)、[offload.c](https://android.googlesource.com/platform/packages/modules/Connectivity/+/bd692130a596b4e9bc1ea6778db72c423bb8ab6f/bpf_progs/offload.c)：实读 TC attach/detach、upstream/downstream 规则、统计差分/清理、IPv4 分片/options 与低 TTL punt、缺统计/limit 的慢路径；未将这些 TC 契约推广为防火墙允许失败放行。

## Android16 差异核验

- [loader/Android.bp](https://android.googlesource.com/platform/system/bpf/+/4447acd742bf443f9088c300bd69f96ede8eaeb1/loader/Android.bp)、[bpfloader.rs](https://android.googlesource.com/platform/system/bpf/+/4447acd742bf443f9088c300bd69f96ede8eaeb1/loader/bpfloader.rs)、[Loader.cpp](https://android.googlesource.com/platform/system/bpf/+/4447acd742bf443f9088c300bd69f96ede8eaeb1/loader/Loader.cpp)：实读 `RELEASE_BPF_ENABLE_LIBBPF`、特定对象 descriptor/权限、Rust 主入口、legacy 调用和最终 exec。存在 libbpf 路径，不证明任意对象、任意 CO-RE 特性都可用。
- [android_bpf_defs.h](https://android.googlesource.com/platform/system/bpf/+/4447acd742bf443f9088c300bd69f96ede8eaeb1/include/defs/android_bpf_defs.h)：实读 `ENABLE_LIBBPF` 下 `.maps`/section 兼容宏与 legacy include；必须随实际构建开关判断，宏同名不代表旧 metadata 语义全部相同。
- [NetBpfLoad.cpp](https://android.googlesource.com/platform/packages/modules/Connectivity/+/627eb3c63e7c7cb3cb9f8ea319e4bb1676079c3a/bpf/loader/NetBpfLoad.cpp)、[loader Android.bp](https://android.googlesource.com/platform/packages/modules/Connectivity/+/627eb3c63e7c7cb3cb9f8ea319e4bb1676079c3a/bpf/loader/Android.bp)、[netbpfload.rc](https://android.googlesource.com/platform/packages/modules/Connectivity/+/627eb3c63e7c7cb3cb9f8ea319e4bb1676079c3a/bpf/loader/netbpfload.rc)、[netbpfload.35rc](https://android.googlesource.com/platform/packages/modules/Connectivity/+/627eb3c63e7c7cb3cb9f8ea319e4bb1676079c3a/bpf/loader/netbpfload.35rc)：实读网络对象加载、platform loader 转交、`done` 分支置属性、平台占位 service 和 APEX override；不能沿 Android14 的单入口推断新启动链。

## 实际测试定位与覆盖限制

- [Connectivity TEST_MAPPING](https://android.googlesource.com/platform/packages/modules/Connectivity/+/bd692130a596b4e9bc1ea6778db72c423bb8ab6f/TEST_MAPPING)、[tests/unit/Android.bp](https://android.googlesource.com/platform/packages/modules/Connectivity/+/bd692130a596b4e9bc1ea6778db72c423bb8ab6f/tests/unit/Android.bp)、[BpfNetMapsTest.java](https://android.googlesource.com/platform/packages/modules/Connectivity/+/bd692130a596b4e9bc1ea6778db72c423bb8ab6f/tests/unit/java/com/android/server/BpfNetMapsTest.java)：定位 `FrameworksNetTests`，实读 UID 撤权/卸载、接口规则和 A/B 切换/RCU 失败断言；mock 通过不代表真实内核同步通过。
- [netd/Android.bp](https://android.googlesource.com/platform/packages/modules/Connectivity/+/bd692130a596b4e9bc1ea6778db72c423bb8ab6f/netd/Android.bp) 与 [BpfBaseTest.cpp](https://android.googlesource.com/platform/packages/modules/Connectivity/+/bd692130a596b4e9bc1ea6778db72c423bb8ab6f/netd/BpfBaseTest.cpp)：定位 `netd_updatable_unit_test` 的 BpfHandler/BpfBase 源文件，实读基础 cgroup、tagging、关闭 socket 后 tag 清理断言；未宣称完整读取 BpfHandlerTest 正文。
- [Tethering unit Android.bp](https://android.googlesource.com/platform/packages/modules/Connectivity/+/bd692130a596b4e9bc1ea6778db72c423bb8ab6f/Tethering/tests/unit/Android.bp)、[BpfCoordinatorTest.java](https://android.googlesource.com/platform/packages/modules/Connectivity/+/bd692130a596b4e9bc1ea6778db72c423bb8ab6f/Tethering/tests/unit/src/com/android/networkstack/tethering/BpfCoordinatorTest.java)、[integration Android.bp](https://android.googlesource.com/platform/packages/modules/Connectivity/+/bd692130a596b4e9bc1ea6778db72c423bb8ab6f/Tethering/tests/integration/Android.bp)：定位 `TetheringTests`/`TetheringIntegrationTests`；实读缺 map 禁用、clear、attach/detach 和 upstream 更新单元断言，未宣称完整端到端覆盖。
- [CTS net Android.bp](https://android.googlesource.com/platform/packages/modules/Connectivity/+/bd692130a596b4e9bc1ea6778db72c423bb8ab6f/tests/cts/net/Android.bp) 与 [TrafficStatsTest.java](https://android.googlesource.com/platform/packages/modules/Connectivity/+/bd692130a596b4e9bc1ea6778db72c423bb8ab6f/tests/cts/net/src/android/net/cts/TrafficStatsTest.java)：定位 `CtsNetTestCases`，实读接口/total、thread tag 与 localhost 统计断言；不声称它覆盖任意 offload 或 loader 失败。
- [NetworkStack TEST_MAPPING](https://android.googlesource.com/platform/packages/modules/NetworkStack/+/44e87d4600f9f3f746de6940a13863110a60c452/TEST_MAPPING) 与 [unit Android.bp](https://android.googlesource.com/platform/packages/modules/NetworkStack/+/44e87d4600f9f3f746de6940a13863110a60c452/tests/unit/Android.bp)：实读 `NetworkStackTests`/`NetworkStackNextTests` 定义和调度入口；仅供受影响 DHCP/IP provisioning 等边界继续定位，未声称已有 BPF 专项断言。
- [kernel/tests bpf_test.py](https://android.googlesource.com/kernel/tests/+/b8cfaed612887680e2086b9fc8e6337fc92cf5b5/net/test/bpf_test.py)：实读 map、程序、helper 与 cgroup 包/创建 socket 的相关用例段落。具体 VTS module/config suite 未核验，执行时必须从目标版本构建/套件配置定位，不能编造 target。

## 资料读取限制与采用规则

- 高频 helper、Map 冗余、pull/copy 和事件成本的 Review 推导另见 [helper 性能来源](bpf.md#helper-成本与性能审查的补充核验)；Android 对照采用本文件固定 revision 的 `netd.c/offload.c`，保留建项后重查、必要写前处理和 checksum 的反证。

- 一些 Gitiles 网页在浏览工具中不可达；之后对上列固定 revision 的 `?format=TEXT` 成功读取才列为已读。搜索摘要与目录 listing 不作函数行为的已读证据。
- Android14 的 `Connectivity/bpf/...`、旧 `system/netd/server/TrafficController.cpp`、`system/netd/libbpf/...` 等猜测/历史路径未取到正文；实际采用的是 `bpf_progs/`、`service/native/`、`service-t/native/` 与 `netd/`。
- Android16 的旧 `system/bpf/bpfloader/` 路径不可达，已改读该 revision 实存的 `loader/`。字面 `BpfDefs.h` 猜测路径和旧 CTS `NetworkUsageStatsTest.java` 路径未成功读取，不据此描述实现/断言。
- 本地没有目标 AOSP 完整 checkout、产品构建、设备内核、SELinux 合成策略或运行日志；没有运行 CTS/VTS、Atest、真实 attach/load、刷机、重启或策略修改。
- 同尺寸布局错配、UID/netId/ifindex 复用与同 boot 更新规则是基于对象/状态协议的审查方法；是否可达须由被审项目的 key、服务入口、生命周期和受支持升级合同证明。
- GKI、内核版本字符串和安全补丁日期不作为 helper/map/attach 能力或厂商修复的充分证明；以目标 config/源码补丁、真实 loader 与获准运行证据复核。
- 未覆盖的新 release、不同 loader、厂商扩展与热更新机制按其真实契约重查；不能因本文件固定分支可读，就声称目标产品已经验证。
