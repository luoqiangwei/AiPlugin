# 模型推理与部署子项目

`model-serving/` 与 `skills/`、`agents/`、`model-training/` 平级，用于收录模型推理引擎、运行时和服务部署框架。训练与微调项目见 [模型训练目录](../model-training/README.md)。各上游以 Git submodule 管理，父仓库记录仓库地址与固定提交，便于源码研究、架构对照和按需构建。

## 项目目录

| 类型 | 子项目 | 上游 | 研究方向 |
|---|---|---|---|
| 推理引擎 | [vllm](vllm) | [vllm-project/vllm](https://github.com/vllm-project/vllm) | LLM 推理服务、连续批处理、KV Cache、量化与分布式推理 |
| 推理引擎 | [sglang](sglang) | [sgl-project/sglang](https://github.com/sgl-project/sglang) | LLM、多模态及扩散模型推理，大规模服务与 Agent 工作负载 |
| 推理引擎 | [tensorrt-llm](tensorrt-llm) | [NVIDIA/TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM) | NVIDIA GPU 推理优化、专用 kernel、Python 框架与推理运行时 |
| 推理引擎 | [lmdeploy](lmdeploy) | [InternLM/lmdeploy](https://github.com/InternLM/lmdeploy) | LLM/VLM 压缩、量化、TurboMind 与 PyTorch 引擎、多卡服务 |
| 本地运行与多模型管理 | [llama.cpp](llama.cpp) | [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) | C/C++ 推理、GGUF、CPU/GPU/Metal 后端与 HTTP 服务 |
| 本地运行与多模型管理 | [ollama](ollama) | [ollama/ollama](https://github.com/ollama/ollama) | 本地模型运行与管理、REST API 和应用集成 |
| 本地运行与多模型管理 | [mlx-lm](mlx-lm) | [ml-explore/mlx-lm](https://github.com/ml-explore/mlx-lm) | Apple Silicon 本地文本生成、量化、微调与开发验证 |
| 本地运行与多模型管理 | [xinference](xinference) | [xorbitsai/inference](https://github.com/xorbitsai/inference) | 多模型统一 API、WebUI、语言/语音/多模态模型与分布式部署 |
| 服务与编排 | [triton-inference-server](triton-inference-server) | [triton-inference-server/server](https://github.com/triton-inference-server/server) | 多后端推理服务器、HTTP/gRPC、动态批处理、调度与推理流水线 |
| 服务与编排 | [ray](ray) | [ray-project/ray](https://github.com/ray-project/ray) | Ray Serve 分布式服务、请求路由、自动扩缩容与多模型编排 |
| 服务与编排 | [bentoml](bentoml) | [bentoml/BentoML](https://github.com/bentoml/BentoML) | Python 模型 API、依赖与模型版本管理、容器构建和部署 |
| 服务与编排 | [kserve](kserve) | [kserve/kserve](https://github.com/kserve/kserve) | Kubernetes 推理部署、路由、自动扩缩容、灰度发布与监控 |

## 范围与上游说明

以下说明基于 2026-10-31 核对的上游仓库信息：

- 推理引擎负责执行模型；服务与编排框架负责封装、路由、扩缩容及部署，二者可以组合使用。
- `ggerganov/llama.cpp` 已迁至 `ggml-org/llama.cpp`，添加时按同一上游去重。
- Ray Serve 源码位于 Ray 主仓库的 `python/ray/serve/`，因此收录完整 Ray 仓库。
- Triton Inference Server 是模型推理服务器。其 `main` 为开发分支，配套 core、backend、client 等组件应按上游构建流程获取。
- MLX LM 定位为 Apple Silicon 本地推理与开发验证；其 [HTTP server 文档](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/SERVER.md)明确不建议将该 server 用于生产服务。
- 各项目的硬件、驱动、模型格式和许可要求以相应上游文档及 LICENSE 为准。TensorRT-LLM 包含第三方许可，具体应读取其 LICENSE。

## 拉取与维护

在 AiPlugin 项目根目录拉取本目录的全部子模块：

```sh
GIT_LFS_SKIP_SMUDGE=1 git submodule update --init --depth 1 -- \
  model-serving/vllm model-serving/sglang model-serving/tensorrt-llm model-serving/lmdeploy \
  model-serving/llama.cpp model-serving/ollama model-serving/mlx-lm model-serving/xinference \
  model-serving/triton-inference-server model-serving/ray model-serving/bentoml model-serving/kserve
```

首次收录使用浅克隆，固定上游提交。Git LFS 管理的大文件按需获取，工作区可能保留相应指针；TensorRT-LLM 的部分预编译内核、生成文件与测试资源属于此类。构建或运行需要这些资源时，在对应子模块中拉取，例如：

```sh
git -C model-serving/tensorrt-llm lfs pull
```

后续更新应明确选择目标提交，再提交父仓库中的子模块指针。运行环境、配套组件和模型权重按上游说明准备。

添加其他框架前，先检查根目录 `.gitmodules` 与已有仓库 `origin`，按迁移后的上游地址跨 `skills/`、`agents/`、`ai-platforms/`、`model-training/`、`model-serving/` 去重。
