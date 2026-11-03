import re
from typing import Optional, Tuple
from tools.muapi_llm import MuAPILLM

REFUSAL_PATTERNS = [
    r"safety\s*(?:system|policy|filter|guidelines)",
    r"cannot\s+(?:generate|create|fulfill|process)",
    r"content\s+(?:policy|violation|warning|moderation)",
    r"prohibited\s+(?:content|words|elements)",
    r"sensitive\s+theme",
    r"blocked\s+by\s+safety",
    r"refused",
    r"nsfw|violence|weapon|blood|harm",
]

class AutoFixEngine:
    """
    Intelligent Prompt Auto-Fix & Repair Engine.
    Detects AI safety refusal errors and automatically rewrites prompts
    using 9Router LLM so they bypass censorship filters while preserving
    cinematic visual drama, tension, and storytelling intent.
    """

    def __init__(self, llm: Optional[MuAPILLM] = None):
        self.llm = llm or MuAPILLM()

    def is_refusal_error(self, error_message: str) -> bool:
        """Check if an error string indicates a safety filter or content refusal."""
        if not error_message:
            return False
        err_lower = error_message.lower()
        for pattern in REFUSAL_PATTERNS:
            if re.search(pattern, err_lower):
                return True
        return False

    async def repair_prompt(
        self,
        original_prompt: str,
        reason: str = "safety filter refusal",
        media_type: str = "image",
    ) -> str:
        """
        Rewrite a rejected prompt into a compliant, cinematic version.
        Replaces sensitive trigger words (e.g. violent actions, blood, intense physical harm)
        with symbolic, atmospheric, and high-tension cinematic storytelling alternatives.
        """
        system_prompt = (
            "You are an expert AI Prompt Compliance and Cinematic Safety Engineer. "
            "Your task is to rewrite rejected AI prompts to strictly comply with AI content filters (ChatGPT, Google, Midjourney) "
            "WITHOUT losing the original dramatic intensity, emotional arc, and visual composition.\n\n"
            "Rules:\n"
            "- Remove any explicit violence, gore, weapons, blood, or policy-triggering keywords.\n"
            "- Replace physical harm with psychological tension, dramatic confrontation, shadows, expressions, and atmospheric lighting.\n"
            "- For medical/drama scenes: frame as urgent clinical care or dramatic recovery rather than injury.\n"
            "- Output ONLY the rewritten prompt string in plain English. No preamble, no quotes, no explanation."
        )

        user_prompt = f"""The following {media_type} prompt was REJECTED by an AI safety filter ({reason}):

Original Prompt:
{original_prompt}

Please rewrite this prompt so it passes all safety and moderation filters while preserving 100% of the cinematic tension, characters, lighting, and composition."""

        try:
            repaired = await self.llm.complete(
                prompt=user_prompt,
                system_prompt=system_prompt,
                timeout=45,
                fallback=self._rule_based_sanitize(original_prompt),
            )
            clean_result = repaired.strip().strip('"').strip("'")
            print(f"[AutoFix] Successfully repaired prompt:\n  Original: {original_prompt[:60]}...\n  Repaired: {clean_result[:60]}...")
            return clean_result
        except Exception as e:
            print(f"[AutoFix] LLM repair failed ({e}), using rule-based sanitizer.")
            return self._rule_based_sanitize(original_prompt)

    def _rule_based_sanitize(self, prompt: str) -> str:
        """Fallback rule-based keyword sanitization."""
        substitutions = [
            (r"\bblood(?:y)?\b", "shadows and raindrops"),
            (r"\bkilled|murdered|stabbed|shot\b", "confronted dramatically"),
            (r"\bgun|knife|weapon|pistol\b", "clenched fist"),
            (r"\bcorpse|dead body\b", "unconscious person"),
            (r"\btorture|beat up\b", "intense argument"),
            (r"\bgore|wound(?:ed)?\b", "exhausted and weary"),
        ]
        clean = prompt
        for pat, repl in substitutions:
            clean = re.sub(pat, repl, clean, flags=re.IGNORECASE)
        return clean
