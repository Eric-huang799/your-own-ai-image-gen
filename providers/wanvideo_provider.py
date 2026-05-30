import os
import json
import time
import requests
from .image_base import ImageProvider, ImageResult


class WanVideoProvider(ImageProvider):
    """Wan2.1 T2V video generation via ComfyUI WanVideoWrapper."""

    name = "wanvideo"
    label = "Wan2.1 Video (Local)"

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

    def load_workflow(self) -> dict:
        path = os.path.join(self.workflow_dir, "wan_t2v_api.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Wan2.1 workflow not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def generate(self, prompt: str, negative_prompt: str = "",
                 width: int = 832, height: int = 480, steps: int = 20,
                 seed: int = -1, **kwargs) -> ImageResult:
        url = self._detect_url()
        workflow = self.load_workflow()

        num_frames = kwargs.get("num_frames", 81)
        cfg = kwargs.get("cfg", 5.0)
        shift = kwargs.get("shift", 5.0)
        frame_rate = kwargs.get("frame_rate", 16)
        preview_enabled = kwargs.get("preview_enabled", True)

        for node in workflow.get("nodes", []):
            node_type = node.get("type", "")
            wv = node.get("widgets_values", [])

            if node_type == "WanVideoEmptyEmbeds":
                # widgets_values: [width, height, num_frames]
                node["widgets_values"] = [width, height, num_frames]

            elif node_type == "CLIPTextEncode":
                # Two CLIPTextEncode nodes: first is negative (id=50), second is positive (id=49)
                node_id = node.get("id", 0)
                if node_id == 50:
                    node["widgets_values"] = [negative_prompt]
                elif node_id == 49:
                    node["widgets_values"] = [prompt]

            elif node_type == "WanVideoTextEncode":
                # widgets_values: [prompt, negative_prompt, ...]
                if len(wv) >= 2:
                    wv[0] = prompt
                    wv[1] = negative_prompt
                    node["widgets_values"] = wv

            elif node_type == "WanVideoSampler":
                # widgets_values: [steps, cfg, shift, seed, ...]
                if len(wv) >= 4:
                    wv[0] = steps
                    wv[1] = cfg
                    wv[2] = shift
                    wv[3] = seed if seed >= 0 else 42
                    node["widgets_values"] = wv

            elif node_type == "VHS_VideoCombine":
                # widgets_values is a dict for this node type
                if isinstance(wv, dict):
                    wv["frame_rate"] = frame_rate
                    node["widgets_values"] = wv

            elif node_type == "WanVideoDecode":
                # widgets_values has tiled decode settings
                if isinstance(wv, list) and len(wv) >= 5:
                    wv[0] = preview_enabled
                    node["widgets_values"] = wv

        payload = {"prompt": workflow, "client_id": "ai_video_studio"}
        r = requests.post(f"{url}/prompt", json=payload, timeout=30)
        r.raise_for_status()
        result = r.json()

        if "prompt_id" not in result:
            raise Exception(f"ComfyUI error: {json.dumps(result, ensure_ascii=False)[:500]}")

        prompt_id = result["prompt_id"]

        for attempt in range(300):
            time.sleep(3)
            try:
                r = requests.get(f"{url}/history/{prompt_id}", timeout=10)
                r.raise_for_status()
                history = r.json()
                if prompt_id in history:
                    outputs = history[prompt_id].get("outputs", {})
                    for node_output in outputs.values():
                        if "gifs" in node_output:
                            for gif_info in node_output["gifs"]:
                                filename = gif_info["filename"]
                                subfolder = gif_info.get("subfolder", "")
                                folder_type = gif_info.get("type", "output")
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
                        # Also check for image outputs (some video nodes output MP4)
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

            if attempt % 30 == 0 and attempt > 0:
                pass

        raise TimeoutError("Wan2.1 video generation timed out (15 minutes)")
