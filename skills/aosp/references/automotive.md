# Android Automotive：车辆能力、乘员与电源边界

具体机制见[车辆服务/VHAL/电源](automotive-vehicle-services.md)、[乘员/HMI/显示](automotive-occupants-ui.md)、[车载媒体](automotive-media-integration.md)与[SDV 服务协议](sdv-service-protocols.md)。

本页将官方机制归纳为开发判断，不构成车辆功能安全认证。
基线核实日期：2026-10-28。Car API、VHAL 版本、配置格式和服务归属以目标分支为准。
先在 manifest 固定的 `packages/services/Car`、HAL 接口及产品配置中核实，再应用官网当前版本的说明。

## AAOS、Android Auto 与 GAS

AAOS 是运行在车载硬件上的 Android 操作系统，可承载车载应用与车辆集成。
Android Auto 是手机与兼容车机协作的投射体验，两者可在同一车辆产品中共存。
GAS 是车厂可选择授权集成的一组 Google 应用和服务，不等于 AAOS 开源平台。
因此“实现 AAOS 功能”“兼容手机投射”“满足 GAS 合作要求”是不同的交付目标。[平台定义][overview]

| 层次 | 承担的语义 | 不能据此推断 |
|---|---|---|
| Car API / Car Manager | 向客户端提供汽车能力契约 | 普通应用具有所有车辆权限 |
| CarService | 实现车辆策略、权限与服务协调 | 所有策略都应放到 VHAL |
| VHAL | 车辆属性配置、读取、写入、订阅 | 它是允许任意 CAN 访问的透传口 |
| OEM 车辆接口 | 对接 ECU、总线及车厂协议 | AAOS API 已覆盖硬实时控制责任 |

CarService 的 Binder 接口、子服务与生命周期可从 `ICarImpl` 及其委托实现定位。
“系统服务”不代表一定运行在 `system_server`；以实际进程、用户及注册链为准。[实现入口][car-service]
新的 SDV、多 VM 和车辆服务机制需另核对目标版本，不能把经典 IVI 架构视为 AAOS 的全部范围。

## VHAL 的属性契约

VHAL 暴露车辆功能的属性，而非应用数据库字段。
属性的 ID、类型、area、访问权限、变化模式及配置共同组成契约。
调用方应区分“不支持”“暂不可用”“读取失败”和一个有效的零值。[VHAL][vhal]

- `areaId` 表达座椅、车窗等区域语义，不能用数组下标或 Android user ID 替代。
- 订阅是持续数据流；订阅频率、重连和取消订阅影响负载与资源占用。
- 写入请求成功不一定等于物理动作完成；按目标属性语义验证回读、异步结果或状态通知。
- 车速、档位等输入可能暂不可用或过期；策略不能把缓存值当成无限期有效的事实。
- 标准属性的语义与权限应保持兼容；厂商扩展使用规定的扩展空间和访问控制。

Android 13 起采用 AIDL VHAL；已有旧分支可能仍是 HIDL。
不要仅更新客户端生成代码而保留不匹配的 HAL 实现、配置或 VINTF 声明。
审查新增属性时，重点核实数据所有者、读写授权、单位、边界值和失联语义。

## 多区域音频

Car audio 在核心音频策略上增加音区、音量组、焦点与车辆场景的协调。
音区连接到输出设备和乘员关系，不能把“同一音频流在两路输出”直接当成两个独立用户音区。
各音区可以独立维护焦点与音量；实际隔离仍依赖硬件和 Audio HAL 的路由能力。[音区路由][audio]

`car_audio_configuration.xml`、音频策略设备地址和实际 HAL 端口必须一致。
处理插拔、用户切换和区域重分配时，避免旧用户会话继续路由到新乘员输出。
导航、媒体、通话和安全提示的优先关系不能仅靠应用层抢焦点实现。
音频问题的证据应同时包含焦点决策、设备路由、音量组与硬件能力，不能仅凭播放器状态判断。

## 用户、显示与乘员区域

Headless system user 承载后台系统职责，不能作为车主日常登录身份。
乘员使用的 Android 用户、显示 ID、物理座位和 occupant zone 是相关但不同的标识。
多用户多显示能力受 Android 版本和产品 overlay 控制，不是所有 AAOS 设备都默认具备。[多用户机制][users]

- 缓存、订阅、账号和媒体会话需明确按用户还是按车辆全局保存。
- 换人、访客退出和用户删除后，旧回调及敏感缓存不应继续对新用户可见。
- 显示区域改变时，Activity 放置、输入焦点、音区和 UX restrictions 需要对应同一乘员语义。
- 一个进程服务所有用户，不代表其所有 API 都可以跨用户访问。

审查用户切换缺陷时，先判断是身份映射、服务生命周期还是异步回调滞后，不直接归因于 UI 刷新。

## 电源状态与 Garage Mode

车辆的 VMCU、应用处理器和外设具有独立电源职责。
屏幕熄灭、STR、STD、关闭处理器与系统仍在后台维护不是同一个状态。[车辆电源][power]
CarPowerManagementService 与车辆状态交互，电源策略再约束显示、音频、网络等组件。
电源策略守护进程维护策略状态，应用不应绕过它私自恢复已被关闭的能力。[电源策略][power-policy]

Garage Mode 提供停车后的维护窗口，例如作业和更新；它不等于无限制后台运行。
维护任务需要能完成、超时或取消，并向电源状态机正确释放结束条件。[Garage Mode][garage]
不要为延长任务而无限持有唤醒锁、吞掉关机通知或重复触发唤醒。
恢复后应区分重新初始化与恢复旧会话，防止重复订阅、重复播放或过期车辆状态重新生效。

## 驾驶分心与安全边界

UI 应消费 `CarUxRestrictionsManager` 的限制，而不是只用车速大于零自行推导可显示内容。
限制可以随市场、显示和配置变化；同一时刻司机屏与乘客屏不必采用同一策略。[限制消费][ux-consume]
Distraction Optimized 声明只让平台识别 Activity 的声明，不证明界面实际符合要求。[分心指南][ux-guidelines]
在声明之外，还需让受限界面及时响应状态变化，避免已经打开的界面继续提供受限交互。

信息娱乐策略、车身能力访问和车辆安全控制之间应有明确边界。
通用 Android 测试、UX 声明或 VHAL 连通性不能证明功能安全等级或法规合规。
涉及仪表、倒车影像、警示音或车辆执行器时，需使用项目已建立的安全架构和降级责任分配。
无法确认安全责任时，应明确未决边界；不要以 UI 可用或“车辆已停车”代替论证。

## 从现象还原机制

| 现象 | 优先寻找的证据 | 需要避免的误推 |
|---|---|---|
| 车辆属性读到错误值 | property/area 配置、状态、时间戳、VHAL 与 ECU 链 | 把缺失值补成 0 即可 |
| 乘客声音进入司机扬声器 | 用户到音区映射、设备地址、焦点和实际路由 | 只修应用音量 |
| 换用户后仍收到旧事件 | Binder listener 所属用户、订阅释放和重连 | 所有 listener 都是全局 |
| 停车后电量异常 | 电源转换、Garage 作业、唤醒来源和持续时间 | 熄屏意味着处理器已休眠 |
| 行驶时受限界面仍可操作 | UXR 回调、显示映射、Activity 声明与控件状态 | DO 标签已经保证安全 |
| 断开车辆接口后策略异常 | 错误状态传播、缓存年龄、重连及重放 | 最后一次值永远可信 |

判断改动是否落在正确层，依据是规则所有权与失效范围。
车辆协议错误修在接口适配处；跨入口一致的车辆策略修在负责该策略的服务；视觉限制响应修在 UI 消费处。
只在应用中掩盖 HAL 的不合法单位或失联状态，会使其他调用方继续收到错误事实。

## 官方依据与版本复核

以下页面已阅读并用于上述归纳；持续更新的网页不固定产品分支的行为。
类名、权限、属性配置与产品 overlay 必须在交付 manifest 对应的源码和测试中再次核实。

[overview]: https://source.android.com/docs/automotive/start/what_automotive
[car-service]: https://android.googlesource.com/platform/packages/services/Car/+/refs/heads/main/service/src/com/android/car/ICarImpl.java
[vhal]: https://source.android.com/docs/automotive/vhal
[audio]: https://source.android.com/docs/automotive/audio/audio-multizone-routing
[users]: https://source.android.com/docs/devices/admin/multi-user
[power]: https://source.android.com/docs/automotive/power
[power-policy]: https://source.android.com/docs/automotive/power/power_policy
[garage]: https://source.android.com/docs/automotive/power/garage_mode
[ux-consume]: https://source.android.com/docs/automotive/driver_distraction/consume
[ux-guidelines]: https://source.android.com/docs/automotive/driver_distraction/guidelines
