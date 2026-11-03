import os
import pathlib
from typing import Optional, List, Dict, Any
import httpx


class ZernioPublisher:
    """
    Client for Zernio Social Media Publishing API (https://zernio.com/api/v1)
    Supports publishing vertical 9:16 video microdramas to TikTok, Instagram Reels,
    YouTube Shorts, Facebook Reels, and other connected platforms using an API Key.
    """

    BASE_URL = "https://zernio.com/api/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ZERNIO_API_KEY", "").strip()

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise ValueError("ZERNIO_API_KEY belum dikonfigurasi. Masukkan API Key di Pengaturan.")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def list_accounts(self) -> List[Dict[str, Any]]:
        """
        Fetch connected accounts from Zernio dashboard.
        Accounts are connected once in Zernio; this retrieves their accountId and platforms.
        """
        if not self.api_key:
            return []

        url = f"{self.BASE_URL}/accounts"
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.get(url, headers=self._headers())
            if res.status_code != 200:
                print(f"[Zernio] Failed to list accounts: {res.status_code} - {res.text}")
                return []
            data = res.json()
            raw_accounts = data.get("accounts", [])
            results = []
            for a in raw_accounts:
                results.append({
                    "id": a.get("_id") or a.get("id"),
                    "platform": a.get("platform", "unknown"),
                    "username": a.get("username") or a.get("displayName") or a.get("name") or "Account",
                    "display_name": a.get("displayName") or a.get("username") or "",
                    "profile_picture": a.get("profilePictureUrl") or a.get("avatar") or "",
                    "is_active": a.get("isActive", True) and a.get("status") != "disconnected",
                    "status": a.get("status", "connected"),
                })
            return results

    async def upload_media_file(self, file_path: str) -> str:
        """
        Upload local MP4 video file to Zernio Cloud Storage via Presigned URL.
        Returns the public URL of the uploaded video.
        """
        path = pathlib.Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"File video tidak ditemukan: {file_path}")

        file_size = path.stat().st_size
        filename = path.name

        # 1. Request presigned upload URL
        presign_url = f"{self.BASE_URL}/media/presign"
        payload = {
            "filename": filename,
            "contentType": "video/mp4",
            "size": file_size,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(presign_url, headers=self._headers(), json=payload)
            if res.status_code not in (200, 201):
                raise RuntimeError(f"Gagal mendapatkan presign URL Zernio: {res.status_code} - {res.text}")
            
            presign_data = res.json()
            upload_url = presign_data.get("uploadUrl")
            public_url = presign_data.get("publicUrl")

            if not upload_url or not public_url:
                raise ValueError(f"Presign response tidak memiliki uploadUrl/publicUrl: {presign_data}")

            # 2. PUT raw video data to presigned cloud storage
            file_bytes = path.read_bytes()
            put_res = await client.put(
                upload_url,
                content=file_bytes,
                headers={"Content-Type": "video/mp4"},
                timeout=300.0,
            )
            if put_res.status_code not in (200, 201, 204):
                raise RuntimeError(f"Gagal mengunggah video ke cloud Zernio: {put_res.status_code} - {put_res.text}")

            print(f"[Zernio] Upload video sukses: {public_url}")
            return public_url

    async def publish_video(
        self,
        video_path_or_url: str,
        caption: str,
        platform_targets: List[Dict[str, str]],
        publish_now: bool = True,
    ) -> Dict[str, Any]:
        """
        Publish vertical video post across one or more platforms via Zernio.
        platform_targets: list of dicts [{"platform": "tiktok", "accountId": "..."}]
        """
        if not platform_targets:
            raise ValueError("Pilih setidaknya satu akun media sosial tujuan untuk publish.")

        # Determine video public URL
        if video_path_or_url.startswith("http://") or video_path_or_url.startswith("https://"):
            public_url = video_path_or_url
        else:
            public_url = await self.upload_media_file(video_path_or_url)

        # Build platforms array format for Zernio POST /v1/posts
        formatted_platforms = []
        for target in platform_targets:
            p_entry = {
                "platform": target.get("platform"),
                "accountId": target.get("accountId") or target.get("id"),
            }
            # For Instagram Reel
            if target.get("platform") == "instagram":
                p_entry["platformSpecificData"] = {"shareToFeed": True}
            # For Facebook Reel
            elif target.get("platform") == "facebook":
                p_entry["platformSpecificData"] = {"contentType": "reel"}

            formatted_platforms.append(p_entry)

        post_payload = {
            "content": caption.strip(),
            "mediaItems": [
                {
                    "type": "video",
                    "url": public_url,
                }
            ],
            "platforms": formatted_platforms,
            "publishNow": publish_now,
        }

        posts_url = f"{self.BASE_URL}/posts"
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(posts_url, headers=self._headers(), json=post_payload)
            if res.status_code not in (200, 201):
                raise RuntimeError(f"Zernio Publish Error ({res.status_code}): {res.text}")

            data = res.json()
            print(f"[Zernio] Post berhasil dipublikasikan: {data.get('message')}")
            return data
