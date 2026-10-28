# aosp 规则来源与案例记录

本文件仅用于规则溯源与版本复核，不是执行 Review 的前置阅读；可执行规则已写入专项资料。

## 来源字典

下列资料均于 **2026-10-27** 实际读取核验。当前在线文档与老分支可能不同；规则、API 与测试名称须以目标 release 和仓库为准。

| 来源 ID | 标题与链接 | 用途 |
|---|---|---|
| AOSP-01 | [Android security best practices](https://source.android.com/docs/security/best-practices) | 平台/OEM 安全基线与 CDD/CTS 入口 |
| AOSP-02 | [Android Binder API reference](https://developer.android.com/reference/android/os/Binder) | caller identity、线程局部 clear/restore、WorkSource API 语义 |
| AOSP-03 | [WorkSource fix 266b3bdd](https://android.googlesource.com/platform/frameworks/base/+/266b3bddcf14d448c0972db64b42950f76c759e3) | 真实序列化根因、补丁与回归测试 |
| AOSP-04 | [Binder — Handle threads](https://source.android.com/docs/core/architecture/ipc/binder-threading) | 同步/oneway、重入、死锁与线程池 |
| AOSP-05 | [Customize SELinux](https://source.android.com/docs/security/features/selinux/customize) | 最小策略、neverallow、分区策略边界 |
| AOSP-06 | [Stable AIDL](https://source.android.com/docs/core/architecture/aidl/stable-aidl) | 结构化接口、版本跟踪与兼容机制 |
| AOSP-07 | [AIDL API guidelines](https://source.android.com/docs/core/architecture/aidl/stable-aidl-apis) | 冻结快照、接口演进、依赖版本和错误处理 |
| AOSP-08 | [AIDL for HALs](https://source.android.com/docs/core/architecture/aidl/aidl-hals) | system/vendor 稳定边界、backend、VINTF 与 VTS |
| AOSP-09 | [Compatibility Test Suite overview](https://source.android.com/docs/compatibility/cts) | 行为兼容验证和对应 CDD 入口 |
| AOSP-10 | [Fuzz with libFuzzer](https://source.android.com/docs/security/test/libfuzzer) | AOSP fuzz 与 sanitizer 验证选择；不直接执行页面中的历史刷机示例 |
| AOSP-11 | [Android Security Bulletin — March 2023](https://source.android.com/docs/security/bulletin/2023-03-01) | CVE-2023-20963 的官方类型、严重度、版本和补丁链接 |
| AOSP-12 | [AOSP Java code style for contributors](https://source.android.com/docs/setup/contribute/code-style?hl=en) | 平台 Java 贡献规范及与 App 风格的适用区别 |
| AOSP-13 | [Run tests (Atest)](https://source.android.com/docs/core/tests/development/atest) | 目标化测试运行、环境要求和 TEST_MAPPING 入口 |
| AOSP-14 | [Privileged permission allowlist](https://source.android.com/docs/core/permissions/perms-allowlist) | 特权权限的分区约束与 allow/deny 配置 |
| AOSP-15 | [AppOpsManager API reference](https://developer.android.com/reference/android/app/AppOpsManager) | 包名/UID 绑定校验与 AppOps API 条件 |

## 原始历史案例记录

**CVE-2023-20963：WorkSource parcel/unparcel 不对称。** 2023 年 3 月 Android 公告将其列为 Framework 高危本地提权，列出的更新 AOSP 版本为 11、12、12L、13，并链接修复 `266b3bddcf14d448c0972db64b42950f76c759e3`。[AOSP-11] 补丁说明：非 null 但为空的 WorkChain list 会被写入 Parcel，读取侧仅在 size 为正时读该 list，留下未消费的数据并影响后续字段；修复统一读写逻辑，提交注明 `atest android.security.cts.WorkSourceTest#testWorkChainParceling`。[AOSP-03]

审查迁移：检查 null、空集合、非空集合的所有编码分支；round-trip 后校验邻接字段和 data position，避免只测典型非空值。回移时核对目标分支的字段布局、关联修复和已有测试，不能仅凭提交 SHA 或系统显示的日期判断安全性。公告中的受影响版本不是对任意厂商分支的完整判定，也不证明当前被审项目存在该漏洞；攻击链细节不能从补丁的序列化错误任意外推。
