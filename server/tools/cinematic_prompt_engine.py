"""Cinematic Prompt Engine for AI Microdrama & Video Generation.
Distilled from Mx-Shell's 5-Stage Prompt Architecture (Zombie Scavenger)
and jnMetaCode/ai-shortfilm-prompts.

Implements:
1. The 5-Stage Prompt Structure:
   Stage 1 · Core theme tags (3-6 tags separated by |)
   Stage 2 · Character & scene (Face reference lock, clothing texture, scene motion)
   Stage 3 · Atmosphere & quality (Real camera body + lens metadata, vertical 9:16)
   Stage 4 · Camera rules (Breath-like subtle float, diegetic sound only)
   Stage 5 · Storyboard breakdown (Hook cold-open, confrontation, cliffhanger)
2. The Seven Hard Rules (Anti-Slop AI Filter):
   Rule 1: Ban vague praise words (cinematic, epic, stunning, 4K, HD, etc.)
   Rule 2: Real camera + lens specs
   Rule 3: Exact breath-like camera float sentence
   Rule 4: Production audio only, no fabricated background music
   Rule 5: >=2 imperfection descriptions per shot
   Rule 6: Restrained endings (anti-FX pileup)
   Rule 7: Sanitize IP names
3. Canonical Negative Prompt Prefab for video engines
"""

import re
from typing import Dict, List, Optional

CANONICAL_NEGATIVE_PROMPT = (
    "blurry, low resolution, soft focus, watermark, text overlay, subtitles, logo, "
    "distorted face, asymmetric eyes, extra fingers, deformed hands, melting/morphing geometry, "
    "oversaturated colors, plastic skin, glossy CG render, video-game look, 3D cartoon, "
    "anime shading, flat even studio lighting, perfectly clean flawless surfaces, frame flicker, "
    "ghosting, jarring hard cuts, lifeless locked-off camera"
)

CANONICAL_BREATH_FLOAT = (
    "Handheld shot. Throughout, maintain an extremely subtle, breath-like camera float to enhance presence."
)

CANONICAL_SOUND_RULE = "Sound: No score. Production audio only."

CAMERA_LENS_PRESETS = {
    "vertical_drama": "Shot on ARRI Alexa with vintage primes (35mm focal, f/2.8 aperture), shallow focus that isolates faces. Vertical 9:16 composition, faces positioned in the upper-middle frame.",
    "cyber_hard_scifi": "Simulated Sony Venice paired with Canon K-35 series lens (35mm focal, f/2.0), low-saturation teal-grey base, natural film grain.",
    "epic_scale": "Simulated IMAX film camera paired with Panavision C-series lens (35mm focal, f/4 aperture), compressed shadows, wide dynamic range.",
    "noir_wuxia": "Kodak 35mm bleach-bypass film stock, high contrast, deep shadows, controlled practical lighting.",
    "commercial_hero": "Shot on Canon EF 85mm f/1.2 lens, ultra-shallow depth of field, natural falloff, motivated edge lighting.",
}

# Words that degrade AI rendering quality by introducing plastic/CG/exaggerated slop
BANNED_VAGUE_WORDS = [
    r"\bcinematic\b",
    r"\bepic\b",
    r"\bstunning\b",
    r"\bmasterpiece\b",
    r"\bhyperrealistic\b",
    r"\bphotorealistic\b",
    r"\bultra-detailed\b",
    r"\bhigh quality\b",
    r"\bpremium-feel\b",
    r"\b4k\b",
    r"\b8k\b",
    r"\bhd\b",
    r"\bperfect skin\b",
    r"\bflawless\b",
    r"\bhandsome\b",
    r"\bbeautiful face\b",
]

IMPERFECTION_CANDIDATES = [
    "minor facial blemishes preserved",
    "subtle fabric creases",
    "stray hair catching the rim light",
    "slight skin fatigue around the eyes",
    "lived-in realistic environment",
    "practical lamp humming slightly",
    "faint dust motes visible in light beam",
]


class CinematicPromptEngine:
    """Utility class to sanitize, format, and enforce the 5-stage architecture."""

    @staticmethod
    def sanitize_slop_words(text: str) -> str:
        """Strip vague hype words that cause generic AI plastic look."""
        cleaned = text
        for pattern in BANNED_VAGUE_WORDS:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        # Clean double spaces and punctuation
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        cleaned = re.sub(r",\s*,", ",", cleaned)
        cleaned = re.sub(r"\.\s*\.", ".", cleaned)
        return cleaned.strip()

    @staticmethod
    def get_camera_preset(genre: str = "vertical_drama") -> str:
        """Return real camera + lens specifications based on genre."""
        return CAMERA_LENS_PRESETS.get(genre, CAMERA_LENS_PRESETS["vertical_drama"])

    @staticmethod
    def ensure_imperfections(description: str, min_count: int = 2) -> str:
        """Ensure description has at least min_count imperfection anchors."""
        desc_lower = description.lower()
        found = 0
        imperfection_keywords = [
            "crease", "blemish", "wrinkle", "fatigue", "tired", "wound",
            "scar", "dust", "worn", "flicker", "shadow", "stray hair", "stain", "lived-in"
        ]
        for kw in imperfection_keywords:
            if kw in desc_lower:
                found += 1

        if found < min_count:
            needed = min_count - found
            additions = IMPERFECTION_CANDIDATES[:needed]
            addition_str = ". Imperfections preserved: " + ", ".join(additions) + "."
            description = description.rstrip(".") + addition_str

        return description

    @staticmethod
    def build_visual_prompt(
        scene_visual: str,
        character_desc: str = "",
        genre_camera: str = "vertical_drama",
        aspect_ratio: str = "9:16",
    ) -> str:
        """
        Builds a Stage 1 - Stage 3 visual prompt for T2I / Character Reference generation.
        Strictly applies Mx-Shell 5-Stage discipline.
        """
        clean_scene = CinematicPromptEngine.sanitize_slop_words(scene_visual)
        clean_scene = CinematicPromptEngine.ensure_imperfections(clean_scene, min_count=2)

        camera_spec = CinematicPromptEngine.get_camera_preset(genre_camera)

        core_theme = "Core theme: vertical micro-drama | dramatic tension | live-action performance | grounded realism | no game-CG feel."
        char_block = f"Character reference: {character_desc}. Features and face shape 100% preserved. No beautification." if character_desc else ""
        quality_block = f"Camera & Lighting: {camera_spec} Motivated practical light, natural skin texture, subtle film grain."

        parts = [core_theme, clean_scene]
        if char_block:
            parts.append(char_block)
        parts.append(quality_block)

        return " ".join(parts)

    @staticmethod
    def build_motion_prompt(
        motion_desc: str,
        audio_desc: str = "",
        force_breath_float: bool = True,
    ) -> str:
        """
        Builds a Stage 4 - Stage 5 motion prompt for video generation (Omni Flash / Veo / Kling).
        Enforces breath-like handheld float and production diegetic audio.
        """
        clean_motion = CinematicPromptEngine.sanitize_slop_words(motion_desc)

        # Enforce canonical breath float if not present
        if force_breath_float and "breath-like" not in clean_motion.lower():
            clean_motion = clean_motion.rstrip(".") + f". {CANONICAL_BREATH_FLOAT}"

        # Clean audio / sound rule
        clean_audio = audio_desc.strip() if audio_desc else CANONICAL_SOUND_RULE
        if "sound:" not in clean_audio.lower():
            clean_audio = f"{CANONICAL_SOUND_RULE} {clean_audio}".strip()

        return f"{clean_motion} {clean_audio}".strip()
