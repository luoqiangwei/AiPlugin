# 产品组成、SBOM 与应用更新所有权

核实日期：2026-10-28。本页使用官方 Setup 的 SBOM、app ownership、reference boards、custom devices 及公开构建工具解释交付输入。
源码组合、产品/board/ABI、模块选入和运行产物验证见 [setup-product-integration.md](setup-product-integration.md)；构建/签名/OTA 另见现有专题。
这里的“供应链”落实到构建图、元数据、文件身份和安装状态，不能从文档存在推导已经完成产品审计。

## SBOM 属于某次具体产品构建

官方 SBOM 使用 SPDX 2.3，Android CI 可为具体 build 提供预生成工件；自定义产品则使用同一 target 的 `m sbom` 生成相应输出。
CI 中某个绿色构建的清单不能代表加入 OEM blob、额外 APK、firmware 或替换工具链后的产品。
官方要求平台新增内容（包括 binary、build/release toolchain）在产品组成中被表示；只扫描 external 目录不能满足这个范围。[官方生成入口][sbom]

| 对象 | 需要关联的身份 | 不足以替代的证据 |
|---|---|---|
| 源码组合 | manifest/revision、本地改动、上游版本 | 只记录 `repo init` 分支名 |
| 模块/构建依赖 | 变体、源/prebuilt、静态/动态依赖、生成输入 | 源目录里有一个 LICENSE |
| 安装文件 | 产品输出、分区、文件内容/校验、所属模块 | 单模块编译通过 |
| 外部供应工件 | 实际版本、supplier、来源、对应 metadata/SBOM | 文件名含“latest” |
| 运行设备 | Build ID、活动 slot/APEX/APK 与实际装载文件 | 只确认工作区 HEAD 已更新 |

这是证据关系，不要求任何特定团队审批流程。关键不变式是清单和被解释的二进制来自同一构建输入/输出，不能混用旧 out 目录与新源码的元数据。

## 官方生成器显示的溯源机制

公开 `build/tools/sbom/gen_sbom.py` 从 compliance metadata 数据库取得安装文件与模块关系，读取邻近 METADATA，区分 source、prebuilt 与 upstream。
生成器表示文件校验及 GENERATED_FROM/VARIANT_OF/STATIC_LINK 等关系，并追踪传递静态依赖；静态库即使不单独装到设备，仍可成为已交付二进制的组成。
其报告还区分缺文件元数据、缺 METADATA、字段不完整与静态依赖找不到模块。[官方生成器][generator]

由此推导，清单“能输出 JSON”不是完整性证明：应对照实际 installed files、遗漏报告及非标准复制/生成路径。
版本/来源字段来自元数据，不会自动证明供应商二进制与上游版本完全相同；本地修补 fork 应保留实际交付身份与 upstream 关系。
SBOM 表达组成，也不等于可重复构建证明、签名验证或漏洞状态的实时结论；这些结论需要各自输入和证据。

诊断缺项时，先区分模块是否被选入/安装、构建 metadata 是否生成、METADATA 是否正确定位、prebuilt 类型是否被识别，以及静态依赖是否可回溯。
不要为了让报告“没有缺项”把未知版本随便填成上游最新版，也不能把产生数据的目录中所有文件都宣称交付。
上述源码取自公开 main，函数和 schema 会变化；应在目标分支定位对应实现，不能把这里的路径承诺为所有 Android 版本固定接口。

## Update owner 与 installer of record 是不同状态

installer of record 表示最近负责安装的 installer；Android 14 起初始 installer 可请求成为 update owner。
其它 installer 更新有 owner 的包时，需要处理用户确认，持有 INSTALL_PACKAGES 也不能自动跳过 `STATUS_PENDING_USER_ACTION`。
owner 不替代 APK 签名、版本或其它安装资格；它决定更新控制与用户交互，不能让错误签名的 APK 合法覆盖应用。[更新所有权][ownership]

预装应用通常没有自然的 installer owner，可通过 sysconfig 的 `update-ownership` 将包映射到指定 installer。
包名、owner installer 与实际安装状态要一致；预装在 system 分区不自动把 OEM 商店设成 update owner。
确认请求、用户批准、安装 session commit 与包真正生效分别有状态，installer 应等待最终结果，不应先把 UI 标成更新成功。

legacy update ownership denylist 的语义容易反读：列入的包不能被任何 installer 取得 update ownership，安装本身仍可成功。
installer 更新时可改变 denylist，并清除新列入包的既有 owner；之后这些包的更新不再因 owner 冲突要求同一确认流程。
它不是“只允许原商店更新”的黑名单，也不是禁止列入包安装/升级的政策。
排查商店更新被挂起，应同时记录包当前 owner、installer of record、请求 installer、session status 与 pending intent，而不是只检查 INSTALL_PACKAGES。[所有权与 denylist][ownership]

## 参考板不能替代产品支持声明

官方 reference board 页面列 DragonBoard 845c/RB3、RB5、Khadas VIM3 等开发入口，同时明确这些板不由 AOSP 统一支持和测试。
BSP 来自板厂；某板能启动 AOSP-based image，不代表任意 release、内核、GPU、摄像头、key hardware 或认证都受支持。
Pixel/Nexus 的相应设备专用 binary 也需匹配具体 build/device，不能因为 AOSP 开源就省略这些输入。[参考板][boards]

判断参考板是否适合一项验证，应落到证据范围：Framework/ABI 机制可用相应软件环境；射频、功耗、sensor 时序、安全硬件必须有匹配实现。
“头文件有 HAL”“样例 service 起了”“参考板有某接口”与“目标产品硬件路径工作”是不同事实。
产品校验要连接最终继承配置、模块/分区/ABI、VINTF、权限与实际运行版本，不能从参考板型号推断完整能力集合。

## Flash 工件与锁定状态也是产品输入

`fastboot-info.txt` 是目标输出中的刷写任务工件，可描述 partition flash、super 更新与条件擦除；多 target 对应多个工件。
最近的 ANDROID_PRODUCT_OUT 不保证就是计划交付的 target，审查时应绑定明确输出与镜像文件。
修改脚本动作并不会自动验证镜像兼容、AVB 或 slot 正确；本页不要求执行刷写/擦除来理解机制。[自定义设备][custom]

getFlashLockState/PersistentDataBlockManager 表达 bootloader lock state，LOCKED、UNLOCKED 与旧升级设备的 UNKNOWN 有不同条件。
读取值还应能关联真实 bootloader 信号；Android UI 不显示解锁选项不能证明 bootloader 处于锁定信任状态。
锁状态测试与 secure boot/用户数据变化需分开，不能把“能刷机”视为正常发布用户态的能力。[锁状态][custom]

## Setup 主要分支归属与边界

| 官方 Setup 分支 | 承接知识 | 未在本页逐项展开 |
|---|---|---|
| Start/requirements/older versions | `setup-product-integration.md` | 每个历史主机工具/发行版组合 |
| Download/Repo/source workflow | `setup-product-integration.md` | 每个 Repo 子命令和同步后端实现 |
| Build/products/multilib/reference | `setup-product-integration.md`、`build-release.md` | 每个 Android.bp 属性、全部内核构建分支 |
| Create/SBOM/app ownership/reference boards/custom device | 本页 | METADATA proto 全 schema、每家 BSP 与全部安装 API |
| Test/run/AVD | `testing-diagnostics.md`、`devices-virtualization.md` | 真实设备完整 bring-up/刷写规程 |
| Contribute/release lifecycle/build numbers | `reference-and-evolution.md`、`setup-product-integration.md` | 每个 release/tag 差异与项目贡献例外 |

主要失效判断是：缺 source revision、错误 product/variant、prebuilt/静态依赖漏记、清单与镜像不一致、owner 冲突或运行设备未更新。
这些问题的证据层不同，不能用一次“完整构建成功”或“APK 版本号上升”合并证明。

## 官方依据

[sbom]: https://source.android.com/docs/setup/create/create-sbom
[generator]: https://android.googlesource.com/platform/build/+/refs/heads/main/tools/sbom/gen_sbom.py
[ownership]: https://source.android.com/docs/setup/create/app-ownership
[boards]: https://source.android.com/docs/setup/create/devices
[custom]: https://source.android.com/docs/setup/create/custom-devices
