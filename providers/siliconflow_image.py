import io
import time
import requests
from .image_base import ImageProvider, ImageResult


class SiliconFlowProvider(ImageProvider):
    """SiliconFlow (硅基流动) - Chinese cloud service with SD models.
    API docs: https://docs.siliconflow.cn
    Models: stabilityai/stable-diffusion-3-5-large, black-forest-labs/FLUX.1-dev, etc.
    """

    name = "siliconflow"
    label = "SiliconFlow 硅基流动 (Cloud)"

    def __init__(self, api_key: str = "", model: str = "stabilityai/stable-diffusion-3-5-large"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.siliconflow.cn/v1"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, negative_prompt: str = "",
                 width: int = 1024, height: int = 1024, steps: int = 0,
                 seed: int = -1, **kwargs) -> ImageResult:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "prompt": prompt,
            "negative_prompt": negative_prompt or "blurry, low quality, distorted, bad anatomy",
            "image_size": f"{width}x{height}",
            "batch_size": 1,
            "num_inference_steps": steps if steps > 0 else 20,
        }
        if seed >= 0:
            payload["seed"] = seed

        r = requests.post(
            f"{self.base_url}/images/generations",
            headers=headers,
            json=payload,
            timeout=120,
        )
        r.raise_for_status()
        result = r.json()

        images = result.get("images", [])
        if not images:
            raise Exception(f"SiliconFlow returned no images: {result}")

        import base64
        img_data = base64.b64decode(images[0].get("image", images[0].get("b64_json", "")))
        filename = f"siliconflow_{int(time.time())}.png"
        return ImageResult(image_data=img_data, filename=filename)
