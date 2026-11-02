"""
Windows Application Indexer & Launcher.
Scans Windows Start Menu, Desktop shortcuts, and system executables
to reliably locate and launch installed applications by voice name.
"""
import os
import subprocess
import glob
from pathlib import Path
from typing import Optional, Dict, Tuple


class AppLauncher:
    # Common Windows built-in aliases and protocol URIs
    BUILTINS: Dict[str, str] = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "brave": "brave.exe",
        "brave browser": "brave.exe",
        "edge": "msedge.exe",
        "microsoft edge": "msedge.exe",
        "browser": "msedge.exe",
        "paint": "mspaint.exe",
        "mspaint": "mspaint.exe",
        "file explorer": "explorer.exe",
        "explorer": "explorer.exe",
        "files": "explorer.exe",
        "task manager": "taskmgr.exe",
        "terminal": "wt.exe",
        "windows terminal": "wt.exe",
        "cmd": "cmd.exe",
        "command prompt": "cmd.exe",
        "powershell": "powershell.exe",
        "settings": "ms-settings:",
        "camera": "microsoft.windows.camera:",
        "spotify": "spotify:",
        "vs code": "code",
        "vscode": "code",
        "code": "code",
        "word": "winword.exe",
        "excel": "excel.exe",
        "powerpoint": "powerpnt.exe",
        "discord": "discord:",
    }

    # Common web URLs for direct opening
    COMMON_SITES: Dict[str, str] = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "github": "https://www.github.com",
        "chatgpt": "https://chatgpt.com",
        "claude": "https://claude.ai",
        "gemini": "https://gemini.google.com",
        "reddit": "https://www.reddit.com",
        "gmail": "https://mail.google.com",
        "netflix": "https://www.netflix.com",
        "twitter": "https://x.com",
        "x": "https://x.com",
        "instagram": "https://www.instagram.com",
        "whatsapp": "https://web.whatsapp.com",
        "telegram": "https://web.telegram.org",
        "amazon": "https://www.amazon.com",
        "maps": "https://maps.google.com",
        "google maps": "https://maps.google.com",
    }

    def __init__(self):
        self.indexed_apps: Dict[str, str] = {}
        self.refresh_index()

    def refresh_index(self):
        """Scans Desktop and Start Menu for installed applications."""
        self.indexed_apps.clear()
        self.indexed_apps.update(self.BUILTINS)

        search_paths = [
            Path(os.path.expanduser("~")) / "Desktop",
            Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
            Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        ]

        for folder in search_paths:
            if not folder.exists():
                continue
            for lnk in folder.rglob("*.lnk"):
                name = lnk.stem.lower().strip()
                # Remove version numbers and architecture tags for easier voice matching
                clean_name = name.replace(" - shortcut", "").replace(" 64-bit", "").strip()
                self.indexed_apps[clean_name] = str(lnk)
                self.indexed_apps[name] = str(lnk)

    def find_app(self, query: str) -> Optional[Tuple[str, str]]:
        """
        Locates target application by exact match, token boundary, or fuzzy similarity.
        Avoids false positives from arbitrary substring containment.
        Returns: (matched_name, executable_or_path) or None
        """
        import re
        import difflib

        q = query.lower().strip()
        # Strip all punctuation (. , ! ? " ' etc.)
        clean_q = re.sub(r'[^\w\s]', ' ', q)
        clean_q = re.sub(r'\s+', ' ', clean_q).strip()

        # Clean filler prefixes and suffixes
        clean_q = re.sub(r'^(?:the\s+|an?\s+)+', '', clean_q).strip()
        clean_q = re.sub(r'\s+(?:app|application|software|program|tool)$', '', clean_q).strip()

        # 1. Exact match in indexed apps or builtins
        if clean_q in self.indexed_apps:
            return clean_q, self.indexed_apps[clean_q]

        # 2. Exact match in common sites
        if clean_q in self.COMMON_SITES:
            return clean_q, self.COMMON_SITES[clean_q]

        # 3. Whole-word / token boundary scoring
        candidates = []
        for name, path in self.indexed_apps.items():
            if name == clean_q:
                candidates.append((100, len(name), name, path))
            elif name.startswith(clean_q) or clean_q.startswith(name):
                # Strong prefix match
                score = 80 + min(len(name), len(clean_q))
                candidates.append((score, len(name), name, path))
            elif re.search(rf'\b{re.escape(clean_q)}\b', name):
                # Target clean query is a full word inside app name (e.g. 'chrome' in 'google chrome')
                candidates.append((70, len(name), name, path))

        if candidates:
            # Sort by score desc, then name length desc
            candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
            return candidates[0][2], candidates[0][3]

        # 4. Fuzzy match with difflib for slight typos
        matches = difflib.get_close_matches(clean_q, self.indexed_apps.keys(), n=1, cutoff=0.75)
        if matches:
            best = matches[0]
            return best, self.indexed_apps[best]

        return None

    def launch(self, target: str) -> Tuple[bool, str]:
        """Executes the application path, URI, or command non-blockingly."""
        import threading

        def _exec():
            try:
                # 1. If it's a web URL
                if target.startswith("http://") or target.startswith("https://"):
                    import webbrowser
                    webbrowser.open(target)
                    return

                # 2. If it's a protocol URI (e.g. spotify:, ms-settings:)
                if target.endswith(":") or (":" in target and "\\" not in target and "/" not in target):
                    os.startfile(target)
                    return

                # 3. If it's an existing file or shortcut (.lnk or .exe)
                p = Path(target)
                if p.exists():
                    os.startfile(str(p))
                    return

                # 4. If it's a known Windows executable
                subprocess.Popen(f'start "" "{target}"', shell=True)
            except Exception as e:
                print(f"[App Launch Error] {e}")

        threading.Thread(target=_exec, daemon=True).start()
        return True, f"Launched {target}"

