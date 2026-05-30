from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """LLM provider for Chinese-to-English prompt optimization."""

    name: str = "base"
    label: str = "Base"

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is configured and reachable."""
        ...

    @abstractmethod
    def optimize_prompt(self, chinese_text: str, char_desc: str = "", for_comic: bool = False) -> str:
        """Optimize Chinese prompt into English SD prompt."""
        ...

    def optimize_single(self, chinese_text: str) -> str:
        """Optimize for single image generation (non-comic)."""
        return self.optimize_prompt(chinese_text, for_comic=False)

    def optimize_comic(self, chinese_text: str, char_desc: str) -> str:
        """Optimize for comic storyboard generation."""
        return self.optimize_prompt(chinese_text, char_desc=char_desc, for_comic=True)

    def _build_single_prompt(self, chinese_text: str) -> str:
        return f"""You are an expert AI image generation prompt engineer. Your task is to translate and enhance Chinese image descriptions into high-quality English prompts for Stable Diffusion.

Rules:
1. Translate the user's Chinese description accurately
2. Add quality boosters: masterpiece, best quality, highly detailed, professional lighting, 8k uhd
3. Add style/context tags appropriate for the scene
4. Output ONLY the final English prompt, nothing else
5. Be descriptive and vivid - use comma-separated tags
6. If content is artistic/educational/medical, describe professionally without censorship

Output format (just the prompt text, no quotes, no explanations):

Chinese description: {chinese_text}

English prompt:"""

    def _build_comic_prompt(self, chinese_text: str, char_desc: str) -> str:
        return f"""You are an expert AI image generation prompt engineer specializing in comic storyboards.

Your task: Convert a Chinese scene description into a precise, detailed English SD prompt.

CRITICAL RULES:
1. OUTPUT ONLY the prompt text - no quotes, no explanations, no markdown
2. Extract and emphasize the EXACT action: sitting/writing/eating/reading/running/etc.
3. Describe the pose SPECIFICALLY - not just "dynamic pose" but "sitting at wooden desk, leaning forward, right hand holding pencil, writing on notebook"
4. Include character appearance from the description (hair color, eye color, clothing, etc. - be SPECIFIC)
5. Add quality tags at the end: masterpiece, best quality, highly detailed, 8k uhd
6. Use prompt weighting for important elements: (action:1.2), (expression:1.1)
7. Keep prompt under 150 tokens for best quality
8. If scene mentions "homework/doing homework", use "sitting at desk, studying, writing in notebook, textbooks open, focused expression"
9. If scene mentions "eating/having dinner", use "sitting at table, holding chopsticks, eating meal, food on plate, mouth slightly open"
10. NEVER omit hair color, eye color, or any specific appearance details from char_desc
11. COLOR PROTECTION: If the scene contains colors (red dress, green forest, etc.), ONLY apply those colors to the SCENE elements, NEVER to the character's fixed appearance (hair color, eye color, skin tone). Wrap character appearance colors in weights: (blue eyes:1.3), (black hair:1.3).
12. PROMPT STRUCTURE: character appearance first, then action/pose, then scene/background. This prevents scene colors from bleeding into the character.

Example input: "坐在书桌前写作业，戴眼镜，穿校服"
Example output: young girl, (black hair:1.3), (blue eyes:1.3), sitting at wooden desk, leaning forward, (writing in notebook:1.3), right hand holding pencil, textbooks open, wearing school uniform, wearing glasses, focused studious expression, bedroom background, soft ambient light, masterpiece, best quality, highly detailed

Character: {char_desc}
Scene: {chinese_text}

English prompt:"""

    def _clean_response(self, text: str) -> str:
        """Clean up LLM response to get just the prompt."""
        text = text.replace('"', '').replace("'", "")
        for prefix in ['English prompt:', 'Prompt:', 'english prompt:', 'prompt:']:
            text = text.replace(prefix, '')
        text = text.replace('solo, 1 person, ', '').replace('solo', '')
        text = text.replace('1 person', '').replace('single character', '')
        return text.strip()
