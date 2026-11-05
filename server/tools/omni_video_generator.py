import asyncio
import os
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional

# Internal Decoupled Engine
try:
    from engines.flow_engine import flow, flow_two_layer
    from engines.flow_engine.paths import get_flow_profile_dir, get_app_data_dir
    HAS_FLOW_ENGINE = True
except Exception as e_internal:
    # Optional fallback for local dev PC
    FLOW_ENGINE_PATH = Path(r"C:\Users\HP\flow-video-generator")
    if FLOW_ENGINE_PATH.exists() and str(FLOW_ENGINE_PATH) not in sys.path:
        sys.path.insert(0, str(FLOW_ENGINE_PATH))
    try:
        from flowvideo import flow, flow_two_layer
        HAS_FLOW_ENGINE = True
    except Exception as e_ext:
        HAS_FLOW_ENGINE = False
        print(f"[OmniVideoGenerator] Warning: Could not import flow engine ({e_internal} / {e_ext})")

from tools.cinematic_prompt_engine import (
    CinematicPromptEngine,
    CANONICAL_BREATH_FLOAT,
    CANONICAL_NEGATIVE_PROMPT,
)


class OmniVideoGenerator:
    """Google Omni Flash 1.1 Video Generator for Microdrama series.
    Decoupled & cross-platform ready (Windows & macOS).
    Zero API cost, leverages authenticated Google Flow session.
    """

    def __init__(self, account_name: str = "auto", profile_path: Optional[str] = None):
        self.account_name = account_name
        if profile_path:
            self.profile_path = Path(profile_path)
        elif os.environ.get("FLOW_PROFILE"):
            self.profile_path = Path(os.environ["FLOW_PROFILE"])
        else:
            try:
                from engines.flow_engine.paths import get_flow_profile_dir
                self.profile_path = get_flow_profile_dir(account_name if account_name != "auto" else "default")
            except Exception:
                self.profile_path = Path.home() / ".google-flow-creator" / "browser-profile"

    async def generate_video_from_image(
        self,
        prompt: str,
        image_url: Optional[str] = None,
        duration: int = 10,
        aspect_ratio: str = "9:16",
        output_path: Optional[str] = None,
    ) -> str:
        """Render a 10s 9:16 video clip using Google Omni Flash 1.1 with or without character reference."""
        if not HAS_FLOW_ENGINE:
            raise RuntimeError(
                "Engine flow-video-generator tidak ditemukan"
            )

        # 1. Ensure local reference image if provided
        ref_image_path = None
        if image_url:
            try:
                ref_image_path = await self._resolve_local_image(image_url)
            except Exception as e:
                print(f"[OmniFlash1.1] Warning: Cannot resolve image '{image_url}': {e}. Falling back to prompt-only render.")
                ref_image_path = None

        # 2. Sanitize prompt & enforce Mx-Shell breath-like camera float
        enhanced_prompt = CinematicPromptEngine.sanitize_slop_words(prompt)
        if "breath-like" not in enhanced_prompt.lower():
            enhanced_prompt = f"{enhanced_prompt.rstrip('.')}. {CANONICAL_BREATH_FLOAT}"

        # 3. Run FlowTwoLayerGenerator in threadpool to keep async loop unblocked
        loop = asyncio.get_running_loop()
        final_video_path = await loop.run_in_executor(
            None,
            self._execute_flow_render,
            enhanced_prompt,
            ref_image_path,
            aspect_ratio,
            output_path,
        )

        return final_video_path

    def _execute_flow_render(
        self,
        prompt: str,
        ref_image_path: str,
        aspect_ratio: str,
        output_path: Optional[str],
    ) -> str:
        """Synchronous wrapper for Google Flow 2-Layer generator."""
        print(f"[OmniFlash1.1] Starting render for prompt: {prompt[:60]}...")
        print(f"[OmniFlash1.1] Using reference image: {ref_image_path}")

        has_cookies = self.profile_path and (self.profile_path / "Default" / "Network" / "Cookies").exists()
        generator = flow_two_layer.FlowTwoLayerGenerator(
            account_name=self.account_name,
            profile=self.profile_path if has_cookies else None,
            allow_offscreen_fallback=True,
            on_log=lambda lvl, msg: print(f"[OmniFlash1.1][{lvl}] {msg}", flush=True),
        )

        result = generator.generate(
            prompt=prompt,
            image_paths=[ref_image_path] if ref_image_path else [],
            aspect_ratio=aspect_ratio or "9:16",
            output_path=output_path,
            timeout_seconds=360,
        )

        if not result.get("success") or not result.get("video_path"):
            err = result.get("error") or "Google Omni Flash gagal menghasilkan video."
            raise RuntimeError(f"Omni Flash render error: {err}")

        video_path = result["video_path"]
        print(f"[OmniFlash1.1] Video successfully created: {video_path}")
        return video_path

    async def _resolve_local_image(self, image_url: str) -> str:
        """Convert remote URL or local path into a verified local file path."""
        p = Path(image_url)
        if p.exists() and p.is_file():
            return str(p.resolve())

        # If it's a web URL, download to a temporary file
        if image_url.startswith("http://") or image_url.startswith("https://"):
            temp_dir = Path(tempfile.gettempdir()) / "microdrama_refs"
            temp_dir.mkdir(parents=True, exist_ok=True)
            local_dest = temp_dir / f"ref_{os.path.basename(image_url).split('?')[0]}"
            if not local_dest.suffix:
                local_dest = local_dest.with_suffix(".png")

            def download():
                req = urllib.request.Request(
                    image_url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                )
                with urllib.request.urlopen(req, timeout=30) as r, open(local_dest, "wb") as f:
                    f.write(r.read())

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, download)
            return str(local_dest.resolve())

        return image_url
