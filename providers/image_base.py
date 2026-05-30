from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ImageResult:
    image_data: bytes
    filename: str
    save_path: str = ""


class ImageProvider(ABC):
    """Image generation provider (local or cloud)."""

    name: str = "base"
    label: str = "Base"

    @abstractmethod
    def is_available(self) -> bool:
        ...

    @abstractmethod
    def generate(self, prompt: str, negative_prompt: str = "",
                 width: int = 1024, height: int = 1024, steps: int = 25,
                 seed: int = -1, **kwargs) -> ImageResult:
        ...
