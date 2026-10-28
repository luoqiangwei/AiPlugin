# Android 与 AOSP 日志规则溯源

复核日期：2026-10-27 至 2026-10-28。以下官方正文与源码已实际读取；运行文件是原创审查归纳，示例用于推演，不是生产补丁。平台机制基线固定到 `refs/heads/android16-release`，仍须按目标 manifest revision、厂商改动及构建配置复核；分支名不表示已验证用户产品。

## 公开 Log API 与发布可见性

- [Log API](https://developer.android.com/reference/android/util/Log)：实读类说明、Throwable 重载、`isLoggable`、`getStackTraceString`、`wtf`；页面更新时间为 2026-08-03 UTC。
- 用途：确认 tag 与级别入口、调用前字符串构造开销、运行时可记录性以及 `UnknownHostException` cause 链可能抑制堆栈；旧 API 的 tag 长度限制只在实际支持时展开。
- [Logcat command-line tool](https://developer.android.com/tools/logcat)：实读日志系统概览、编译过滤、属性过滤、进程过滤及显示过滤；官方滚动文档，访问于本次复核日。
- 用途：区分“调用存在”“发送给 logd”“buffer 留存”“读取者能看到”。`main/system/crash` 是不同 buffer；属性、采集身份和显示筛选要分别取证。
- [Configure build variants](https://developer.android.com/build/build-variants)：实读 build type、flavor、variant 和模块级配置部分；官方滚动文档。
- 用途：App 的构建配置与设备构建是不同维度；具体 `BuildConfig.DEBUG` 以当前工程生成源、导入模块和实际产物为证，不从命名猜测。

## AOSP 日志说明

- [Understand logging](https://source.android.com/docs/core/tests/debug/understanding-logging)：实读级别指导、App logging、system logging、native logging、security and privacy；页面更新时间为 2026-10-09 UTC。
- 用途：确认 `isLoggable`、tag 属性、静态 DEBUG 与 R8 的不同作用，平台 `Slog`、EventLog、native wrapper 的用途及数据最小化原则。
- 解释边界：表中的级别保留指导不是每个产物的输出保证；具体 release 可见性用构建规则、代码条件、liblog 配置和采集结果确认。没有照抄网页 R8 示例作为通用配置。

## Java 平台源码

以下文件均从 `platform/frameworks/base` 的 `refs/heads/android16-release` 官方 Gitiles `?format=TEXT` 接口下载、解码后阅读。浏览工具对部分 HTML 页面访问失败，没有据失败页面声明已读；下列 blob 是对所读内容按 Git blob 算法计算的标识。

- [Log.java](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/android16-release/core/java/android/util/Log.java?format=TEXT)
  - blob：`f8737a55a5b09329a125b7f3bdf7cffec8d27068`。
  - 实读：级别常量、main buffer 重载、`isLoggable`、`wtf/wtfQuiet`、`sWtfHandler`、堆栈与 `printlns`。
  - 关键差异：公开 API 文案称 ASSERT；此实现实际以 ERROR 调用 `printlns`，再交给 terrible-failure handler。不能由文案推断总是 abort，也不能把 ERROR 输出当作普通错误路径。
- [Slog.java](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/android16-release/core/java/android/util/Slog.java?format=TEXT)
  - blob：`b2017a5fa868ac3e27947cc348a6de09f453ea97`。
  - 实读：隐藏/模块 API 声明、system buffer 重载、Throwable 字符串构造、`wtf/wtfStack/wtfQuiet`。
  - 用途：区分系统组件日志与普通 App API，确认 system 标志及相应 wtf 契约；不把 Log/Slog 的堆栈处理与终止语义一概视为相同。
- [RuntimeInit.java](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/android16-release/core/java/com/android/internal/os/RuntimeInit.java?format=TEXT)
  - blob：`f6de3459a1f585b2618f26933ff06ed3b964913c`。
  - 实读：`wtf`、早期启动 fallback、`ApplicationWtfHandler` 返回契约及 exit 分支。
  - 用途：该路径调用 ActivityManager 或启动期处理器，依据返回值决定 kill/exit；本次未据此展开全部 AMS/厂商报告策略，涉及报告或进程处置的 finding 必须继续追目标实现。
- [Build.java](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/android16-release/core/java/android/os/Build.java?format=TEXT)
  - blob：`0ceafa01017efa37ed569be22682eeb3fd48b4f4`。
  - 实读：`IS_DEBUGGABLE/isDebuggable` 与 user/userdebug/eng 字段。
  - 用途：`IS_DEBUGGABLE` 来自 `ro.debuggable`，字段为隐藏平台 API；不等于 App variant、APK `debuggable` 或普通 SDK App 可用能力。

## Native 宏与断言入口

以下文件均实读 `platform/system/logging` 的 `refs/heads/android16-release`。本次分支根页面 commit 为 `d78b713380007d3c0dde14712cbcbec27f491ad9`；分支仍可移动，Review 要回到目标 revision。

- [log_main.h](https://android.googlesource.com/platform/system/logging/+/refs/heads/android16-release/liblog/include/log/log_main.h?format=TEXT)
  - blob：`0cb7dd78e8864ba0096c6a2be6ff0945e25a4ce7`。
  - 实读：`LOG_NDEBUG/NDEBUG`、`ALOGV/ALOGD`、条件宏、`IF_ALOG`、`android_testLog`、`LOG_ALWAYS_FATAL[_IF]`、`LOG_FATAL[_IF]`、`ALOG_ASSERT`。
  - 用途：区分编译移除、运行时 guard、调用参数先求值与始终保留的断言；此头文件未定义 `ALOG_FATAL`，同名项目封装必须展开，不能赋予统一行为。
- [android/log.h](https://android.googlesource.com/platform/system/logging/+/refs/heads/android16-release/liblog/include/android/log.h?format=TEXT)
  - blob：`b33f6095b69c29a5d15029c056d11b886f070bc6`。
  - 实读：日志预算/循环 buffer、priority、`__android_log_print/write/assert`、buffer、可记录性、最低级别与 aborter API。
  - 用途：确认优先级和断言调用是不同机制，默认 aborter 会 abort，自定义 aborter 另查；native 的实际编译参数和封装可改变运行行为。
- [NDK Logging](https://developer.android.com/ndk/reference/group/logging)：实读 priority、`__android_log_assert`、`__android_log_is_loggable`、最低级别及 aborter 契约，用于交叉核对公开 native API；不将所有新 API 套给旧目标。

## 数据最小化与替代证据

- [Log Info Disclosure](https://developer.android.com/privacy-and-security/risks/log-info-disclosure)：实读 overview、production 裁剪与脱敏章节；页面更新时间为 2024-09-24 UTC。
  - 用途：异常消息、外部组件和对象输出同样可能携带秘密；发布日志按允许字段检查，R8 只负责选定裁剪，不能证明保留内容安全。未复制网页中的示意配置和代码。
- [EventLog API](https://developer.android.com/reference/android/util/EventLog)：实读类说明和写入重载；页面更新时间为 2026-08-03 UTC。
  - 用途：这是面向系统集成的整数 tag/schema 诊断事件；存在 EventLog 类不证明某故障已有记录。
- [Statsd](https://source.android.com/docs/core/ota/modular-system/statsd)：实读服务职责、模块边界与 API 依赖；页面更新时间为 2026-10-09 UTC。
  - 用途：指标收集与文本诊断分别核对；是否有相关 atom、写入路径、配置和可取回数据，须在目标代码与部署中确认。
- [Perfetto Android Log](https://perfetto.dev/docs/data-sources/android-log)：实读数据源能力、buffer/tag/priority 过滤和 TraceConfig；官方滚动文档。
  - 用途：日志可与 trace 时间对齐，但该页面明确 `android.log` 数据源仅支持 userdebug；不能把一般 Perfetto 可用性推成 user 构建必然采到 logcat。

“关键路径必须有证据”、责任层去重、限速/有界聚合及状态迁移例子是基于这些机制的审查推导；不将日志数量、个人 tag 偏好或某种后端名称直接当成缺陷。ANR/Watchdog 的期限与等待链仍由各自专题维护。
