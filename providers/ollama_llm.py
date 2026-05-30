import requests
from .llm_base import LLMProvider


class OllamaProvider(LLMProvider):
    name = "ollama"
    label = "Ollama (Local)"

    def __init__(self, base_url: str = "http://127.0.0.1:11434", model: str = "wizardlm-uncensored"):
        self.base_url = base_url
        self.model = model

    def is_available(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return [m.get("name", "") for m in r.json().get("models", [])]
        except Exception:
            return []

    def optimize_prompt(self, chinese_text: str, char_desc: str = "", for_comic: bool = False) -> str:
        temperature = 0.5 if for_comic else 0.7
        max_tokens = 250 if for_comic else 200

        if for_comic and char_desc:
            system_prompt = self._build_comic_prompt(chinese_text, char_desc)
        else:
            system_prompt = self._build_single_prompt(chinese_text)

        payload = {
            "model": self.model,
            "prompt": system_prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }

        r = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=60)
        r.raise_for_status()
        result = r.json().get("response", "").strip()
        return self._clean_response(result)
