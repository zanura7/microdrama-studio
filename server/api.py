import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pipelines.idea2video import Idea2VideoPipeline
from pipelines.script2video import Script2VideoPipeline
from agents.character_extractor import CharacterExtractor
from tools.zernio_publisher import ZernioPublisher
from tools.muapi_llm import MuAPILLM
from tools.batch_queue_manager import BatchQueueManager


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(title="MicroDrama AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure outputs directory exists on startup
OUTPUTS_DIR = Path("outputs")
OUTPUTS_DIR.mkdir(exist_ok=True)

app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")


# ---------------------------------------------------------------------------
# In-memory job store
# ---------------------------------------------------------------------------
# job structure:
# {
#   "status": "running" | "completed" | "failed",
#   "events": [...],           # list of JSON-serialisable dicts
#   "video_url": str | None,
#   "error": str | None,
#   "queue": asyncio.Queue,    # fed by pipeline, consumed by SSE
# }
jobs: Dict[str, Dict[str, Any]] = {}
batch_queue = BatchQueueManager()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------
class BatchAddRequest(BaseModel):
    items: List[Dict[str, Any]]


class BatchSingleAddRequest(BaseModel):
    title: str = ""
    idea: str
    script: str = ""
    style: str = "Cinematic"
    skill_id: str = ""
    mode: str = "idea2video"
    use_storyboard_sheets: bool = True
class SettingsRequest(BaseModel):
    llm_base_url: str = "http://localhost:20128/v1"
    llm_model: str = "gh/gpt-4o"
    api_key: str = ""
    video_engine: str = "google_omni_flash"
    snapgen_api_key: str = ""
    zernio_api_key: str = ""


class GenerateRequest(BaseModel):
    idea: str
    user_requirement: str = ""
    style: str = "Cinematic"
    mode: str = "idea2video"  # "idea2video" or "script2video"
    script: str = ""          # used when mode == "script2video"
    skill_id: str = ""        # optional skill formula ID (e.g. "revenge_ceo")
    use_storyboard_sheets: bool = True  # Flow Studio 4-in-1 Storyboard Sheets


class GenerateResponse(BaseModel):
    job_id: str


class JobResult(BaseModel):
    job_id: str
    status: str
    video_url: str | None = None
    error: str | None = None


class PublishRequest(BaseModel):
    job_id: str
    caption: str
    platforms: List[Dict[str, Any]]  # [{"platform": "tiktok", "accountId": "..."}, ...]
    publish_now: bool = True


# ---------------------------------------------------------------------------
# Background pipeline runner
# ---------------------------------------------------------------------------
async def run_pipeline(job_id: str, req: GenerateRequest) -> None:
    job = jobs[job_id]
    queue: asyncio.Queue = job["queue"]
    job["idea"] = req.idea
    job["style"] = req.style
    job["skill_id"] = req.skill_id

    # Load skill rules if requested
    skill_rules = ""
    if req.skill_id:
        skill_path = Path(__file__).parent / "skills" / f"{req.skill_id}.json"
        if skill_path.is_file():
            try:
                skill_data = json.loads(skill_path.read_text(encoding="utf-8"))
                skill_rules = skill_data.get("rules", "")
            except Exception as e:
                print(f"[Skill] Failed to load {req.skill_id}: {e}")

    async def progress_callback(stage: str, message: str, progress: int) -> None:
        event = {
            "type": "progress",
            "stage": stage,
            "message": message,
            "progress": progress,
        }
        job["events"].append(event)
        await queue.put(event)

    try:
        if req.mode == "script2video":
            # Script2Video: user provides a single scene script
            pipeline = Script2VideoPipeline()
            character_extractor = CharacterExtractor()

            await progress_callback("characters", "Extracting characters...", 10)
            characters = await character_extractor.extract_characters(req.script or req.idea)

            output_dir = str(OUTPUTS_DIR / job_id / "scene_00")
            video_path = await pipeline.run(
                script=req.script or req.idea,
                characters=characters,
                user_requirement=req.user_requirement,
                style=req.style,
                working_dir=output_dir,
                progress_callback=progress_callback,
                scene_idx=0,
                base_progress=15,
                progress_range=80,
                use_storyboard_sheets=req.use_storyboard_sheets,
            )
        else:
            # Idea2Video: full agentic pipeline
            pipeline = Idea2VideoPipeline()
            video_path = await pipeline.run(
                idea=req.idea,
                user_requirement=req.user_requirement,
                style=req.style,
                job_id=job_id,
                progress_callback=progress_callback,
                skill_rules=skill_rules,
                use_storyboard_sheets=req.use_storyboard_sheets,
            )

        # Convert local path to URL
        rel_path = Path(video_path).relative_to(Path("."))
        video_url = f"/{rel_path}"

        job["status"] = "completed"
        job["video_url"] = video_url
        job["video_path"] = str(Path(video_path).resolve())

        complete_event = {
            "type": "complete",
            "video_url": video_url,
            "progress": 100,
        }
        job["events"].append(complete_event)
        await queue.put(complete_event)

    except Exception as exc:
        error_msg = str(exc)
        job["status"] = "failed"
        job["error"] = error_msg

        error_event = {
            "type": "error",
            "message": error_msg,
            "progress": -1,
        }
        job["events"].append(error_event)
        await queue.put(error_event)

    finally:
        # Signal SSE consumers that the stream is done
        await queue.put(None)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "microdrama-api"}


@app.post("/api/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "running",
        "events": [],
        "video_url": None,
        "error": None,
        "queue": asyncio.Queue(),
    }
    background_tasks.add_task(run_pipeline, job_id, req)
    return GenerateResponse(job_id=job_id)


@app.get("/api/status/{job_id}")
async def status_stream(job_id: str):
    """SSE endpoint — streams progress events until job completes or fails."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    async def event_generator():
        # Replay already-emitted events first (in case client reconnects)
        for event in job["events"]:
            yield f"data: {json.dumps(event)}\n\n"

        # If job is already done, we've replayed everything — finish
        if job["status"] in ("completed", "failed"):
            return

        # Otherwise stream live events from queue
        queue: asyncio.Queue = job["queue"]
        while True:
            event = await queue.get()
            if event is None:
                # Sentinel — pipeline finished
                break
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("type") in ("complete", "error"):
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/result/{job_id}", response_model=JobResult)
async def get_result(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    return JobResult(
        job_id=job_id,
        status=job["status"],
        video_url=job.get("video_url"),
        error=job.get("error"),
    )


@app.get("/api/jobs")
async def list_jobs():
    """List all recent microdrama jobs with current status and video URLs."""
    result = []
    for jid, job in jobs.items():
        latest_event = job.get("events", [])[-1] if job.get("events") else {}
        result.append({
            "job_id": jid,
            "status": job.get("status", "unknown"),
            "idea": job.get("idea", ""),
            "style": job.get("style", ""),
            "skill_id": job.get("skill_id", ""),
            "progress": latest_event.get("progress", 100 if job.get("status") == "completed" else 0),
            "latest_message": latest_event.get("message", ""),
            "video_url": job.get("video_url"),
            "video_path": job.get("video_path"),
            "error": job.get("error"),
        })
    return {"jobs": result, "count": len(result)}


@app.get("/api/job/{job_id}")
async def get_job_summary(job_id: str):
    """Detailed summary of a single microdrama job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = jobs[job_id]
    latest_event = job.get("events", [])[-1] if job.get("events") else {}
    return {
        "job_id": job_id,
        "status": job.get("status", "unknown"),
        "idea": job.get("idea", ""),
        "style": job.get("style", ""),
        "skill_id": job.get("skill_id", ""),
        "progress": latest_event.get("progress", 100 if job.get("status") == "completed" else 0),
        "stage": latest_event.get("stage", ""),
        "latest_message": latest_event.get("message", ""),
        "video_url": job.get("video_url"),
        "video_path": job.get("video_path"),
        "error": job.get("error"),
        "events_count": len(job.get("events", [])),
    }


@app.get("/api/settings")
async def get_settings():
    flow_profile_path = Path(
        os.environ.get("FLOW_PROFILE")
        or Path.home() / ".google-flow-creator" / "browser-profile"
    )
    zernio_key = os.environ.get("ZERNIO_API_KEY", "")
    return {
        "llm_base_url": os.environ.get("OPENAI_BASE_URL", "http://localhost:20128/v1"),
        "llm_model": os.environ.get("LLM_MODEL", "gh/gpt-4o"),
        "has_api_key": bool(os.environ.get("OPENAI_API_KEY")),
        "video_engine": os.environ.get("VIDEO_ENGINE", "google_omni_flash"),
        "has_snapgen_key": bool(os.environ.get("SNAPGEN_API_KEY")),
        "has_zernio_key": bool(zernio_key),
        "flow_profile": str(flow_profile_path),
        "flow_profile_exists": flow_profile_path.exists(),
    }


@app.post("/api/settings")
async def save_settings(req: SettingsRequest):
    env_path = Path(__file__).parent / ".env"
    existing_key = os.environ.get("OPENAI_API_KEY", "")
    new_key = req.api_key.strip() if req.api_key.strip() else existing_key

    existing_snapgen = os.environ.get("SNAPGEN_API_KEY", "")
    new_snapgen = req.snapgen_api_key.strip() if req.snapgen_api_key.strip() else existing_snapgen

    existing_zernio = os.environ.get("ZERNIO_API_KEY", "")
    new_zernio = req.zernio_api_key.strip() if req.zernio_api_key.strip() else existing_zernio

    os.environ["OPENAI_BASE_URL"] = req.llm_base_url.strip()
    os.environ["OPENAI_API_KEY"] = new_key
    os.environ["LLM_MODEL"] = req.llm_model.strip()
    os.environ["VIDEO_ENGINE"] = req.video_engine.strip()
    os.environ["SNAPGEN_API_KEY"] = new_snapgen
    os.environ["ZERNIO_API_KEY"] = new_zernio

    flow_profile = os.environ.get(
        "FLOW_PROFILE",
        str(Path.home() / ".google-flow-creator" / "browser-profile"),
    )
    flow_account = os.environ.get("FLOW_ACCOUNT", "auto")

    lines = [
        "# Microdrama AI Configuration",
        "# LLM Provider: 9Router Local (Zero API Cost)",
        f"OPENAI_BASE_URL={req.llm_base_url.strip()}",
        f"OPENAI_API_KEY={new_key}",
        f"LLM_MODEL={req.llm_model.strip()}",
        "",
        "# Video Generation Engine: Google Omni Flash 1.1 / SnapGen.ai (AdFlx standard)",
        f"VIDEO_ENGINE={req.video_engine.strip()}",
        f"SNAPGEN_API_KEY={new_snapgen}",
        f"ZERNIO_API_KEY={new_zernio}",
        f"FLOW_PROFILE={flow_profile.replace(chr(92), '/')}",
        f"FLOW_ACCOUNT={flow_account}",
    ]
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "saved", "message": "Konfigurasi berhasil disimpan."}


@app.get("/api/skills")
async def list_skills():
    """Returns all available drama storytelling and video formula skills."""
    skills_dir = Path(__file__).parent / "skills"
    results = []
    if skills_dir.is_dir():
        for skill_file in sorted(skills_dir.glob("*.json")):
            try:
                data = json.loads(skill_file.read_text(encoding="utf-8"))
                results.append(data)
            except Exception as e:
                print(f"[Skills] Error reading {skill_file.name}: {e}")
    return {"skills": results}


@app.get("/api/zernio/accounts")
async def get_zernio_accounts():
    """Fetch social media accounts connected in user's Zernio dashboard."""
    publisher = ZernioPublisher()
    if not publisher.is_configured:
        return {"configured": False, "accounts": [], "message": "Zernio API Key belum disetel."}
    try:
        accounts = await publisher.list_accounts()
        return {"configured": True, "accounts": accounts}
    except Exception as exc:
        return {"configured": True, "accounts": [], "error": str(exc)}


@app.post("/api/publish")
async def publish_video_to_zernio(req: PublishRequest):
    """Publish generated microdrama video to selected social platforms via Zernio."""
    if req.job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job video tidak ditemukan.")

    job = jobs[req.job_id]
    if job.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Video belum selesai dirender.")

    video_path = job.get("video_path")
    if not video_path or not Path(video_path).is_file():
        # Fallback to relative path lookup
        rel_url = job.get("video_url", "").lstrip("/")
        fallback_path = Path(__file__).parent / rel_url
        if fallback_path.is_file():
            video_path = str(fallback_path)
        else:
            raise HTTPException(status_code=404, detail="File video lokal tidak ditemukan di disk.")

    publisher = ZernioPublisher()
    if not publisher.is_configured:
        raise HTTPException(status_code=400, detail="Zernio API Key belum disetel di pengaturan.")

    try:
        result = await publisher.publish_video(
            video_path_or_url=video_path,
            caption=req.caption,
            platform_targets=req.platforms,
            publish_now=req.publish_now,
        )
        return {
            "status": "published",
            "message": "Video berhasil dipublikasikan ke media sosial via Zernio!",
            "result": result,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gagal publish ke Zernio: {exc}")


@app.post("/api/caption/{job_id}")
async def generate_viral_caption(job_id: str):
    """Generate viral social media caption & hashtags using 9Router LLM based on drama story."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan.")

    job = jobs[job_id]
    idea = job.get("idea", "Drama Pendek Vertikal")
    style = job.get("style", "Cinematic")

    prompt = f"""Kamu adalah Social Media Growth Specialist untuk TikTok, Instagram Reels, dan YouTube Shorts.
Buatkan 1 paket postingan siap viral untuk drama vertikal berikut:

Ide Cerita: {idea}
Style Visual: {style}

Format respon:
1. Hook / Judul Clickbait di baris pertama
2. Deskripsi / Sinopsis singkat 2-3 kalimat yang memancing rasa penasaran
3. Call to Action (ajak komentar / tonton sampai habis)
4. 5-8 hashtag relevan dan viral (misal: #microdrama #dramatiktok #filmpendek #viral #fyp #reels)

Tulis dalam Bahasa Indonesia santai dan memikat penonton."""

    llm = MuAPILLM()
    try:
        caption = await llm.complete(prompt, timeout=60, fallback=f"🔥 Saksikan kisah tak terduga ini! Tonton sampai akhir dan tulis pendapatmu di kolom komentar! 👇\n\n{idea}\n\n#microdrama #dramapendek #fyp #viral #shortmovie")
        return {"job_id": job_id, "caption": caption.strip()}
    except Exception as e:
        return {"job_id": job_id, "caption": f"🔥 Jangan lewatkan kisah seru ini!\n\n{idea}\n\n#microdrama #filmpendek #fyp"}


@app.post("/api/flow/open-browser")
async def open_flow_browser():
    """Launch Google Chrome with the dedicated Google Flow profile for login."""
    import subprocess
    import shutil

    profile_path = Path(
        os.environ.get("FLOW_PROFILE")
        or Path.home() / ".google-flow-creator" / "browser-profile"
    )
    profile_path.mkdir(parents=True, exist_ok=True)

    chrome_candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        str(Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe"),
        shutil.which("chrome"),
        shutil.which("google-chrome"),
    ]
    chrome_exe = next((c for c in chrome_candidates if c and Path(c).is_file()), None)
    if not chrome_exe:
        raise HTTPException(status_code=500, detail="Google Chrome tidak ditemukan di PC.")

    cmd = [
        chrome_exe,
        f"--user-data-dir={profile_path}",
        "--new-window",
        "https://flow.google.com/",
    ]
    subprocess.Popen(cmd)
    return {
        "status": "opened",
        "message": "Jendela Chrome Google Flow telah dibuka. Silakan login di browser tersebut.",
    }


# ---------------------------------------------------------------------------
# Overnight Batch & Scene Queue Endpoints
# ---------------------------------------------------------------------------
async def _batch_pipeline_runner(item: Dict[str, Any], progress_cb) -> str:
    """Runner callback for BatchQueueManager."""
    job_id = item["id"]
    req = GenerateRequest(
        idea=item["idea"],
        style=item.get("style", "Cinematic"),
        mode=item.get("mode", "idea2video"),
        script=item.get("script", ""),
        skill_id=item.get("skill_id", ""),
        use_storyboard_sheets=item.get("use_storyboard_sheets", True),
    )
    jobs[job_id] = {
        "status": "running",
        "events": [],
        "video_url": None,
        "error": None,
        "queue": asyncio.Queue(),
    }

    # Intercept progress callback to update batch queue item
    async def wrapped_cb(stage: str, msg: str, pct: int):
        await progress_cb(stage, msg, pct)
        if job_id in jobs:
            event = {"type": "progress", "stage": stage, "message": msg, "progress": pct}
            jobs[job_id]["events"].append(event)
            await jobs[job_id]["queue"].put(event)

    await run_pipeline(job_id, req)
    job = jobs.get(job_id)
    if job and job.get("status") == "completed" and job.get("video_url"):
        return job["video_url"]
    elif job and job.get("error"):
        raise RuntimeError(job["error"])
    raise RuntimeError("Unknown batch execution error")


@app.get("/api/batch/status")
async def get_batch_status():
    return await batch_queue.get_queue_status()


@app.post("/api/batch/add")
async def add_batch_items(req: BatchAddRequest):
    added = await batch_queue.add_batch(req.items)
    # Auto-start worker if not already running
    if not batch_queue.is_running:
        batch_queue.start_worker(_batch_pipeline_runner)
    return {"status": "ok", "count": len(added), "items": added}


@app.post("/api/batch/add-single")
async def add_single_batch_item(req: BatchSingleAddRequest):
    item = await batch_queue.add_item(
        title=req.title,
        idea=req.idea,
        style=req.style,
        skill_id=req.skill_id,
        mode=req.mode,
        script=req.script,
        use_storyboard_sheets=req.use_storyboard_sheets,
    )
    if not batch_queue.is_running:
        batch_queue.start_worker(_batch_pipeline_runner)
    return {"status": "ok", "item": item}


@app.post("/api/batch/start")
async def start_batch():
    batch_queue.is_paused = False
    if not batch_queue.is_running:
        batch_queue.start_worker(_batch_pipeline_runner)
    return {"status": "started", "is_running": batch_queue.is_running}


@app.post("/api/batch/pause")
async def pause_batch():
    await batch_queue.pause()
    return {"status": "paused", "is_paused": True}


@app.post("/api/batch/resume")
async def resume_batch():
    await batch_queue.resume()
    if not batch_queue.is_running:
        batch_queue.start_worker(_batch_pipeline_runner)
    return {"status": "resumed", "is_paused": False}


@app.post("/api/batch/retry/{item_id}")
async def retry_batch_item(item_id: str):
    success = await batch_queue.retry_item(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Item tidak ditemukan di antrean.")
    if not batch_queue.is_running:
        batch_queue.start_worker(_batch_pipeline_runner)
    return {"status": "queued", "id": item_id}


@app.delete("/api/batch/{item_id}")
async def delete_batch_item(item_id: str):
    removed = await batch_queue.remove_item(item_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Item tidak ditemukan di antrean.")
    return {"status": "removed", "id": item_id}


@app.post("/api/batch/clear")
async def clear_batch():
    removed_count = await batch_queue.clear_completed()
    return {"status": "cleared", "removed_count": removed_count}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
