import os
import sys
from pathlib import Path

def get_app_data_dir() -> Path:
    """
    Returns OS-compliant application data directory:
    - Windows: %APPDATA%/MicrodramaStudio or ~/.microdrama-studio
    - macOS: ~/Library/Application Support/MicrodramaStudio
    - Linux: ~/.local/share/microdrama-studio or ~/.microdrama-studio
    """
    if sys.platform == "win32":
        app_data = os.environ.get("APPDATA")
        if app_data:
            base = Path(app_data) / "MicrodramaStudio"
        else:
            base = Path.home() / ".microdrama-studio"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "MicrodramaStudio"
    else:
        xdg_data = os.environ.get("XDG_DATA_HOME")
        if xdg_data:
            base = Path(xdg_data) / "microdrama-studio"
        else:
            base = Path.home() / ".microdrama-studio"

    base.mkdir(parents=True, exist_ok=True)
    return base

def get_flow_profile_dir(account: str = "default") -> Path:
    """Returns the dedicated Flow browser profile directory for an account."""
    base = get_app_data_dir() / "profiles" / "flow" / account / "browser-profile"
    base.mkdir(parents=True, exist_ok=True)
    return base
