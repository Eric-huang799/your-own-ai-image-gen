import io
import time
import requests
from PIL import Image
from .image_base import ImageProvider, ImageResult


class StabilityAIProvider(ImageProvider):
    name = "stability"
    label = "Stability AI (Cloud)"

    def __init__(self, api_key: str = "", model: str = "stable-diffusion-xl-1024-v1-0"):
        self.api_key = api_key
        self.model = model

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, negative_prompt: str = "",
                 width: int = 1024, height: int = 1024, steps: int = 30,
                 seed: int = 0, **kwargs) -> ImageResult:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "image/png",
        }
        data = {
            "text_prompts": [
                {"text": prompt, "weight": 1.0},
                {"text": negative_prompt or "blurry, low quality, distorted", "weight": -1.0},
            ],
            "cfg_scale": 7,
            "steps": steps,
            "width": width,
            "height": height,
            "samples": 1,
        }
        if seed > 0:
            data["seed"] = seed

        r = requests.post(
            "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
            headers=headers,
            json=data,
            timeout=120,
        )
        r.raise_for_status()
        result = r.json()
        img_data = io.BytesIO()
        for i, image in enumerate(result.get("artifacts", [])):
            if image.get("base64"):
                import base64
                img_data.write(base64.b64decode(image["base64"]))
        img_data.seek(0)
        filename = f"stability_{int(time.time())}.png"
        return ImageResult(image_data=img_data.read(), filename=filename)

    def img2img(self, image_path: str, prompt: str, negative_prompt: str = "",
                strength: float = 0.55, **kwargs) -> ImageResult:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        with open(image_path, "rb") as f:
            files = {"init_image": f}
            data = {
                "text_prompts[0][text]": prompt,
                "text_prompts[0][weight]": 1,
                "text_prompts[1][text]": negative_prompt or "blurry, low quality",
                "text_prompts[1][weight]": -1,
                "image_strength": 1.0 - strength,
                "cfg_scale": 7,
                "samples": 1,
            }
            r = requests.post(
                "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/image-to-image",
                headers=headers,
                files=files,
                data=data,
                timeout=120,
            )
        r.raise_for_status()
        result = r.json()
        img_data = io.BytesIO()
        for image in result.get("artifacts", []):
            if image.get("base64"):
                import base64
                img_data.write(base64.b64decode(image["base64"]))
        img_data.seek(0)
        filename = f"stability_i2i_{int(time.time())}.png"
        return ImageResult(image_data=img_data.read(), filename=filename)
