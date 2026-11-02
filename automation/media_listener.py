"""
Windows System Media Transport Controls (SMTC) Real-Time Listener.
Detects any audio or video playing across the entire Windows OS (Chrome, YouTube, Spotify, VLC, Edge, etc.)
and extracts title, artist, playback status, position, duration, and thumbnail artwork.
"""
import os
import sys
import json
import time
import subprocess
import threading
from pathlib import Path
from typing import Optional, Dict, Any

from PySide6.QtCore import QObject, Signal

from config import DATA_DIR

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False


POWERSHELL_SMTC_SCRIPT = r"""
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { 
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' 
})[0]

function Await-WinRT($asyncOp, $type) {
    if (-not $asyncOp) { return $null }
    $asTask = $asTaskGeneric.MakeGenericMethod($type)
    $netTask = $asTask.Invoke($null, @($asyncOp))
    $netTask.Wait(-1) | Out-Null
    return $netTask.Result
}

try {
    [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager, Windows.Media, ContentType = WindowsRuntime] | Out-Null
    $managerAsync = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]::RequestAsync()
    $manager = Await-WinRT $managerAsync ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager])
} catch {
    Write-Output '{"Status":"Unavailable"}'
    exit
}

$lastTitle = ""
$lastStatus = ""
$thumbSaved = $false
$thumbPath = [System.IO.Path]::Combine($args[0], "current_media_thumb.jpg")

while ($true) {
    try {
        $session = $manager.GetCurrentSession()
        if ($session) {
            $info = $session.GetPlaybackInfo()
            $status = "$($info.PlaybackStatus)"
            $propsAsync = $session.TryGetMediaPropertiesAsync()
            $props = Await-WinRT $propsAsync ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties])
            
            $title = if ($props -and $props.Title) { $props.Title } else { "" }
            $artist = if ($props -and $props.Artist) { $props.Artist } else { "" }
            
            $timeline = $session.GetTimelineProperties()
            $pos = if ($timeline) { [math]::Round($timeline.Position.TotalSeconds, 1) } else { 0 }
            $dur = if ($timeline) { [math]::Round($timeline.EndTime.TotalSeconds, 1) } else { 0 }
            
            if ($title -ne $lastTitle) {
                $lastTitle = $title
                $thumbSaved = $false
                # Extract new thumbnail artwork
                if ($props -and $props.Thumbnail) {
                    try {
                        $thumbRef = $props.Thumbnail
                        $streamAsync = $thumbRef.OpenReadAsync()
                        $stream = Await-WinRT $streamAsync ([Windows.Storage.Streams.IRandomAccessStreamWithContentType])
                        if ($stream) {
                            $m = [System.IO.WindowsRuntimeStreamExtensions].GetMethod("AsStream", [Type[]]@([Windows.Storage.Streams.IRandomAccessStream]))
                            $netStream = $m.Invoke($null, @($stream))
                            $fileStream = [System.IO.File]::Create($thumbPath)
                            $netStream.CopyTo($fileStream)
                            $fileStream.Close()
                            $thumbSaved = $true
                        }
                    } catch {
                        $thumbSaved = $false
                    }
                }
            }
            
            $hasThumb = if ($thumbSaved -and (Test-Path $thumbPath)) { $thumbPath } else { "" }
            
            $obj = @{
                Status = $status
                Title = $title
                Artist = $artist
                Position = $pos
                Duration = $dur
                SourceApp = "$($session.SourceAppUserModelId)"
                ThumbnailPath = $hasThumb
            }
            Write-Output ($obj | ConvertTo-Json -Compress)
        } else {
            Write-Output '{"Status":"Closed"}'
        }
    } catch {
        Write-Output '{"Status":"Closed"}'
    }
    Start-Sleep -Milliseconds 800
}
"""


class SystemMediaListener(QObject):
    """
    Watches Windows System Media Transport Controls in real time.
    Emits media_updated(dict) on playback events.
    """
    media_updated = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._proc: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self.script_path = DATA_DIR / "smtc_listener.ps1"
        self.thumb_path = DATA_DIR / "current_media_thumb.jpg"
        self.last_state: Dict[str, Any] = {"Status": "Closed"}

    def start(self):
        if self._running:
            return
        self._running = True

        # Write the PowerShell script file into data directory
        try:
            self.script_path.write_text(POWERSHELL_SMTC_SCRIPT, encoding="utf-8")
        except Exception as e:
            print(f"[MediaListener] Error writing script: {e}")

        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._proc:
            try:
                self._proc.terminate()
            except Exception:
                pass
            self._proc = None

    def _worker(self):
        while self._running:
            try:
                data_dir_str = str(DATA_DIR)
                cmd = [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy", "Bypass",
                    "-File", str(self.script_path),
                    data_dir_str
                ]

                # Run powershell worker without showing console window
                startupinfo = None
                if sys.platform == "win32":
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = 0

                self._proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    bufsize=1,
                    startupinfo=startupinfo
                )

                for line in self._proc.stdout:
                    if not self._running:
                        break
                    line_str = line.strip()
                    if not line_str:
                        continue
                    try:
                        data = json.loads(line_str)
                        self.last_state = data
                        self.media_updated.emit(data)
                    except Exception:
                        pass

            except Exception as e:
                # Sleep before retrying if listener encounters an issue
                time.sleep(2.0)

            time.sleep(1.0)

    # --- MEDIA ACTION HELPERS ---
    @staticmethod
    def play_pause():
        if HAS_PYAUTOGUI:
            pyautogui.press("playpause")

    @staticmethod
    def next_track():
        if HAS_PYAUTOGUI:
            pyautogui.press("nexttrack")

    @staticmethod
    def prev_track():
        if HAS_PYAUTOGUI:
            pyautogui.press("prevtrack")
