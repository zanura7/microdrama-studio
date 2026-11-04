"""
Cross-Platform Browser Session & Login Manager for Google Flow & AI Services.
Works natively on Windows, macOS, and Linux without hardcoded batch files.
Supports in-app trigger via API for Tauri / Electron UI.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any

from engines.flow_engine.paths import get_flow_profile_dir, get_app_data_dir

def find_system_chrome() -> str:
    """Find installed Google Chrome binary across Windows and macOS."""
    if sys.platform == "win32":
        candidates = [
            Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        ]
        for c in candidates:
            if c.exists() and c.is_file():
                return str(c)
        return "chrome.exe"
    elif sys.platform == "darwin":
        mac_candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        ]
        for mc in mac_candidates:
            if os.path.isfile(mc):
                return mc
        return "google-chrome"
    else:
        return "google-chrome"

def launch_flow_login_window(account_name: str = "default") -> Dict[str, Any]:
    """
    Spawns a clean Chrome browser window dedicated to the account profile
    so the user can authenticate Google Flow in-app.
    """
    profile_dir = get_flow_profile_dir(account_name)
    chrome_bin = find_system_chrome()
    url = "https://flow.google.com/?hl=en"

    cmd = [
        chrome_bin,
        f"--user-data-dir={str(profile_dir)}",
        "--no-first-run",
        "--no-default-browser-check",
        url,
    ]

    try:
        # Spawn detached process so it doesn't block backend
        if sys.platform == "win32":
            subprocess.Popen(cmd, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)

        return {
            "success": True,
            "account": account_name,
            "profile_dir": str(profile_dir),
            "message": "Login window launched. Please sign in to Google Flow and close the browser when done.",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "profile_dir": str(profile_dir),
        }

def check_flow_session_status(account_name: str = "default") -> Dict[str, Any]:
    """Checks if cookies/session exist for the given profile."""
    profile_dir = get_flow_profile_dir(account_name)
    cookie_db = profile_dir / "Default" / "Network" / "Cookies"

    # Also check legacy path on dev PC
    legacy_cookie = Path.home() / ".google-flow-creator" / "browser-profile" / "Default" / "Network" / "Cookies"
    legacy_accounts = list((Path.home() / ".google-flow-creator" / "accounts").glob("*/browser-profile/Default/Network/Cookies")) if (Path.home() / ".google-flow-creator" / "accounts").exists() else []

    is_logged_in = cookie_db.exists() and cookie_db.stat().st_size > 0
    if not is_logged_in and (legacy_cookie.exists() or legacy_accounts):
        is_logged_in = True

    return {
        "account": account_name,
        "is_authenticated": is_logged_in,
        "profile_dir": str(profile_dir),
    }
