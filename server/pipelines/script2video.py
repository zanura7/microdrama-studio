import asyncio
import os
import random
import shutil
from pathlib import Path
from typing import Callable, Awaitable, List, Optional

from agents.storyboard_artist import StoryboardArtist
from interfaces.character import CharacterInScene
from interfaces.shot import ShotDescription
from tools.muapi_image_generator import MuAPIImageGenerator
from tools.muapi_video_generator import MuAPIVideoGenerator
from tools.omni_video_generator import OmniVideoGenerator
from tools.muapi_uploader import upload_image_from_url
from tools.storyboard_slicer import StoryboardSlicer
from tools.autofix_engine import AutoFixEngine
from tools.cinematic_prompt_engine import (
    CinematicPromptEngine,
    CANONICAL_BREATH_FLOAT,
    CANONICAL_SOUND_RULE,
)
from utils.video import concatenate_videos, download_video, create_still_video


ProgressCallback = Callable[[str, str, int], Awaitable[None]]


class Script2VideoPipeline:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("MUAPI_KEY", "")
        self.storyboard_artist = StoryboardArtist()
        self.image_gen = MuAPIImageGenerator(api_key=self.api_key)

        video_engine = os.environ.get("VIDEO_ENGINE", "omni").lower().strip()
        if video_engine in ("omni", "flow", "google_flow", ""):
            account = os.environ.get("FLOW_ACCOUNT", "auto")
            profile = os.environ.get("FLOW_PROFILE")
            self.video_gen = OmniVideoGenerator(account_name=account, profile_path=profile)
        else:
            self.video_gen = MuAPIVideoGenerator(api_key=self.api_key)

        self.autofix = AutoFixEngine()

    async def run(
        self,
        script: str,
        characters: List[CharacterInScene],
        user_requirement: str,
        style: str,
        working_dir: str,
        progress_callback: ProgressCallback,
        scene_idx: int = 0,
        base_progress: int = 30,
        progress_range: int = 60,
        use_storyboard_sheets: bool = True,
    ) -> str:
        """
        Run the script-to-video pipeline for a single scene.
        Supports Flow Studio / 0xFlow style Storyboard Sheets (4 scenes in 1 image)
        and intelligent Auto-Fix safety repair.
        """
        Path(working_dir).mkdir(parents=True, exist_ok=True)

        # Step 1: Generate character portraits in parallel
        await progress_callback(
            "portraits",
            f"Generating character portraits for scene {scene_idx + 1}...",
            base_progress + int(progress_range * 0.05),
        )
        character_portrait_urls: dict[str, str] = {}
        if characters:
            portrait_tasks = {
                c.name: self._generate_portrait(c, style)
                for c in characters
                if c.is_visible
            }
            results = await asyncio.gather(*portrait_tasks.values(), return_exceptions=True)
            for name, result in zip(portrait_tasks.keys(), results):
                if isinstance(result, Exception):
                    # Non-fatal: continue without portrait
                    print(f"Warning: portrait generation failed for {name}: {result}")
                else:
                    character_portrait_urls[name] = result

        # Step 2: Design storyboard
        await progress_callback(
            "storyboard",
            f"Designing storyboard for scene {scene_idx + 1}...",
            base_progress + int(progress_range * 0.15),
        )
        shots_brief = await self.storyboard_artist.design_storyboard(
            script, characters, f"{user_requirement}. Style: {style}"
        )

        shots: List[ShotDescription] = [
            ShotDescription(**s.model_dump()) for s in shots_brief
        ]

        # Stage 3 Atmosphere Lock: Identical camera, lens, lighting, and color grading across all shots in this episode
        episode_atmosphere_lock = CinematicPromptEngine.generate_atmosphere_lock(
            genre_camera="vertical_drama",
            style_mood=style,
        )

        # Step 3: Generate first frames (Storyboard Sheets 4-in-1 or Sequential Fallback)
        if use_storyboard_sheets and len(shots) >= 2:
            await progress_callback(
                "storyboard_sheet",
                f"Generating Storyboard Sheet (4-in-1 Grid) for Scene {scene_idx + 1}...",
                base_progress + int(progress_range * 0.25),
            )
            try:
                await self._process_storyboard_sheets(
                    shots=shots,
                    characters=characters,
                    style=style,
                    working_dir=working_dir,
                    scene_idx=scene_idx,
                    progress_callback=progress_callback,
                    base_progress=base_progress + int(progress_range * 0.25),
                    atmosphere_lock=episode_atmosphere_lock,
                )
            except Exception as e:
                print(f"[StoryboardSlicer] Sheet processing error ({e}), falling back to single frame T2I...")
                await self._fallback_single_frames(
                    shots, characters, character_portrait_urls, style, progress_callback, base_progress, progress_range, scene_idx, atmosphere_lock=episode_atmosphere_lock
                )
        else:
            await self._fallback_single_frames(
                shots, characters, character_portrait_urls, style, progress_callback, base_progress, progress_range, scene_idx, atmosphere_lock=episode_atmosphere_lock
            )

        # Step 4: Generate videos sequentially (Concurrency = 1, Anti-Ban Throttling & Auto-Retry)
        await progress_callback(
            "video",
            f"Memulai rendering video berurutan scene {scene_idx + 1} (Concurrency = 1)...",
            base_progress + int(progress_range * 0.60),
        )

        valid_shots = shots
        shot_video_paths = []

        for i, shot in enumerate(valid_shots):
            # Natural anti-ban delay between shots
            if i > 0:
                inter_shot_delay = random.uniform(2.0, 5.0)
                await progress_callback(
                    "video",
                    f"Anti-Ban Throttling: Menunggu jeda natural {inter_shot_delay:.1f}s sebelum shot {i + 1}...",
                    base_progress + int(progress_range * (0.60 + 0.25 * (i / len(valid_shots)))),
                )
                await asyncio.sleep(inter_shot_delay)

            await progress_callback(
                "video",
                f"Generating video shot {i + 1}/{len(valid_shots)} (scene {scene_idx + 1})...",
                base_progress + int(progress_range * (0.60 + 0.25 * ((i + 0.5) / len(valid_shots)))),
            )

            # Auto-retry loop (up to 3 attempts with Auto-Fix & fallback)
            v_path = await self._generate_shot_video_with_retry(
                shot=shot,
                shot_idx=i,
                working_dir=working_dir,
                progress_callback=progress_callback,
            )
            if v_path:
                shot_video_paths.append(v_path)
                shot.video_url = v_path

        if not shot_video_paths:
            raise RuntimeError(f"All video generation failed for scene {scene_idx + 1}")

        # Step 5: Concatenate shot videos
        await progress_callback(
            "concat",
            f"Combining shots for scene {scene_idx + 1}...",
            base_progress + int(progress_range * 0.90),
        )
        scene_video_path = str(Path(working_dir) / "scene_video.mp4")
        await concatenate_videos(shot_video_paths, scene_video_path)

        return scene_video_path

    async def _process_storyboard_sheets(
        self,
        shots: List[ShotDescription],
        characters: List[CharacterInScene],
        style: str,
        working_dir: str,
        scene_idx: int,
        progress_callback: ProgressCallback,
        base_progress: int,
        atmosphere_lock: Optional[str] = None,
    ):
        """Processes shots in groups of 4 using 2x2 Storyboard Sheets with Auto-Fix."""
        chunk_size = 4
        for chunk_idx in range(0, len(shots), chunk_size):
            batch_shots = shots[chunk_idx : chunk_idx + chunk_size]
            prompt = StoryboardSlicer.build_sheet_prompt(
                [s.model_dump() for s in batch_shots],
                characters,
                style=style,
                atmosphere_lock=atmosphere_lock,
            )

            # Generate sheet with Auto-Fix support
            sheet_img_url = None
            try:
                sheet_img_url = await self.image_gen.generate_image(prompt, aspect_ratio="1:1")
            except Exception as exc:
                if self.autofix.is_refusal_error(str(exc)):
                    await progress_callback(
                        "autofix",
                        f"Auto-Fix: Sensor terdeteksi, menulis ulang prompt Storyboard Sheet {chunk_idx // 4 + 1}...",
                        base_progress + 5,
                    )
                    repaired_prompt = await self.autofix.repair_prompt(prompt, reason=str(exc))
                    sheet_img_url = await self.image_gen.generate_image(repaired_prompt, aspect_ratio="1:1")
                else:
                    raise exc

            # Resolve local image file
            sheet_local_path = Path(working_dir) / f"sheet_batch_{chunk_idx // 4}.png"
            if sheet_img_url.startswith("http://") or sheet_img_url.startswith("https://"):
                await self._download_file(sheet_img_url, str(sheet_local_path))
            else:
                shutil.copy(sheet_img_url, str(sheet_local_path))

            # Slice into 9:16 vertical frames
            sliced_paths = StoryboardSlicer.slice_sheet(
                str(sheet_local_path),
                working_dir,
                prefix=f"sliced_sc{scene_idx + 1}_b{chunk_idx // 4}",
                target_aspect_ratio=(9, 16),
            )

            # Assign sliced frames back to shots
            for i, shot in enumerate(batch_shots):
                if i < len(sliced_paths):
                    shot.first_frame_url = sliced_paths[i]

    async def _fallback_single_frames(
        self,
        shots: List[ShotDescription],
        characters: List[CharacterInScene],
        character_portrait_urls: dict,
        style: str,
        progress_callback: ProgressCallback,
        base_progress: int,
        progress_range: int,
        scene_idx: int,
        atmosphere_lock: Optional[str] = None,
    ):
        """Fallback to individual shot frame generation."""
        frame_progress_step = int(progress_range * 0.35 / max(len(shots), 1))
        for i, shot in enumerate(shots):
            await progress_callback(
                "frames",
                f"Generating frame for shot {i + 1}/{len(shots)} (scene {scene_idx + 1})...",
                base_progress + int(progress_range * 0.20) + i * frame_progress_step,
            )
            try:
                frame_url = await self._generate_first_frame(
                    shot, characters, character_portrait_urls, style, atmosphere_lock=atmosphere_lock
                )
                shot.first_frame_url = frame_url
            except Exception as e:
                print(f"[FirstFrame] Warning: Failed to generate frame for shot {i + 1} ({e}). Flow will render directly from prompt.")
                shot.first_frame_url = None

    async def _generate_portrait(self, character: CharacterInScene, style: str) -> str:
        """Generate a character portrait image using real lens specs and imperfection retention."""
        clean_static = CinematicPromptEngine.sanitize_slop_words(character.static_features)
        clean_dynamic = CinematicPromptEngine.sanitize_slop_words(character.dynamic_features)
        prompt = (
            f"Reference character portrait photo of {character.name}. "
            f"{clean_static}. Wearing: {clean_dynamic}. "
            "Shot on Canon EF 85mm f/1.2 lens, neutral background, motivated edge lighting. "
            "Natural skin texture with subtle imperfections preserved, no beautification, full face visible, no game-CG feel."
        )
        try:
            return await self.image_gen.generate_image(prompt, aspect_ratio="2:3")
        except Exception as exc:
            if self.autofix.is_refusal_error(str(exc)):
                repaired = await self.autofix.repair_prompt(prompt, reason=str(exc))
                return await self.image_gen.generate_image(repaired, aspect_ratio="2:3")
            raise exc

    async def _generate_first_frame(
        self,
        shot: ShotDescription,
        characters: List[CharacterInScene],
        portrait_urls: dict,
        style: str,
        atmosphere_lock: Optional[str] = None,
    ) -> str:
        """Generate first frame for a shot using the 5-stage prompt standard and Atmosphere Lock."""
        mentioned_chars = [
            c for c in characters if c.name.lower() in shot.visual_desc.lower()
        ]

        reference_url = None
        if mentioned_chars and portrait_urls.get(mentioned_chars[0].name):
            reference_url = portrait_urls[mentioned_chars[0].name]

        char_desc = ""
        if mentioned_chars:
            char_desc = " ".join([f"{c.name} ({c.dynamic_features})" for c in mentioned_chars])

        full_prompt = CinematicPromptEngine.build_visual_prompt(
            scene_visual=shot.visual_desc,
            character_desc=char_desc,
            genre_camera="vertical_drama",
            aspect_ratio="9:16",
            atmosphere_lock=atmosphere_lock,
        )

        try:
            if reference_url:
                try:
                    return await self.image_gen.generate_image_with_reference(
                        full_prompt, reference_url, aspect_ratio="9:16"
                    )
                except Exception as e:
                    print(f"Warning: reference image generation failed, falling back to T2I: {e}")

            return await self.image_gen.generate_image(full_prompt, aspect_ratio="9:16")
        except Exception as exc:
            if self.autofix.is_refusal_error(str(exc)):
                repaired = await self.autofix.repair_prompt(full_prompt, reason=str(exc))
                return await self.image_gen.generate_image(repaired, aspect_ratio="9:16")
            raise exc

    async def _generate_shot_video(
        self, shot: ShotDescription, shot_idx: int, working_dir: str
    ) -> str:
        """Generate a video clip for a shot with breath-like float and sound rules. Returns local file path."""
        motion_part = CinematicPromptEngine.build_motion_prompt(
            motion_desc=shot.motion_desc,
            audio_desc=shot.audio_desc,
            force_breath_float=True,
        )
        if shot.first_frame_url:
            video_prompt = motion_part
        else:
            video_prompt = f"{shot.visual_desc}. {motion_part}"

        frame_url = shot.first_frame_url

        local_path = str(Path(working_dir) / f"shot_{shot_idx:03d}.mp4")
        try:
            video_url = await self.video_gen.generate_video_from_image(
                video_prompt, frame_url, duration=10, aspect_ratio="9:16", output_path=local_path
            )
        except Exception as exc:
            if self.autofix.is_refusal_error(str(exc)):
                repaired_video_prompt = await self.autofix.repair_prompt(
                    video_prompt, reason=str(exc), media_type="video motion"
                )
                video_url = await self.video_gen.generate_video_from_image(
                    repaired_video_prompt, frame_url, duration=10, aspect_ratio="9:16", output_path=local_path
                )
            else:
                raise exc

        if video_url.startswith("http://") or video_url.startswith("https://"):
            await download_video(video_url, local_path)
        elif Path(video_url).resolve() != Path(local_path).resolve():
            shutil.copy(video_url, local_path)

        return local_path

    async def _generate_shot_video_with_retry(
        self,
        shot: ShotDescription,
        shot_idx: int,
        working_dir: str,
        progress_callback: ProgressCallback,
        max_attempts: int = 3,
    ) -> Optional[str]:
        """Auto-retry loop (up to 3 attempts) with Auto-Fix Shield & graceful fallback."""
        for attempt in range(1, max_attempts + 1):
            try:
                return await self._generate_shot_video(shot, shot_idx, working_dir)
            except Exception as exc:
                err_str = str(exc)
                print(f"[VideoRetry] Shot {shot_idx + 1} attempt {attempt}/{max_attempts} failed: {err_str}")
                if attempt < max_attempts:
                    retry_delay = random.uniform(3.0, 6.0)
                    await progress_callback(
                        "video_retry",
                        f"Auto-Retry: Shot {shot_idx + 1} gagal ({err_str[:60]}). Mencoba ulang ({attempt + 1}/{max_attempts}) dalam {retry_delay:.1f}s...",
                        -1,
                    )
                    await asyncio.sleep(retry_delay)
                else:
                    print(f"[VideoRetry] Shot {shot_idx + 1} exceeded max attempts. Creating graceful still fallback clip...")
                    await progress_callback(
                        "video_retry",
                        f"Shot {shot_idx + 1} gagal total. Mengaktifkan fallback frame sinematik agar episode tetap selesai...",
                        -1,
                    )
                    return await self._create_fallback_clip(shot, shot_idx, working_dir)
        return None

    async def _create_fallback_clip(
        self, shot: ShotDescription, shot_idx: int, working_dir: str
    ) -> Optional[str]:
        """Creates a smooth still video clip from the shot's first frame so the pipeline never crashes."""
        if not shot.first_frame_url:
            return None
        fallback_path = str(Path(working_dir) / f"shot_{shot_idx:03d}_fallback.mp4")
        try:
            # If first_frame_url is a remote URL, download first
            frame_source = shot.first_frame_url
            if frame_source.startswith("http://") or frame_source.startswith("https://"):
                local_img = str(Path(working_dir) / f"temp_frame_{shot_idx}.png")
                await self._download_file(frame_source, local_img)
                frame_source = local_img

            await create_still_video(frame_source, fallback_path, duration=3.0)
            return fallback_path
        except Exception as e:
            print(f"[FallbackClip] Error creating fallback clip: {e}")
            return None

    async def _download_file(self, url: str, local_path: str):
        """Download file asynchronously."""
        def dl():
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            )
            with urllib.request.urlopen(req, timeout=45) as r, open(local_path, "wb") as f:
                f.write(r.read())

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, dl)
