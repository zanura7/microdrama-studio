"""
MicroDrama Studio — Model Context Protocol (MCP) Server.
Enables Claude (Claude Desktop / Claude Code) and Codex CLI to orchestrate,
generate, monitor, and auto-publish vertical 9:16 AI micro-drama series.
"""

import json
import urllib.request
import urllib.error
from typing import Optional, List, Dict, Any
from mcp.server.fastmcp import FastMCP

API_BASE_URL = "http://127.0.0.1:8000"

mcp = FastMCP("microdrama-studio")


def _http_get(endpoint: str) -> Dict[str, Any]:
    url = f"{API_BASE_URL}{endpoint}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "MicroDrama-MCP/1.0", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except urllib.error.URLError as e:
        return {"error": f"Gagal terhubung ke MicroDrama Server ({API_BASE_URL}): {str(e)}"}
    except Exception as e:
        return {"error": f"Request failed: {str(e)}"}


def _http_post(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{API_BASE_URL}{endpoint}"
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={
            "User-Agent": "MicroDrama-MCP/1.0",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode("utf-8"))
            return {"error": err_body.get("detail", str(e)), "status_code": e.code}
        except Exception:
            return {"error": f"HTTP Error {e.code}: {e.reason}"}
    except urllib.error.URLError as e:
        return {"error": f"Gagal terhubung ke MicroDrama Server ({API_BASE_URL}): {str(e)}"}
    except Exception as e:
        return {"error": f"Request failed: {str(e)}"}


@mcp.tool()
def create_microdrama(
    idea: str,
    style: str = "Cinematic",
    skill_id: str = "revenge_ceo",
    use_storyboard_sheets: bool = True,
    user_requirement: str = "",
    mode: str = "idea2video",
    script: str = "",
) -> Dict[str, Any]:
    """
    Buat serial microdrama AI baru (Format Vertikal 9:16).
    Mendukung Storyboard Sheets (4 adegan dalam 1 gambar grid 2x2, hemat ~70% kredit, wajah/baju 100% konsisten)
    serta perlindungan Auto-Fix jika ada kata yang disensor oleh AI filter.

    Parameters:
      idea: Ide premis cerita atau sinopsis drama.
      style: Gaya visual sinematik ("Cinematic", "Realistic", "Korean Drama", "Dark Thriller", "Cyberpunk").
      skill_id: Formula naskah viral ("revenge_ceo", "ugc_affiliate", "urban_horror", "office_romcom").
      use_storyboard_sheets: True untuk menggunakan engine 4-in-1 Flow Studio (sangat disarankan).
      user_requirement: Catatan khusus sutradara (pacing, lighting, angle kamera).
      mode: "idea2video" (otomatis full pipeline) atau "script2video" (dari naskah buatan sendiri).
      script: Naskah manual jika mode="script2video".
    """
    payload = {
        "idea": idea,
        "style": style,
        "skill_id": skill_id,
        "use_storyboard_sheets": use_storyboard_sheets,
        "user_requirement": user_requirement,
        "mode": mode,
        "script": script,
    }
    res = _http_post("/api/generate", payload)
    if "job_id" in res:
        job_id = res["job_id"]
        res["tracking_url"] = f"http://localhost:3000/generate/{job_id}"
        res["message"] = f"Job microdrama berhasil dimulai! Pantau status via get_drama_status(job_id='{job_id}')"
    return res


@mcp.tool()
def get_drama_status(job_id: str) -> Dict[str, Any]:
    """
    Cek status progres dan hasil video microdrama berdasarkan job_id.
    Mengembalikan progress persentase (0-100%), tahapan aktif, pesan terakhir,
    status (running/completed/failed), dan URL/path file video MP4 jika sudah selesai.
    """
    return _http_get(f"/api/job/{job_id}")


@mcp.tool()
def list_drama_jobs() -> Dict[str, Any]:
    """
    Dapatkan daftar seluruh pekerjaan microdrama yang ada di server beserta status dan link video.
    """
    return _http_get("/api/jobs")


@mcp.tool()
def list_story_skills() -> Dict[str, Any]:
    """
    Daftar formula naskah drama viral (Skills) yang tersedia di MicroDrama Studio
    (contoh: Balas Dendam CEO, UGC Affiliate Storytelling, Horor Urban Legend, Romcom Kantor).
    """
    return _http_get("/api/skills")


@mcp.tool()
def generate_viral_caption(job_id: str, platform: str = "tiktok") -> Dict[str, Any]:
    """
    Generate caption clickbait viral, hook naskah, dan hashtag otomatis menggunakan 9Router LLM
    khusus untuk microdrama yang sudah dibuat.
    """
    return _http_post(f"/api/caption/{job_id}?platform={platform}", {})


@mcp.tool()
def get_connected_social_accounts() -> Dict[str, Any]:
    """
    Dapatkan daftar akun media sosial (TikTok, Instagram, YouTube, Facebook)
    yang terhubung melalui Zernio API Key.
    """
    return _http_get("/api/zernio/accounts")


@mcp.tool()
def publish_drama_to_social(
    job_id: str,
    caption: str,
    platforms: List[Dict[str, Any]],
    publish_now: bool = True,
) -> Dict[str, Any]:
    """
    Publikasikan video microdrama yang sudah selesai ke multi-platform media sosial via Zernio API.

    Parameters:
      job_id: ID pekerjaan drama yang sudah berstatus 'completed'.
      caption: Teks caption dan hashtag untuk postingan.
      platforms: List akun tujuan, contoh: [{"platform": "tiktok", "accountId": "acc_123"}]
      publish_now: True untuk langsung posting saat ini juga.
    """
    payload = {
        "job_id": job_id,
        "caption": caption,
        "platforms": platforms,
        "publish_now": publish_now,
    }
    return _http_post("/api/publish", payload)


@mcp.tool()
def get_studio_info() -> Dict[str, Any]:
    """
    Dapatkan info status sistem MicroDrama Studio: koneksi LLM 9Router, status profil Google Flow,
    engine video aktif (Omni Flash 1.1 / SnapGen), serta konfigurasi Zernio.
    """
    settings = _http_get("/api/settings")
    health = _http_get("/api/health")
    return {
        "status": health.get("status", "unknown"),
        "settings": settings,
        "web_ui_url": "http://localhost:3000",
        "api_url": API_BASE_URL,
    }


if __name__ == "__main__":
    mcp.run()
