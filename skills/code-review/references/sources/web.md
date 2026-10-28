# Web 来源与提炼映射

本文件只用于出处核验与知识库维护；日常 Review 直接执行专项资料，不要求打开外链。资料核验日期：2026-10-27。

## 来源 → 审查能力

| 运行规则 | 原始依据 | 已提炼的决策能力 |
|---|---|---|
| 对象与租户授权、缓存隔离 | WEB-01/02/03/08 | 对象与租户授权不能被缓存命中绕过；用两主体和权限变化检验隔离，而非只看路由登录检查 |
| 输出上下文与脚本注入 | WEB-04 | 按最终解析上下文选择防护；区分纯文本、安全转义、富文本净化及 URL 能力 |
| 服务端请求目的地 | WEB-06 | 跟踪校验结果到实际连接；检查 DNS、跳转、代理和重试，避免校验/使用不一致 |
| 并发副作用与幂等 | WEB-01/03 与跨领域原子性推导 | 从业务不变式、交错和故障点推导幂等状态机；区分本地提交与外部副作用 |
| 内部标志信任模型 | WEB-11 | 从具体中间件绕过提炼“外部输入不能冒充内部能力”，不依赖攻击头黑名单 |
| 其他规则 | WEB-01/02/05/07/09/10 | 凭证与跨站前提、资源预算、可观察性能和可操作的无障碍验证 |

规则是多来源结合代码机制的原创审查归纳，不冒充标准逐条翻译，也不将历史公告版本作为当前安全升级目标。

## 历史案例证据

CVE-2025-29927

**官方事实（WEB-11）**：Next.js 中间件内的授权可能被绕过。公告列出的受影响分支包括 `>=11.1.4,<12.3.5`、`>=13.0.0,<13.5.9`、`>=14.0.0,<14.2.25`、`>=15.0.0,<15.2.3`；Vercel 托管部署在该公告中注明有自动保护。公告给出的临时措施是阻止含 `x-middleware-subrequest` 的外部请求到达应用。

**审查推导**：确认实际解析版本、部署平台/入口保护，以及业务是否把中间件作为唯一授权点。检查外部可控头是否被当成内部可信状态，并追踪实际数据访问授权。历史版本号或使用 Next.js 本身都不足以证明当前项目可利用。

**处理与验证**：按维护者公告选择当前受支持且修复该问题的版本；临时入口规则需覆盖所有直连入口，不能只在一个 CDN 层生效。用隔离测试中的未授权主体访问受保护资源，比较普通请求与带该保留头请求，均应被拒绝，并覆盖允许访问的正常主体。此处的历史修复版本不是今天的安全升级目标。

## 来源字典


以下均已于 **2026-10-27** 读取核验。版本化规范优先固定版本；Living Standard 和框架公告在实际审查时重新核对。

| 来源 ID | 官方资料 | 用途 / 基线 |
|---|---|---|
| WEB-01 | [OWASP ASVS](https://asvs.owasp.org/) | 安全控制要求；5.0.0 |
| WEB-02 | [OWASP WSTG](https://owasp.org/projects/web-security-testing-guide) | 测试方法与场景；稳定版 4.2，5.0 为开发中 |
| WEB-03 | [OWASP API Security Top 10 2023](https://api-security.owasp.org/editions/2023/en/0x11-t10/) | 对象/字段/功能授权、资源与业务流风险；风险分类不替代完整要求 |
| WEB-04 | [OWASP XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html) | 编码上下文、安全接收点与净化边界 |
| WEB-05 | [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html) | token、来源检查与 SameSite 局限 |
| WEB-06 | [OWASP SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html) | 目的地址、DNS、重定向和出站边界 |
| WEB-07 | [WHATWG Fetch：CORS protocol](https://fetch.spec.whatwg.org/#http-cors-protocol) | CORS 与凭证的浏览器协议语义；Living Standard |
| WEB-08 | [IETF RFC 9111：HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111.html) | 共享缓存、缓存键及响应控制指令 |
| WEB-09 | [Google Web Vitals](https://web.dev/articles/vitals) | LCP、INP、CLS；实验室与现场测量边界 |
| WEB-10 | [W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/) | 键盘、焦点、名称、错误与可感知性要求 |
| WEB-11 | [Next.js 官方公告 GHSA-f82v-jwr5-mffw](https://github.com/vercel/next.js/security/advisories/GHSA-f82v-jwr5-mffw) | CVE-2025-29927 的条件、历史版本与处置 |
