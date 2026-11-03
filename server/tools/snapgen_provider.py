import asyncio
import base64
import mimetypes
import os
import time
import uuid as uuid_lib
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

import httpx

DEFAULT_API_BASE_URL = "https://api.snapgen.ai/uapi/v1"
DEFAULT_CREATE_ENDPOINT = f"{DEFAULT_API_BASE_URL}/video-gen/veo"
VIDEO_EXTENSIONS = (".mp4", ".webm", ".mov", ".m4v")
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_record(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _status_code(payload: Dict[str, Any]) -> Optional[int]:
    data = _unwrap_payload(payload)
    for key in ("status", "state"):
        value = data.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return None


def _unwrap_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(payload.get("data"), dict):
        return payload["data"]
    if isinstance(payload.get("result"), dict):
        return payload["result"]
    return payload


def _clean_url(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    url = value.strip()
    if not url.lower().startswith(("http://", "https://")):
        return None
    return url


def _pick_media_url(item: Any) -> Optional[str]:
    record = _as_record(item)
    for key in ("video_url", "file_download_url", "url", "media_url", "file_url"):
        url = _clean_url(record.get(key))
        if url:
            return url
    return None


def _extract_video_url(payload: Dict[str, Any]) -> Optional[str]:
    data = _unwrap_payload(payload)
    direct = _clean_url(data.get("generate_result"))
    if direct:
        return direct

    for key in ("media_files", "generated_video"):
        items = data.get(key)
        if isinstance(items, list):
            for item in items:
                url = _pick_media_url(item)
                if url:
                    return url

    for key in (
        "video_url",
        "file_download_url",
        "download_url",
        "output_url",
        "media_url",
        "file_url",
        "url",
    ):
        url = _clean_url(data.get(key))
        if url:
            return url
    return None


def _extract_image_url(payload: Dict[str, Any]) -> Optional[str]:
    data = _unwrap_payload(payload)
    direct = _clean_url(data.get("generate_result")) or _clean_url(data.get("image_url"))
    if direct:
        return direct

    items = data.get("generated_image")
    if isinstance(items, list):
        for item in items:
            record = _as_record(item)
            for key in ("image_url", "url", "file_download_url"):
                url = _clean_url(record.get(key))
                if url:
                    return url

    thumb = _clean_url(data.get("thumbnail_url"))
    if thumb:
        return thumb
    return None


def _extract_image_base64(payload: Dict[str, Any]) -> Optional[str]:
    data = _unwrap_payload(payload)
    items = data.get("generated_image")
    if isinstance(items, list):
        for item in items:
            record = _as_record(item)
            value = record.get("base64_data")
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _extract_error(payload: Dict[str, Any]) -> str:
    data = _unwrap_payload(payload)
    detail = _as_record(data.get("detail"))
    for source in (data, detail):
        for key in ("error_message", "error", "message", "status_desc"):
            val = source.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return "SnapGen request failed"


def _history_urls(base_url: str, job_id: Any, job_uuid: Any) -> List[str]:
    values = {"id": job_id or "", "uuid": job_uuid or job_id or ""}
    return [
        f"{base_url}/history/{values['uuid']}",
        f"{base_url}/history/{values['id']}",
    ]


class SnapGenProvider:
    """SnapGen.ai unified provider for images and video generation (AdFlx standard)."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("SNAPGEN_API_KEY") or os.environ.get("GEMINIGEN_API_KEY", "")
        self.base_url = DEFAULT_API_BASE_URL
        self.output_dir = Path("D:/microdrama-app/server/generated_media")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate_character_portrait(self, prompt: str, aspect_ratio: str = "1:1") -> str:
        """Generate character portrait using SnapGen image generation."""
        if not self.api_key:
            raise RuntimeError("SNAPGEN_API_KEY belum disetting di environment / Settings UI.")

        create_endpoint = f"{self.base_url}/generate_image"
        headers = {"x-api-key": self.api_key}

        form_items = [
            ("prompt", (None, f"{prompt}, professional character portrait, cinematic lighting, sharp focus")),
            ("model", (None, "nano-banana-pro")),
            ("aspect_ratio", (None, aspect_ratio or "1:1")),
            ("style", (None, "Photorealistic")),
        ]

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(create_endpoint, headers=headers, files=form_items)
            if resp.status_code >= 400:
                raise RuntimeError(f"SnapGen image create failed ({resp.status_code}): {resp.text[:200]}")
            data = resp.json()
            payload = _unwrap_payload(data)
            job_id = payload.get("id")
            job_uuid = payload.get("uuid") or job_id

            # Check direct result
            img_url = _extract_image_url(data)
            if img_url:
                return img_url

            # Poll
            for _ in range(60):
                await asyncio.sleep(3)
                for h_url in _history_urls(self.base_url, job_id, job_uuid):
                    h_resp = await client.get(h_url, headers=headers)
                    if h_resp.status_code == 200:
                        h_data = h_resp.json()
                        st = _status_code(h_data)
                        if st == 3:
                            raise RuntimeError(_extract_error(h_data))
                        url = _extract_image_url(h_data)
                        if st == 2 and url:
                            return url
                        break
            raise TimeoutError("SnapGen portrait timed out after 180s")

    async def generate_scene_frame(self, prompt: str, reference_url: str, aspect_ratio: str = "9:16") -> str:
        """Generate scene frame conditioned on actor reference image."""
        if not self.api_key:
            raise RuntimeError("SNAPGEN_API_KEY belum disetting di environment / Settings UI.")

        create_endpoint = f"{self.base_url}/generate_image"
        headers = {"x-api-key": self.api_key}

        final_prompt = (
            f"{prompt} "
            "ABSOLUTE COMPOSITION LOCK: true portrait 9:16 vertical frame, dramatic cinematography, "
            "consistent actor facial features matching reference."
        )

        form_items = [
            ("prompt", (None, final_prompt)),
            ("model", (None, "nano-banana-pro")),
            ("aspect_ratio", (None, aspect_ratio or "9:16")),
            ("style", (None, "Cinematic")),
        ]
        if reference_url:
            form_items.append(("file_urls", (None, reference_url)))

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(create_endpoint, headers=headers, files=form_items)
            if resp.status_code >= 400:
                raise RuntimeError(f"SnapGen scene frame create failed ({resp.status_code}): {resp.text[:200]}")
            data = resp.json()
            payload = _unwrap_payload(data)
            job_id = payload.get("id")
            job_uuid = payload.get("uuid") or job_id

            img_url = _extract_image_url(data)
            if img_url:
                return img_url

            for _ in range(60):
                await asyncio.sleep(3)
                for h_url in _history_urls(self.base_url, job_id, job_uuid):
                    h_resp = await client.get(h_url, headers=headers)
                    if h_resp.status_code == 200:
                        h_data = h_resp.json()
                        st = _status_code(h_data)
                        if st == 3:
                            raise RuntimeError(_extract_error(h_data))
                        url = _extract_image_url(h_data)
                        if st == 2 and url:
                            return url
                        break
            raise TimeoutError("SnapGen scene frame timed out after 180s")

    async def generate_video(
        self,
        prompt: str,
        image_url: Optional[str] = None,
        duration: int = 10,
        aspect_ratio: str = "9:16",
    ) -> str:
        """Generate video via SnapGen (Veo 3.1 / I2V) as in AdFlx."""
        if not self.api_key:
            raise RuntimeError("SNAPGEN_API_KEY belum disetting di environment / Settings UI.")

        create_endpoint = f"{self.base_url}/video-gen/veo"
        headers = {"x-api-key": self.api_key}

        form_items = [
            ("prompt", (None, prompt)),
            ("model", (None, "veo-3.1-fast")),
            ("resolution", (None, "720p")),
            ("duration", (None, str(duration or 8))),
            ("aspect_ratio", (None, aspect_ratio or "9:16")),
        ]
        if image_url:
            form_items.append(("mode_image", (None, "frame")))
            form_items.append(("ref_images", (None, image_url)))

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(create_endpoint, headers=headers, files=form_items)
            if resp.status_code >= 400:
                raise RuntimeError(f"SnapGen video create failed ({resp.status_code}): {resp.text[:200]}")
            data = resp.json()
            payload = _unwrap_payload(data)
            job_id = payload.get("id")
            job_uuid = payload.get("uuid") or job_id

            v_url = _extract_video_url(data)
            if v_url:
                return v_url

            for _ in range(120):
                await asyncio.sleep(5)
                for h_url in _history_urls(self.base_url, job_id, job_uuid):
                    h_resp = await client.get(h_url, headers=headers)
                    if h_resp.status_code == 200:
                        h_data = h_resp.json()
                        st = _status_code(h_data)
                        if st == 3:
                            raise RuntimeError(_extract_error(h_data))
                        url = _extract_video_url(h_data)
                        if st == 2 and url:
                            return url
                        break
            raise TimeoutError("SnapGen video generation timed out after 600s")
