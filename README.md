# 🎨 Your Own AI Image Gen

> 中文提示词 → AI 自动优化 → 本地/云端出图。单图生成 + 漫画分镜 + 视频创作，一站式 AI 图像工作室。

<p align="center">
  <img src="screenshots/02_single_image.png" alt="单图生成" width="45%">
  <img src="screenshots/03_comic_studio.png" alt="漫画工作室" width="45%">
</p>

---

## ✨ 功能亮点

| 功能 | 说明 |
|---|---|
| 🎨 **单图生成** | 中文描述 → LLM 翻译优化 → ComfyUI / 云端出图 |
| 📖 **漫画工作室** | 分镜脚本 → 批量生成同角色多场景图片 |
| 🧠 **IPAdapter 角色一致性** | 一张参考图锁定面部特征，跨场景保持同一张脸 |
| 🎬 **视频生成** | 文字描述 → Wan2.1 / HunyuanVideo 生成视频 |
| 🎭 **风格预设** | Soft Moe / Dark Dramatic / Watercolor 一键切换 |
| 🌐 **WebUI 版** | Gradio 网页界面，浏览器即开即用（v3.2 新增） |
| 🤖 **Anima 动漫模型** | 支持 20 亿参数 Cosmos Predict2 动漫特化模型（v3.2 新增） |
| 🔧 **多模型切换** | dreamshaper / pony / meinamix / Anima 自由切换 |
| ☁️ **多后端支持** | ComfyUI 本地 / Pollinations.AI / Stability AI / 硅基流动 |
| 🖥️ **纯本地运行** | 无需联网，所有推理在本地完成 |

---

## 🚀 快速开始

### 环境要求

| 组件 | 要求 |
|---|---|
| 操作系统 | Windows 10/11（Linux/macOS 自行适配） |
| Python | 3.10+（[官网下载](https://www.python.org/downloads/)） |
| GPU | NVIDIA 4GB+（SD 1.5）/ 8GB+（SDXL）/ 16GB+（视频） |
| Ollama | [ollama.com](https://ollama.com) 下载安装 |
| ComfyUI | [GitHub](https://github.com/comfyanonymous/ComfyUI) 克隆到 `C:\Users\你的用户名\ComfyUI\` |

### 安装步骤

**第一步：克隆本项目**
```bash
git clone https://github.com/Eric-huang799/your-own-ai-image-gen.git
cd your-own-ai-image-gen
pip install -r requirements.txt
```

**第二步：安装 Ollama 并拉取模型**
```bash
# 下载安装 Ollama 后：
ollama pull wizardlm-uncensored
```

**第三步：安装 ComfyUI 并下载生图模型**

将 ComfyUI 克隆到 `~/ComfyUI/`（即 `C:\Users\你的用户名\ComfyUI\`）。

下载至少一个生图模型到 `ComfyUI\models\checkpoints\`：

| 模型 | 风格 | 大小 | 下载 |
|---|---|---|---|
| `anima-base-v1.0.safetensors` | 🆕 动漫特化 | ~4GB | [HuggingFace](https://huggingface.co/circlestone-labs/Anima) |
| `meinamix_v12Final.safetensors` | 二次元萌系 | ~2GB | [Civitai](https://civitai.com/models/7240/meinamix) |
| `ponyDiffusionV6XL_v6.safetensors` | 二次元插画 | ~7GB | [Civitai](https://civitai.com/models/257749/pony-diffusion-xl-v6) |
| `dreamshaper_8.safetensors` | 通用写实 | ~2GB | [Civitai](https://civitai.com/models/4384/dreamshaper) |

> **Anima 额外文件**：还需要 `qwen_3_06b_base.safetensors`（放入 `models/text_encoders/`）和 `qwen_image_vae.safetensors`（放入 `models/vae/`），均从 [HuggingFace](https://huggingface.co/circlestone-labs/Anima) 下载。

**第四步：运行**

```bash
# 桌面 GUI 版
双击 start.bat → 选择 [1]

# 网页 WebUI 版（v3.2）
双击 start.bat → 选择 [2]
# 浏览器打开 http://127.0.0.1:7862
```

启动脚本会自动检测并启动 Ollama，检查 Python 依赖是否齐全。ComfyUI 需手动启动。

### 模型自动检测

启动时自动识别 GPU 显存并推荐模型：

| 显存 | 推荐 |
|---|---|
| 2.5-4GB | Dreamshaper 8 / Meinamix（SD 1.5，512px） |
| 4-8GB | Anything V5（SD 1.5，1024px） |
| 8GB+ | Pony Diffusion XL / Anima（SDXL/DiT，2048px） |

---

## 📖 使用指南

### 🎨 单图生成

1. 输入中文描述（如"日系少女，蓝发，校服，樱花树下微笑"）
2. 点击「🪄 AI 优化」——LLM 自动翻译为英文 Danbooru 标签
3. 调整参数或直接点击「🚀 生成」
4. 右侧显示生成结果

### 📖 漫画工作室

1. **角色设定**：填写固定外貌特征（脸型、发型、瞳色等）
2. **分镜脚本**：每行一个场景，包含动作/表情/服装/背景
3. **选择模式**：
   - 🧠 **IPAdapter**（推荐）：txt2img + 面部注入，动作自由且脸一致
   - 🔒 **Face Lock**：img2img 参考图打底，脸最像但动作受限
4. 点击「🚀 生成漫画」批量出图

### 🎬 视频生成

1. 切换到「视频生成」Tab
2. 输入视频描述（中文即可）
3. 选择模型：Wan2.1 1.3B（轻量）/ HunyuanVideo 1.5（高质量）
4. 点击生成

---

## 🤖 Anima 动漫模型

[Anima](https://huggingface.co/circlestone-labs/Anima) 是 CircleStone Labs × Comfy Org 联合推出的 20 亿参数动漫特化文生图模型。

**特点**：
- Cosmos Predict2 DiT 架构，专注动漫/插画风格
- 支持 Danbooru 标签 + 自然语言混合提示
- 推荐采样器 `er_sde`，调度器 `beta`，CFG 4-5

**ComfyUI 部署**：

| 文件 | 放置位置 |
|---|---|
| `anima-base-v1.0.safetensors` | `models/diffusion_models/` |
| `qwen_3_06b_base.safetensors` | `models/text_encoders/` |
| `qwen_image_vae.safetensors` | `models/vae/` |

> ⚠️ RTX 50 系列（Blackwell）显卡需启动 ComfyUI 时加 `--use-pytorch-cross-attention` 参数。

---

## ☁️ 云端 API（可选）

在「设置」Tab 填入 API Key 即可切换云端后端，无需本地 GPU。

| 类型 | Provider | 说明 |
|---|---|---|
| LLM 优化 | DeepSeek | 便宜，中文友好 |
| LLM 优化 | OpenAI | GPT-4o-mini，质量高 |
| LLM 优化 | Claude | Prompt 工程能力强 |
| 图像生成 | Stability AI | SDXL，速度最快 |
| 图像生成 | 硅基流动 | 国内网络友好 |
| 图像生成 | Pollinations.AI | 免费，无需注册 |

---

## 🔧 项目结构

```
your-own-ai-image-gen/
├── ai_image_studio.py          # 桌面 GUI 主程序（tkinter）
├── ai_studio_web.py            # WebUI 版（Gradio，v3.2 新增）
├── config_manager.py           # 配置持久化
├── providers/                  # Provider 抽象层
│   ├── llm_base.py             #   LLM 基类
│   ├── ollama_llm.py           #   Ollama 本地
│   ├── openai_llm.py           #   OpenAI
│   ├── claude_llm.py           #   Claude
│   ├── deepseek_llm.py         #   DeepSeek
│   ├── image_base.py           #   图像生成基类
│   ├── comfyui_image.py        #   ComfyUI 本地
│   ├── stability_image.py      #   Stability AI
│   ├── siliconflow_image.py    #   硅基流动
│   ├── pollinations_image.py   #   Pollinations.AI（免费）
│   └── wanvideo_provider.py   #   Wan2.1 视频
├── workflows/                  # ComfyUI API 工作流
│   ├── txt2img_api.json
│   ├── img2img_api.json
│   ├── ipadapter_api.json
│   └── wan_t2v_api.json
├── screenshots/                # 截图与作品展示
├── start.bat                   # 一键启动
└── README.md
```

---

## ⚠️ 重要法律声明与使用条款

> **本项目使用无审查（Uncensored）AI 模型，具有生成任何类型图像的技术能力。使用者必须严格遵守法律法规，开发者对任何滥用行为不承担任何责任。**

### 一、项目定位

本项目是**开源学术研究工具**，旨在探索本地 AI 图像生成的技术边界，为创作者提供自由表达的创作环境。

**本项目不是内容生产平台，不提供、不托管、不传播任何第三方内容。**

### 二、明确禁止的行为

使用本工具时，**严格禁止**以下行为：

- ❌ 生成、传播或分发任何违法内容
- ❌ 侵犯他人知识产权（未经授权使用他人角色、商标、版权素材）
- ❌ 用于任何商业色情产业或相关服务
- ❌ 冒充、诽谤或损害任何真实人物的肖像权和名誉权
- ❌ 生成可能误导公众的深度伪造（Deepfake）内容用于恶意目的
- ❌ 将生成内容用于诈骗、勒索、骚扰等犯罪活动

### 三、使用者责任

下载、安装或使用本软件，即表示您同意并承诺：

1. 您年满 18 周岁或已达到所在司法管辖区的法定成年年龄
2. 您对自己使用本工具生成的所有内容承担全部法律责任
3. 您仅将本工具用于合法的个人学习、艺术创作或学术研究
4. 您不会将本工具或生成的内容用于任何商业违法活动

### 四、免责声明

- 本工具按"原样"（AS IS）提供，不作任何明示或暗示的担保
- 开发者不对因使用或无法使用本工具而引起的任何损失、索赔或损害负责
- 开发者不对用户生成的任何内容承担审查、监控或法律责任
- 如用户违反上述条款，开发者保留配合执法机关调查的权利

### 五、开源协议

本项目代码以 [MIT License](LICENSE) 开源。MIT License 仅适用于**源代码本身**，不延伸至用户生成的内容，也不构成对任何违法行为的许可或授权。

**代码开源 ≠ 使用无限制。技术无罪，但使用有界。请做一个负责任的创作者。**

---

## 📝 更新日志

### v3.2 (2026-06)
- 🆕 **WebUI 版**：Gradio 网页界面，浏览器即开即用
- 🆕 **Anima 动漫模型**：支持 Cosmos Predict2 2B 动漫特化模型
- 🆕 **Pollinations.AI 后端**：免费云端生图，无需注册
- 🆕 **两段式提示词优化**：中文→英文翻译 + Danbooru 标签扩展
- 🆕 **RTX 50 系列兼容**：Blackwell GPU 使用 PyTorch SDPA 替代 xformers
- 🔧 修复：wizardlm 审查问题（SYSTEM prompt 置空）

### v3.1 (2026-05)
- 🎬 视频生成 Tab：Wan2.1 14B T2V
- 视频参数可调：分辨率、帧数、CFG

### v3.0 (2026-05)
- Provider 抽象层：LLM/图像生成解耦
- 云端 API 支持：OpenAI / Claude / DeepSeek + Stability AI / 硅基流动
- 可视化设置 Tab

---

*Maintained by Eric-huang799. Issues and PRs welcome.*
