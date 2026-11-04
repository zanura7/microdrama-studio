import os
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from PIL import Image
from tools.cinematic_prompt_engine import (
    CinematicPromptEngine,
    CANONICAL_BREATH_FLOAT,
    CANONICAL_SOUND_RULE,
)


class StoryboardSlicer:
    """
    Storyboard Sheets Generator & Slicer Engine.
    Adopts the Flow Studio / 0xFlow paradigm:
    "4 scenes. 1 image. ~70% fewer credits. Perfect character consistency."
    
    1. Formulates a structured 2x2 grid prompt for up to 4 sequential shots.
    2. Slices the generated 2x2 sheet into 4 individual 9:16 vertical start frames.
    """

    @staticmethod
    def build_sheet_prompt(
        shots: List[Dict[str, Any]],
        characters: List[Any],
        style: str = "vertical_drama",
        atmosphere_lock: Optional[str] = None,
    ) -> str:
        """
        Builds a comprehensive prompt directing image models (SnapGen / Google Flow / Midjourney)
        to render a 2x2 quadrant storyboard sheet with identical characters and cohesive lighting.
        Enforces Atmosphere Lock & anti-slop rules.
        """
        char_desc = ""
        if characters:
            char_desc = " ".join([
                f"{getattr(c, 'name', '')}: {getattr(c, 'static_features', '')}, wearing {getattr(c, 'dynamic_features', '')}."
                for c in characters if getattr(c, 'is_visible', True)
            ])
        char_desc = CinematicPromptEngine.sanitize_slop_words(char_desc)

        panel_labels = [
            "Top-Left Panel (Scene 1)",
            "Top-Right Panel (Scene 2)",
            "Bottom-Left Panel (Scene 3)",
            "Bottom-Right Panel (Scene 4)",
        ]

        panels_text = []
        for idx, shot in enumerate(shots[:4]):
            label = panel_labels[idx] if idx < len(panel_labels) else f"Panel {idx + 1}"
            raw_desc = shot.get("visual_desc", "") or shot.get("prompt", "")
            clean_desc = CinematicPromptEngine.sanitize_slop_words(raw_desc)
            panels_text.append(f"[{label}]: {clean_desc}")

        joined_panels = "\n".join(panels_text)

        if not atmosphere_lock:
            atmosphere_lock = CinematicPromptEngine.generate_atmosphere_lock(
                genre_camera="vertical_drama", style_mood=style
            )

        prompt = (
            "A clean 2x2 grid live-action storyboard sheet displaying 4 sequential story scenes. "
            f"{atmosphere_lock}\n"
            f"CHARACTER CONTINUITY RULE: Characters ({char_desc}) MUST look 100% identical with exact same face, hair, and clothing in all 4 panels. Features 100% preserved, no beautification.\n\n"
            "Panels layout:\n"
            f"{joined_panels}\n\n"
            "Crisp dividing borders between the 4 quadrants, consistent color grading, photorealistic vertical film compositions."
        )
        return prompt

    @staticmethod
    def slice_sheet(
        image_path: str,
        output_dir: str,
        prefix: str = "frame",
        target_aspect_ratio: Tuple[int, int] = (9, 16),
    ) -> List[str]:
        """
        Slices a 2x2 grid image into 4 vertical 9:16 frame images.
        Quadrant order:
          0: Top-Left (Scene 1)
          1: Top-Right (Scene 2)
          2: Bottom-Left (Scene 3)
          3: Bottom-Right (Scene 4)
        """
        src = Path(image_path)
        if not src.is_file():
            raise FileNotFoundError(f"Storyboard sheet file not found: {image_path}")

        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        with Image.open(src) as img:
            # Ensure RGB
            if img.mode != "RGB":
                img = img.convert("RGB")

            width, height = img.size
            mid_x = width // 2
            mid_y = height // 2

            quadrants = [
                (0, 0, mid_x, mid_y),          # Top-Left (1)
                (mid_x, 0, width, mid_y),      # Top-Right (2)
                (0, mid_y, mid_x, height),     # Bottom-Left (3)
                (mid_x, mid_y, width, height), # Bottom-Right (4)
            ]

            saved_frames = []
            for idx, box in enumerate(quadrants):
                cropped = img.crop(box)
                
                # Fit cropped quadrant into 9:16 vertical format
                w, h = cropped.size
                target_w_ratio, target_h_ratio = target_aspect_ratio
                target_ratio = target_w_ratio / target_h_ratio
                current_ratio = w / h

                if current_ratio > target_ratio:
                    # Current is wider than 9:16, crop sides
                    new_w = int(h * target_ratio)
                    offset_x = (w - new_w) // 2
                    final_frame = cropped.crop((offset_x, 0, offset_x + new_w, h))
                else:
                    # Current is taller than 9:16, crop top/bottom slightly
                    new_h = int(w / target_ratio)
                    offset_y = (h - new_h) // 2
                    final_frame = cropped.crop((0, offset_y, w, offset_y + new_h))

                # Standardize resolution (720x1280 for HD vertical 9:16)
                final_frame = final_frame.resize((720, 1280), Image.Resampling.LANCZOS)

                frame_filename = f"{prefix}_{idx + 1:02d}.png"
                frame_filepath = out_path / frame_filename
                final_frame.save(frame_filepath, format="PNG", quality=95)
                saved_frames.append(str(frame_filepath.resolve()))
                print(f"[StoryboardSlicer] Sliced panel {idx + 1} -> {frame_filepath.name} (720x1280, 9:16)")

            return saved_frames
