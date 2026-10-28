# Android 应用

本文件处理 Android 应用的组件、平台能力、界面生命周期和发布约束。Java、Kotlin 或 JNI 内的语言语义另读相应语言资料；只有实际修改系统服务才补 AOSP，涉及网页内容才读 Web 相关部分。Jetpack/Compose 条目仅用于实际采用这些组件的代码。

## 先固定实际运行条件

读取 `minSdk/targetSdk`、设备 API、AGP/Kotlin/AndroidX、build variant、**合并后的 Manifest** 与实际依赖树。导出行为、PendingIntent 标志、后台限制、网络策略和裁剪结果以这些条件为准。源码中声明安全不代表发布 APK 仍相同。

为改动入口记录：`谁能调用 → 哪些字段可控 → 本 App 使用什么权限/资源 → 谁收到结果`。普通 App 与 `adb shell` 的身份能力不同；跨 App 安全测试使用不同 UID 的测试 App。

启动、输入、组件回调或其依赖变化时，按 [场景索引](../index.json) 的 `android-app.checks` 读取 ANR 专题；共享状态、Handler/Binder/线程池交接和回调注销读取并发专题。把阻塞操作放入工作线程不代表等待方安全，也不能只用平均耗时排除超时风险。

日志变更及新增失败、初始化、降级或恢复路径，同时检查通用日志规则与 Android 日志专题；尤其确认必要证据在 release 构建仍可用，高频回调不会因拼接、打印堆栈或锁内输出拖慢关键线程。

## 组件调用与 URI 能力转交

**触发**：导出组件、deeplink、嵌套 Intent、转发/回传 Intent 或 URI 授权变化。不能只检查 extras 的业务字段。

1. 从合并 Manifest 和动态注册点确认入口可达性与生效权限。`exported=true` 本身不是漏洞；导出的登录、分享入口可以是需求。
2. 给 `component/package/action/data/ClipData/categories/extras/flags` 标记所有者，沿 `startActivity*`、`setResult`、`grantUriPermission` 和 PendingIntent 查到接收方。
3. 区分数据与能力：URI 与 grant flags 可能授予访问；显式 component 可能代理调用内部组件。只验证业务 extra、清一个 flag 或设置 package，不能证明其他能力已移除。
4. 对 URI 查 Provider 的 `exported/grantUriPermissions`、path/read/write permissions 和 `query/openFile/update` 实现；`exported=false` 不排除经 URI grant 访问。
5. “外部可控能力字段 → 本 App 有权授予/执行 → 未授权接收者获益”链路成立才确认缺陷；Provider 数据未知时不扩大为全部数据泄漏。

```kotlin
// 风险：仍携带调用方的 URI、ClipData 和授权标志。
val reply = intent
reply.putExtra("selectedAccount", selectedId)
setResult(RESULT_OK, reply)

// 返回协议只有一个业务字段，构造最小输出。
val reply = Intent().putExtra("selectedAccount", selectedId)
setResult(RESULT_OK, reply)
```

转发到其他组件时同样构造允许目标和字段；确需转发 URI 时验证对象、调用方、权限与有效期，明确能否继续转授。Provider 不需外部授权时关闭授予能力；确有分享需求时不能以一律禁用功能代替修复。

**修复后不变式**：输入方只能影响协议允许的业务数据，不能借本 App 增加组件、文件或 URI 权限；合法分享的对象范围与存活期符合协议。

**区分性验证**：不同 UID 的 App 分别输入 `data`、`ClipData`、读/写及组合 grant flags、嵌套 Intent，断言结果返回前后内部 URI 均不可读写。合法分享应能访问指定对象、不能访问相邻对象、撤销后失败。只断言 extra 正确会漏掉能力泄漏。

### PendingIntent 的修改与重放

先判断接收者是否必须修改 Intent；无需时使用 immutable，需要 mutable 时固定目标并限定可填写字段。检查 token identity、requestCode 与更新/取消策略，证明不同账户/订单不会复用同一能力。immutable 不等于一次性，one-shot 不等于正确授权。用接收方 `fillIn`、跨业务 token 复用、重复发送、撤销后发送验证；平台强制标志依实际 target/API 判断。

## WebView 内容来源与原生桥

**触发**：网页调用原生桥，或导航、富文本、message channel、SSL 回调变化。

1. 从 `loadUrl/loadData*` 追踪来源，继续查重定向、后续导航、iframe、远程脚本和可注入内容。初始 URL 受控不代表所有脚本受控。
2. 解析 URL 后比较允许的 scheme、完整 host 和 port；不用 `contains("trusted.example")`、字符串前缀或不带域边界的后缀代替来源验证。
3. `addJavascriptInterface` 对象可被 frame 访问；顶层来源不能证明调用 frame 来源。JS 入参自报的 `origin/userId/token` 不是可信身份。
4. 列出桥的每项能力：凭据、文件、支付、启动组件、发请求。逐项检查参数与对象授权；无敏感能力的展示桥不能直接报高危。
5. 采用项目支持的来源受限消息机制时，检查原生收到的真实 source origin、frame 语义与允许列表；不能验证消息内自报来源后就放行。

```text
风险：可信顶层页面 + 不可信 iframe + 向所有 frame 暴露 readPrivateFile(path)
      → 顶层 URL 校验无法阻止子 frame 越权。
修复：只在内容和子 frame 均受控的隔离 WebView 暴露最小能力；
      无法保证时移除桥，或用受支持的来源约束通道验证真实发送方；
      原生端仍只允许当前主体获准的对象。
```

**反证**：仅启用 JavaScript、仅存在 bridge、仅允许外链不构成完整漏洞；须证明不可信脚本与敏感桥处在同一可调用边界。忽略证书错误、放开文件访问另按实际路径判断，HTTPS 字样不替代校验。

**修复后不变式**：不可信页面、子 frame、伪造消息不能调用敏感原生操作；合法来源也不能访问任意对象。

**区分性验证**：正常页面、恶意子 frame、相近域名、跨域重定向、消息伪造 origin、证书错误分别测试；断言敏感操作被拒且正常功能保留。只验证页面能打开不覆盖来源边界。

## 界面生命周期与结果归属

**触发**：新增 coroutine/Flow/Compose effect、页面回调、账户/查询切换或后台恢复。

1. 标出任务应有生命周期：Fragment 的 View、ViewModel、会话或跨页面业务。长于页面的任务可以合法，但不能持有失效 View 或把结果提交到错误会话。
2. 检查 scope、收集起止、effect keys 和注销路径。Fragment 实例尚存不代表 View 尚存；composition 存在也不一定等于页面可见。
3. 检查 `catch(Exception)`、`runCatching`、`finally` 是否吞掉取消后继续写状态。可恢复业务错误与取消分别处理。
4. 写出 `A开始 → B开始 → B完成 → A完成`；证明取消旧请求、版本比较或状态机能阻止旧结果覆盖新状态。客户端取消不保证远端副作用被撤销。

```kotlin
// 风险：没有 View 生命周期边界，旋转/离开后可能访问销毁后的 View。
GlobalScope.launch(Dispatchers.Main) { binding.title.text = repository.loadTitle() }

// View 存在且可见时收集；业务加载由合适的状态所有者管理。
viewLifecycleOwner.lifecycleScope.launch {
    viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
        viewModel.state.collect { state -> render(state) }
    }
}

// 恢复业务错误时保留取消传播。
try { repository.refresh() }
catch (cancelled: CancellationException) { throw cancelled }
catch (error: IOException) { showRecoverableError(error) }
```

`render`、加载器、错误处理仍须满足线程契约；换 scope 不会自动把阻塞 IO 移出主线程。必须完成的写操作明确持久化、重试与幂等责任，不用 GlobalScope 规避取消。

**修复后不变式**：已销毁 UI 不再被访问、不重复订阅；当前界面只接收当前用户/请求的结果；取消不转换成普通成功/错误状态。

**区分性验证**：旋转、快速进出、后台前台、切账户、每个等待点取消，以及强制 A 晚于 B 完成。断言调用次数、最终账户/内容与注销。跨进程状态另测杀进程重建；ViewModel 不保证跨进程保存。

## 其余检查按条件展开

| 审查主题 | 必须得出的结论 | 处理、验证与误报排除 |
|---|---|---|
| ContentProvider 与 URI 访问 | URI 映射的对象、文件根和 SQL 条件受约束 | 参数化查询；路径覆盖编码、相邻目录和链接/竞态，不能只比较字符串前缀。验证跨 UID、越界路径、selection 注入与授权撤销；内部 Provider 仍校验参数。 |
| 敏感数据与密钥 | 敏感数据经日志、SDK、备份、缓存、存储和登出流程可被谁获得 | 最小保留、脱敏、必要的认证加密和密钥管理；验证 release 日志、恢复、切账户、密钥失效。Keystore 不可导出不表示受侵进程不能调用密钥；不把所有未加密数据一概报漏洞。 |
| 网络信任与发布配置 | release 实际网络栈执行证书、主机名与明文策略 | 删除 trust-all/忽略证书错误，调试 CA 限调试配置；测试错误主机名、不可信 CA、明文和重定向。按域批准的非敏感明文不自动等于高危。 |
| 主线程与资源开销 | 阻塞、泄漏或额外成本影响真实设备场景 | 查主线程 IO/同步 Binder、注册注销、唤醒锁和昂贵重组；同设备/构建比较 trace、启动、滚动和内存。一次 debug 慢或存在 recomposition 不能证明发布回退。 |
| 发布产物与依赖 | release 产物的入口、反射/JNI、资源和 SDK 行为正确 | 查 merged Manifest、variant 依赖、裁剪规则；相关 release smoke 验证权限与数据流。宽泛 keep rule 不是默认修复；依赖命中须核对实际交付和补丁。 |

## 交付 Review 时

发现写清普通外部主体能控制什么、调用链如何扩大能力、预期与实际差异及区分性用例。报告设备/API/variant 和未执行限制；lint、单测、instrumentation、release smoke 与性能测量分别说明。缺少 Provider/设备证据时不虚构数据泄漏范围或声称已利用成功。

来源、版本事实与原始漏洞记录仅在需要复核时读取：[规则溯源](../sources/android-app.md)。
