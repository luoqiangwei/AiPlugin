# 模型训练子项目

`model-training/` 与 `model-serving/` 平级，收录通用训练框架、模型训练组件、分布式训练、微调和强化学习后训练项目。各上游以 Git submodule 管理，父仓库记录仓库地址与固定提交，用于源码研究和按需构建。

## 项目目录

| 类型 | 子项目 | 上游 | 研究方向 |
|---|---|---|---|
| 基础训练栈 | [pytorch](pytorch) | [pytorch/pytorch](https://github.com/pytorch/pytorch) | 张量、自动求导、神经网络、FSDP 与分布式训练基础 |
| 基础训练栈 | [tensorflow](tensorflow) | [tensorflow/tensorflow](https://github.com/tensorflow/tensorflow) | 通用机器学习训练、自动求导、算子与分布式执行 |
| 基础训练栈 | [jax](jax) | [jax-ml/jax](https://github.com/jax-ml/jax) | 自动微分、JIT、向量化与加速器分片的数值计算底座 |
| 基础训练栈 | [flax](flax) | [google/flax](https://github.com/google/flax) | JAX 上的 NNX 神经网络、优化器、检查点与训练示例 |
| 模型与训练组件 | [transformers](transformers) | [huggingface/transformers](https://github.com/huggingface/transformers) | 文本、视觉、语音和多模态模型定义，以及 Trainer 训练流程 |
| 模型与训练组件 | [diffusers](diffusers) | [huggingface/diffusers](https://github.com/huggingface/diffusers) | 扩散模型组件、图像和视频生成模型的训练与微调脚本 |
| 分布式与大规模训练 | [accelerate](accelerate) | [huggingface/accelerate](https://github.com/huggingface/accelerate) | 自定义 PyTorch 训练循环的设备、混合精度、分布式启动与集成 |
| 分布式与大规模训练 | [deepspeed](deepspeed) | [deepspeedai/DeepSpeed](https://github.com/deepspeedai/DeepSpeed) | ZeRO、内存卸载、多维并行与训练优化 |
| 分布式与大规模训练 | [megatron-lm](megatron-lm) | [NVIDIA/Megatron-LM](https://github.com/NVIDIA/Megatron-LM) | 大规模 Transformer 预训练、Megatron Core 与多维并行 |
| 分布式与大规模训练 | [torchtitan](torchtitan) | [pytorch/torchtitan](https://github.com/pytorch/torchtitan) | PyTorch 原生预训练、SFT、TitanRL 与多维并行组合 |
| 参数高效微调与训练工具 | [peft](peft) | [huggingface/peft](https://github.com/huggingface/peft) | LoRA 等参数高效微调方法与适配器 |
| 参数高效微调与训练工具 | [llama-factory](llama-factory) | [hiyouga/LlamaFactory](https://github.com/hiyouga/LlamaFactory) | CLI/WebUI、持续预训练、SFT、LoRA/QLoRA 与偏好对齐 |
| 参数高效微调与训练工具 | [axolotl](axolotl) | [axolotl-ai-cloud/axolotl](https://github.com/axolotl-ai-cloud/axolotl) | YAML 配置驱动的全量/LoRA 微调、多模态、RL 与多 GPU 训练 |
| 参数高效微调与训练工具 | [unsloth](unsloth) | [unslothai/unsloth](https://github.com/unslothai/unsloth) | 高效微调、LoRA/QLoRA、强化学习与模型导出 |
| 强化学习与后训练 | [trl](trl) | [huggingface/trl](https://github.com/huggingface/trl) | SFT、DPO、GRPO 等后训练与对齐 Trainer |
| 强化学习与后训练 | [verl](verl) | [verl-project/verl](https://github.com/verl-project/verl) | HybridFlow、PPO/GRPO、分布式 RL、训练与 rollout 编排 |
| 强化学习与后训练 | [openrlhf](openrlhf) | [OpenRLHF/OpenRLHF](https://github.com/OpenRLHF/OpenRLHF) | 基于 Ray、vLLM、DeepSpeed 的 RLHF 与多轮 Agent RL |

## 复用已有子项目

同一上游只挂载一次。下列训练能力直接引用已有仓库：

| 已有目录 | 训练相关用途 |
|---|---|
| [Ray](../model-serving/ray) | `python/ray/train/` 提供分布式训练执行，`python/ray/tune/` 提供超参数搜索 |
| [MLX LM](../model-serving/mlx-lm) | Apple Silicon 本地微调、LoRA 与分布式微调 |
| [vLLM](../model-serving/vllm)、[SGLang](../model-serving/sglang) | 与强化学习训练系统配合的 rollout/生成引擎 |

## 上游与范围说明

以下说明基于 2026-10-31 核对的上游仓库信息：

- DeepSpeed 原地址 `microsoft/DeepSpeed` 已迁至 `deepspeedai/DeepSpeed`。
- verl 原地址 `volcengine/verl` 已迁至 `verl-project/verl`；配套 `recipe/` 为独立仓库的嵌套子模块，按需初始化。
- LlamaFactory 原地址 `hiyouga/LLaMA-Factory` 已迁至 `hiyouga/LlamaFactory`。
- JAX 原地址 `google/jax` 已迁至 `jax-ml/jax`。JAX 是计算与程序变换底座，Flax 提供其上的神经网络层；两者分别收录。
- Accelerate 负责封装训练执行与启动，可与模型库及训练工具组合；TorchTitan 包含预训练和 TitanRL 等路径，最新功能的环境要求以上游为准。
- 各仓库及组件的使用条件以相应 LICENSE 为准。Unsloth 核心包为 Apache-2.0，部分可选组件如 Studio UI 使用 AGPL-3.0；Megatron-LM 的实际 LICENSE 包含 NVIDIA BSD 风格主条款及第三方许可。

## 拉取与维护

在 AiPlugin 项目根目录拉取本目录全部子模块：

```sh
GIT_LFS_SKIP_SMUDGE=1 git submodule update --init --depth 1 -- \
  model-training/pytorch model-training/tensorflow model-training/jax model-training/flax \
  model-training/transformers model-training/diffusers model-training/accelerate \
  model-training/deepspeed model-training/megatron-lm model-training/torchtitan \
  model-training/peft model-training/llama-factory model-training/axolotl model-training/unsloth \
  model-training/trl model-training/verl model-training/openrlhf
```

首次收录使用浅克隆并固定提交；Git LFS 大文件按需获取，工作区可能保留相应指针。需要这些资源时，在对应子模块中执行 `git lfs pull`。嵌套子模块、数据集、模型权重和运行环境按各上游的构建及训练文档准备。

后续更新应明确选择目标提交，再提交父仓库的子模块指针。添加新项目时，按迁移后的上游地址跨 `skills/`、`agents/`、`ai-platforms/`、`model-training/`、`model-serving/` 去重。
