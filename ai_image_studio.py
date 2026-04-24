import subprocess
import requests
import json
import os
import sys
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from PIL import Image, ImageTk
import io

# ============ 配置 ============
OLLAMA_URL = "http://127.0.0.1:11434"
COMFYUI_URL = "http://127.0.0.1:8189"
COMFYUI_ALT_URL = "http://127.0.0.1:8188"
WORKFLOW_TXT2IMG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "workflows", "txt2img_api.json")
WORKFLOW_IMG2IMG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "workflows", "img2img_api.json")
OUTPUT_DIR = os.path.expanduser("~/Desktop/AI_picture")
COMFYUI_START_BAT = os.path.expanduser("~/.openclaw/workspace/start_comfy_conda.bat")
CONDA_PYTHON = os.path.expanduser("~/.conda/envs/comfyui/python.exe")
COMFYUI_MAIN = os.path.expanduser("~/ComfyUI/main.py")
COMFYUI_INPUT_DIR = os.path.expanduser("~/ComfyUI/input")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(COMFYUI_INPUT_DIR, exist_ok=True)


class AIImageStudio:
    def __init__(self, root):
        self.root = root
        root.title("AI Image Studio - MOSS Edition v2.0")
        root.geometry("1100x980")
        root.configure(bg="#1a1a2e")
        
        self.comfy_url = COMFYUI_URL
        self.comic_generating = False
        self.reference_image_path = None
        self.thumbnails = []
        
        # 状态栏
        self.status_var = tk.StringVar(value="Initializing...")
        self.status_bar = tk.Label(root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W, bg="#16213e", fg="#e94560")
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # ============ Notebook / Tabs ============
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: 单图生成
        self.tab_single = tk.Frame(self.notebook, bg="#1a1a2e")
        self.notebook.add(self.tab_single, text="🎨 单图生成")
        self.build_single_ui(self.tab_single)
        
        # Tab 2: 漫画工作室
        self.tab_comic = tk.Frame(self.notebook, bg="#1a1a2e")
        self.notebook.add(self.tab_comic, text="📖 漫画工作室")
        self.build_comic_ui(self.tab_comic)
        
        self.check_services()
    
    # ============ 服务检查 ============
    def check_services(self):
        def check():
            # Ollama
            try:
                r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
                if r.status_code == 200:
                    data = r.json()
                    models = [m.get('name', '') for m in data.get('models', [])]
                    has_wizard = any('wizardlm' in m.lower() for m in models)
                    status = "Ollama: OK"
                    if has_wizard:
                        status += " (wizardlm ready)"
                    self.ollama_status.config(text=status, fg="#51cf66")
                    self.ollama_status2.config(text=status, fg="#51cf66")
                else:
                    self.ollama_status.config(text="Ollama: not ready", fg="#fcc419")
                    self.ollama_status2.config(text="Ollama: not ready", fg="#fcc419")
            except:
                self.ollama_status.config(text="Ollama: offline", fg="#ff6b6b")
                self.ollama_status2.config(text="Ollama: offline", fg="#ff6b6b")
            
            # ComfyUI
            comfy_ok = False
            self.comfy_url = COMFYUI_ALT_URL
            for url in [COMFYUI_ALT_URL, COMFYUI_URL]:
                try:
                    r = requests.get(f"{url}/system_stats", timeout=2)
                    if r.status_code == 200:
                        r.json()
                        comfy_ok = True
                        self.comfy_url = url
                        break
                except:
                    pass
            
            if comfy_ok:
                self.comfy_status.config(text=f"ComfyUI: OK ({self.comfy_url})", fg="#51cf66")
                self.comfy_status2.config(text=f"ComfyUI: OK ({self.comfy_url})", fg="#51cf66")
            else:
                self.comfy_status.config(text="ComfyUI: offline", fg="#ff6b6b")
                self.comfy_status2.config(text="ComfyUI: offline", fg="#ff6b6b")
            
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
            for url in [COMFYUI_ALT_URL, COMFYUI_URL]:
                try:
                    r = requests.get(f"{url}/system_stats", timeout=2)
                    if r.status_code == 200:
                        self.comfy_url = url
                        self.status_var.set(f"ComfyUI already running at {url}")
                        self.check_services()
                        return
                except:
                    pass
            
            if os.path.exists(COMFYUI_START_BAT):
                subprocess.Popen([COMFYUI_START_BAT], creationflags=subprocess.CREATE_NEW_CONSOLE)
            elif os.path.exists(CONDA_PYTHON) and os.path.exists(COMFYUI_MAIN):
                subprocess.Popen([CONDA_PYTHON, COMFYUI_MAIN, "--listen", "127.0.0.1", "--port", "8188"], creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                messagebox.showerror("Error", "Cannot find ComfyUI startup script")
                return
        except Exception as e:
            messagebox.showerror("Error", f"Cannot start ComfyUI: {e}")
        
        def wait():
            for i in range(60):
                time.sleep(2)
                self.status_var.set(f"Waiting for ComfyUI... ({i+1}/60)")
                for url in [COMFYUI_ALT_URL, COMFYUI_URL]:
                    try:
                        r = requests.get(f"{url}/system_stats", timeout=2)
                        if r.status_code == 200:
                            self.comfy_url = url
                            self.status_var.set(f"ComfyUI started at {url}")
                            self.check_services()
                            return
                    except:
                        pass
            self.status_var.set("ComfyUI startup timeout")
        
        threading.Thread(target=wait, daemon=True).start()
    
    # ============ 单图生成 UI ============
    def build_single_ui(self, parent):
        main_frame = tk.Frame(parent, bg="#1a1a2e", padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title = tk.Label(main_frame, text="AI Image Studio", font=("Microsoft YaHei", 24, "bold"), bg="#1a1a2e", fg="#e94560")
        title.pack(pady=(0, 5))
        subtitle = tk.Label(main_frame, text="Chinese Prompt -> WizardLM Optimize -> ComfyUI Generate", font=("Microsoft YaHei", 11), bg="#1a1a2e", fg="#a0a0a0")
        subtitle.pack(pady=(0, 15))
        
        # 服务状态
        svc_frame = tk.Frame(main_frame, bg="#16213e", bd=2, relief=tk.RIDGE, padx=15, pady=10)
        svc_frame.pack(fill=tk.X, pady=(0, 15))
        tk.Label(svc_frame, text="Service Status", font=("Microsoft YaHei", 12, "bold"), bg="#16213e", fg="#fff").pack(anchor=tk.W)
        self.ollama_status = tk.Label(svc_frame, text="Ollama: Checking...", bg="#16213e", fg="#ff6b6b")
        self.ollama_status.pack(anchor=tk.W, pady=2)
        self.comfy_status = tk.Label(svc_frame, text="ComfyUI: Checking...", bg="#16213e", fg="#ff6b6b")
        self.comfy_status.pack(anchor=tk.W, pady=2)
        btn_frame = tk.Frame(svc_frame, bg="#16213e")
        btn_frame.pack(anchor=tk.W, pady=5)
        tk.Button(btn_frame, text="Start Ollama", command=self.start_ollama, bg="#0f3460", fg="#fff", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Start ComfyUI", command=self.start_comfyui, bg="#0f3460", fg="#fff", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Refresh", command=self.check_services, bg="#0f3460", fg="#fff", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=2)
        
        # 输入区
        input_frame = tk.LabelFrame(main_frame, text="Chinese Prompt", font=("Microsoft YaHei", 12, "bold"), bg="#1a1a2e", fg="#e94560", padx=10, pady=10)
        input_frame.pack(fill=tk.X, pady=(0, 15))
        self.prompt_input = scrolledtext.ScrolledText(input_frame, height=4, font=("Microsoft YaHei", 11), wrap=tk.WORD, bg="#16213e", fg="#fff", insertbackground="#fff")
        self.prompt_input.pack(fill=tk.X, pady=5)
        self.prompt_input.insert(tk.END, "A girl in Hanfu standing under cherry blossom tree")
        
        # 参数区
        param_frame = tk.Frame(input_frame, bg="#1a1a2e")
        param_frame.pack(fill=tk.X, pady=5)
        tk.Label(param_frame, text="Size:", bg="#1a1a2e", fg="#fff", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
        self.width_var = tk.StringVar(value="1024")
        tk.Spinbox(param_frame, from_=256, to=2048, increment=64, textvariable=self.width_var, width=6, font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)
        tk.Label(param_frame, text="x", bg="#1a1a2e", fg="#fff").pack(side=tk.LEFT)
        self.height_var = tk.StringVar(value="1024")
        tk.Spinbox(param_frame, from_=256, to=2048, increment=64, textvariable=self.height_var, width=6, font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)
        tk.Label(param_frame, text="  Steps:", bg="#1a1a2e", fg="#fff", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=(20,0))
        self.steps_var = tk.StringVar(value="25")
        tk.Spinbox(param_frame, from_=10, to=50, increment=5, textvariable=self.steps_var, width=5, font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)
        tk.Label(param_frame, text="  Model:", bg="#1a1a2e", fg="#fff", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=(20,0))
        self.model_var = tk.StringVar(value="dreamshaper_8.safetensors")
        model_combo = ttk.Combobox(param_frame, textvariable=self.model_var, values=["dreamshaper_8.safetensors", "ponyDiffusionV6XL_v6.safetensors", "meinamix_v12Final.safetensors"], width=22, font=("Microsoft YaHei", 10))
        model_combo.pack(side=tk.LEFT, padx=5)
        
        # 生成按钮
        gen_btn = tk.Button(main_frame, text="GENERATE", command=self.generate, bg="#e94560", fg="#fff", font=("Microsoft YaHei", 14, "bold"), height=2)
        gen_btn.pack(fill=tk.X, pady=(0, 15))
        
        # 进度条
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=(0, 10))
        
        # 输出区
        out_frame = tk.Frame(main_frame, bg="#1a1a2e")
        out_frame.pack(fill=tk.BOTH, expand=True)
        left_frame = tk.LabelFrame(out_frame, text="Optimized English Prompt", font=("Microsoft YaHei", 11, "bold"), bg="#1a1a2e", fg="#00d9ff", padx=5, pady=5)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        self.en_prompt = scrolledtext.ScrolledText(left_frame, height=8, font=("Consolas", 10), wrap=tk.WORD, bg="#16213e", fg="#00ff88", insertbackground="#fff")
        self.en_prompt.pack(fill=tk.BOTH, expand=True)
        right_frame = tk.LabelFrame(out_frame, text="Generated Image", font=("Microsoft YaHei", 11, "bold"), bg="#1a1a2e", fg="#e94560", padx=5, pady=5)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        self.img_label = tk.Label(right_frame, bg="#16213e", text="[Waiting...]", fg="#666")
        self.img_label.pack(fill=tk.BOTH, expand=True)
    
    # ============ 漫画工作室 UI ============
    def build_comic_ui(self, parent):
        main_frame = tk.Frame(parent, bg="#1a1a2e", padx=15, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title = tk.Label(main_frame, text="📖 Comic Studio", font=("Microsoft YaHei", 22, "bold"), bg="#1a1a2e", fg="#e94560")
        title.pack(pady=(0, 5))
        subtitle = tk.Label(main_frame, text="Character Consistency Story Generation", font=("Microsoft YaHei", 11), bg="#1a1a2e", fg="#a0a0a0")
        subtitle.pack(pady=(0, 10))
        
        # 服务状态（漫画工作室也显示）
        svc_frame = tk.Frame(main_frame, bg="#16213e", bd=2, relief=tk.RIDGE, padx=15, pady=8)
        svc_frame.pack(fill=tk.X, pady=(0, 10))
        self.ollama_status2 = tk.Label(svc_frame, text="Ollama: Checking...", bg="#16213e", fg="#ff6b6b")
        self.ollama_status2.pack(side=tk.LEFT, padx=10)
        self.comfy_status2 = tk.Label(svc_frame, text="ComfyUI: Checking...", bg="#16213e", fg="#ff6b6b")
        self.comfy_status2.pack(side=tk.LEFT, padx=10)
        tk.Button(svc_frame, text="Refresh", command=self.check_services, bg="#0f3460", fg="#fff", font=("Microsoft YaHei", 9)).pack(side=tk.RIGHT, padx=5)
        
        # ===== 左右分栏 =====
        content_frame = tk.Frame(main_frame, bg="#1a1a2e")
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # --- 左侧面板 ---
        left_panel = tk.Frame(content_frame, bg="#1a1a2e")
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # 角色设定
        char_frame = tk.LabelFrame(left_panel, text="🎭 Character Setup", font=("Microsoft YaHei", 11, "bold"), bg="#1a1a2e", fg="#00d9ff", padx=10, pady=8)
        char_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(char_frame, text="Name:", bg="#1a1a2e", fg="#fff", font=("Microsoft YaHei", 10)).pack(anchor=tk.W)
        self.char_name_var = tk.StringVar(value="Ling")
        tk.Entry(char_frame, textvariable=self.char_name_var, font=("Microsoft YaHei", 10), bg="#16213e", fg="#fff", insertbackground="#fff").pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(char_frame, text="Appearance (face, hair, body, skin - fixed features):", bg="#1a1a2e", fg="#fff", font=("Microsoft YaHei", 10)).pack(anchor=tk.W)
        self.char_desc_input = scrolledtext.ScrolledText(char_frame, height=4, font=("Microsoft YaHei", 10), wrap=tk.WORD, bg="#16213e", fg="#fff", insertbackground="#fff")
        self.char_desc_input.pack(fill=tk.X, pady=5)
        self.char_desc_input.insert(tk.END, "a young woman with long black hair, brown eyes, oval face, fair skin, slender build, delicate features")
        
        char_btn_frame = tk.Frame(char_frame, bg="#1a1a2e")
        char_btn_frame.pack(fill=tk.X, pady=5)
        tk.Button(char_btn_frame, text="🎨 Generate Character Sheet", command=self.generate_character_sheet, bg="#0f3460", fg="#fff", font=("Microsoft YaHei", 10, "bold")).pack(side=tk.LEFT, padx=2)
        tk.Button(char_btn_frame, text="📁 Load Reference Image", command=self.load_reference_image, bg="#0f3460", fg="#fff", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=2)
        
        # 分镜脚本
        script_frame = tk.LabelFrame(left_panel, text="📝 Storyboard Script", font=("Microsoft YaHei", 11, "bold"), bg="#1a1a2e", fg="#00d9ff", padx=10, pady=8)
        script_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        tk.Label(script_frame, text="One scene per line (action/clothing/expression/background):", bg="#1a1a2e", fg="#aaa", font=("Microsoft YaHei", 9)).pack(anchor=tk.W)
        self.script_input = scrolledtext.ScrolledText(script_frame, height=6, font=("Microsoft YaHei", 10), wrap=tk.WORD, bg="#16213e", fg="#fff", insertbackground="#fff")
        self.script_input.pack(fill=tk.BOTH, expand=True, pady=5)
        sample = """smiling under cherry blossom tree, wearing pink floral dress
surprised looking out rainy window, wearing cozy sweater
running through autumn forest, wearing brown leather jacket
sitting at desk reading book, wearing glasses and school uniform"""
        self.script_input.insert(tk.END, sample)
        
        # 生成参数
        param_frame = tk.LabelFrame(left_panel, text="⚙️ Generation Settings", font=("Microsoft YaHei", 11, "bold"), bg="#1a1a2e", fg="#00d9ff", padx=10, pady=8)
        param_frame.pack(fill=tk.X)
        
        p1 = tk.Frame(param_frame, bg="#1a1a2e")
        p1.pack(fill=tk.X, pady=2)
        tk.Label(p1, text="Size:", bg="#1a1a2e", fg="#fff", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
        self.c_width_var = tk.StringVar(value="1024")
        tk.Spinbox(p1, from_=256, to=2048, increment=64, textvariable=self.c_width_var, width=6, font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)
        tk.Label(p1, text="x", bg="#1a1a2e", fg="#fff").pack(side=tk.LEFT)
        self.c_height_var = tk.StringVar(value="1024")
        tk.Spinbox(p1, from_=256, to=2048, increment=64, textvariable=self.c_height_var, width=6, font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)
        tk.Label(p1, text="  Steps:", bg="#1a1a2e", fg="#fff", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=(20,0))
        self.c_steps_var = tk.StringVar(value="25")
        tk.Spinbox(p1, from_=10, to=50, increment=5, textvariable=self.c_steps_var, width=5, font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)
        tk.Label(p1, text="  Model:", bg="#1a1a2e", fg="#fff", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=(20,0))
        self.c_model_var = tk.StringVar(value="meinamix_v12Final.safetensors")
        c_model_combo = ttk.Combobox(p1, textvariable=self.c_model_var, values=["meinamix_v12Final.safetensors", "dreamshaper_8.safetensors", "ponyDiffusionV6XL_v6.safetensors"], width=22, font=("Microsoft YaHei", 10))
        c_model_combo.pack(side=tk.LEFT, padx=5)
        
        p2 = tk.Frame(param_frame, bg="#1a1a2e")
        p2.pack(fill=tk.X, pady=5)
        tk.Label(p2, text="Consistency:", bg="#1a1a2e", fg="#fff", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
        self.denoise_var = tk.DoubleVar(value=0.70)
        tk.Scale(p2, from_=0.5, to=0.85, resolution=0.05, orient=tk.HORIZONTAL, variable=self.denoise_var, length=180, bg="#1a1a2e", fg="#fff", highlightthickness=0).pack(side=tk.LEFT, padx=5)
        tk.Label(p2, text="(0.5=very similar, 0.85=more creative)", bg="#1a1a2e", fg="#888", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)
        
        p3 = tk.Frame(param_frame, bg="#1a1a2e")
        p3.pack(fill=tk.X, pady=2)
        tk.Label(p3, text="Seed:", bg="#1a1a2e", fg="#fff", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
        self.seed_mode_var = tk.StringVar(value="fixed")
        tk.Radiobutton(p3, text="Fixed (max consistency)", variable=self.seed_mode_var, value="fixed", bg="#1a1a2e", fg="#fff", selectcolor="#16213e", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(p3, text="Series (slight variation)", variable=self.seed_mode_var, value="series", bg="#1a1a2e", fg="#fff", selectcolor="#16213e", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=5)
        self.base_seed_var = tk.StringVar(value="123456")
        tk.Entry(p3, textvariable=self.base_seed_var, width=10, font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)
        
        # 模式选择
        p4 = tk.Frame(param_frame, bg="#1a1a2e")
        p4.pack(fill=tk.X, pady=8)
        tk.Label(p4, text="Mode:", bg="#1a1a2e", fg="#fff", font=("Microsoft YaHei", 10, "bold")).pack(side=tk.LEFT)
        self.use_ref_var = tk.BooleanVar(value=False)
        tk.Radiobutton(p4, text="🎭 Action Free (txt2img + fixed seed, full pose freedom)", variable=self.use_ref_var, value=False, bg="#1a1a2e", fg="#fff", selectcolor="#16213e", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(p4, text="🔒 Face Lock (img2img + reference, limits pose changes)", variable=self.use_ref_var, value=True, bg="#1a1a2e", fg="#fff", selectcolor="#16213e", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=5)
        
        note = tk.Label(param_frame, text="Tip: Action Free is recommended for story comics. Use Face Lock only for close-up portraits.", bg="#1a1a2e", fg="#888", font=("Microsoft YaHei", 9))
        note.pack(anchor=tk.W, pady=(5,0))
        
        # 风格预设
        p5 = tk.Frame(param_frame, bg="#1a1a2e")
        p5.pack(fill=tk.X, pady=8)
        tk.Label(p5, text="Style Preset:", bg="#1a1a2e", fg="#fff", font=("Microsoft YaHei", 10, "bold")).pack(side=tk.LEFT)
        self.style_preset_var = tk.StringVar(value="Default")
        style_combo = ttk.Combobox(p5, textvariable=self.style_preset_var, values=["Default", "Soft Moe (pastel/soft)", "Dark Dramatic (dark/contrast)", "Watercolor (paint/wash)"], width=28, font=("Microsoft YaHei", 10))
        style_combo.pack(side=tk.LEFT, padx=5)
        
        # --- 右侧面板 ---
        right_panel = tk.Frame(content_frame, bg="#1a1a2e", width=320)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right_panel.pack_propagate(False)
        
        # 参考图预览
        ref_frame = tk.LabelFrame(right_panel, text="👤 Reference Image", font=("Microsoft YaHei", 11, "bold"), bg="#1a1a2e", fg="#e94560", padx=5, pady=5, height=220)
        ref_frame.pack(fill=tk.X, pady=(0, 10))
        ref_frame.pack_propagate(False)
        self.ref_img_label = tk.Label(ref_frame, bg="#16213e", text="[No reference image]\nGenerate or load one first", fg="#666")
        self.ref_img_label.pack(fill=tk.BOTH, expand=True)
        
        # 批量生成按钮
        self.comic_gen_btn = tk.Button(right_panel, text="🚀 GENERATE COMIC", command=self.generate_comic_batch, bg="#e94560", fg="#fff", font=("Microsoft YaHei", 14, "bold"), height=2)
        self.comic_gen_btn.pack(fill=tk.X, pady=(0, 10))
        
        # 进度
        self.comic_progress = ttk.Progressbar(right_panel, mode='determinate')
        self.comic_progress.pack(fill=tk.X, pady=(0, 10))
        self.comic_status = tk.Label(right_panel, text="Ready", bg="#1a1a2e", fg="#aaa", font=("Microsoft YaHei", 10))
        self.comic_status.pack(anchor=tk.W, pady=(0, 5))
        
        # 缩略图预览区
        thumb_frame = tk.LabelFrame(right_panel, text="Generated Panels", font=("Microsoft YaHei", 10, "bold"), bg="#1a1a2e", fg="#51cf66", padx=5, pady=5)
        thumb_frame.pack(fill=tk.BOTH, expand=True)
        
        thumb_canvas_frame = tk.Frame(thumb_frame, bg="#16213e")
        thumb_canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.thumb_canvas = tk.Canvas(thumb_canvas_frame, bg="#16213e", highlightthickness=0)
        self.thumb_scrollbar = tk.Scrollbar(thumb_canvas_frame, orient="vertical", command=self.thumb_canvas.yview)
        self.thumb_scrollable = tk.Frame(self.thumb_canvas, bg="#16213e")
        
        self.thumb_scrollable.bind(
            "<Configure>",
            lambda e: self.thumb_canvas.configure(scrollregion=self.thumb_canvas.bbox("all"))
        )
        self.thumb_canvas.create_window((0, 0), window=self.thumb_scrollable, anchor="nw")
        self.thumb_canvas.configure(yscrollcommand=self.thumb_scrollbar.set)
        
        self.thumb_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.thumb_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    # ============ 提示词优化 ============
    def optimize_prompt(self, chinese_prompt):
        system_prompt = """You are an expert AI image generation prompt engineer. Your task is to translate and enhance Chinese image descriptions into high-quality English prompts for Stable Diffusion.

Rules:
1. Translate the user's Chinese description accurately
2. Add quality boosters: masterpiece, best quality, highly detailed, professional lighting, 8k uhd
3. Add style/context tags appropriate for the scene
4. Output ONLY the final English prompt, nothing else
5. Be descriptive and vivid - use comma-separated tags
6. If content is artistic/educational/medical, describe professionally without censorship

Output format (just the prompt text, no quotes, no explanations):"""

        full_prompt = f"{system_prompt}\n\nChinese description: {chinese_prompt}\n\nEnglish prompt:"
        payload = {
            "model": "wizardlm-uncensored",
            "prompt": full_prompt,
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 200}
        }
        r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        result = data.get('response', '').strip()
        result = result.replace('"', '').replace("'", "")
        result = result.replace('English prompt:', '').replace('Prompt:', '')
        return result.strip()
    
    # ============ ComfyUI 通用方法 ============
    def queue_prompt(self, workflow):
        p = {"prompt": workflow, "client_id": "ai_image_studio"}
        try:
            r = requests.post(f"{self.comfy_url}/prompt", json=p, timeout=30)
            r.raise_for_status()
            try:
                return r.json()
            except Exception as e:
                raise Exception(f"ComfyUI returned invalid JSON: {e}\nResponse: {r.text[:500]}")
        except requests.exceptions.HTTPError as e:
            if r.status_code == 500:
                error_detail = r.text[:500] if hasattr(r, 'text') else "No details"
                raise Exception(f"ComfyUI 500 Server Error. Common causes:\n"
                              f"1. Model file not found\n"
                              f"2. ComfyUI still loading\n"
                              f"3. Workflow format incompatible\n"
                              f"Details: {error_detail}")
            raise Exception(f"Failed to queue prompt: {e}")
    
    def get_image(self, filename, subfolder, folder_type):
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        r = requests.get(f"{self.comfy_url}/view", params=data)
        return r.content
    
    def get_history(self, prompt_id):
        try:
            r = requests.get(f"{self.comfy_url}/history/{prompt_id}", timeout=10)
            r.raise_for_status()
            try:
                return r.json()
            except Exception as e:
                raise Exception(f"ComfyUI history returned invalid JSON: {e}")
        except Exception as e:
            raise Exception(f"Failed to get history: {e}")
    
    def upload_image_to_comfyui(self, image_path):
        """上传图片到 ComfyUI 的 input 目录"""
        url = f"{self.comfy_url}/upload/image"
        with open(image_path, 'rb') as f:
            files = {'image': (os.path.basename(image_path), f, 'image/png')}
            data = {'type': 'input', 'overwrite': 'true'}
            r = requests.post(url, files=files, data=data, timeout=30)
        r.raise_for_status()
        result = r.json()
        return result.get('name', os.path.basename(image_path))
    
    def wait_for_image(self, prompt_id, timeout_sec=120):
        """等待 ComfyUI 生成完成并返回图片数据"""
        for i in range(timeout_sec // 2):
            time.sleep(2)
            try:
                history = self.get_history(prompt_id)
                if prompt_id in history:
                    outputs = history[prompt_id].get('outputs', {})
                    for node_id, node_output in outputs.items():
                        if 'images' in node_output:
                            for img_info in node_output['images']:
                                filename = img_info['filename']
                                subfolder = img_info.get('subfolder', '')
                                folder_type = img_info.get('type', 'output')
                                img_data = self.get_image(filename, subfolder, folder_type)
                                return img_data, filename
            except Exception:
                continue
        return None, None
    
    def load_workflow(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Workflow not found: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # ============ 单图生成 ============
    def generate(self):
        chinese = self.prompt_input.get("1.0", tk.END).strip()
        if not chinese:
            messagebox.showwarning("Tip", "Please enter a Chinese prompt")
            return
        if "offline" in self.ollama_status.cget("text"):
            messagebox.showwarning("Tip", "Ollama is offline, please start it first")
            return
        if "offline" in self.comfy_status.cget("text"):
            messagebox.showwarning("Tip", "ComfyUI is offline, please start it first")
            return
        
        self.progress.start()
        self.status_var.set("Optimizing prompt...")
        self.root.update()
        
        def run():
            try:
                en_prompt = self.optimize_prompt(chinese)
                self.en_prompt.delete("1.0", tk.END)
                self.en_prompt.insert(tk.END, en_prompt)
                self.status_var.set(f"Optimized: {en_prompt[:80]}...")
                
                workflow = self.load_workflow(WORKFLOW_TXT2IMG)
                width = int(self.width_var.get())
                height = int(self.height_var.get())
                steps = int(self.steps_var.get())
                model_name = self.model_var.get()
                
                model_paths = [
                    os.path.expanduser(f"~/ComfyUI/models/checkpoints/{model_name}"),
                    f"C:/Users/lenovo/ComfyUI/models/checkpoints/{model_name}",
                    f"C:/ComfyUI/models/checkpoints/{model_name}",
                ]
                if not any(os.path.exists(p) for p in model_paths):
                    raise FileNotFoundError(f"Model not found: {model_name}")
                
                for node_id, node in workflow.items():
                    if node.get('class_type') == 'CheckpointLoaderSimple':
                        node['inputs']['ckpt_name'] = model_name
                    elif node.get('class_type') == 'CLIPTextEncode':
                        meta_title = node.get('_meta', {}).get('title', '')
                        if 'Positive' in meta_title or node_id == '2':
                            node['inputs']['text'] = en_prompt
                    elif node.get('class_type') == 'EmptyLatentImage':
                        node['inputs']['width'] = width
                        node['inputs']['height'] = height
                    elif node.get('class_type') == 'KSampler':
                        node['inputs']['steps'] = steps
                
                self.status_var.set("Submitting to ComfyUI...")
                result = self.queue_prompt(workflow)
                if 'prompt_id' not in result:
                    raise Exception(f"ComfyUI returned: {json.dumps(result, ensure_ascii=False)[:500]}")
                
                prompt_id = result['prompt_id']
                self.status_var.set("Generating image...")
                img_data, filename = self.wait_for_image(prompt_id)
                
                if img_data:
                    save_path = os.path.join(OUTPUT_DIR, filename)
                    with open(save_path, 'wb') as f:
                        f.write(img_data)
                    self.show_image(img_data, save_path)
                    self.status_var.set(f"Done! Saved: {save_path}")
                else:
                    self.status_var.set("Timeout, check ComfyUI status")
                
                self.progress.stop()
            except Exception as e:
                self.status_var.set(f"Error: {str(e)}")
                self.progress.stop()
                messagebox.showerror("Generation Failed", str(e))
        
        threading.Thread(target=run, daemon=True).start()
    
    def show_image(self, img_data, path):
        try:
            img = Image.open(io.BytesIO(img_data))
            img.thumbnail((450, 450), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.img_label.config(image=photo, text="")
            self.img_label.image = photo
            def open_image(event):
                os.startfile(path)
            self.img_label.bind("<Button-1>", open_image)
            self.img_label.config(cursor="hand2")
        except Exception as e:
            self.img_label.config(text=f"[Image display failed: {e}]")
    
    # ============ 漫画工作室 ============
    def load_reference_image(self):
        """从文件选择对话框加载参考图"""
        path = filedialog.askopenfilename(
            title="Select Reference Image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.webp"), ("All files", "*.*")]
        )
        if path:
            self.set_reference_image(path)
    
    def set_reference_image(self, path):
        """设置参考图并显示预览"""
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
        """生成角色设定图（正面站立，中性表情）"""
        if "offline" in self.comfy_status2.cget("text"):
            messagebox.showwarning("Tip", "ComfyUI is offline, please start it first")
            return
        if "offline" in self.ollama_status2.cget("text"):
            messagebox.showwarning("Tip", "Ollama is offline, please start it first")
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
                # 构建角色设定图的提示词
                sheet_prompt = f"{char_desc}, standing pose, front view, neutral expression, full body, simple clean background, character design reference sheet, clear face details, masterpiece, best quality, highly detailed, professional lighting, 8k uhd"
                
                # 用 Ollama 优化
                self.comic_status.config(text="Optimizing prompt...")
                en_prompt = self.optimize_prompt(sheet_prompt)
                
                # 加载 txt2img workflow
                workflow = self.load_workflow(WORKFLOW_TXT2IMG)
                width = int(self.c_width_var.get())
                height = int(self.c_height_var.get())
                steps = int(self.c_steps_var.get())
                model_name = self.c_model_var.get()
                
                for node_id, node in workflow.items():
                    if node.get('class_type') == 'CheckpointLoaderSimple':
                        node['inputs']['ckpt_name'] = model_name
                    elif node.get('class_type') == 'CLIPTextEncode':
                        meta_title = node.get('_meta', {}).get('title', '')
                        if 'Positive' in meta_title or node_id == '2':
                            node['inputs']['text'] = en_prompt
                    elif node.get('class_type') == 'EmptyLatentImage':
                        node['inputs']['width'] = width
                        node['inputs']['height'] = height
                    elif node.get('class_type') == 'KSampler':
                        node['inputs']['steps'] = steps
                        node['inputs']['control_after_generate'] = "fixed"
                        node['inputs']['seed'] = int(self.base_seed_var.get())
                
                self.comic_status.config(text="Submitting to ComfyUI...")
                result = self.queue_prompt(workflow)
                prompt_id = result['prompt_id']
                
                self.comic_status.config(text="Generating character sheet...")
                img_data, filename = self.wait_for_image(prompt_id)
                
                if img_data:
                    # 保存到 output 目录
                    save_path = os.path.join(OUTPUT_DIR, f"{char_name}_reference_{filename}")
                    with open(save_path, 'wb') as f:
                        f.write(img_data)
                    
                    # 同时保存到 ComfyUI input 目录作为参考
                    ref_path = os.path.join(COMFYUI_INPUT_DIR, "reference.png")
                    with open(ref_path, 'wb') as f:
                        f.write(img_data)
                    
                    self.set_reference_image(save_path)
                    self.comic_status.config(text=f"Character sheet saved: {save_path}", fg="#51cf66")
                else:
                    self.comic_status.config(text="Timeout", fg="#ff6b6b")
                
            except Exception as e:
                self.comic_status.config(text=f"Error: {str(e)}", fg="#ff6b6b")
                messagebox.showerror("Character Sheet Failed", str(e))
            finally:
                self.comic_gen_btn.config(state=tk.NORMAL)
        
        threading.Thread(target=run, daemon=True).start()
    
    def generate_comic_batch(self):
        """批量生成漫画分镜"""
        if self.comic_generating:
            messagebox.showwarning("Tip", "Generation in progress, please wait")
            return
        
        # 检查脚本
        script_text = self.script_input.get("1.0", tk.END).strip()
        if not script_text:
            messagebox.showwarning("Tip", "Please enter storyboard script")
            return
        
        scenes = [line.strip() for line in script_text.split('\n') if line.strip()]
        if not scenes:
            messagebox.showwarning("Tip", "No valid scenes found")
            return
        
        if "offline" in self.comfy_status2.cget("text"):
            messagebox.showwarning("Tip", "ComfyUI is offline, please start it first")
            return
        
        use_reference = self.use_ref_var.get()
        
        # 如果选 Face Lock 模式，检查参考图
        if use_reference:
            if not self.reference_image_path or not os.path.exists(self.reference_image_path):
                auto_ref = os.path.join(COMFYUI_INPUT_DIR, "reference.png")
                if os.path.exists(auto_ref):
                    self.reference_image_path = auto_ref
                else:
                    messagebox.showwarning("Tip", "Face Lock mode requires a reference image.\nPlease generate or load one first, or switch to Action Free mode.")
                    return
        
        char_desc = self.char_desc_input.get("1.0", tk.END).strip()
        char_name = self.char_name_var.get().strip()
        
        self.comic_generating = True
        self.comic_gen_btn.config(state=tk.DISABLED, text="Generating...")
        self.comic_progress['maximum'] = len(scenes)
        self.comic_progress['value'] = 0
        
        mode_text = "Face Lock" if use_reference else "Action Free"
        self.comic_status.config(text=f"Mode: {mode_text} | Preparing {len(scenes)} panels...", fg="#e94560")
        
        # 清空旧缩略图
        for widget in self.thumb_scrollable.winfo_children():
            widget.destroy()
        self.thumbnails.clear()
        
        def run():
            try:
                width = int(self.c_width_var.get())
                height = int(self.c_height_var.get())
                steps = int(self.c_steps_var.get())
                model_name = self.c_model_var.get()
                denoise = float(self.denoise_var.get())
                seed_mode = self.seed_mode_var.get()
                base_seed = int(self.base_seed_var.get())
                
                # Face Lock 模式：上传参考图
                ref_name = None
                if use_reference:
                    self.root.after(0, lambda: self.comic_status.config(
                        text=f"Mode: Face Lock | Uploading reference...", fg="#e94560"))
                    ref_name = self.upload_image_to_comfyui(self.reference_image_path)
                
                generated_files = []
                
                for idx, scene in enumerate(scenes):
                    self.root.after(0, lambda i=idx+1, total=len(scenes): 
                        self.comic_status.config(text=f"Mode: {mode_text} | Panel {i}/{total}..."))
                    
                    # ===== 风格注入 =====
                    style = self.style_preset_var.get()
                    style_pos = ""
                    style_neg_add = ""
                    if style == "Soft Moe (pastel/soft)":
                        style_pos = "meinamix, pastel colors, soft lighting, muted tones, low contrast, kawaii, moe, gentle shading, fluffy atmosphere, dreamy, airy, soft focus, warm ambient light, delicate details, beautiful detailed eyes, detailed face, anime style, "
                        style_neg_add = ", harsh shadows, high contrast, dramatic lighting, sharp edges, dark colors, gritty, cinematic, heavy shadows, realistic, 3d, western, ugly, bad anatomy"
                    elif style == "Dark Dramatic (dark/contrast)":
                        style_pos = "dark atmosphere, dramatic lighting, high contrast, deep shadows, cinematic, moody, intense colors, "
                        style_neg_add = ", pastel, soft lighting, low contrast, fluffy, cute, bright colors"
                    elif style == "Watercolor (paint/wash)":
                        style_pos = "watercolor painting, soft wash, bleeding colors, painterly, artistic, traditional media, paper texture, loose brushwork, "
                        style_neg_add = ", photorealistic, 3d render, sharp edges, digital art, clean lines"
                    
                    # ===== 构建提示词 =====
                    if use_reference:
                        # Face Lock: 角色描述 + 场景，但不重复强调外貌（参考图已锁定）
                        full_prompt = f"{style_pos}{char_desc}, {scene}, masterpiece, best quality, highly detailed, professional lighting, 8k uhd"
                    else:
                        # Action Free: 每帧都带完整角色描述 + 场景 + 强制动作权重
                        full_prompt = f"{style_pos}{char_desc}, {scene}, dynamic pose, masterpiece, best quality, highly detailed, professional lighting, 8k uhd"
                    
                    # 优化提示词（第一帧用 Ollama，后面复用结构但跳过 API 加速）
                    if idx == 0 and "offline" not in self.ollama_status2.cget("text"):
                        try:
                            en_prompt = self.optimize_prompt(full_prompt)
                        except:
                            en_prompt = full_prompt
                    else:
                        en_prompt = full_prompt
                    
                    # 计算 seed
                    if seed_mode == "fixed":
                        current_seed = base_seed
                    else:
                        current_seed = base_seed + idx
                    
                    # ===== 选择 Workflow =====
                    if use_reference:
                        # Face Lock: img2img
                        workflow = self.load_workflow(WORKFLOW_IMG2IMG)
                        
                        for node_id, node in workflow.items():
                            if node.get('class_type') == 'CheckpointLoaderSimple':
                                node['inputs']['ckpt_name'] = model_name
                            elif node.get('class_type') == 'CLIPTextEncode':
                                meta_title = node.get('_meta', {}).get('title', '')
                                if 'Positive' in meta_title or node_id == '2':
                                    node['inputs']['text'] = en_prompt
                                elif 'Negative' in meta_title or node_id == '3':
                                    neg = node['inputs'].get('text', '')
                                    if 'same pose' not in neg:
                                        node['inputs']['text'] = neg + ", same pose, identical pose, static posture, unchanged stance, duplicate" + style_neg_add
                            elif node.get('class_type') == 'LoadImage':
                                node['inputs']['image'] = ref_name
                            elif node.get('class_type') == 'EmptyLatentImage':
                                node['inputs']['width'] = width
                                node['inputs']['height'] = height
                            elif node.get('class_type') == 'KSampler':
                                node['inputs']['steps'] = steps
                                node['inputs']['denoise'] = denoise
                                node['inputs']['seed'] = current_seed
                                node['inputs']['control_after_generate'] = "fixed"
                    else:
                        # Action Free: txt2img + fixed seed
                        workflow = self.load_workflow(WORKFLOW_TXT2IMG)
                        
                        for node_id, node in workflow.items():
                            if node.get('class_type') == 'CheckpointLoaderSimple':
                                node['inputs']['ckpt_name'] = model_name
                            elif node.get('class_type') == 'CLIPTextEncode':
                                meta_title = node.get('_meta', {}).get('title', '')
                                if 'Positive' in meta_title or node_id == '2':
                                    node['inputs']['text'] = en_prompt
                                elif 'Negative' in meta_title or node_id == '3':
                                    neg = node['inputs'].get('text', '')
                                    if 'mutated face' not in neg:
                                        node['inputs']['text'] = neg + ", mutated face, wrong face, different person, extra limbs" + style_neg_add
                            elif node.get('class_type') == 'EmptyLatentImage':
                                node['inputs']['width'] = width
                                node['inputs']['height'] = height
                            elif node.get('class_type') == 'KSampler':
                                node['inputs']['steps'] = steps
                                node['inputs']['seed'] = current_seed
                                node['inputs']['control_after_generate'] = "fixed"
                    
                    # 提交生成
                    result = self.queue_prompt(workflow)
                    prompt_id = result['prompt_id']
                    
                    # 等待完成
                    img_data, filename = self.wait_for_image(prompt_id, timeout_sec=180)
                    
                    if img_data:
                        panel_name = f"{char_name}_panel_{idx+1:03d}_{filename}"
                        save_path = os.path.join(OUTPUT_DIR, panel_name)
                        with open(save_path, 'wb') as f:
                            f.write(img_data)
                        generated_files.append(save_path)
                        self.root.after(0, lambda p=save_path, n=idx+1: self.add_thumbnail(p, n))
                    else:
                        self.root.after(0, lambda n=idx+1: self.comic_status.config(
                            text=f"Panel {n} timeout", fg="#ff6b6b"))
                    
                    self.root.after(0, lambda v=idx+1: self.comic_progress.config(value=v))
                
                self.root.after(0, lambda: self.comic_status.config(
                    text=f"Done! {len(generated_files)} panels | Mode: {mode_text} | Saved to {OUTPUT_DIR}", fg="#51cf66"))
                
            except Exception as e:
                self.root.after(0, lambda: self.comic_status.config(text=f"Error: {str(e)}", fg="#ff6b6b"))
                self.root.after(0, lambda: messagebox.showerror("Comic Generation Failed", str(e)))
            finally:
                self.comic_generating = False
                self.root.after(0, lambda: self.comic_gen_btn.config(
                    state=tk.NORMAL, text="🚀 GENERATE COMIC"))
        
        threading.Thread(target=run, daemon=True).start()
    
    def add_thumbnail(self, img_path, panel_num):
        """添加缩略图到预览区"""
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
            
            txt = tk.Label(inner, text=f"#{panel_num}", bg="#16213e", fg="#fff", font=("Microsoft YaHei", 9))
            txt.pack(side=tk.LEFT, padx=8, pady=5)
            
            def open_img(event, p=img_path):
                os.startfile(p)
            lbl.bind("<Button-1>", open_img)
            lbl.config(cursor="hand2")
            
            self.thumbnails.append((frame, photo))
            
            # 滚动到新图
            self.thumb_canvas.update_idletasks()
            self.thumb_canvas.yview_moveto(1.0)
        except Exception as e:
            print(f"Thumbnail error: {e}")


def main():
    try:
        from PIL import Image, ImageTk
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow", "requests"])
        from PIL import Image, ImageTk
    
    root = tk.Tk()
    app = AIImageStudio(root)
    root.mainloop()


if __name__ == "__main__":
    main()
