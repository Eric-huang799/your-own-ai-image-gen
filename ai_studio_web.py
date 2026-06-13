"""AI Image Studio Web — 移植原 tkinter 版到 Gradio 网页"""
import json, os, time, subprocess, urllib.request, glob, threading
import gradio as gr

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", ".openclaw", "workspace", "your-own-ai-image-gen", "config.json")
COMFY_URL = "http://127.0.0.1:8190"
OLLAMA_URL = "http://127.0.0.1:11434"
OUTPUT_DIR = os.path.expanduser("~/ComfyUI/output")
MODEL_DIR = os.path.expanduser("~/ComfyUI/models")

def load_config():
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except:
        return {
            "llm_provider": "ollama", "image_provider": "comfyui",
            "ollama": {"model": "wizardlm-uncensored-nosys"},
            "pollinations": {"model": "flux"},
            "comfyui": {"base_url": COMFY_URL},
            "generation": {"default_width": 1024, "default_height": 1024, "default_steps": 30}
        }

config = load_config()

def get_models():
    models = []
    for p in ["checkpoints/*.safetensors", "checkpoints/*.ckpt", "diffusion_models/*.safetensors"]:
        models.extend(glob.glob(os.path.join(MODEL_DIR, p)))
    return sorted([os.path.basename(m) for m in models]) or ["anima-base-v1.0.safetensors"]

# ============================================================
# LLM Prompt Optimizer (同 anima_webui 的两段式)
# ============================================================
def optimize_prompt(raw_prompt):
    """Two-step: Chinese→English, then Danbooru tags"""
    if not raw_prompt.strip():
        return raw_prompt

    # Step 1: Translate
    try:
        r1 = subprocess.run(
            ['ollama', 'run', config['ollama']['model'],
             f'Translate to English. Keep ALL details. Output ONLY English: {raw_prompt}'],
            capture_output=True, text=True, timeout=15, encoding='utf-8'
        )
        english = r1.stdout.strip()
        for pfx in ['English:', 'Translation:', 'Here is the translation:']:
            if english.lower().startswith(pfx.lower()):
                english = english[len(pfx):].strip()
        english = english.strip('"\'')
        if not english or len(english) < 3 or 'cannot' in english.lower():
            return raw_prompt
    except:
        return raw_prompt

    # Step 2: Danbooru tags
    tag_prompt = f"""Convert to Danbooru anime tags. Start 'masterpiece, best quality,'.
Include ALL details: hair, eyes, outfit, expression, pose, background, lighting.
Output ONLY tags:

Description: a cute young girl with twin tails, pink hair, blue eyes, wearing a frilly dress, winking
Tags: masterpiece, best quality, 1girl, cute, twin tails, pink hair, blue eyes, frilly dress, wink

Description: {english}
Tags:"""
    try:
        r2 = subprocess.run(
            ['ollama', 'run', config['ollama']['model'], tag_prompt],
            capture_output=True, text=True, timeout=15, encoding='utf-8'
        )
        tags = r2.stdout.strip().split('\n')[0]
        if tags.lower().startswith('tags:'): tags = tags[5:].strip()
        if ',' in tags and len(tags) > 20:
            return tags
        return english
    except:
        return english

# ============================================================
# ComfyUI Image Generation
# ============================================================
def comfyui_generate(model_name, prompt, neg_prompt, width, height, steps, cfg, seed):
    if seed == -1: seed = int(time.time() % 100000)

    if 'anima' in model_name.lower() and not model_name.endswith('.gguf'):
        workflow = {
            "1": {"class_type": "UNETLoader", "inputs": {"unet_name": model_name, "weight_dtype": "default"}},
            "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_3_06b_base.safetensors", "type": "cosmos"}},
            "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
            "4": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
            "5": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": neg_prompt, "clip": ["2", 0]}},
            "7": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": steps, "cfg": cfg, "sampler_name": "er_sde", "scheduler": "beta", "denoise": 1.0, "model": ["1", 0], "positive": ["5", 0], "negative": ["6", 0], "latent_image": ["4", 0]}},
            "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
            "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "AIStudio", "images": ["8", 0]}},
        }
    else:
        workflow = {
            "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": model_name}},
            "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
            "3": {"class_type": "CLIPTextEncode", "inputs": {"text": neg_prompt, "clip": ["1", 1]}},
            "4": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
            "5": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": steps, "cfg": cfg, "sampler_name": "er_sde", "scheduler": "beta", "denoise": 1.0, "model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0]}},
            "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
            "7": {"class_type": "SaveImage", "inputs": {"filename_prefix": "AIStudio", "images": ["6", 0]}},
        }

    data = json.dumps({"prompt": workflow}).encode()
    try:
        resp = json.loads(urllib.request.urlopen(
            urllib.request.Request(f"{COMFY_URL}/prompt", data=data, method="POST"),
            timeout=30).read())
        pid = resp['prompt_id']

        for _ in range(60):
            time.sleep(3)
            try:
                hist = json.loads(urllib.request.urlopen(f"{COMFY_URL}/history/{pid}", timeout=10).read())
                if pid in hist:
                    s = hist[pid].get('status', {})
                    if s.get('status_str') == 'error':
                        return None, f"生成失败"
                    for out in hist[pid]['outputs'].values():
                        if 'images' in out:
                            img = out['images'][0]
                            sf = img.get('subfolder', '')
                            parts = [OUTPUT_DIR] if not sf else [OUTPUT_DIR, sf]
                            parts.append(img['filename'])
                            path = os.path.join(*parts)
                            return path, f"✅ {img['filename']} | seed={seed}"
            except: pass
        return None, "⏰ 超时"
    except Exception as e:
        return None, f"❌ {str(e)[:100]}"

# ============================================================
# Pollinations.AI Image Generation (fast, no GPU needed)
# ============================================================
def pollinations_generate(prompt, neg_prompt, width, height, seed):
    if seed == -1: seed = int(time.time() % 100000)
    url = f"https://image.pollinations.ai/prompt/{urllib.request.quote(prompt)}?width={width}&height={height}&seed={seed}&nologo=true&model=flux"
    try:
        resp = urllib.request.urlopen(url, timeout=60)
        path = os.path.join(OUTPUT_DIR, f"Pollinations_{seed}.png")
        with open(path, 'wb') as f:
            f.write(resp.read())
        return path, f"✅ Pollinations | seed={seed}"
    except Exception as e:
        return None, f"❌ Pollinations: {str(e)[:100]}"

# ============================================================
# Main Generation (routes to ComfyUI or Pollinations)
# ============================================================
def generate_image(model_name, prompt, neg_prompt, width, height, steps, cfg, seed, provider, use_optimizer):
    if use_optimizer:
        prompt = optimize_prompt(prompt)

    if provider == "ComfyUI (本地)":
        return comfyui_generate(model_name, prompt, neg_prompt, width, height, steps, cfg, seed)
    elif provider == "Pollinations.AI (云端)":
        return pollinations_generate(prompt, neg_prompt, width, height, seed)
    else:
        return None, "未选择后端"

# ============================================================
# Comic Studio — multi-panel generation
# ============================================================
def comic_generate(script_text, model_name, width, height, steps, cfg, panels):
    """Generate multiple comic panels from a script"""
    results = []
    panel_prompts = []

    # Split script into panels
    lines = [l.strip() for l in script_text.split('\n') if l.strip()]
    n_panels = min(panels, len(lines))

    for i in range(n_panels):
        panel_prompt = f"comic panel, {lines[i]}, masterpiece, best quality"
        # Use ComfyUI for each panel
        img_path, status = comfyui_generate(model_name, panel_prompt,
                                            "worst quality, low quality, text, watermark",
                                            width, height, steps, cfg, int(time.time() % 100000))
        if img_path:
            results.append(img_path)
            panel_prompts.append(lines[i])
        else:
            results.append(None)

    return results, "\n".join(panel_prompts)

# ============================================================
# Service Check
# ============================================================
def check_services():
    status = []
    # ComfyUI
    try:
        urllib.request.urlopen(f"{COMFY_URL}/system_stats", timeout=2)
        status.append("🟢 ComfyUI")
    except:
        status.append("🔴 ComfyUI")
    # Ollama
    try:
        urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=2)
        status.append("🟢 Ollama")
    except:
        status.append("🔴 Ollama")
    # Pollinations
    try:
        urllib.request.urlopen("https://image.pollinations.ai/", timeout=3)
        status.append("🟢 Pollinations.AI")
    except:
        status.append("🟡 Pollinations.AI")
    return " | ".join(status)

# ================================================================
# Gradio UI
# ================================================================
models = get_models()
default_model = next((m for m in models if 'anima-base-v1.0.safetensors' in m), models[0])

with gr.Blocks(title="AI Image Studio Web", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🎨 AI Image Studio Web")
    gr.Markdown("移植自原版 tkinter GUI — 单图生成 + 漫画工作室 + 多后端支持")

    status_display = gr.Textbox(value=check_services(), label="服务状态", interactive=False)

    with gr.Tabs():
        # ── Tab 1: Single Image ──
        with gr.Tab("🎨 单图生成"):
            with gr.Row():
                with gr.Column(scale=1):
                    provider_r = gr.Radio(["ComfyUI (本地)", "Pollinations.AI (云端)"],
                                          value="ComfyUI (本地)", label="图像后端")
                    model_dd = gr.Dropdown(models, value=default_model, label="模型")
                    prompt_txt = gr.Textbox("masterpiece, best quality, 1girl, blue hair, smile, cherry blossoms",
                                            label="正向提示词", lines=4)
                    neg_txt = gr.Textbox("worst quality, low quality, bad anatomy, 3d, realistic",
                                         label="负向提示词", lines=2)
                    with gr.Row():
                        opt_btn = gr.Button("🪄 AI 优化", size="sm")
                        opt_check = gr.Checkbox(False, label="生成时自动优化", value=True)

                    with gr.Row():
                        w_sl = gr.Slider(256, 1536, 1024, step=64, label="宽度")
                        h_sl = gr.Slider(256, 1536, 1024, step=64, label="高度")
                    with gr.Row():
                        steps_sl = gr.Slider(10, 60, 30, step=1, label="步数")
                        cfg_sl = gr.Slider(1.0, 10.0, 5.0, step=0.5, label="CFG")
                    seed_num = gr.Number(-1, label="种子 (-1=随机)", precision=0)
                    gen_btn = gr.Button("🚀 生成", variant="primary", size="lg")

                with gr.Column(scale=1):
                    output_img = gr.Image(label="生成结果", type="filepath")
                    status_txt = gr.Textbox("就绪", label="状态", interactive=False)

            opt_btn.click(fn=optimize_prompt, inputs=[prompt_txt], outputs=[prompt_txt])
            gen_btn.click(fn=generate_image,
                         inputs=[model_dd, prompt_txt, neg_txt, w_sl, h_sl, steps_sl, cfg_sl, seed_num, provider_r, opt_check],
                         outputs=[output_img, status_txt])

        # ── Tab 2: Comic Studio ──
        with gr.Tab("📖 漫画工作室"):
            with gr.Row():
                with gr.Column(scale=1):
                    comic_script = gr.Textbox(
                        "1girl, school uniform, walking to school, cherry blossoms\n"
                        "1girl, sitting at desk, writing, classroom\n"
                        "1girl, eating lunch with friends, rooftop, sunshine\n"
                        "1girl, walking home, sunset, golden hour",
                        label="漫画脚本（每行一个分镜）", lines=8)
                    comic_model = gr.Dropdown(models, value=default_model, label="模型")
                    panels_sl = gr.Slider(1, 6, 4, step=1, label="分镜数")
                    comic_btn = gr.Button("🎬 生成漫画", variant="primary")

                with gr.Column(scale=2):
                    comic_gallery = gr.Gallery(label="漫画分镜", columns=4, height=400)
                    comic_status = gr.Textbox("输入脚本后点击生成", label="状态")

            comic_btn.click(fn=comic_generate,
                           inputs=[comic_script, comic_model, w_sl, h_sl, steps_sl, cfg_sl, panels_sl],
                           outputs=[comic_gallery, comic_status])

        # ── Tab 3: Settings ──
        with gr.Tab("⚙️ 设置"):
            gr.Markdown("### 服务配置")
            gr.Markdown(f"**ComfyUI**: {COMFY_URL}")
            gr.Markdown(f"**Ollama**: {OLLAMA_URL} | 模型: {config['ollama']['model']}")
            gr.Markdown(f"**输出目录**: {OUTPUT_DIR}")
            refresh_btn = gr.Button("🔄 刷新服务状态")
            refresh_btn.click(fn=check_services, outputs=[status_display])

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7862, share=False)
