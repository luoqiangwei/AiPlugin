# C++ 来源与提炼边界

以下一手规范或指南入口已于 **2026-10-27** 读取；语言模块包含执行所需语义，不要求审查时访问外链。

| 实际读取的资料 | 提炼用途 |
|---|---|
| [C++ Core Guidelines](https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines) | 读取资源管理、移动后有效状态及析构失败章节；提炼资源交接窗口与不抛异常的清理，不把指南中的风格建议一律当错误 |
| [C++ 公开工作草案：异常展开](https://eel.is/c++draft/except.ctor) | 已构造的自动对象与构造失败时已完成子对象的析构范围 |
| [C++ 公开工作草案：移动辅助函数](https://eel.is/c++draft/forward) | std::move 返回引用转换；是否发生移动由后续操作及重载决定 |
| [C++ 公开工作草案：标准库对象的移动后状态](https://eel.is/c++draft/lib.types.movedfrom) | 默认有效但值未指定；区分类型明确保证与未证明的源内容依赖 |
| [C++ 公开工作草案：string_view](https://eel.is/c++draft/string.view.template) | 视图以底层指针/长度构造，底层指针失效会传播到视图的元素访问 |
| [C++ 公开工作草案：vector 修改](https://eel.is/c++draft/vector.modifiers) | 重分配与无重分配插入、擦除各自的引用/迭代器失效范围 |
| [C++ 公开工作草案：terminate](https://eel.is/c++draft/except.terminate) | 异常逃出不抛异常函数、异常展开中析构再抛的终止语义 |

公开工作草案会继续演进，不冒充已发布 ISO 版本；本模块仅取已用于常见 C++ 版本的上述基础语义，实际审查仍以项目标准版本与库契约为准。复制、借用和显式完成接口的建议须由实际失效或失败路径支撑，不能仅凭使用裸指针或 moved-from 对象判错。
