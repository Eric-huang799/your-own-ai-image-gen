from .llm_base import LLMProvider
from .image_base import ImageProvider
from .ollama_llm import OllamaProvider
from .openai_llm import OpenAIProvider
from .claude_llm import ClaudeProvider
from .deepseek_llm import DeepSeekProvider
from .comfyui_image import ComfyUIProvider
from .stability_image import StabilityAIProvider
from .siliconflow_image import SiliconFlowProvider
from .wanvideo_provider import WanVideoProvider

LLM_PROVIDERS = {
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
    "claude": ClaudeProvider,
    "deepseek": DeepSeekProvider,
}

IMAGE_PROVIDERS = {
    "comfyui": ComfyUIProvider,
    "stability": StabilityAIProvider,
    "siliconflow": SiliconFlowProvider,
    "wanvideo": WanVideoProvider,
}
