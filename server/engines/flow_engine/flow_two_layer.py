"""Google Flow 2-Layer Video Generator (ViBot Architecture Replication).

Menggabungkan:
1. Arsitektur 2-Layer Eksekusi (ViBot):
   - Layer 1: Native Headless Chrome modern (`--headless=new`, `--disable-gpu`)
   - Layer 2: Off-Screen Window Fallback (`headless=False`, `--window-position=-3200,-3200`)
   - Isolasi profil temporer per job (`work/chrome_tmp/flow_job_{pid}_{uuid}`)
2. Logika UI Flow yang sudah teruji (`autopost.flow`):
   - Pembuatan project baru & pembersihan overlay banner/agent
   - Lampirkan referensi gambar via dialog aset Flow
   - Setelan aspek rasio 9:16 portrait
   - Pemicu 'Start generation'
   - Submit, polling tile, dan download Original size melalui flow.generate_batch,
     mengikuti engine browser Autopost; tidak memilih URL CDN sembarang.
"""

import json
import logging
import os
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from . import flow

from .paths import get_flow_profile_dir, get_app_data_dir

logger = logging.getLogger("flow_two_layer")

FLOW_HOME = "https://flow.google.com/?hl=en"


def _log(level: str, msg: str, callback: Optional[Callable[[str, str], None]] = None):
    text = f"[Flow2Layer] [{level.upper()}] {msg}"
    if level == "error":
        logger.error(text)
    elif level == "warning":
        logger.warning(text)
    else:
        logger.info(text)
    if callback:
        try:
            callback(level, msg)
        except Exception:
            pass
    print(text, flush=True)


def clear_profile_locks(profile_dir: Path):
    """Hapus lock file Chrome agar tidak bentrok dengan instance lain."""
    lock_names = ["SingletonLock", "SingletonCookie", "SingletonSocket", "lockfile"]
    for name in lock_names:
        p = profile_dir / name
        if p.exists() or p.is_symlink():
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass
    default_dir = profile_dir / "Default"
    if default_dir.exists():
        for lk in default_dir.glob("**/LOCK"):
            try:
                lk.unlink(missing_ok=True)
            except Exception:
                pass


def clone_session_profile(src_profile: Path, target_dir: Path, on_log=None):
    """Clone sesi penting dari akun utama ke direktori temp agar akun asli tidak pernah terkunci."""
    target_dir.mkdir(parents=True, exist_ok=True)
    # 1. Salin Local State di root (kunci enkripsi DPAPI cookies Chrome v120+)
    local_state = src_profile / "Local State"
    if local_state.exists():
        shutil.copy2(local_state, target_dir / "Local State")

    # Salin file konfigurasi dasar root jika ada
    for fname in ["Preferences", "Secure Preferences", "Variations", "Last Version"]:
        src_f = src_profile / fname
        if src_f.exists():
            try:
                shutil.copy2(src_f, target_dir / fname)
            except Exception:
                pass

    default_src = src_profile / "Default"
    default_dst = target_dir / "Default"

    if default_src.exists():
        default_dst.mkdir(parents=True, exist_ok=True)
        # Salin file sesi & cookies penting
        essential_files = [
            "Cookies", "Cookies-journal",
            "Network Persistent State",
            "Preferences", "Secure Preferences",
            "Login Data", "Web Data",
        ]
        for f in essential_files:
            sf = default_src / f
            if sf.exists():
                try:
                    shutil.copy2(sf, default_dst / f)
                except Exception:
                    pass

        # Salin Local Storage & Session Storage & Network
        for folder in ["Local Storage", "Session Storage", "Network"]:
            s_folder = default_src / folder
            if s_folder.exists():
                try:
                    d_folder = default_dst / folder
                    if d_folder.exists():
                        shutil.rmtree(d_folder, ignore_errors=True)
                    shutil.copytree(s_folder, d_folder, dirs_exist_ok=True)
                except Exception:
                    pass

    clear_profile_locks(target_dir)
    if on_log:
        on_log("info", f"Profil di-clone ke isolasi temp: {target_dir.name}")


class FlowTwoLayerGenerator:
    """Mesin Pembuat Video Google Flow dengan 2 Layer (ViBot Architecture)."""

    def __init__(
        self,
        account_name: str = "akun1",
        profile: Optional[Path] = None,
        chrome_exe: Optional[str] = None,
        tmp_root: Optional[Path] = None,
        on_log: Optional[Callable[[str, str], None]] = None,
        allow_offscreen_fallback: bool = True,
    ):
        self.allow_offscreen_fallback = allow_offscreen_fallback
        self.account_name = account_name
        self.on_log = on_log or (lambda lvl, msg: None)
        self.tmp_root = Path(tmp_root or Path("work/chrome_tmp"))
        self.tmp_root.mkdir(parents=True, exist_ok=True)

        # Cari binary Chrome
        self.chrome_exe = chrome_exe or flow.chrome_path() or self._find_chrome()
        if not self.chrome_exe:
            raise FileNotFoundError("Google Chrome tidak ditemukan di sistem!")

        # Profil selalu milik Flow Video Generator. Tidak ada ketergantungan
        # runtime ke folder/repo Autopost atau ViBot.
        self.src_profile = Path(profile) if profile else self._resolve_profile(account_name)
        if not self.src_profile.exists():
            raise FileNotFoundError(f"Profil Flow untuk akun '{account_name}' tidak ditemukan di {self.src_profile}")

    def _find_chrome(self) -> str:
        cands = [
            os.environ.get("CHROME_PATH"),
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            str(Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe"),
            shutil.which("google-chrome"),
            shutil.which("chrome"),
        ]
        for c in cands:
            if c and os.path.isfile(c):
                return str(c)
        return ""

    def _resolve_profile(self, name: str) -> Path:
        p = Path(name)
        if p.exists() and (p / "Default").exists():
            return p

        # 1. First check standalone app profile directory (Cross-platform)
        app_profile = get_flow_profile_dir(name if name and name not in ("default", "auto") else "default")
        if (app_profile / "Default" / "Network" / "Cookies").exists():
            return app_profile

        # 2. Backward compatibility: check legacy .google-flow-creator directory if on dev PC
        base = Path.home() / ".google-flow-creator"
        if not name or name in ("default", "auto"):
            for cand in ["akun1", "akun2", "akun3", "akun4"]:
                cand_p = base / "accounts" / cand / "browser-profile"
                if cand_p.exists() and (cand_p / "Default" / "Network" / "Cookies").exists():
                    return cand_p
            if (base / "browser-profile" / "Default").exists():
                return base / "browser-profile"

        legacy_prof = base / "accounts" / name / "browser-profile"
        if legacy_prof.exists() and (legacy_prof / "Default").exists():
            return legacy_prof

        # Fallback to standard cross-platform app profile
        return app_profile

    def generate(
        self,
        prompt: str,
        image_paths: Optional[List[str]] = None,
        aspect_ratio: str = "9:16",
        output_path: Optional[str] = None,
        timeout_seconds: int = 240,
        approve_credits: Optional[int] = None,
        on_submit: Optional[Callable[[], None]] = None,
    ) -> Dict[str, Any]:
        """Eksekusi proses generasi video dengan otomatis mencoba Layer 1 lalu fallback ke Layer 2."""
        flow.LAST.update(sent=False, project_url=None, credits=0,
                         balance=None)
        image_paths = [str(Path(p).resolve()) for p in (image_paths or []) if Path(p).exists()]
        if not output_path:
            # Next to tmp_root (data/chrome_tmp in the app), never relative to the cwd.
            out_dir = self.tmp_root.parent / "flow_results"
            out_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(out_dir / f"flow_{int(time.time())}_{uuid.uuid4().hex[:6]}.mp4")

        out_path_obj = Path(output_path).resolve()
        out_path_obj.parent.mkdir(parents=True, exist_ok=True)
        # Nothing was submitted yet, so an existing file is a leftover from an
        # earlier attempt; the size checks below must never accept it as this render.
        out_path_obj.unlink(missing_ok=True)

        job_id = f"flow_job_{os.getpid()}_{uuid.uuid4().hex}"
        job_profile = self.tmp_root / job_id

        try:
            clone_session_profile(self.src_profile, job_profile, self.on_log)

            # Coba Layer 1: Native Headless modern
            _log("info", ">>> MENJALANKAN LAYER 1: Chrome Native Headless modern (--headless=new)", self.on_log)
            try:
                res = self._run_browser_cycle(
                    layer=1,
                    profile_dir=job_profile,
                    prompt=prompt,
                    image_paths=image_paths,
                    aspect_ratio=aspect_ratio,
                    output_path=str(out_path_obj),
                    timeout_seconds=timeout_seconds,
                    approve_credits=approve_credits,
                    on_submit=on_submit,
                )
                if res.get("success"):
                    _log("info", f"Layer 1 BERHASIL! Video tersimpan: {out_path_obj}", self.on_log)
                    res["layer_used"] = 1
                    return res
                else:
                    if flow.LAST.get("sent") or not self.allow_offscreen_fallback:
                        raise flow.FlowError(res.get("error") or "Submit sudah dilakukan; lanjutkan unduhan tanpa generate ulang")
                    _log("warning", f"Layer 1 tidak menghasilkan video: {res.get('error')}. Mempersiapkan Layer 2...", self.on_log)
            except Exception as e:
                # Begitu klik Generate mungkin sudah diterima Google, jangan
                # pernah pindah layer dan menghabiskan kredit untuk kedua kali.
                # Saldo kurang juga tidak berubah di Layer 2; pemanggil merotasi akun.
                if flow.LAST.get("sent") or isinstance(e, flow.CreditsLow) or not self.allow_offscreen_fallback:
                    raise
                _log("warning", f"Layer 1 error / terdeteksi ({str(e)[:140]}). Beralih otomatis ke Layer 2...", self.on_log)

            # Fallback ke Layer 2: Off-Screen Window
            _log("info", ">>> MENJALANKAN LAYER 2: Off-Screen Window Fallback (--window-position=-3200,-3200)", self.on_log)
            # Like Autopost: fallback gets a fresh clone, not the failed browser's state.
            fallback_profile = self.tmp_root / (job_id + "_fallback")
            clone_session_profile(self.src_profile, fallback_profile, self.on_log)
            res2 = self._run_browser_cycle(
                layer=2,
                profile_dir=fallback_profile,
                prompt=prompt,
                image_paths=image_paths,
                aspect_ratio=aspect_ratio,
                output_path=str(out_path_obj),
                timeout_seconds=timeout_seconds,
                approve_credits=approve_credits,
                on_submit=on_submit,
            )
            res2["layer_used"] = 2
            return res2

        finally:
            try:
                time.sleep(1)
                shutil.rmtree(job_profile, ignore_errors=True)
                shutil.rmtree(self.tmp_root / (job_id + "_fallback"), ignore_errors=True)
            except Exception:
                pass

    def _run_browser_cycle(
        self, layer: int, profile_dir: Path, prompt: str,
        image_paths: List[str], aspect_ratio: str, output_path: str,
        timeout_seconds: int, approve_credits: Optional[int],
        on_submit: Optional[Callable[[], None]],
    ) -> Dict[str, Any]:
        """Use the same UI submit/poll/download path as Autopost's browser engine."""
        if aspect_ratio != "9:16":
            raise flow.FlowError("Generator Omni ini mendukung rasio 9:16")
        details = {}
        outputs = flow.generate_batch(
            [{"prompt": prompt, "refs": image_paths, "out": Path(output_path)}],
            profile=profile_dir, approve_credits=approve_credits,
            timeout_s=timeout_seconds, on_submit=on_submit, details=details,
            headless=layer == 1, offscreen=layer == 2,
            chrome_exe=self.chrome_exe,
            log=lambda message: _log("info", message, self.on_log),
        )
        if len(outputs) != 1 or not Path(outputs[0]).is_file():
            raise flow.FlowError("Flow tidak mengembalikan satu file video")
        target = Path(outputs[0])
        with target.open("rb") as video:
            valid = b"ftyp" in video.read(64)
        if not valid or target.stat().st_size < 1024:
            raise flow.FlowError("Hasil Flow bukan MP4 yang valid")
        return dict(success=True, video_path=str(target),
                    file_size=target.stat().st_size, **details)

    def _download_stream(self, url: str, target_file: str):
        """Download binary MP4 langsung dari URL CDN Google."""
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            },
        )
        # Write to a .part file so an interrupted stream never leaves a truncated
        # MP4 at target_file that later size checks would accept as a result.
        partial = Path(str(target_file) + ".part")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp, open(partial, "wb") as f:
                shutil.copyfileobj(resp, f)
            partial.replace(target_file)
        finally:
            partial.unlink(missing_ok=True)
