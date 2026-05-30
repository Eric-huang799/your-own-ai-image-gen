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
        """Only probes once via _detect_url, avoids double HTTP request."""
        try:
            url = self._detect_url()
            # _detect_url already verified the URL is alive if it returned non-default
            # If it returned base_url, we need to verify it wasn't just the fallback
            if url == self.base_url:
                # Probe base_url once to confirm
                r = requests.get(f"{url}/system_stats", timeout=2)
                return r.status_code == 200
            return True  # alt_url was verified by _detect_url
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

        # Workflow is now API format: dict keyed by node ID string
        # Inject parameters into the correct node inputs
        for nid, node in workflow.items():
            ntype = node.get("class_type", "")
            inputs = node.get("inputs", {})

            if ntype == "WanVideoTextEncode":
                inputs["positive_prompt"] = prompt
                inputs["negative_prompt"] = negative_prompt

            elif ntype == "WanVideoEmptyEmbeds":
                inputs["width"] = width
                inputs["height"] = height
                inputs["num_frames"] = num_frames

            elif ntype == "WanVideoSampler":
                inputs["steps"] = steps
                inputs["cfg"] = cfg
                inputs["shift"] = shift
                inputs["seed"] = seed if seed >= 0 else 42

            elif ntype == "SaveAnimatedWEBP":
                inputs["fps"] = float(frame_rate)

        payload = {"prompt": workflow, "client_id": "ai_video_studio"}
        r = requests.post(f"{url}/prompt", json=payload, timeout=30)
        if r.status_code != 200:
            detail = ""
            try:
                detail = r.text[:800]
            except Exception:
                pass
            raise Exception(
                f"ComfyUI {r.status_code} Error.\n"
                f"Common causes: missing model file, wrong path, or incompatible node version.\n"
                f"Details: {detail}"
            )
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
