import os
import json
import time
import requests
from .image_base import ImageProvider, ImageResult


class ComfyUIProvider(ImageProvider):
    name = "comfyui"
    label = "ComfyUI (Local)"

    def __init__(self, base_url: str = "http://127.0.0.1:8188",
                 workflow_dir: str = "",
                 output_dir: str = ""):
        self.base_url = base_url
        self.alt_url = "http://127.0.0.1:8189"
        self.workflow_dir = workflow_dir
        self.output_dir = output_dir

    def _detect_url(self) -> str:
        for url in [self.alt_url, self.base_url]:
            try:
                r = requests.get(f"{url}/system_stats", timeout=2)
                if r.status_code == 200:
                    r.json()
                    return url
            except Exception:
                pass
        return self.base_url

    def is_available(self) -> bool:
        try:
            url = self._detect_url()
            r = requests.get(f"{url}/system_stats", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def load_workflow(self, name: str) -> dict:
        path = os.path.join(self.workflow_dir, f"{name}_api.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Workflow not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def upload_image(self, image_path: str) -> str:
        url = f"{self._detect_url()}/upload/image"
        with open(image_path, "rb") as f:
            files = {"image": (os.path.basename(image_path), f, "image/png")}
            data = {"type": "input", "overwrite": "true"}
            r = requests.post(url, files=files, data=data, timeout=30)
        r.raise_for_status()
        return r.json().get("name", os.path.basename(image_path))

    def generate(self, prompt: str, negative_prompt: str = "",
                 width: int = 1024, height: int = 1024, steps: int = 25,
                 seed: int = -1, **kwargs) -> ImageResult:
        url = self._detect_url()
        workflow_name = kwargs.get("workflow", "txt2img")
        model_name = kwargs.get("model_name", "dreamshaper_8.safetensors")
        ref_image_name = kwargs.get("ref_image_name", "")
        denoise = kwargs.get("denoise", 0.55)
        use_ipadapter = kwargs.get("use_ipadapter", False)
        use_img2img = kwargs.get("use_img2img", False)

        workflow = self.load_workflow(workflow_name)

        for node_id, node in workflow.items():
            class_type = node.get("class_type", "")
            if class_type == "CheckpointLoaderSimple":
                node["inputs"]["ckpt_name"] = model_name
            elif class_type == "CLIPTextEncode":
                meta_title = node.get("_meta", {}).get("title", "")
                if "Positive" in meta_title or node_id in ("2", "6"):
                    node["inputs"]["text"] = prompt
                elif "Negative" in meta_title or node_id in ("3", "7"):
                    node["inputs"]["text"] = negative_prompt
            elif class_type == "EmptyLatentImage":
                node["inputs"]["width"] = width
                node["inputs"]["height"] = height
            elif class_type == "KSampler":
                node["inputs"]["steps"] = steps
                if seed >= 0:
                    node["inputs"]["seed"] = seed
                node["inputs"]["control_after_generate"] = "fixed"
                if use_img2img:
                    node["inputs"]["denoise"] = denoise
            elif class_type == "LoadImage" and ref_image_name:
                node["inputs"]["image"] = ref_image_name

        payload = {"prompt": workflow, "client_id": "ai_image_studio"}
        r = requests.post(f"{url}/prompt", json=payload, timeout=30)
        r.raise_for_status()
        result = r.json()

        if "prompt_id" not in result:
            raise Exception(f"ComfyUI error: {json.dumps(result, ensure_ascii=False)[:500]}")

        prompt_id = result["prompt_id"]

        for _ in range(90):
            time.sleep(2)
            try:
                r = requests.get(f"{url}/history/{prompt_id}", timeout=10)
                r.raise_for_status()
                history = r.json()
                if prompt_id in history:
                    outputs = history[prompt_id].get("outputs", {})
                    for node_output in outputs.values():
                        if "images" in node_output:
                            for img_info in node_output["images"]:
                                filename = img_info["filename"]
                                subfolder = img_info.get("subfolder", "")
                                folder_type = img_info.get("type", "output")
                                r2 = requests.get(f"{url}/view", params={
                                    "filename": filename,
                                    "subfolder": subfolder,
                                    "type": folder_type,
                                })
                                save_path = os.path.join(self.output_dir, filename)
                                return ImageResult(
                                    image_data=r2.content,
                                    filename=filename,
                                    save_path=save_path,
                                )
            except Exception:
                continue

        raise TimeoutError("ComfyUI generation timed out")
