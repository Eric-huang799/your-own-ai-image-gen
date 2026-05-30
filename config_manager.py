import os
import json

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "llm_provider": "ollama",
    "image_provider": "comfyui",
    "ollama": {
        "base_url": "http://127.0.0.1:11434",
        "model": "wizardlm-uncensored",
    },
    "openai": {
        "api_key": "",
        "model": "gpt-4o-mini",
        "base_url": "https://api.openai.com/v1",
    },
    "claude": {
        "api_key": "",
        "model": "claude-sonnet-4-6",
        "base_url": "https://api.anthropic.com/v1",
    },
    "deepseek": {
        "api_key": "",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com/v1",
    },
    "stability": {
        "api_key": "",
        "model": "stable-diffusion-xl-1024-v1-0",
    },
    "siliconflow": {
        "api_key": "",
        "model": "stabilityai/stable-diffusion-3-5-large",
    },
    "comfyui": {
        "base_url": "http://127.0.0.1:8188",
        "alt_url": "http://127.0.0.1:8189",
        "output_dir": "",
    },
    "generation": {
        "default_width": 1024,
        "default_height": 1024,
        "default_steps": 25,
        "default_model": "dreamshaper_8.safetensors",
    },
}


def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            cfg = DEFAULT_CONFIG.copy()
            _deep_merge(cfg, saved)
            return cfg
        except Exception:
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def _deep_merge(base: dict, override: dict) -> None:
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
