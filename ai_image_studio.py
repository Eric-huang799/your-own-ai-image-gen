import subprocess
import json
import os
import sys
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from PIL import Image, ImageTk
import io
import re

from config_manager import load_config, save_config, DEFAULT_CONFIG
from providers import LLM_PROVIDERS, IMAGE_PROVIDERS, WanVideoProvider
from resource_limiter import engage_limits, restore_limits

# ── Paths ──────────────────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKFLOW_DIR = os.path.join(PROJECT_DIR, "workflows")
OUTPUT_DIR_DEFAULT = os.path.join(PROJECT_DIR, "output")
COMFYUI_START_BAT = os.path.expanduser("~/.openclaw/workspace/start_comfy_conda.bat")
CONDA_PYTHON = os.path.expanduser("~/.conda/envs/comfyui/python.exe")
COMFYUI_MAIN = os.path.expanduser("~/ComfyUI/main.py")
COMFYUI_INPUT_DIR = os.path.expanduser("~/ComfyUI/input")

os.makedirs(OUTPUT_DIR_DEFAULT, exist_ok=True)
os.makedirs(COMFYUI_INPUT_DIR, exist_ok=True)


class AIImageStudio:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Image Studio - MOSS Edition v3.0")
        self.root.geometry("1100x980")
        self.root.configure(bg="#1a1a2e")

        # ── Config & Providers ──
        self.config = load_config()
        self.llm = None
        self.image_provider = None
        self._init_providers()

        # ── State ──
        self.comic_generating = False
        self.reference_image_path = None
        self.thumbnails = []

        # ── Status Bar ──
        self.status_var = tk.StringVar(value="Initializing...")
        self.status_bar = tk.Label(
            root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN,
            anchor=tk.W, bg="#16213e", fg="#e94560")
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # ── Notebook ──
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tab_single = tk.Frame(self.notebook, bg="#1a1a2e")
        self.notebook.add(self.tab_single, text="🎨 单图生成")
        self.build_single_ui(self.tab_single)

        self.tab_comic = tk.Frame(self.notebook, bg="#1a1a2e")
        self.notebook.add(self.tab_comic, text="📖 漫画工作室")
        self.build_comic_ui(self.tab_comic)

        self.tab_video = tk.Frame(self.notebook, bg="#1a1a2e")
        self.notebook.add(self.tab_video, text="🎬 视频生成")
        self.build_video_ui(self.tab_video)

        self.tab_settings = tk.Frame(self.notebook, bg="#1a1a2e")
        self.notebook.add(self.tab_settings, text="⚙️ 设置")
        self.build_settings_ui(self.tab_settings)

        self.check_services()

    # ═══════════════════════════════════════════════
    #  Provider Management
    # ═══════════════════════════════════════════════

    def _init_providers(self):
        llm_name = self.config.get("llm_provider", "ollama")
        img_name = self.config.get("image_provider", "comfyui")

        if llm_name == "ollama":
            cfg = self.config.get("ollama", {})
            self.llm = LLM_PROVIDERS["ollama"](
                base_url=cfg.get("base_url", "http://127.0.0.1:11434"),
                model=cfg.get("model", "wizardlm-uncensored"),
            )
        elif llm_name == "openai":
            cfg = self.config.get("openai", {})
            self.llm = LLM_PROVIDERS["openai"](
                api_key=cfg.get("api_key", ""),
                model=cfg.get("model", "gpt-4o-mini"),
                base_url=cfg.get("base_url", "https://api.openai.com/v1"),
            )
        elif llm_name == "claude":
            cfg = self.config.get("claude", {})
            self.llm = LLM_PROVIDERS["claude"](
                api_key=cfg.get("api_key", ""),
                model=cfg.get("model", "claude-sonnet-4-6"),
                base_url=cfg.get("base_url", "https://api.anthropic.com/v1"),
            )
        elif llm_name == "deepseek":
            cfg = self.config.get("deepseek", {})
            self.llm = LLM_PROVIDERS["deepseek"](
                api_key=cfg.get("api_key", ""),
                model=cfg.get("model", "deepseek-chat"),
                base_url=cfg.get("base_url", "https://api.deepseek.com/v1"),
            )

        if img_name == "comfyui":
            cfg = self.config.get("comfyui", {})
            self.image_provider = IMAGE_PROVIDERS["comfyui"](
                base_url=cfg.get("base_url", "http://127.0.0.1:8188"),
                workflow_dir=WORKFLOW_DIR,
                output_dir=cfg.get("output_dir") or OUTPUT_DIR_DEFAULT,
            )
        elif img_name == "stability":
            cfg = self.config.get("stability", {})
            self.image_provider = IMAGE_PROVIDERS["stability"](
                api_key=cfg.get("api_key", ""),
                model=cfg.get("model", "stable-diffusion-xl-1024-v1-0"),
            )
        elif img_name == "siliconflow":
            cfg = self.config.get("siliconflow", {})
            self.image_provider = IMAGE_PROVIDERS["siliconflow"](
                api_key=cfg.get("api_key", ""),
                model=cfg.get("model", "stabilityai/stable-diffusion-3-5-large"),
            )

        # WanVideo is always available (uses same ComfyUI backend)
        cfg = self.config.get("comfyui", {})
        self.wanvideo = WanVideoProvider(
            base_url=cfg.get("base_url", "http://127.0.0.1:8188"),
            workflow_dir=WORKFLOW_DIR,
            output_dir=cfg.get("output_dir") or OUTPUT_DIR_DEFAULT,
        )

    def _reinit_providers(self):
        self._init_providers()
        self.check_services()

    # ═══════════════════════════════════════════════
    #  Service Check
    # ═══════════════════════════════════════════════

    def check_services(self):
        def check():
            llm_ok = self.llm.is_available() if self.llm else False
            img_ok = self.image_provider.is_available() if self.image_provider else False
            wan_ok = self.wanvideo.is_available() if self.wanvideo else False

            llm_label = self.llm.label if self.llm else "None"
            img_label = self.image_provider.label if self.image_provider else "None"

            color_ok = "#51cf66"
            color_fail = "#ff6b6b"
            color_warn = "#fcc419"

            llm_color = color_ok if llm_ok else color_fail
            img_color = color_ok if img_ok else color_warn
            wan_color = color_ok if wan_ok else color_warn

            llm_text = f"LLM [{llm_label}]: {'OK' if llm_ok else 'Not Available'}"
            img_text = f"Image [{img_label}]: {'OK' if img_ok else 'Not Available'}"
            wan_text = f"Wan2.1: {'OK' if wan_ok else 'Not Available'}"

            # Single/Comic tabs
            self.ollama_status.config(text=llm_text, fg=llm_color)
            self.ollama_status2.config(text=llm_text, fg=llm_color)
            self.comfy_status.config(text=img_text, fg=img_color)
            self.comfy_status2.config(text=img_text, fg=img_color)
            # Video tab
            self.video_llm_status.config(text=llm_text, fg=llm_color)
            self.video_wan_status.config(text=wan_text, fg=wan_color)

            self.status_var.set("Ready")

        threading.Thread(target=check, daemon=True).start()

    def start_ollama(self):
        self.status_var.set("Starting Ollama...")
        try:
            subprocess.Popen(["ollama", "serve"], creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot start Ollama: {e}")
        time.sleep(3)
        self.check_services()

    def start_comfyui(self):
        self.status_var.set("Starting ComfyUI...")
        try:
            if os.path.exists(COMFYUI_START_BAT):
                subprocess.Popen([COMFYUI_START_BAT], creationflags=subprocess.CREATE_NEW_CONSOLE)
            elif os.path.exists(CONDA_PYTHON) and os.path.exists(COMFYUI_MAIN):
                subprocess.Popen(
                    [CONDA_PYTHON, COMFYUI_MAIN, "--listen", "127.0.0.1", "--port", "8188"],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
            else:
                messagebox.showerror("Error", "Cannot find ComfyUI startup script")
                return
        except Exception as e:
            messagebox.showerror("Error", f"Cannot start ComfyUI: {e}")

        def wait():
            for i in range(60):
                time.sleep(2)
                self.status_var.set(f"Waiting for ComfyUI... ({i + 1}/60)")
                if self.image_provider and self.image_provider.is_available():
                    self.status_var.set("ComfyUI started")
                    self.check_services()
                    return
            self.status_var.set("ComfyUI startup timeout")

        threading.Thread(target=wait, daemon=True).start()

    # ═══════════════════════════════════════════════
    #  Prompt Helpers
    # ═══════════════════════════════════════════════

    def protect_character_colors(self, char_desc):
        colors = [
            "black", "brown", "blonde", "blond", "golden", "silver",
            "white", "red", "blue", "green", "purple", "pink", "gray",
            "grey", "auburn", "chestnut",
        ]
        protected = char_desc
        for color in colors:
            pattern = r"\b(" + color + r")\b(?!\s*\:)"
            protected = re.sub(pattern, r"(\1:1.3)", protected, flags=re.IGNORECASE)
        protected = re.sub(r"\((\([^)]+\:1\.3\)\:1\.3)\)", r"\1", protected)
        return protected

    def get_camera_variation(self, idx):
        variations = [
            "front view, medium shot, centered composition",
            "three-quarter view, medium close-up, slightly off-center",
            "side profile view, medium shot, rule of thirds composition",
            "from slightly above, medium shot, looking down angle",
            "from below, medium close-up, heroic angle",
            "dutch angle, medium shot, dynamic tilt",
            "over-the-shoulder shot, close-up on face",
            "wide shot, full body visible, environmental context",
        ]
        return variations[idx % len(variations)]

    # ═══════════════════════════════════════════════
    #  Image Display Helper
    # ═══════════════════════════════════════════════

    def show_image_in_label(self, img_data, label_widget, max_size=(450, 450)):
        try:
            img = Image.open(io.BytesIO(img_data))
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            label_widget.config(image=photo, text="")
            label_widget.image = photo
        except Exception as e:
            label_widget.config(text=f"[Display error: {e}]")

    # ═══════════════════════════════════════════════
    #  Tab 1: 单图生成
    # ═══════════════════════════════════════════════

    def build_single_ui(self, parent):
        main_frame = tk.Frame(parent, bg="#1a1a2e", padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text="AI Image Studio", font=("Microsoft YaHei", 24, "bold"),
                 bg="#1a1a2e", fg="#e94560").pack(pady=(0, 5))
        tk.Label(main_frame, text="Chinese Prompt -> LLM Optimize -> Image Generate",
                 font=("Microsoft YaHei", 11), bg="#1a1a2e", fg="#a0a0a0").pack(pady=(0, 15))

        # Service status
        svc_frame = tk.Frame(main_frame, bg="#16213e", bd=2, relief=tk.RIDGE, padx=15, pady=10)
        svc_frame.pack(fill=tk.X, pady=(0, 15))
        tk.Label(svc_frame, text="Service Status", font=("Microsoft YaHei", 12, "bold"),
                 bg="#16213e", fg="#fff").pack(anchor=tk.W)
        self.ollama_status = tk.Label(svc_frame, text="LLM: Checking...", bg="#16213e", fg="#ff6b6b")
        self.ollama_status.pack(anchor=tk.W, pady=2)
        self.comfy_status = tk.Label(svc_frame, text="Image: Checking...", bg="#16213e", fg="#ff6b6b")
        self.comfy_status.pack(anchor=tk.W, pady=2)

        btn_frame = tk.Frame(svc_frame, bg="#16213e")
        btn_frame.pack(anchor=tk.W, pady=5)
        tk.Button(btn_frame, text="Start Ollama", command=self.start_ollama,
                  bg="#0f3460", fg="#fff", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Start ComfyUI", command=self.start_comfyui,
                  bg="#0f3460", fg="#fff", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Refresh", command=self.check_services,
                  bg="#0f3460", fg="#fff", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=2)

        # Input
        input_frame = tk.LabelFrame(main_frame, text="Chinese Prompt",
                                     font=("Microsoft YaHei", 12, "bold"),
                                     bg="#1a1a2e", fg="#e94560", padx=10, pady=10)
        input_frame.pack(fill=tk.X, pady=(0, 15))
        self.prompt_input = scrolledtext.ScrolledText(
            input_frame, height=4, font=("Microsoft YaHei", 11),
            wrap=tk.WORD, bg="#16213e", fg="#fff", insertbackground="#fff")
        self.prompt_input.pack(fill=tk.X, pady=5)

        # Parameters
        param_frame = tk.Frame(input_frame, bg="#1a1a2e")
        param_frame.pack(fill=tk.X, pady=5)

        tk.Label(param_frame, text="Size:", bg="#1a1a2e", fg="#fff",
                 font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
        self.width_var = tk.StringVar(value=str(self.config["generation"]["default_width"]))
        tk.Spinbox(param_frame, from_=256, to=2048, increment=64, textvariable=self.width_var,
                   width=6, font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)
        tk.Label(param_frame, text="x", bg="#1a1a2e", fg="#fff").pack(side=tk.LEFT)
        self.height_var = tk.StringVar(value=str(self.config["generation"]["default_height"]))
        tk.Spinbox(param_frame, from_=256, to=2048, increment=64, textvariable=self.height_var,
                   width=6, font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)

        tk.Label(param_frame, text="  Steps:", bg="#1a1a2e", fg="#fff",
                 font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=(20, 0))
        self.steps_var = tk.StringVar(value=str(self.config["generation"]["default_steps"]))
        tk.Spinbox(param_frame, from_=10, to=50, increment=5, textvariable=self.steps_var,
                   width=5, font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)

        tk.Label(param_frame, text="  Model:", bg="#1a1a2e", fg="#fff",
                 font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=(20, 0))
        self.model_var = tk.StringVar(value=self.config["generation"]["default_model"])
        model_combo = ttk.Combobox(param_frame, textvariable=self.model_var,
                                    values=["dreamshaper_8.safetensors",
                                            "ponyDiffusionV6XL_v6.safetensors",
                                            "meinamix_v12Final.safetensors"],
                                    width=22, font=("Microsoft YaHei", 10))
        model_combo.pack(side=tk.LEFT, padx=5)

        # Generate button
        tk.Button(main_frame, text="GENERATE", command=self.generate,
                  bg="#e94560", fg="#fff", font=("Microsoft YaHei", 14, "bold"),
                  height=2).pack(fill=tk.X, pady=(0, 15))

        # Progress
        self.progress = ttk.Progressbar(main_frame, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=(0, 10))

        # Output
        out_frame = tk.Frame(main_frame, bg="#1a1a2e")
        out_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = tk.LabelFrame(out_frame, text="Optimized English Prompt",
                                    font=("Microsoft YaHei", 11, "bold"),
                                    bg="#1a1a2e", fg="#00d9ff", padx=5, pady=5)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        self.en_prompt = scrolledtext.ScrolledText(
            left_frame, height=8, font=("Consolas", 10), wrap=tk.WORD,
            bg="#16213e", fg="#00ff88", insertbackground="#fff")
        self.en_prompt.pack(fill=tk.BOTH, expand=True)

        right_frame = tk.LabelFrame(out_frame, text="Generated Image",
                                     font=("Microsoft YaHei", 11, "bold"),
                                     bg="#1a1a2e", fg="#e94560", padx=5, pady=5)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        self.img_label = tk.Label(right_frame, bg="#16213e", text="[Waiting...]", fg="#666")
        self.img_label.pack(fill=tk.BOTH, expand=True)

    # ═══════════════════════════════════════════════
    #  Tab 2: 漫画工作室
    # ═══════════════════════════════════════════════

    def build_comic_ui(self, parent):
        main_frame = tk.Frame(parent, bg="#1a1a2e", padx=15, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text="📖 Comic Studio", font=("Microsoft YaHei", 22, "bold"),
                 bg="#1a1a2e", fg="#e94560").pack(pady=(0, 5))
        tk.Label(main_frame, text="Character Consistency Story Generation",
                 font=("Microsoft YaHei", 11), bg="#1a1a2e", fg="#a0a0a0").pack(pady=(0, 10))

        # Service status bar
        svc_frame = tk.Frame(main_frame, bg="#16213e", bd=2, relief=tk.RIDGE, padx=15, pady=8)
        svc_frame.pack(fill=tk.X, pady=(0, 10))
        self.ollama_status2 = tk.Label(svc_frame, text="LLM: Checking...", bg="#16213e", fg="#ff6b6b")
        self.ollama_status2.pack(side=tk.LEFT, padx=10)
        self.comfy_status2 = tk.Label(svc_frame, text="Image: Checking...", bg="#16213e", fg="#ff6b6b")
        self.comfy_status2.pack(side=tk.LEFT, padx=10)
        tk.Button(svc_frame, text="Refresh", command=self.check_services,
                  bg="#0f3460", fg="#fff", font=("Microsoft YaHei", 9)).pack(side=tk.RIGHT, padx=5)

        content_frame = tk.Frame(main_frame, bg="#1a1a2e")
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Left panel
        left_panel = tk.Frame(content_frame, bg="#1a1a2e")
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # Character setup
        char_frame = tk.LabelFrame(left_panel, text="🎭 Character Setup",
                                    font=("Microsoft YaHei", 11, "bold"),
                                    bg="#1a1a2e", fg="#00d9ff", padx=10, pady=8)
        char_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(char_frame, text="Name:", bg="#1a1a2e", fg="#fff",
                 font=("Microsoft YaHei", 10)).pack(anchor=tk.W)
        self.char_name_var = tk.StringVar(value="Ling")
        tk.Entry(char_frame, textvariable=self.char_name_var, font=("Microsoft YaHei", 10),
                 bg="#16213e", fg="#fff", insertbackground="#fff").pack(fill=tk.X, pady=(0, 5))

        tk.Label(char_frame, text="Appearance (face, hair, body, skin - fixed features):",
                 bg="#1a1a2e", fg="#fff", font=("Microsoft YaHei", 10)).pack(anchor=tk.W)
        self.char_desc_input = scrolledtext.ScrolledText(
            char_frame, height=4, font=("Microsoft YaHei", 10), wrap=tk.WORD,
            bg="#16213e", fg="#fff", insertbackground="#fff")
        self.char_desc_input.pack(fill=tk.X, pady=5)

        char_btn_frame = tk.Frame(char_frame, bg="#1a1a2e")
        char_btn_frame.pack(fill=tk.X, pady=5)
        tk.Button(char_btn_frame, text="🎨 Generate Character Sheet",
                  command=self.generate_character_sheet, bg="#0f3460", fg="#fff",
                  font=("Microsoft YaHei", 10, "bold")).pack(side=tk.LEFT, padx=2)
        tk.Button(char_btn_frame, text="📁 Load Reference Image",
                  command=self.load_reference_image, bg="#0f3460", fg="#fff",
                  font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=2)

        # Storyboard script
        script_frame = tk.LabelFrame(left_panel, text="📝 Storyboard Script",
                                      font=("Microsoft YaHei", 11, "bold"),
                                      bg="#1a1a2e", fg="#00d9ff", padx=10, pady=8)
        script_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        tk.Label(script_frame, text="One scene per line (action/clothing/expression/background):",
                 bg="#1a1a2e", fg="#aaa", font=("Microsoft YaHei", 9)).pack(anchor=tk.W)
        self.script_input = scrolledtext.ScrolledText(
            script_frame, height=6, font=("Microsoft YaHei", 10), wrap=tk.WORD,
            bg="#16213e", fg="#fff", insertbackground="#fff")
        self.script_input.pack(fill=tk.BOTH, expand=True, pady=5)
        self.script_input.insert(tk.END, """smiling under cherry blossom tree, wearing pink floral dress
surprised looking out rainy window, wearing cozy sweater
running through autumn forest, wearing brown leather jacket
sitting at desk reading book, wearing glasses and school uniform""")

        # Generation settings
        param_frame = tk.LabelFrame(left_panel, text="⚙️ Generation Settings",
                                     font=("Microsoft YaHei", 11, "bold"),
                                     bg="#1a1a2e", fg="#00d9ff", padx=10, pady=8)
        param_frame.pack(fill=tk.X)

        p1 = tk.Frame(param_frame, bg="#1a1a2e")
        p1.pack(fill=tk.X, pady=2)
        tk.Label(p1, text="Size:", bg="#1a1a2e", fg="#fff",
                 font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
        self.c_width_var = tk.StringVar(value="1024")
        tk.Spinbox(p1, from_=256, to=2048, increment=64, textvariable=self.c_width_var,
                   width=6, font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)
        tk.Label(p1, text="x", bg="#1a1a2e", fg="#fff").pack(side=tk.LEFT)
        self.c_height_var = tk.StringVar(value="1024")
        tk.Spinbox(p1, from_=256, to=2048, increment=64, textvariable=self.c_height_var,
                   width=6, font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)
        tk.Label(p1, text="  Steps:", bg="#1a1a2e", fg="#fff",
                 font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=(20, 0))
        self.c_steps_var = tk.StringVar(value="25")
        tk.Spinbox(p1, from_=10, to=50, increment=5, textvariable=self.c_steps_var,
                   width=5, font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)
        tk.Label(p1, text="  Model:", bg="#1a1a2e", fg="#fff",
                 font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=(20, 0))
        self.c_model_var = tk.StringVar(value="meinamix_v12Final.safetensors")
        ttk.Combobox(p1, textvariable=self.c_model_var,
                     values=["meinamix_v12Final.safetensors",
                             "dreamshaper_8.safetensors",
                             "ponyDiffusionV6XL_v6.safetensors"],
                     width=22, font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)

        p2 = tk.Frame(param_frame, bg="#1a1a2e")
        p2.pack(fill=tk.X, pady=5)
        tk.Label(p2, text="Consistency:", bg="#1a1a2e", fg="#fff",
                 font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
        self.denoise_var = tk.DoubleVar(value=0.55)
        tk.Scale(p2, from_=0.35, to=0.75, resolution=0.05, orient=tk.HORIZONTAL,
                 variable=self.denoise_var, length=180, bg="#1a1a2e", fg="#fff",
                 highlightthickness=0).pack(side=tk.LEFT, padx=5)
        tk.Label(p2, text="(0.35=face almost identical, 0.55=balanced, 0.75=more creative)",
                 bg="#1a1a2e", fg="#888", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)

        p3 = tk.Frame(param_frame, bg="#1a1a2e")
        p3.pack(fill=tk.X, pady=2)
        tk.Label(p3, text="Seed:", bg="#1a1a2e", fg="#fff",
                 font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
        self.seed_mode_var = tk.StringVar(value="fixed")
        tk.Radiobutton(p3, text="Fixed (max consistency)", variable=self.seed_mode_var,
                       value="fixed", bg="#1a1a2e", fg="#fff", selectcolor="#16213e",
                       font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(p3, text="Series (varied poses)", variable=self.seed_mode_var,
                       value="series", bg="#1a1a2e", fg="#fff", selectcolor="#16213e",
                       font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=5)
        self.base_seed_var = tk.StringVar(value="123456")
        tk.Entry(p3, textvariable=self.base_seed_var, width=10,
                 font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)

        p4 = tk.Frame(param_frame, bg="#1a1a2e")
        p4.pack(fill=tk.X, pady=8)
        tk.Label(p4, text="Mode:", bg="#1a1a2e", fg="#fff",
                 font=("Microsoft YaHei", 10, "bold")).pack(side=tk.LEFT)
        self.mode_var = tk.StringVar(value="ipadapter")
        tk.Radiobutton(p4, text="🧠 IPAdapter (BEST consistency ✨)", variable=self.mode_var,
                       value="ipadapter", bg="#1a1a2e", fg="#00d9ff", selectcolor="#16213e",
                       font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(p4, text="🔒 Face Lock (img2img)", variable=self.mode_var,
                       value="face_lock", bg="#1a1a2e", fg="#fff", selectcolor="#16213e",
                       font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(p4, text="🎭 Action Free (txt2img)", variable=self.mode_var,
                       value="action_free", bg="#1a1a2e", fg="#888", selectcolor="#16213e",
                       font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=5)

        tk.Label(param_frame,
                 text="Tip: IPAdapter/Face Lock require ComfyUI. Cloud providers use Action Free only.",
                 bg="#1a1a2e", fg="#00d9ff", font=("Microsoft YaHei", 9)).pack(anchor=tk.W, pady=(5, 0))

        p5 = tk.Frame(param_frame, bg="#1a1a2e")
        p5.pack(fill=tk.X, pady=8)
        tk.Label(p5, text="Style Preset:", bg="#1a1a2e", fg="#fff",
                 font=("Microsoft YaHei", 10, "bold")).pack(side=tk.LEFT)
        self.style_preset_var = tk.StringVar(value="Default")
        ttk.Combobox(p5, textvariable=self.style_preset_var,
                     values=["Default", "Soft Moe (pastel/soft)",
                             "Dark Dramatic (dark/contrast)",
                             "Watercolor (paint/wash)"],
                     width=28, font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)

        # Right panel
        right_panel = tk.Frame(content_frame, bg="#1a1a2e", width=320)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right_panel.pack_propagate(False)

        ref_frame = tk.LabelFrame(right_panel, text="👤 Reference Image",
                                   font=("Microsoft YaHei", 11, "bold"),
                                   bg="#1a1a2e", fg="#e94560", padx=5, pady=5, height=220)
        ref_frame.pack(fill=tk.X, pady=(0, 10))
        ref_frame.pack_propagate(False)
        self.ref_img_label = tk.Label(ref_frame, bg="#16213e",
                                       text="[No reference image]", fg="#666")
        self.ref_img_label.pack(fill=tk.BOTH, expand=True)

        self.comic_gen_btn = tk.Button(right_panel, text="🚀 GENERATE COMIC",
                                        command=self.generate_comic_batch,
                                        bg="#e94560", fg="#fff",
                                        font=("Microsoft YaHei", 14, "bold"), height=2)
        self.comic_gen_btn.pack(fill=tk.X, pady=(0, 10))

        self.comic_progress = ttk.Progressbar(right_panel, mode="determinate")
        self.comic_progress.pack(fill=tk.X, pady=(0, 10))
        self.comic_status = tk.Label(right_panel, text="Ready", bg="#1a1a2e", fg="#aaa",
                                      font=("Microsoft YaHei", 10))
        self.comic_status.pack(anchor=tk.W, pady=(0, 5))

        thumb_frame = tk.LabelFrame(right_panel, text="Generated Panels",
                                     font=("Microsoft YaHei", 10, "bold"),
                                     bg="#1a1a2e", fg="#51cf66", padx=5, pady=5)
        thumb_frame.pack(fill=tk.BOTH, expand=True)

        thumb_canvas_frame = tk.Frame(thumb_frame, bg="#16213e")
        thumb_canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.thumb_canvas = tk.Canvas(thumb_canvas_frame, bg="#16213e", highlightthickness=0)
        self.thumb_scrollbar = tk.Scrollbar(thumb_canvas_frame, orient="vertical",
                                            command=self.thumb_canvas.yview)
        self.thumb_scrollable = tk.Frame(self.thumb_canvas, bg="#16213e")
        self.thumb_scrollable.bind(
            "<Configure>",
            lambda e: self.thumb_canvas.configure(
                scrollregion=self.thumb_canvas.bbox("all")))
        self.thumb_canvas.create_window((0, 0), window=self.thumb_scrollable, anchor="nw")
        self.thumb_canvas.configure(yscrollcommand=self.thumb_scrollbar.set)
        self.thumb_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.thumb_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # ═══════════════════════════════════════════════
    #  Tab 3: 设置
    # ═══════════════════════════════════════════════

    def build_settings_ui(self, parent):
        main_frame = tk.Frame(parent, bg="#1a1a2e", padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text="⚙️ Settings", font=("Microsoft YaHei", 20, "bold"),
                 bg="#1a1a2e", fg="#e94560").pack(pady=(0, 20))

        # ── LLM Provider Selection ──
        llm_frame = tk.LabelFrame(main_frame, text="LLM Provider (Prompt Optimization)",
                                   font=("Microsoft YaHei", 12, "bold"),
                                   bg="#1a1a2e", fg="#00d9ff", padx=15, pady=10)
        llm_frame.pack(fill=tk.X, pady=(0, 15))

        self.llm_provider_var = tk.StringVar(value=self.config.get("llm_provider", "ollama"))
        llm_sel = tk.Frame(llm_frame, bg="#1a1a2e")
        llm_sel.pack(fill=tk.X, pady=5)
        tk.Label(llm_sel, text="Provider:", bg="#1a1a2e", fg="#fff",
                 font=("Microsoft YaHei", 10), width=10, anchor=tk.W).pack(side=tk.LEFT)
        ttk.Combobox(llm_sel, textvariable=self.llm_provider_var,
                     values=["ollama", "openai", "claude", "deepseek"],
                     state="readonly", width=20, font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)
        tk.Button(llm_sel, text="Apply", command=self._apply_llm_provider,
                  bg="#0f3460", fg="#fff", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=10)

        # Ollama settings
        self.ollama_frame = tk.Frame(llm_frame, bg="#1a1a2e")
        self.ollama_frame.pack(fill=tk.X, pady=5)
        tk.Label(self.ollama_frame, text="URL:", bg="#1a1a2e", fg="#fff",
                 font=("Microsoft YaHei", 9), width=10, anchor=tk.W).pack(side=tk.LEFT)
        self.ollama_url_var = tk.StringVar(value=self.config["ollama"]["base_url"])
        tk.Entry(self.ollama_frame, textvariable=self.ollama_url_var, width=30,
                 font=("Microsoft YaHei", 9), bg="#16213e", fg="#fff").pack(side=tk.LEFT, padx=5)
        tk.Label(self.ollama_frame, text="Model:", bg="#1a1a2e", fg="#fff",
                 font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=(10, 0))
        self.ollama_model_var = tk.StringVar(value=self.config["ollama"]["model"])
        tk.Entry(self.ollama_frame, textvariable=self.ollama_model_var, width=20,
                 font=("Microsoft YaHei", 9), bg="#16213e", fg="#fff").pack(side=tk.LEFT, padx=5)

        # Cloud API settings
        self._api_key_vars = {}
        self._api_model_vars = {}
        self._api_url_vars = {}

        cloud_providers = [
            ("openai", "OpenAI", "gpt-4o-mini", True),
            ("claude", "Claude", "claude-sonnet-4-6", True),
            ("deepseek", "DeepSeek", "deepseek-chat", True),
        ]

        for name, label, default_model, show_url in cloud_providers:
            cfg = self.config.get(name, {})
            frm = tk.Frame(llm_frame, bg="#1a1a2e")
            frm.pack(fill=tk.X, pady=3)
            tk.Label(frm, text=f"{label}:", bg="#1a1a2e", fg="#fff",
                     font=("Microsoft YaHei", 9), width=10, anchor=tk.W).pack(side=tk.LEFT)

            kv = tk.StringVar(value=cfg.get("api_key", ""))
            self._api_key_vars[name] = kv
            tk.Entry(frm, textvariable=kv, width=35, show="*",
                     font=("Microsoft YaHei", 9), bg="#16213e", fg="#fff").pack(side=tk.LEFT, padx=5)

            tk.Label(frm, text="Model:", bg="#1a1a2e", fg="#fff",
                     font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=(10, 0))
            mv = tk.StringVar(value=cfg.get("model", default_model))
            self._api_model_vars[name] = mv
            tk.Entry(frm, textvariable=mv, width=18,
                     font=("Microsoft YaHei", 9), bg="#16213e", fg="#fff").pack(side=tk.LEFT, padx=5)

            if show_url:
                tk.Label(frm, text="URL:", bg="#1a1a2e", fg="#fff",
                         font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=(10, 0))
                uv = tk.StringVar(value=cfg.get("base_url", ""))
                self._api_url_vars[name] = uv
                tk.Entry(frm, textvariable=uv, width=28,
                         font=("Microsoft YaHei", 9), bg="#16213e", fg="#fff").pack(side=tk.LEFT, padx=5)

        # ── Image Provider Selection ──
        img_frame = tk.LabelFrame(main_frame, text="Image Generation Provider",
                                   font=("Microsoft YaHei", 12, "bold"),
                                   bg="#1a1a2e", fg="#00d9ff", padx=15, pady=10)
        img_frame.pack(fill=tk.X, pady=(0, 15))

        self.img_provider_var = tk.StringVar(value=self.config.get("image_provider", "comfyui"))
        img_sel = tk.Frame(img_frame, bg="#1a1a2e")
        img_sel.pack(fill=tk.X, pady=5)
        tk.Label(img_sel, text="Provider:", bg="#1a1a2e", fg="#fff",
                 font=("Microsoft YaHei", 10), width=10, anchor=tk.W).pack(side=tk.LEFT)
        ttk.Combobox(img_sel, textvariable=self.img_provider_var,
                     values=["comfyui", "stability", "siliconflow"],
                     state="readonly", width=20, font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)
        tk.Button(img_sel, text="Apply", command=self._apply_img_provider,
                  bg="#0f3460", fg="#fff", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=10)

        # Stability AI
        stab_frame = tk.Frame(img_frame, bg="#1a1a2e")
        stab_frame.pack(fill=tk.X, pady=3)
        tk.Label(stab_frame, text="Stability AI:", bg="#1a1a2e", fg="#fff",
                 font=("Microsoft YaHei", 9), width=10, anchor=tk.W).pack(side=tk.LEFT)
        self.stability_key_var = tk.StringVar(value=self.config["stability"]["api_key"])
        tk.Entry(stab_frame, textvariable=self.stability_key_var, width=35, show="*",
                 font=("Microsoft YaHei", 9), bg="#16213e", fg="#fff").pack(side=tk.LEFT, padx=5)

        # SiliconFlow
        sf_frame = tk.Frame(img_frame, bg="#1a1a2e")
        sf_frame.pack(fill=tk.X, pady=3)
        tk.Label(sf_frame, text="SiliconFlow:", bg="#1a1a2e", fg="#fff",
                 font=("Microsoft YaHei", 9), width=10, anchor=tk.W).pack(side=tk.LEFT)
        self.sf_key_var = tk.StringVar(value=self.config["siliconflow"]["api_key"])
        tk.Entry(sf_frame, textvariable=self.sf_key_var, width=35, show="*",
                 font=("Microsoft YaHei", 9), bg="#16213e", fg="#fff").pack(side=tk.LEFT, padx=5)
        tk.Label(sf_frame, text="Model:", bg="#1a1a2e", fg="#fff",
                 font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=(10, 0))
        self.sf_model_var = tk.StringVar(value=self.config["siliconflow"]["model"])
        tk.Entry(sf_frame, textvariable=self.sf_model_var, width=28,
                 font=("Microsoft YaHei", 9), bg="#16213e", fg="#fff").pack(side=tk.LEFT, padx=5)

        # ── Save / Reset ──
        btn_frame = tk.Frame(main_frame, bg="#1a1a2e")
        btn_frame.pack(fill=tk.X, pady=(20, 0))
        tk.Button(btn_frame, text="💾 Save All Settings", command=self._save_all_settings,
                  bg="#e94560", fg="#fff", font=("Microsoft YaHei", 12, "bold"),
                  height=2).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="🔄 Reset to Defaults", command=self._reset_settings,
                  bg="#0f3460", fg="#fff", font=("Microsoft YaHei", 10),
                  height=2).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="🔁 Reload Providers", command=self._reinit_providers,
                  bg="#0f3460", fg="#fff", font=("Microsoft YaHei", 10),
                  height=2).pack(side=tk.RIGHT, padx=5)

        # Status
        self.settings_status = tk.Label(main_frame, text="", bg="#1a1a2e", fg="#51cf66",
                                         font=("Microsoft YaHei", 10))
        self.settings_status.pack(pady=(15, 0))

    def _apply_llm_provider(self):
        self.config["llm_provider"] = self.llm_provider_var.get()
        self._reinit_providers()
        self.settings_status.config(text=f"LLM switched to: {self.llm.label}", fg="#51cf66")

    def _apply_img_provider(self):
        self.config["image_provider"] = self.img_provider_var.get()
        self._reinit_providers()
        self.settings_status.config(
            text=f"Image provider switched to: {self.image_provider.label}", fg="#51cf66")

    def _save_all_settings(self):
        self.config["llm_provider"] = self.llm_provider_var.get()
        self.config["image_provider"] = self.img_provider_var.get()

        self.config["ollama"]["base_url"] = self.ollama_url_var.get()
        self.config["ollama"]["model"] = self.ollama_model_var.get()

        for name in ["openai", "claude", "deepseek"]:
            if name in self._api_key_vars:
                self.config[name]["api_key"] = self._api_key_vars[name].get()
            if name in self._api_model_vars:
                self.config[name]["model"] = self._api_model_vars[name].get()
            if name in self._api_url_vars:
                self.config[name]["base_url"] = self._api_url_vars[name].get()

        self.config["stability"]["api_key"] = self.stability_key_var.get()
        self.config["siliconflow"]["api_key"] = self.sf_key_var.get()
        self.config["siliconflow"]["model"] = self.sf_model_var.get()

        save_config(self.config)
        self._reinit_providers()
        self.settings_status.config(text="✅ Settings saved and providers reloaded!", fg="#51cf66")

    def _reset_settings(self):
        if messagebox.askyesno("Reset", "Reset all settings to defaults?"):
            from config_manager import CONFIG_PATH as CP
            self.config = DEFAULT_CONFIG.copy()
            try:
                os.remove(CP)
            except Exception:
                pass
            self._reinit_providers()
            self.notebook.forget(self.tab_settings)
            self.tab_settings = tk.Frame(self.notebook, bg="#1a1a2e")
            self.notebook.add(self.tab_settings, text="⚙️ 设置")
            self.build_settings_ui(self.tab_settings)
            self.settings_status = tk.Label(self.tab_settings, text="", bg="#1a1a2e", fg="#51cf66",
                                             font=("Microsoft YaHei", 10))
            self.settings_status.pack(pady=(15, 0))
            self.settings_status.config(text="Settings reset to defaults", fg="#fcc419")

    # ═══════════════════════════════════════════════
    #  Single Image Generation
    # ═══════════════════════════════════════════════

    def generate(self):
        chinese = self.prompt_input.get("1.0", tk.END).strip()
        if not chinese:
            messagebox.showwarning("Tip", "Please enter a Chinese prompt")
            return
        if not self.llm or not self.llm.is_available():
            messagebox.showwarning("Tip", "LLM provider is not available. Check settings.")
            return
        if not self.image_provider or not self.image_provider.is_available():
            messagebox.showwarning("Tip", "Image provider is not available. Check settings.")
            return

        self.progress.start()
        self.status_var.set("Optimizing prompt...")
        self.root.update()

        def run():
            freed = engage_limits()
            try:
                en_prompt = self.llm.optimize_single(chinese)
                self.en_prompt.delete("1.0", tk.END)
                self.en_prompt.insert(tk.END, en_prompt)
                self.status_var.set(f"Optimized: {en_prompt[:80]}...")

                width = int(self.width_var.get())
                height = int(self.height_var.get())
                steps = int(self.steps_var.get())
                model_name = self.model_var.get()

                self.status_var.set("Generating image...")
                result = self.image_provider.generate(
                    prompt=en_prompt,
                    negative_prompt="blurry, low quality, distorted, bad anatomy, watermark",
                    width=width, height=height, steps=steps,
                    model_name=model_name,
                    workflow="txt2img",
                )

                save_path = result.save_path or os.path.join(
                    OUTPUT_DIR_DEFAULT, result.filename)
                with open(save_path, "wb") as f:
                    f.write(result.image_data)

                self.show_image_in_label(result.image_data, self.img_label)
                self.img_label.bind("<Button-1>", lambda e: os.startfile(save_path))
                self.img_label.config(cursor="hand2")
                self.status_var.set(f"Done! Saved: {save_path}")

            except Exception as e:
                self.status_var.set(f"Error: {e}")
                messagebox.showerror("Generation Failed", str(e))
            finally:
                restore_limits()
                self.progress.stop()

        threading.Thread(target=run, daemon=True).start()

    # ═══════════════════════════════════════════════
    #  Comic Studio
    # ═══════════════════════════════════════════════

    def load_reference_image(self):
        path = filedialog.askopenfilename(
            title="Select Reference Image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.webp"), ("All files", "*.*")])
        if path:
            self.set_reference_image(path)

    def set_reference_image(self, path):
        self.reference_image_path = path
        try:
            img = Image.open(path)
            img.thumbnail((280, 280), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.ref_img_label.config(image=photo, text="")
            self.ref_img_label.image = photo
            self.comic_status.config(text=f"Reference: {os.path.basename(path)}", fg="#51cf66")
        except Exception as e:
            self.comic_status.config(text=f"Failed to load: {e}", fg="#ff6b6b")

    def generate_character_sheet(self):
        if not self.image_provider or not self.image_provider.is_available():
            messagebox.showwarning("Tip", "Image provider is not available")
            return
        if not self.llm or not self.llm.is_available():
            messagebox.showwarning("Tip", "LLM provider is not available")
            return

        char_name = self.char_name_var.get().strip()
        char_desc = self.char_desc_input.get("1.0", tk.END).strip()
        if not char_desc:
            messagebox.showwarning("Tip", "Please enter character appearance description")
            return

        self.comic_gen_btn.config(state=tk.DISABLED)
        self.comic_status.config(text="Generating character sheet...", fg="#e94560")
        self.root.update()

        def run():
            try:
                sheet_prompt = (
                    f"{char_desc}, standing pose, front view, neutral expression, "
                    f"full body, simple clean background, character design reference sheet, "
                    f"clear face details, masterpiece, best quality, highly detailed, "
                    f"professional lighting, 8k uhd"
                )
                en_prompt = self.llm.optimize_single(sheet_prompt)

                width = int(self.c_width_var.get())
                height = int(self.c_height_var.get())
                steps = int(self.c_steps_var.get())
                model_name = self.c_model_var.get()
                seed = int(self.base_seed_var.get())

                result = self.image_provider.generate(
                    prompt=en_prompt,
                    negative_prompt="blurry, low quality, distorted, bad anatomy",
                    width=width, height=height, steps=steps,
                    seed=seed, model_name=model_name, workflow="txt2img",
                )

                save_path = result.save_path or os.path.join(
                    OUTPUT_DIR_DEFAULT, f"{char_name}_reference_{result.filename}")
                with open(save_path, "wb") as f:
                    f.write(result.image_data)

                ref_path = os.path.join(COMFYUI_INPUT_DIR, "reference.png")
                try:
                    with open(ref_path, "wb") as f:
                        f.write(result.image_data)
                except Exception:
                    pass

                self.set_reference_image(save_path)
                self.comic_status.config(text=f"Character sheet saved: {save_path}", fg="#51cf66")

            except Exception as e:
                self.comic_status.config(text=f"Error: {e}", fg="#ff6b6b")
                messagebox.showerror("Character Sheet Failed", str(e))
            finally:
                self.comic_gen_btn.config(state=tk.NORMAL)

        threading.Thread(target=run, daemon=True).start()

    def generate_comic_batch(self):
        if self.comic_generating:
            messagebox.showwarning("Tip", "Generation in progress")
            return

        script_text = self.script_input.get("1.0", tk.END).strip()
        if not script_text:
            messagebox.showwarning("Tip", "Please enter storyboard script")
            return

        scenes = [line.strip() for line in script_text.split("\n") if line.strip()]
        if not scenes:
            messagebox.showwarning("Tip", "No valid scenes found")
            return

        if not self.image_provider or not self.image_provider.is_available():
            messagebox.showwarning("Tip", "Image provider is not available")
            return

        mode = self.mode_var.get()
        use_ipadapter = (mode == "ipadapter")
        use_reference = (mode == "face_lock")
        is_cloud = self.config["image_provider"] != "comfyui"

        if is_cloud and (use_ipadapter or use_reference):
            messagebox.showwarning(
                "Cloud Mode",
                "IPAdapter and Face Lock require ComfyUI (local).\n"
                "Switching to Action Free mode for cloud generation.")
            use_ipadapter = False
            use_reference = False

        if use_reference or use_ipadapter:
            if not self.reference_image_path or not os.path.exists(self.reference_image_path):
                auto_ref = os.path.join(COMFYUI_INPUT_DIR, "reference.png")
                if os.path.exists(auto_ref):
                    self.reference_image_path = auto_ref
                else:
                    messagebox.showwarning(
                        "Tip", "No reference image. Generate a character sheet first.")
                    return

        char_desc = self.char_desc_input.get("1.0", tk.END).strip()
        char_name = self.char_name_var.get().strip()
        llm_ok = self.llm and self.llm.is_available()

        self.comic_generating = True
        self.comic_gen_btn.config(state=tk.DISABLED, text="Generating...")
        self.comic_progress["maximum"] = len(scenes)
        self.comic_progress["value"] = 0

        mode_text = "IPAdapter" if use_ipadapter else ("Face Lock" if use_reference else "Action Free")
        self.comic_status.config(
            text=f"Mode: {mode_text} | Preparing {len(scenes)} panels...", fg="#e94560")

        for widget in self.thumb_scrollable.winfo_children():
            widget.destroy()
        self.thumbnails.clear()

        def run():
            engage_limits()
            try:
                width = int(self.c_width_var.get())
                height = int(self.c_height_var.get())
                steps = int(self.c_steps_var.get())
                model_name = self.c_model_var.get()
                denoise = float(self.denoise_var.get())
                seed_mode = self.seed_mode_var.get()
                base_seed = int(self.base_seed_var.get())

                ref_name = None
                if (use_reference or use_ipadapter) and not is_cloud:
                    if hasattr(self.image_provider, "upload_image"):
                        ref_name = self.image_provider.upload_image(self.reference_image_path)

                generated_files = []

                for idx, scene in enumerate(scenes):
                    self.comic_status.config(
                        text=f"Mode: {mode_text} | Panel {idx + 1}/{len(scenes)}...")
                    self.root.update()

                    style = self.style_preset_var.get()
                    style_pos = ""
                    style_neg_add = ""
                    if style == "Soft Moe (pastel/soft)":
                        style_pos = (
                            "meinamix, pastel colors, soft lighting, muted tones, "
                            "low contrast, kawaii, moe, gentle shading, fluffy atmosphere, "
                            "dreamy, airy, soft focus, warm ambient light, delicate details, "
                            "beautiful detailed eyes, detailed face, anime style, ")
                        style_neg_add = (
                            ", harsh shadows, high contrast, dramatic lighting, "
                            "sharp edges, dark colors, gritty, cinematic, heavy shadows, "
                            "realistic, 3d, western, ugly, bad anatomy")
                    elif style == "Dark Dramatic (dark/contrast)":
                        style_pos = (
                            "dark atmosphere, dramatic lighting, high contrast, "
                            "deep shadows, cinematic, moody, intense colors, ")
                        style_neg_add = ", pastel, soft lighting, low contrast, fluffy, cute, bright colors"
                    elif style == "Watercolor (paint/wash)":
                        style_pos = (
                            "watercolor painting, soft wash, bleeding colors, painterly, "
                            "artistic, traditional media, paper texture, loose brushwork, ")
                        style_neg_add = ", photorealistic, 3d render, sharp edges, digital art, clean lines"

                    camera_var = self.get_camera_variation(idx)
                    protected_char = self.protect_character_colors(char_desc)

                    en_prompt = (
                        f"{style_pos}(solo:1.4), (1 person:1.3), {protected_char}, "
                        f"{scene}, {camera_var}, masterpiece, best quality, highly detailed, "
                        f"professional lighting, 8k uhd"
                    )

                    if llm_ok:
                        try:
                            en_prompt = self.llm.optimize_comic(scene, protected_char)
                            camera_var = self.get_camera_variation(idx)
                            if ("(solo:" not in en_prompt.lower()
                                    and "(1 person:" not in en_prompt.lower()
                                    and "solo" not in en_prompt.lower()):
                                en_prompt = f"(solo:1.4), (1 person:1.3), {en_prompt}, {camera_var}"
                            else:
                                if camera_var not in en_prompt:
                                    en_prompt = f"{en_prompt}, {camera_var}"
                        except Exception:
                            pass

                    current_seed = base_seed if seed_mode == "fixed" else base_seed + idx

                    neg = (
                        "blurry, low quality, distorted, bad anatomy, watermark, "
                        "mutated face, wrong face, different person, extra limbs, "
                        "multiple characters, group, crowd, extra person, duplicate, "
                        "wrong hair color, wrong eye color, mismatched colors")
                    if use_reference:
                        neg += (", same pose, identical pose, static posture, unchanged stance")
                    neg += style_neg_add

                    if use_ipadapter and not is_cloud:
                        result = self.image_provider.generate(
                            prompt=en_prompt, negative_prompt=neg,
                            width=width, height=height, steps=steps,
                            seed=current_seed, model_name=model_name,
                            workflow="ipadapter", ref_image_name=ref_name,
                        )
                    elif use_reference and not is_cloud:
                        result = self.image_provider.generate(
                            prompt=en_prompt, negative_prompt=neg,
                            width=width, height=height, steps=steps,
                            seed=current_seed, model_name=model_name,
                            workflow="img2img", ref_image_name=ref_name,
                            denoise=denoise, use_img2img=True,
                        )
                    else:
                        result = self.image_provider.generate(
                            prompt=en_prompt, negative_prompt=neg,
                            width=width, height=height, steps=steps,
                            seed=current_seed, model_name=model_name,
                            workflow="txt2img",
                        )

                    panel_name = f"{char_name}_panel_{idx + 1:03d}_{result.filename}"
                    save_path = result.save_path or os.path.join(OUTPUT_DIR_DEFAULT, panel_name)
                    with open(save_path, "wb") as f:
                        f.write(result.image_data)
                    generated_files.append(save_path)

                    self.root.after(0, lambda p=save_path, n=idx + 1: self.add_thumbnail(p, n))
                    self.root.after(0, lambda v=idx + 1: self.comic_progress.config(value=v))

                self.comic_status.config(
                    text=f"Done! {len(generated_files)} panels | Mode: {mode_text}",
                    fg="#51cf66")

            except Exception as e:
                self.comic_status.config(text=f"Error: {e}", fg="#ff6b6b")
                messagebox.showerror("Comic Generation Failed", str(e))
            finally:
                restore_limits()
                self.comic_generating = False
                self.comic_gen_btn.config(state=tk.NORMAL, text="🚀 GENERATE COMIC")

    def add_thumbnail(self, img_path, panel_num):
        try:
            img = Image.open(img_path)
            img.thumbnail((130, 130), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)

            frame = tk.Frame(self.thumb_scrollable, bg="#16213e", bd=2, relief=tk.RIDGE)
            frame.pack(fill=tk.X, padx=5, pady=5)

            inner = tk.Frame(frame, bg="#16213e")
            inner.pack(fill=tk.X, padx=3, pady=3)

            lbl = tk.Label(inner, image=photo, bg="#16213e")
            lbl.image = photo
            lbl.pack(side=tk.LEFT)

            tk.Label(inner, text=f"#{panel_num}", bg="#16213e", fg="#fff",
                     font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=8, pady=5)

            def open_img(event, p=img_path):
                os.startfile(p)

            lbl.bind("<Button-1>", open_img)
            lbl.config(cursor="hand2")

            self.thumbnails.append((frame, photo))
            self.thumb_canvas.update_idletasks()
            self.thumb_canvas.yview_moveto(1.0)
        except Exception as e:
            print(f"Thumbnail error: {e}")


    # ═══════════════════════════════════════════════
    #  Tab 4: 视频生成
    # ═══════════════════════════════════════════════

    def build_video_ui(self, parent):
        main_frame = tk.Frame(parent, bg="#1a1a2e", padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text="🎬 AI Video Studio", font=("Microsoft YaHei", 22, "bold"),
                 bg="#1a1a2e", fg="#e94560").pack(pady=(0, 5))
        tk.Label(main_frame, text="Chinese Prompt → LLM Optimize → Wan2.1 Video Generate",
                 font=("Microsoft YaHei", 11), bg="#1a1a2e", fg="#a0a0a0").pack(pady=(0, 15))

        # Service status
        svc_frame = tk.Frame(main_frame, bg="#16213e", bd=2, relief=tk.RIDGE, padx=15, pady=10)
        svc_frame.pack(fill=tk.X, pady=(0, 15))
        tk.Label(svc_frame, text="Service Status", font=("Microsoft YaHei", 12, "bold"),
                 bg="#16213e", fg="#fff").pack(anchor=tk.W)
        self.video_llm_status = tk.Label(svc_frame, text="LLM: Checking...", bg="#16213e", fg="#ff6b6b")
        self.video_llm_status.pack(anchor=tk.W, pady=2)
        self.video_wan_status = tk.Label(svc_frame, text="Wan2.1: Checking...", bg="#16213e", fg="#ff6b6b")
        self.video_wan_status.pack(anchor=tk.W, pady=2)

        btn_frame = tk.Frame(svc_frame, bg="#16213e")
        btn_frame.pack(anchor=tk.W, pady=5)
        tk.Button(btn_frame, text="Start ComfyUI", command=self.start_comfyui,
                  bg="#0f3460", fg="#fff", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Refresh", command=self._check_video_services,
                  bg="#0f3460", fg="#fff", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=2)

        # Input
        input_frame = tk.LabelFrame(main_frame, text="Chinese Prompt",
                                     font=("Microsoft YaHei", 12, "bold"),
                                     bg="#1a1a2e", fg="#e94560", padx=10, pady=10)
        input_frame.pack(fill=tk.X, pady=(0, 15))
        self.video_prompt_input = scrolledtext.ScrolledText(
            input_frame, height=4, font=("Microsoft YaHei", 11),
            wrap=tk.WORD, bg="#16213e", fg="#fff", insertbackground="#fff")
        self.video_prompt_input.pack(fill=tk.X, pady=5)

        # Parameters
        param_frame = tk.Frame(input_frame, bg="#1a1a2e")
        param_frame.pack(fill=tk.X, pady=5)

        tk.Label(param_frame, text="Size:", bg="#1a1a2e", fg="#fff",
                 font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
        self.v_width_var = tk.StringVar(value="832")
        tk.Spinbox(param_frame, from_=480, to=1280, increment=32, textvariable=self.v_width_var,
                   width=6, font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)
        tk.Label(param_frame, text="x", bg="#1a1a2e", fg="#fff").pack(side=tk.LEFT)
        self.v_height_var = tk.StringVar(value="480")
        tk.Spinbox(param_frame, from_=480, to=720, increment=32, textvariable=self.v_height_var,
                   width=6, font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)

        tk.Label(param_frame, text="  Frames:", bg="#1a1a2e", fg="#fff",
                 font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=(20, 0))
        self.v_frames_var = tk.StringVar(value="81")
        tk.Spinbox(param_frame, from_=33, to=121, increment=8, textvariable=self.v_frames_var,
                   width=5, font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)

        tk.Label(param_frame, text="  Steps:", bg="#1a1a2e", fg="#fff",
                 font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=(20, 0))
        self.v_steps_var = tk.StringVar(value="20")
        tk.Spinbox(param_frame, from_=10, to=50, increment=5, textvariable=self.v_steps_var,
                   width=5, font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)

        tk.Label(param_frame, text="  CFG:", bg="#1a1a2e", fg="#fff",
                 font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=(20, 0))
        self.v_cfg_var = tk.StringVar(value="5.0")
        tk.Spinbox(param_frame, from_=1.0, to=10.0, increment=0.5, textvariable=self.v_cfg_var,
                   width=5, font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)

        tk.Label(param_frame, text="  FPS:", bg="#1a1a2e", fg="#fff",
                 font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=(20, 0))
        self.v_fps_var = tk.StringVar(value="16")
        tk.Spinbox(param_frame, from_=8, to=30, increment=2, textvariable=self.v_fps_var,
                   width=5, font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)

        # Generate button
        tk.Button(main_frame, text="🎬 GENERATE VIDEO", command=self.generate_video,
                  bg="#e94560", fg="#fff", font=("Microsoft YaHei", 14, "bold"),
                  height=2).pack(fill=tk.X, pady=(0, 15))

        # Progress
        self.video_progress = ttk.Progressbar(main_frame, mode="indeterminate")
        self.video_progress.pack(fill=tk.X, pady=(0, 10))

        # Output
        out_frame = tk.Frame(main_frame, bg="#1a1a2e")
        out_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = tk.LabelFrame(out_frame, text="Optimized English Prompt",
                                    font=("Microsoft YaHei", 11, "bold"),
                                    bg="#1a1a2e", fg="#00d9ff", padx=5, pady=5)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        self.video_en_prompt = scrolledtext.ScrolledText(
            left_frame, height=8, font=("Consolas", 10), wrap=tk.WORD,
            bg="#16213e", fg="#00ff88", insertbackground="#fff")
        self.video_en_prompt.pack(fill=tk.BOTH, expand=True)

        right_frame = tk.LabelFrame(out_frame, text="Generated Video",
                                     font=("Microsoft YaHei", 11, "bold"),
                                     bg="#1a1a2e", fg="#e94560", padx=5, pady=5)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        self.video_status_label = tk.Label(right_frame, bg="#16213e",
                                            text="[Waiting...]\n\nWan2.1 T2V 14B\nVideo generation takes 5-15 minutes",
                                            fg="#666", font=("Microsoft YaHei", 11))
        self.video_status_label.pack(fill=tk.BOTH, expand=True)

    def _check_video_services(self):
        def check():
            llm_ok = self.llm.is_available() if self.llm else False
            wan_ok = self.wanvideo.is_available() if self.wanvideo else False

            llm_label = self.llm.label if self.llm else "None"
            llm_color = "#51cf66" if llm_ok else "#ff6b6b"
            wan_color = "#51cf66" if wan_ok else "#fcc419"

            self.video_llm_status.config(
                text=f"LLM [{llm_label}]: {'OK' if llm_ok else 'Not Available'}",
                fg=llm_color)
            self.video_wan_status.config(
                text=f"Wan2.1: {'OK' if wan_ok else 'Not Available (start ComfyUI)'}",
                fg=wan_color)
            self.status_var.set("Ready")

        threading.Thread(target=check, daemon=True).start()

    def generate_video(self):
        chinese = self.video_prompt_input.get("1.0", tk.END).strip()
        if not chinese:
            messagebox.showwarning("Tip", "Please enter a Chinese prompt")
            return
        if not self.llm or not self.llm.is_available():
            messagebox.showwarning("Tip", "LLM provider is not available")
            return
        if not self.wanvideo or not self.wanvideo.is_available():
            messagebox.showwarning("Tip", "Wan2.1 is not available. Start ComfyUI first.")
            return

        self.video_progress.start()
        self.video_status_label.config(text="Optimizing prompt...", fg="#e94560")
        self.status_var.set("Generating video...")
        self.root.update()

        def run():
            freed = engage_limits()
            try:
                # Video-specific prompt optimization
                video_system = f"""You are an expert AI video generation prompt engineer. Convert Chinese to a detailed English video prompt.

Rules:
1. Translate accurately and vividly
2. Describe MOTION specifically: camera movement, subject action, scene dynamics
3. Add video quality tags: cinematic, smooth motion, 4K, high frame rate
4. Describe lighting, atmosphere, visual style
5. Output ONLY the English prompt, nothing else
6. Keep under 200 tokens for best results

Chinese description: {chinese}

English video prompt:"""

                if hasattr(self.llm, '_build_single_prompt'):
                    en_prompt = self.llm.optimize_single(
                        f"视频：{chinese}。请描述动态画面、镜头运动、光影变化。")
                else:
                    en_prompt = f"{chinese}, cinematic, smooth camera motion, high quality, 4K, detailed lighting, dynamic scene"

                self.video_en_prompt.delete("1.0", tk.END)
                self.video_en_prompt.insert(tk.END, en_prompt)
                self.video_status_label.config(
                    text=f"Generating video...\nThis may take 5-15 minutes\n\n{en_prompt[:100]}...",
                    fg="#e94560")
                self.root.update()

                width = int(self.v_width_var.get())
                height = int(self.v_height_var.get())
                num_frames = int(self.v_frames_var.get())
                steps = int(self.v_steps_var.get())
                cfg = float(self.v_cfg_var.get())
                fps = int(self.v_fps_var.get())
                duration = num_frames / fps

                result = self.wanvideo.generate(
                    prompt=en_prompt,
                    negative_prompt="blurry, low quality, distorted, jittery, static, watermark, text, subtitles, bad quality, worst quality, ugly, deformed",
                    width=width, height=height, steps=steps,
                    num_frames=num_frames, cfg=cfg, frame_rate=fps,
                    preview_enabled=True,
                )

                save_path = result.save_path or os.path.join(OUTPUT_DIR_DEFAULT, result.filename)
                with open(save_path, "wb") as f:
                    f.write(result.image_data)

                file_size_mb = os.path.getsize(save_path) / (1024 * 1024)
                self.video_status_label.config(
                    text=f"✅ Done!\n\nSaved: {result.filename}\n"
                         f"Size: {file_size_mb:.1f} MB | "
                         f"Duration: {duration:.1f}s | "
                         f"{width}×{height} @ {fps}fps\n\n"
                         f"Click to open folder",
                    fg="#51cf66")
                self.video_status_label.bind("<Button-1>",
                    lambda e: os.startfile(os.path.dirname(save_path)))
                self.video_status_label.config(cursor="hand2")
                self.status_var.set(f"Video saved: {result.filename}")

            except Exception as e:
                self.video_status_label.config(text=f"❌ Error: {e}", fg="#ff6b6b")
                self.status_var.set(f"Video error: {e}")
                messagebox.showerror("Video Generation Failed", str(e))
            finally:
                restore_limits()
                self.video_progress.stop()

        threading.Thread(target=run, daemon=True).start()


def main():
    try:
        from PIL import Image, ImageTk
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow", "requests"])
        from PIL import Image, ImageTk

    root = tk.Tk()
    AIImageStudio(root)
    root.mainloop()


if __name__ == "__main__":
    main()
