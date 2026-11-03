import asyncio
import os
from typing import Optional

import httpx
from .snapgen_provider import SnapGenProvider


MUAPI_BASE = "https://api.muapi.ai/api/v1"
POLL_INTERVAL = 3  # seconds


class MuAPIImageGenerator:
    """Image generator supporting SnapGen.ai (AdFlx standard) as primary engine,
    with fallback to MuAPI Seedream/Nano Banana if configured.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("MUAPI_KEY", "")
        self.snapgen_key = os.environ.get("SNAPGEN_API_KEY") or os.environ.get("GEMINIGEN_API_KEY", "")
        self.snapgen = SnapGenProvider(api_key=self.snapgen_key)
        self.headers = {"x-api-key": self.api_key, "Content-Type": "application/json"}

    async def generate_image(self, prompt: str, aspect_ratio: str = "1:1") -> str:
        """Generate a photorealistic character portrait.
        Uses SnapGen.ai (AdFlx standard) if SNAPGEN_API_KEY is configured,
        or falls back to Seedream v4.5.
        """
        if self.snapgen_key:
            return await self.snapgen.generate_character_portrait(prompt, aspect_ratio=aspect_ratio)

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{MUAPI_BASE}/bytedance-seedream-v4.5",
                headers=self.headers,
                json={
                    "prompt": prompt,
                    "aspect_ratio": aspect_ratio,
                    "quality": "high",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        request_id = data.get("request_id") or data.get("id")
        if not request_id:
            raise ValueError(f"No request_id in response: {data}")

        result = await self._poll_until_done(request_id, timeout=300)
        return self._extract_url(result)

    async def generate_image_with_reference(
        self,
        prompt: str,
        reference_url: str,
        aspect_ratio: str = "9:16",
    ) -> str:
        """Generate a scene frame using a character reference image.
        Uses SnapGen.ai (AdFlx standard) if SNAPGEN_API_KEY is configured,
        or falls back to Nano Banana 2 Edit.
        """
        if self.snapgen_key:
            return await self.snapgen.generate_scene_frame(
                prompt=prompt,
                reference_url=reference_url,
                aspect_ratio=aspect_ratio or "9:16",
            )

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{MUAPI_BASE}/nano-banana-2-edit",
                headers=self.headers,
                json={
                    "prompt": prompt,
                    "images_list": [reference_url],
                    "aspect_ratio": aspect_ratio,
                    "resolution": "2k",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        request_id = data.get("request_id") or data.get("id")
        if not request_id:
            raise ValueError(f"No request_id in response: {data}")

        result = await self._poll_until_done(request_id, timeout=300)
        return self._extract_url(result)

    def _extract_url(self, result: dict) -> str:
        outputs = result.get("outputs", [])
        if not outputs:
            raise ValueError(f"No outputs in result: {result}")
        output = outputs[0]
        if isinstance(output, dict):
            return output.get("url") or output.get("image_url") or str(output)
        return str(output)

    async def _poll_until_done(self, request_id: str, timeout: int = 300) -> dict:
        elapsed = 0
        async with httpx.AsyncClient(timeout=30) as client:
            while elapsed < timeout:
                await asyncio.sleep(POLL_INTERVAL)
                elapsed += POLL_INTERVAL

                resp = await client.get(
                    f"{MUAPI_BASE}/predictions/{request_id}/result",
                    headers=self.headers,
                )
                resp.raise_for_status()
                data = resp.json()

                status = data.get("status", "")
                if status == "completed":
                    return data
                elif status == "failed":
                    raise RuntimeError(
                        f"MuAPI image job {request_id} failed: {data.get('error', 'unknown error')}"
                    )
                elif status == "cancelled":
                    raise RuntimeError(f"MuAPI image job {request_id} was cancelled")

        raise TimeoutError(
            f"MuAPI image job {request_id} did not complete within {timeout}s"
        )
