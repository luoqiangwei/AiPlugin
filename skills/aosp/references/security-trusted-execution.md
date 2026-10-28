# Trusty IPC、可信应用与 DICE 信任派生

本页用于解释安全环境中的服务边界、Trusty 连接/消息资源及启动测量产生的身份。核实日期：2026-10-28。
先区分目标设备的 TEE 实现、Trusty revision、TA 镜像、启动验证状态与 DICE profile；Android 支持其它 TEE，不能把 Trusty API 当成全部安全硬件的通用接口。
认证 token 与 KeyMint 授权分别见[认证链](security-authentication.md)、[密钥与证明](security-keystore-attestation.md)。

## Trusty 隔离保护的是执行环境

**官方机制**：[Trusty](https://source.android.com/docs/security/features/trusty)由小型内核、Android 内核通信驱动和用户态通信库协作。TA 在 Trusty 内核下以非特权隔离进程运行，具有各自虚拟地址空间。
官方描述的应用交付模型把 TA 与 Trusty 镜像一起签名并在启动时验证；不支持把普通第三方 APK 直接安装成 TA。目标产品的加载与签名实现仍须绑定具体分支。
TA 可以使用设备秘密，新增 TA 也扩大可信计算基；“移到 TEE”没有消除输入解析、状态错误和越权使用秘密的风险。

**工程推导**：至少分别标出 Android 调用者、代理服务、Trusty channel、TA 和 TA 依赖的其它可信服务。
代理拥有访问 TA 的能力，不表示任意经它转发的应用都应获得同样能力。TA 接受某个操作后，即使从不返回密钥材料，也可能成为攻击者的签名或解密代理。
若某协议使用非安全侧共享内存，应把共享内容视为可变化的外部输入，明确读取、复制或固定快照的边界；不能仅凭一轮长度检查认为之后的内容仍相同。

## Port 是服务入口，channel 是连接实例

[Trusty API reference](https://source.android.com/docs/security/features/trusty/trusty-ref)把服务发现与连接分开：安全侧创建命名 port，客户端连接，服务端 `accept()` 后双方各持有一个双向 channel。
普通世界只能连接安全侧公开的服务。`IPC_PORT_ALLOW_TA_CONNECT` 与 `IPC_PORT_ALLOW_NS_CONNECT` 分别控制是否允许可信应用、非安全世界连接；公开 port 的名字本身不是访问凭据。
`accept()` 返回连接方的 TA UUID，而来自非安全世界的连接以全零 UUID 表示。

因此，全零 peer UUID 不能区分 Android 应用 UID、包签名或用户；需要这些身份的服务必须在实际信任链上另有可信授权机制。
客户端在消息里自行填写包名或 UID，只是声明。非安全侧已经失陷的威胁模型下，Android 代理给出的声明也不能自动成为硬件可信身份。
同一 TA 可同时作为客户端和服务端；服务 A 代调用者请求服务 B 时，B 看到的连接身份与最初调用者并不天然相同。

## 异步事件与消息有两套生命周期

| 对象/状态 | 官方契约 | 据此推导的失效方式 |
|---|---|---|
| 异步连接 | 返回 channel 后，等待 `IPC_HANDLE_POLL_READY` 再进入正常通信 | 拿到数值句柄就发业务消息，可能尚未连接 |
| port 的 READY | 表示有待接受连接 | 不执行 accept 会持续观察同一条件 |
| channel 的 MSG/HUP | 位可同时出现：有消息且对方已关闭 | 用单一枚举分支理解事件会漏掉剩余消息或关闭状态 |
| `get_msg` → `read_msg` → `put_msg` | 先取得长度/消息 ID，可按 offset 多次读取，最后 retire | 读完未 retire，缓冲仍占用；retire 后继续读取已失效 |
| 发送队列满 | `send_msg` 返回 `ERR_NOT_ENOUGH_BUFFER`，等待 SEND_UNBLOCKED 再尝试 | 忙循环重试会消耗 TA 执行时间，不能使对端队列腾空 |

大部分事件随条件保持，SEND_UNBLOCKED 则在读取事件时清除。事件循环必须把它记录为一次重新发送机会，而非假定之后仍能再次收到相同通知。
发送成功表明消息进入传输路径，业务处理完成、持久化成功和响应属于应用层协议；底层可靠传输不替协议提供事务语义。

接收时，长度、实际读取字节数、消息类型、协议版本与当前会话状态应共同决定是否接受。
例如声明为“初始化后写入”的命令，在尚未完成初始化或初始化已失败的 channel 上不能复用先前会话的授权状态。
连接中断后，客户端是否能重发需要由操作的幂等性和请求标识说明；单凭没收到响应不能判断 TA 未执行。

## Handle 与 cookie 的所有权

Handle 位于每个 TA 自己的表中，数值只在该应用上下文有效；不能序列化一个整数给另一个 TA 并期待它代表同一资源。
`set_cookie()` 把本地私有指针随事件返回；它是事件分派上下文，不是跨 TA 身份。`close()` 销毁关联资源并从表中移除句柄。
这里沿用官方 reference 的 API 语义，较新分支的 handle 传递与结构扩展需查目标头文件，不能把页面中的保留字段描述提升为永久限制。

**工程推导**：channel 状态、cookie 对象和待处理消息的释放顺序必须一致。若先释放 cookie 所指对象，迟到事件仍可能触达失效内存；若保留旧 channel 的授权状态并复用到新连接，则会跨会话混淆权限。
资源释放也影响可用性：未关闭 channel、未 retire 的消息、无限保留的请求都可能耗尽有限缓冲或句柄。
TA 标准输出/错误可按平台配置进入普通世界可见的日志，因此这些流不构成秘密输出通道。[API reference](https://source.android.com/docs/security/features/trusty/trusty-ref)

## DICE：从设备秘密沿启动路径派生身份

[DICE 官方说明](https://source.android.com/docs/security/features/dice)的根是 ROM 可读取的设备唯一秘密 UDS。
ROM 使用硬件机制锁住 UDS 后续访问，把 UDS、下一阶段测量和配置送入 KDF，产生下一阶段 CDI；之后各阶段以先前 CDI 和下一级测量继续派生。
密钥与证书链随阶段产生，因此前面某阶段的代码或配置改变会影响后续身份。这里的 CDI 是秘密，传给远程方的是可验证的公钥/证书证据，不能混成公开设备序列号。

```text
设备 UDS + ROM 信任
  → 测量/配置绑定的 CDI
  → 下一阶段 CDI 与证书
  → 按加载路径分叉的应用域身份
```

**工程推导**：证书签名有效，只能支持“来自哪条测量链”的判断；接受哪组代码、配置和回退状态，仍是验证方策略。
更新改变测量值后，旧身份匹配失败未必是证书损坏；也可能是验证方仍只接受旧测量。反过来，盲目接受任意新测量会丢掉“运行的是哪份代码”的约束。
ROM/UDS 的可信性、锁存机制及各阶段测量完整性是此模型的前提；Android 进程宣称自己的 hash 不能替代它们。

[DICE 应用](https://source.android.com/docs/security/features/dice/applications-of-dice)说明两种用途：RKP 可把根移到比完整 TEE 更小的可信基础，并在固件修复后重新证明当前状态；分叉的 DICE 链还形成设备内 PKI，使独立安全域互相认证，例如 pVM 与 Secretkeeper 的关系。
恢复信任需要实际修补、测量链与远端接受策略共同成立，不是“使用 DICE 就自动撤销全部历史风险”。Secretkeeper 的稳定秘密释放、授权策略升级和持久存储契约应继续查其目标 HAL，不能由一条 DICE 链直接推出。

## 能解释失败的证据

| 现象 | 需要关联的事实 |
|---|---|
| 能连上 TA，但操作被拒绝 | port 连接 flags、peer UUID 来源、协议授权和 TA 当前会话状态 |
| 请求偶发卡住 | channel 队列、outstanding message、put_msg 结果、SEND_UNBLOCKED 是否被消费 |
| 对端退出后仍收到事件 | MSG/HUP 位组合、close 时刻、cookie 和请求的归属 |
| 更新后远端拒绝证明 | DICE 链所含测量/配置、验证根、允许策略及目标镜像身份 |

本页已提炼 IPC、TA 输入边界与 DICE 派生关系；未穷举 Trusty syscall、TA 专属协议、板级安全内存布局、DICE 证书的全部编码及 Secretkeeper 策略语言。
