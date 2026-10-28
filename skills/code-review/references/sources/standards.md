# 通用规则的来源归档

核验日期：2026-10-27。本文件只供溯源和版本复核；运行指令在 SKILL.md、common/quality.md、common/security.md 和对应专项资料中，执行 Review 不需要逐个访问下列链接。领域原始出处见本目录同名文件。

## 使用原则

1. 先执行用户范围与仓库约定，再核对目标版本的官方契约。规范中的 MUST、建议、示例和本技能的工程归纳需要区分；不把某家公司的流程直接宣布为行业强制标准。
2. Google Review 指南用于审查方法；NIST SSDF 用于开发和漏洞响应过程；ASVS/MASVS 用于安全验证要求；WSTG/MASTG 用于验证方法；CWE 描述弱点类别，CVE 指具体漏洞，CVSS 衡量严重度。它们互补，不能互相替代。
3. 引用 ASVS、MASVS 或其他带编号标准时写版本，读取实际条文再填编号；不从旧版本记忆推测新版条目。Top 10/Top 25 只是风险导航，不能替代完整检查或项目威胁模型。
4. 动态信息以审查当日重新核验为准。官网不可访问时查其官方仓库/发布页；仍无证据则标“未核验”，不能把搜索摘要当成已读完整规范。

## 来源字典

| 审查主题 | 一手来源与固定入口 | 本技能采用的内容及限制 |
|---|---|---|
| COMMON-01 | [Google: The Standard of Code Review](https://google.github.io/eng-practices/review/reviewer/standard.html) | 以持续改善代码健康为目标，基于事实处理分歧；非必要润色不能阻塞有价值的变更。属于 Google 工程实践。 |
| COMMON-02 | [Google: What to look for in a code review](https://google.github.io/eng-practices/review/reviewer/looking-for.html) | 审查设计、行为、复杂度、测试和上下文；用于通用审查维度。 |
| COMMON-03 | [NIST SP 800-218, SSDF 1.1 Final](https://csrc.nist.gov/pubs/sp/800/218/final) | 安全开发与发布后漏洞响应框架；参考 PW.7/PW.8 的代码与运行验证、RV 的漏洞响应。不是逐行检查表。 |
| COMMON-04 | [NIST SSDF Publications](https://csrc.nist.gov/Projects/ssdf/publications) | 核验日列 SSDF 1.1 为 Final、1.2（SP 800-218 Rev.1）为 Draft；不把草案自动当正式要求，后续需复核状态。 |
| COMMON-05 | [OWASP Code Review Guide](https://owasp.org/www-project-code-review-guide/) | 人工安全审查与威胁分析的补充资料。2.0 是较早资料，框架/API 细节由当前官方文档覆盖。 |
| COMMON-06 | [SEI CERT Coding Standards](https://cmu-sei.github.io/secure-coding-standards/) | C/C++/Java 等语言的安全编码规则入口；按语言与标准版本选择，区分 rules 与 recommendations。 |
| COMMON-07 | [C++ Core Guidelines](https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines) | 原生代码的资源所有权、RAII、接口及并发推导。是演进中的指南，不是 ISO 标准；内核与受限运行时不能直接套全部规则。 |
| COMMON-08 | [OWASP ASVS](https://asvs.owasp.org/) | 核验日稳定入口 5.0.0；Web/API 的安全验证需求，细节见 Web 模块，不混用 4.x 编号。 |
| COMMON-09 | [CWE 2025 Top 25](https://cwe.mitre.org/top25/archive/2025/2025_cwe_top25.html) | 辅助选择访问控制、注入、内存、资源限制等风险族；这是指定年份快照，不代表每个项目的风险排序。 |
| COMMON-10 | [FIRST CVSS v4.0 Specification](https://www.first.org/cvss/v4.0/specification-document) | 有条件需要量化安全严重度时记录版本、向量和环境。不能只抄分数或把 P0–P3 等同于 CVSS。 |
| COMMON-11 | [OSV](https://osv.dev/) | 依赖漏洞的生态、版本与提交范围查询入口；继续核对原始维护者公告、实际依赖和回移补丁。 |
| COMMON-12 | [SLSA v1.2](https://slsa.dev/spec/v1.2/) | 构建来源、可追溯性及验证的版本化参考；不能仅凭使用某个 CI 就声称达到某等级。 |
| COMMON-13 | [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html) | 最小权限、默认拒绝、每次请求验证与对象级授权；具体框架实施见专项资料。 |
| COMMON-14 | [MITRE CWE-915](https://cwe.mitre.org/data/definitions/915.html) | 不当控制的动态对象属性修改，包括 mass assignment/自动字段绑定；与 CWE-502 的反序列化根因区分。 |

采用关系：COMMON-01/02 → SKILL 的范围、反证、非阻断偏好和报告流程；COMMON-03 → 测试有效性与安全处置；COMMON-06/07 → 对象所有权与可变数据、并发与同步、内存安全；COMMON-08/09/13/14 → 安全边界与对应领域规则；COMMON-10/11/12 → 严重度、依赖适用性和发布核验。具体判断步骤是本技能的原创工程归纳，不把来源中的所有建议视为强制要求。
