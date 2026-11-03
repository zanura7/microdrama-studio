import asyncio
import json
import os
import random
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class BatchQueueManager:
    """
    Manages overnight mass episode queues with:
    - Serial Execution (Concurrency = 1)
    - Anti-Ban Throttling (Inter-episode delay 5-10s)
    - Persistent JSON storage (survives crashes/restarts)
    - Auto-Retry failed episodes up to 3 times
    """

    def __init__(self, storage_path: Optional[Path] = None):
        if storage_path is None:
            storage_path = Path("outputs") / "batch_queue.json"
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = asyncio.Lock()
        self.is_running = False
        self.is_paused = False
        self.worker_task: Optional[asyncio.Task] = None
        self.pipeline_runner = None  # Injected from api.py

        # Initialize or load queue
        self.queue: List[Dict[str, Any]] = self._load_storage()

    def _load_storage(self) -> List[Dict[str, Any]]:
        if self.storage_path.is_file():
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                # Reset any stuck "processing" items back to "queued" on startup
                for item in data:
                    if item.get("status") == "processing":
                        item["status"] = "queued"
                        item["note"] = "Recovered from server restart"
                return data
            except Exception as e:
                print(f"[BatchQueue] Error reading storage: {e}")
        return []

    def _save_storage(self) -> None:
        try:
            temp_path = self.storage_path.with_suffix(".tmp")
            temp_path.write_text(json.dumps(self.queue, indent=2, ensure_ascii=False), encoding="utf-8")
            if temp_path.is_file():
                temp_path.replace(self.storage_path)
        except Exception as e:
            print(f"[BatchQueue] Error saving storage: {e}")

    async def add_item(
        self,
        title: str,
        idea: str,
        style: str = "Cinematic",
        skill_id: str = "",
        mode: str = "idea2video",
        script: str = "",
        use_storyboard_sheets: bool = True,
    ) -> Dict[str, Any]:
        """Add a single episode to the queue."""
        async with self.lock:
            item_id = str(uuid.uuid4())
            item = {
                "id": item_id,
                "title": title or f"Episode {len(self.queue) + 1}",
                "idea": idea,
                "script": script,
                "mode": mode,
                "style": style,
                "skill_id": skill_id,
                "use_storyboard_sheets": use_storyboard_sheets,
                "status": "queued",  # queued, processing, completed, failed, paused
                "progress": 0,
                "current_stage": "queued",
                "message": "Menunggu giliran antrean...",
                "video_url": None,
                "error": None,
                "attempts": 0,
                "max_attempts": 3,
                "created_at": datetime.now().isoformat(),
                "started_at": None,
                "completed_at": None,
            }
            self.queue.append(item)
            self._save_storage()
            return item

    async def add_batch(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add multiple episodes at once (Overnight Batch)."""
        added = []
        async with self.lock:
            for i, data in enumerate(items):
                item_id = str(uuid.uuid4())
                title = data.get("title") or f"Episode {len(self.queue) + 1}"
                item = {
                    "id": item_id,
                    "title": title,
                    "idea": data.get("idea", ""),
                    "script": data.get("script", ""),
                    "mode": data.get("mode", "idea2video"),
                    "style": data.get("style", "Cinematic"),
                    "skill_id": data.get("skill_id", ""),
                    "use_storyboard_sheets": data.get("use_storyboard_sheets", True),
                    "status": "queued",
                    "progress": 0,
                    "current_stage": "queued",
                    "message": "Menunggu giliran antrean...",
                    "video_url": None,
                    "error": None,
                    "attempts": 0,
                    "max_attempts": 3,
                    "created_at": datetime.now().isoformat(),
                    "started_at": None,
                    "completed_at": None,
                }
                self.queue.append(item)
                added.append(item)
            self._save_storage()
        return added

    async def get_queue_status(self) -> Dict[str, Any]:
        """Get summary and items list."""
        async with self.lock:
            total = len(self.queue)
            queued = sum(1 for x in self.queue if x["status"] == "queued")
            processing = sum(1 for x in self.queue if x["status"] == "processing")
            completed = sum(1 for x in self.queue if x["status"] == "completed")
            failed = sum(1 for x in self.queue if x["status"] == "failed")
            return {
                "is_running": self.is_running,
                "is_paused": self.is_paused,
                "stats": {
                    "total": total,
                    "queued": queued,
                    "processing": processing,
                    "completed": completed,
                    "failed": failed,
                },
                "items": self.queue,
            }

    async def pause(self) -> None:
        self.is_paused = True

    async def resume(self) -> None:
        self.is_paused = False

    async def remove_item(self, item_id: str) -> bool:
        async with self.lock:
            initial_len = len(self.queue)
            self.queue = [x for x in self.queue if x["id"] != item_id]
            if len(self.queue) != initial_len:
                self._save_storage()
                return True
            return False

    async def retry_item(self, item_id: str) -> bool:
        async with self.lock:
            for x in self.queue:
                if x["id"] == item_id:
                    x["status"] = "queued"
                    x["error"] = None
                    x["progress"] = 0
                    x["message"] = "Siap untuk diproses ulang..."
                    x["attempts"] = 0
                    self._save_storage()
                    return True
            return False

    async def clear_completed(self) -> int:
        async with self.lock:
            initial_len = len(self.queue)
            self.queue = [x for x in self.queue if x["status"] not in ("completed", "failed")]
            removed = initial_len - len(self.queue)
            if removed > 0:
                self._save_storage()
            return removed

    def start_worker(self, runner_callback) -> None:
        """Starts background worker if not already running."""
        self.pipeline_runner = runner_callback
        if self.worker_task is None or self.worker_task.done():
            self.is_running = True
            self.worker_task = asyncio.create_task(self._worker_loop())

    async def _worker_loop(self) -> None:
        """Serial worker loop (Concurrency = 1)."""
        print("[BatchWorker] Overnight Queue Worker started.")
        while self.is_running:
            try:
                if self.is_paused:
                    await asyncio.sleep(2.0)
                    continue

                # Find next queued item
                target_item = None
                async with self.lock:
                    for item in self.queue:
                        if item["status"] == "queued":
                            target_item = item
                            item["status"] = "processing"
                            item["started_at"] = datetime.now().isoformat()
                            item["current_stage"] = "starting"
                            item["message"] = "Memulai produksi episode..."
                            self._save_storage()
                            break

                if not target_item:
                    # No jobs pending, idle sleep
                    await asyncio.sleep(3.0)
                    continue

                item_id = target_item["id"]
                print(f"[BatchWorker] Processing item {item_id} ({target_item['title']})...")

                # Setup progress callback for this queue item
                async def item_progress(stage: str, msg: str, pct: int):
                    async with self.lock:
                        for it in self.queue:
                            if it["id"] == item_id:
                                it["current_stage"] = stage
                                it["message"] = msg
                                if pct >= 0:
                                    it["progress"] = pct
                                self._save_storage()
                                break

                # Execute pipeline via runner
                try:
                    video_url = await self.pipeline_runner(target_item, item_progress)
                    async with self.lock:
                        for it in self.queue:
                            if it["id"] == item_id:
                                it["status"] = "completed"
                                it["progress"] = 100
                                it["current_stage"] = "done"
                                it["message"] = "Episode selesai diproduksi!"
                                it["video_url"] = video_url
                                it["completed_at"] = datetime.now().isoformat()
                                self._save_storage()
                                break
                    print(f"[BatchWorker] Item {item_id} completed successfully.")

                except Exception as exc:
                    err_msg = str(exc)
                    print(f"[BatchWorker] Error in item {item_id}: {err_msg}")
                    async with self.lock:
                        for it in self.queue:
                            if it["id"] == item_id:
                                it["attempts"] += 1
                                if it["attempts"] < it["max_attempts"]:
                                    it["status"] = "queued"
                                    it["message"] = f"Gagal ({err_msg[:60]}), akan dicoba lagi ({it['attempts']}/{it['max_attempts']})..."
                                else:
                                    it["status"] = "failed"
                                    it["error"] = err_msg
                                    it["current_stage"] = "failed"
                                    it["message"] = f"Gagal permanen setelah {it['max_attempts']} percobaan."
                                it["completed_at"] = datetime.now().isoformat()
                                self._save_storage()
                                break

                # Anti-ban natural delay between episodes (5 to 10 seconds)
                inter_episode_delay = random.uniform(5.0, 10.0)
                print(f"[BatchWorker] Anti-Ban delay: cooling down {inter_episode_delay:.1f}s before next episode...")
                await asyncio.sleep(inter_episode_delay)

            except asyncio.CancelledError:
                print("[BatchWorker] Worker cancelled.")
                break
            except Exception as e:
                print(f"[BatchWorker] Unexpected loop exception: {e}")
                await asyncio.sleep(5.0)

        self.is_running = False
        print("[BatchWorker] Overnight Queue Worker stopped.")
