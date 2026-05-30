import requests
from .llm_base import LLMProvider


class OpenAIProvider(LLMProvider):
    name = "openai"
    label = "OpenAI (Cloud)"

    def __init__(self, api_key: str = "", model: str = "gpt-4o-mini", base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    def is_available(self) -> bool:
        return bool(self.api_key)

    def optimize_prompt(self, chinese_text: str, char_desc: str = "", for_comic: bool = False) -> str:
        if for_comic and char_desc:
            system_prompt = self._build_comic_prompt(chinese_text, char_desc)
        else:
            system_prompt = self._build_single_prompt(chinese_text)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": system_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 300,
        }

        r = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        r.raise_for_status()
        result = r.json()["choices"][0]["message"]["content"].strip()
        return self._clean_response(result)
