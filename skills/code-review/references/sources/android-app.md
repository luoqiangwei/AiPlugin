# android-app 规则来源与案例记录

本文件仅用于规则溯源与版本复核，不是执行 Review 的前置阅读；可执行规则已写入专项资料。

## 来源字典

下列资料均于 **2026-10-27** 实际读取核验；官方指南随版本变化，执行 Review 时重新确认涉及的 API/targetSdk 条件。本表是本模块的证据索引，不声称覆盖所有 Android 安全规范。

| 来源 ID | 标题与链接 | 用途 |
|---|---|---|
| ANDROID-01 | [Android Developers — Security checklist](https://developer.android.com/privacy-and-security/security-tips) | 存储、IPC、权限、网络与应用安全基线 |
| ANDROID-02 | [Recommendations for Android architecture](https://developer.android.com/topic/architecture/recommendations) | 状态/数据职责及建议的适用边界 |
| ANDROID-03 | [android:exported](https://developer.android.com/privacy-and-security/risks/android-exported) | 组件导出和历史默认值差异 |
| ANDROID-04 | [Intent redirection](https://developer.android.com/privacy-and-security/risks/intent-redirection) | 嵌套 Intent、目的地及 URI grant 检查 |
| ANDROID-05 | [Pending intents](https://developer.android.com/privacy-and-security/risks/pending-intent) | 可变 token、目标与重放风险 |
| ANDROID-06 | [Behavior changes: Apps targeting Android 12](https://developer.android.com/about/versions/12/behavior-changes-12#pending-intent-mutability) | target/API 条件下的 mutability 要求 |
| ANDROID-07 | [WebView — Native bridges](https://developer.android.com/privacy-and-security/risks/insecure-webview-native-bridges) | iframe、原生桥和消息来源边界 |
| ANDROID-08 | [Android Keystore system](https://developer.android.com/privacy-and-security/keystore) | 密钥限制、不可导出性和硬件条件 |
| ANDROID-09 | [Network security configuration](https://developer.android.com/privacy-and-security/security-config) | 调试 CA、明文例外和信任锚 |
| ANDROID-10 | [Use Kotlin coroutines with lifecycle-aware components](https://developer.android.com/topic/libraries/architecture/coroutines) | scope、Compose effect 与生命周期收集 |
| ANDROID-11 | [Best practices for coroutines in Android](https://developer.android.com/kotlin/coroutines/coroutines-best-practices) | 主线程安全、取消、可测试调度器 |
| ANDROID-12 | [Android vitals](https://developer.android.com/google/play/vitals) | 崩溃、ANR、内存、功耗观测维度 |
| ANDROID-13 | [Write a Macrobenchmark](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview) | 启动与 UI 操作性能验证 |
| ANDROID-14 | [Improve your code with lint checks](https://developer.android.com/studio/write/lint) | Android lint 能力与局限 |
| ANDROID-15 | [Nextcloud News — GHSA-2q9v-q3cc-h9f3 / CVE-2021-41256](https://github.com/nextcloud/news-android/security/advisories/GHSA-2q9v-q3cc-h9f3) | 维护者发布的影响条件与修复版本 |
| ANDROID-16 | [Nextcloud News fix 05449cb](https://github.com/nextcloud/news-android/commit/05449cb666059af7de2302df9d5c02997a23df85) | Intent 回传修复的具体代码证据 |
| ANDROID-17 | [OWASP MASVS](https://mas.owasp.org/MASVS/) | 移动端安全控制分类；需要安全专项覆盖时按相关控制读取 MASTG，不能以清单全部勾选声称认证 |

## 原始历史案例记录

**CVE-2021-41256：Nextcloud News for Android 的 Intent URI permissions manipulation。** 维护者公告记录受影响版本 `<0.9.9.63`，当同设备恶意 App 传入 Intent 并被原样回传时，可能获得原本未导出的 ContentProvider 的读写权限；公告中的修复版本为 `0.9.9.63`。修复提交 `05449cb666059af7de2302df9d5c02997a23df85` 将返回 Intent 改为新建并仅填入必要字段。[ANDROID-15][ANDROID-16]

审查迁移：从外部 Intent 追到 `setResult` 和 URI grant，不把 `exported=false` 当完整安全证明；回归使用不同 UID 测试 App 携带 data、ClipData 与 grant flags，请求结果后确认私有 Provider 仍不可读写，正常业务返回值不变。这里的回归设计是依据公告与补丁提炼的建议。历史 CVE 只说明失误模式；判断当前项目受影响还须核对具体版本、补丁和可达路径。
