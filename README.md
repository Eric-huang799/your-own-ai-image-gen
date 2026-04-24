# 你自己的AI生图 (Your Own AI Image Gen)

🎨 本地运行、无需联网的 AI 图像生成工具。支持单图生成和漫画分镜批量创作，角色一致性好。

---

## 🚨 重要法律声明与使用条款

> **⚠️ 警告：本项目使用无审查（Uncensored）AI模型，具有生成任何类型图像的技术能力。使用者必须严格遵守法律法规，开发者对任何滥用行为不承担任何责任。**

### 一、项目定位

本项目是**开源学术研究工具**，旨在：
- 探索本地 AI 图像生成的技术边界
- 为创作者提供自由表达的创作环境
- 研究角色一致性、风格迁移等 AI 绘画技术

**本项目不是内容生产平台，不提供、不托管、不传播任何第三方内容。**

### 二、明确禁止的行为

使用本工具时，**严格禁止**以下行为：

- ❌ **生成、传播或分发任何违法内容**（包括但不限于色情、暴力、仇恨言论、儿童相关内容）
- ❌ **侵犯他人知识产权**（未经授权使用他人角色、商标、版权素材）
- ❌ **用于任何商业色情产业或相关服务**
- ❌ **冒充、诽谤或损害任何真实人物的肖像权和名誉权**
- ❌ **生成可能误导公众的深度伪造（Deepfake）内容用于恶意目的**
- ❌ **将生成内容用于诈骗、勒索、骚扰等犯罪活动**

### 三、使用者责任

下载、安装或使用本软件，即表示您同意并承诺：

1. **您年满 18 周岁或已达到所在司法管辖区的法定成年年龄**
2. **您对自己使用本工具生成的所有内容承担全部法律责任**
3. **您仅将本工具用于合法的个人学习、艺术创作或学术研究**
4. **您不会将本工具或生成的内容用于任何商业违法活动**
5. **您理解并同意开发者无法且不会对您的使用行为进行审查或监控**

### 四、免责声明

**开发者明确声明：**

- 本工具按"原样"（AS IS）提供，**不作任何明示或暗示的担保**
- 开发者**不对因使用或无法使用本工具而引起的任何损失、索赔或损害负责**
- 开发者**不对用户生成的任何内容承担审查、监控或法律责任**
- 开发者**保留随时修改、终止或限制本工具访问的权利，无需事先通知**
- 如用户违反上述条款，开发者**保留配合执法机关调查的权利**

### 五、开源协议

本项目代码以 [MIT License](LICENSE) 开源。MIT License 仅适用于**源代码本身**，不延伸至用户生成的内容，也不构成对任何违法行为的许可或授权。

**代码开源 ≠ 使用无限制。请严格遵守当地法律。**

---

## 功能亮点

| 功能 | 说明 |
|---|---|
| 🎨 **单图生成** | 中文提示词 → AI 自动翻译优化 → ComfyUI 出图 |
| 📖 **漫画工作室** | 角色设定 + 分镜脚本 → 批量生成同角色不同场景的图片 |
| 🎭 **双模式** | Action Free（动作自由）/ Face Lock（高一致性） |
| 🌈 **风格预设** | Soft Moe / Dark Dramatic / Watercolor 一键切换 |
| 🔧 **模型切换** | 支持 dreamshaper / pony / meinamix 等多种模型 |
| 🖥️ **纯本地** | 所有模型、推理、图片全部在本地完成，无需联网 |

---

## 运行环境

- **操作系统**：Windows 10/11
- **Python**：3.10+
- **GPU**：NVIDIA 显卡，至少 6GB 显存（推荐 8GB+）
- **依赖**：Ollama（提示词优化）+ ComfyUI（图像生成）

---

## 界面展示

### 🎨 单图生成
单图生成界面，中文提示词自动翻译优化：

![单图生成](screenshots/02_single_image.png)

### 📖 漫画工作室
角色设定 + 分镜脚本 + 风格预设，一键批量生成：

![漫画工作室](screenshots/03_comic_studio.png)

### 📚 漫画分镜生成结果
同角色不同动作/场景/表情的批量生成效果：

![漫画分镜](screenshots/04_comic_panels.png)

---

## 作品展示

> **以下展示内容均为技术演示，仅用于展示工具功能，不代表任何立场或倾向。**

### 🎭 角色设定

![角色设定](screenshots/artwork_character_portrait.png)

### 📖 漫画分镜

![漫画分镜1](screenshots/artwork_panel_01.png)

![漫画分镜3](screenshots/artwork_panel_03.png)

---

## 快速开始

### 1. 安装依赖

- 安装 [Ollama](https://ollama.com) 并拉取 `wizardlm-uncensored`：
  ```bash
  ollama pull wizardlm-uncensored
  ```
- 安装 [ComfyUI](https://github.com/comfyanonymous/ComfyUI) 到 `~/ComfyUI/` 目录

### 2. 下载模型

将 `.safetensors` 模型文件放到 `ComfyUI/models/checkpoints/`：

| 模型 | 推荐用途 | 下载 |
|---|---|---|
| `dreamshaper_8.safetensors` | 通用写实 | [Civitai](https://civitai.com/models/4384/dreamshaper) |
| `meinamix_v12Final.safetensors` | 二次元萌系（推荐） | [Civitai](https://civitai.com/models/7240/meinamix) |
| `ponyDiffusionV6XL_v6.safetensors` | 二次元插画 | [Civitai](https://civitai.com/models/257749/pony-diffusion-xl-v6) |

> **注意**：模型由第三方提供，下载和使用请遵守 Civitai 平台规则及模型作者的使用条款。

### 3. 运行

双击 `start.bat` 启动程序（会自动检测并启动 Ollama 和 ComfyUI）。

---

## 使用指南

### 🎨 单图生成

1. 在「单图生成」Tab 输入中文描述
2. 点击 **GENERATE**
3. 左侧显示优化后的英文提示词，右侧显示生成的图片

### 📖 漫画工作室

1. **角色设定**：填写角色外貌（脸型、发型、眼睛颜色等固定特征）
2. **生成角色设定图**：点击「🎨 Generate Character Sheet」生成参考图
3. **分镜脚本**：每行写一个场景（动作/表情/服装/背景）
4. **参数调整**：
   - **Mode**：Action Free（动作自由）推荐用于故事漫画
   - **Style Preset**：Soft Moe 适合 pastel 萌系风格
   - **Consistency**：denoise 越低一致性越高
5. 点击 **🚀 GENERATE COMIC** 批量生成

---

## 项目结构

```
your-own-ai-image-gen/
├── ai_image_studio.py        # 主程序（双 Tab GUI）
├── workflows/
│   ├── txt2img_api.json       # 单图生成 workflow
│   └── img2img_api.json       # 漫画一致性 workflow
├── start.bat                  # Windows 启动脚本
├── README.md                  # 本文件
└── .gitignore
```

---

## 技术原理

**角色一致性（Action Free 模式）**：
- txt2img + 固定 Seed + 每帧注入完整角色描述
- 无需参考图，动作完全自由，脸部靠描述+seed保持一致

**角色一致性（Face Lock 模式）**：
- img2img + 参考图打底（VAE Encode）+ 固定 Seed
- 脸部最像，但姿势受参考图限制

---

## ⚠️ 再次提醒

**请在使用前再次确认您已阅读并同意上方的"重要法律声明与使用条款"。**

- 本工具仅用于**个人学习、艺术创作和学术研究**
- **严禁**用于生成、传播违法内容
- **严禁**侵犯他人知识产权和肖像权
- **使用者对自身行为承担全部法律责任**
- 开发者不对任何使用后果负责

**技术无罪，但使用有界。请做一个负责任的创作者。**

---

## 开源协议

本项目代码以 [MIT License](LICENSE) 开源。

> **MIT License 仅授予源代码的使用权限，不构成对任何违法行为的许可。所有使用者必须遵守当地法律法规。开发者保留追究违法使用者责任的权利。**

---

*本项目由 Eric-huang799 维护。如有技术问题，欢迎提交 Issue 讨论。*
