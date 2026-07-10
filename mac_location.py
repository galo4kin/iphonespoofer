"""macOS CoreLocation helper runner.

Launches the bundled WhereAmI.app (a signed CoreLocation helper) to read the
Mac's real location. iOS cannot report the connected phone's real GPS, so the
Mac's own location (it sits next to the phone) is the best real start point.
Result is cached for the session.
"""

import os
import subprocess
import sys
import tempfile
import time


_cache = {"data": None, "ts": 0}
_CACHE_TTL = 300  # 5 min


def _helper_app_path():
    """Locate the bundled WhereAmI.app helper."""
    if getattr(sys, "frozen", False):
        # Frozen: Contents/MacOS/<exe>  ->  Contents/Resources/WhereAmI.app
        macos_dir = os.path.dirname(sys.executable)
        return os.path.join(os.path.dirname(macos_dir), "Resources", "WhereAmI.app")
    # Dev: repo-local build output (may not exist in dev — caller handles None)
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "maclocation", "WhereAmI.app")


def get_mac_location(timeout=25):
    """Return {'lat', 'lon', 'accuracy'} from macOS CoreLocation, or None.

    First call may show a one-time location permission prompt. Cached for 5 min.
    """
    now = time.time()
    if _cache["data"] and now - _cache["ts"] < _CACHE_TTL:
        return _cache["data"]

    app_path = _helper_app_path()
    if not os.path.isdir(app_path):
        return None

    fd, out = tempfile.mkstemp(suffix=".loc", prefix="iphonespoofer_")
    os.close(fd)
    try:
        os.remove(out)
    except OSError:
        pass

    try:
        # `open --args <out>` passes the output path to the helper's argv.
        subprocess.run(["open", app_path, "--args", out], check=False, timeout=10)
    except Exception:
        return None

    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(out):
            try:
                data = open(out).read().strip()
            except OSError:
                data = ""
            if data.startswith("OK"):
                parts = data.split()
                try:
                    result = {
                        "lat": float(parts[1]),
                        "lon": float(parts[2]),
                        "accuracy": float(parts[3].split("=", 1)[1]) if len(parts) > 3 and "=" in parts[3] else None,
                    }
                except (ValueError, IndexError):
                    result = None
                _try_remove(out)
                if result:
                    _cache.update(data=result, ts=time.time())
                return result
            if data.startswith(("DENIED", "TIMEOUT", "ERR")):
                _try_remove(out)
                return None
        time.sleep(0.5)

    _try_remove(out)
    return None


def _try_remove(path):
    try:
        os.remove(path)
    except OSError:
        pass
