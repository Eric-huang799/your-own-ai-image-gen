import requests
from .llm_base import LLMProvider


class ClaudeProvider(LLMProvider):
    name = "claude"
    label = "Claude (Cloud)"

    def __init__(self, api_key: str = "", model: str = "claude-sonnet-4-6", base_url: str = "https://api.anthropic.com/v1"):
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
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": 300,
            "messages": [
                {"role": "user", "content": system_prompt},
            ],
        }

        r = requests.post(
            f"{self.base_url}/messages",
            headers=headers,
            json=payload,
            timeout=30,
        )
        r.raise_for_status()
        result = r.json()["content"][0]["text"].strip()
        return self._clean_response(result)
