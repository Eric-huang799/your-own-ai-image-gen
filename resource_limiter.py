"""Resource Limiter - temporarily reduce non-AI process resource usage during generation.

Does NOT kill processes. Only:
  - Lowers CPU priority (IDLE / BELOW_NORMAL)
  - Trims working set (RAM) of browser and non-essential processes
  - Restores original state after generation completes
"""

import threading
import time
import psutil

# Processes to keep at normal priority (AI infrastructure)
KEEP_NAMES = {
    "python.exe", "python3.exe", "ollama.exe", "ollama_llm_server.exe",
    "comfyui", "cmd.exe", "conhost.exe", "WindowsTerminal.exe",
}

# Processes to throttle (big memory consumers)
THROTTLE_NAMES = {
    "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe",
    "discord.exe", "telegram.exe", "slack.exe", "spotify.exe",
    "Code.exe", "qq.exe", "wechat.exe", "WeChat.exe",
    "explorer.exe",
}


class ResourceLimiter:
    def __init__(self):
        self._saved_states = {}
        self._active = False
        self._monitor_thread = None
        self._freed_mb = 0

    @property
    def freed_mb(self):
        return self._freed_mb

    def engage(self) -> int:
        """Reduce non-AI resource usage. Returns freed RAM in MB."""
        if self._active:
            return 0

        self._active = True
        self._saved_states = {}
        freed = 0

        for proc in psutil.process_iter(["pid", "name", "nice", "memory_info"]):
            try:
                name = proc.info["name"].lower() if proc.info["name"] else ""
                pid = proc.info["pid"]

                # Skip AI infrastructure
                if name in KEEP_NAMES or any(k in name for k in ["ollama", "python", "comfy"]):
                    continue

                # Save original state
                saved = {
                    "nice": proc.nice(),
                    "ionice": None,
                }
                try:
                    saved["ionice"] = proc.ionice()
                except Exception:
                    pass

                # For known memory hogs: aggressively trim
                if any(t in name.lower() for t in THROTTLE_NAMES):
                    saved["mem_before"] = proc.info["memory_info"].rss if proc.info["memory_info"] else 0

                    # Lower CPU priority to idle
                    try:
                        proc.nice(psutil.IDLE_PRIORITY_CLASS)
                    except Exception:
                        try:
                            proc.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
                        except Exception:
                            pass

                    # Trim working set (release physical RAM, pages can be faulted back)
                    try:
                        mem_before = proc.memory_info().rss
                        psutil.Process(pid).memory_full_info()
                        if hasattr(psutil, "windows"):
                            import ctypes
                            ctypes.windll.psapi.EmptyWorkingSet(proc._handle)
                        mem_after = proc.memory_info().rss
                        freed += (mem_before - mem_after)
                    except Exception:
                        pass

                self._saved_states[pid] = saved
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        self._freed_mb = freed // (1024 * 1024)
        return self._freed_mb

    def restore(self):
        """Restore original process priorities."""
        if not self._active:
            return

        for pid, saved in self._saved_states.items():
            try:
                proc = psutil.Process(pid)
                if saved.get("nice") is not None:
                    proc.nice(saved["nice"])
                if saved.get("ionice") is not None:
                    try:
                        proc.ionice(saved["ionice"])
                    except Exception:
                        pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        self._saved_states.clear()
        self._active = False
        self._freed_mb = 0

    def __enter__(self):
        freed = self.engage()
        return self

    def __exit__(self, *args):
        self.restore()


_limiter = ResourceLimiter()


def engage_limits() -> int:
    """Public API: engage resource limits. Returns freed RAM in MB."""
    return _limiter.engage()


def restore_limits():
    """Public API: restore original resource state."""
    _limiter.restore()


def get_limiter() -> ResourceLimiter:
    return _limiter
