"""
Media Automation Player.
Directly searches and launches playback on YouTube and Spotify without third-party API keys.
"""
import urllib.request
import urllib.parse
import re
import os
import webbrowser
from typing import Tuple


class MediaPlayer:
    @staticmethod
    def play_youtube(query: str) -> Tuple[bool, str, str]:
        """
        Launches YouTube playback in background thread without freezing the UI.
        Returns immediately (< 1ms).
        """
        import threading
        search_query = query.strip()
        encoded = urllib.parse.quote_plus(search_query)
        search_url = f"https://www.youtube.com/results?search_query={encoded}"

        def _resolve_and_launch():
            try:
                req = urllib.request.Request(
                    search_url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                )
                with urllib.request.urlopen(req, timeout=1.8) as response:
                    html = response.read().decode("utf-8", errors="ignore")
                    video_ids = re.findall(r'watch\?v=([a-zA-Z0-9_-]{11})', html)
                    if not video_ids:
                        video_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)

                    if video_ids:
                        video_url = f"https://www.youtube.com/watch?v={video_ids[0]}"
                        webbrowser.open(video_url)
                        return
            except Exception:
                pass
            # Fallback to direct search results page
            webbrowser.open(search_url)

        threading.Thread(target=_resolve_and_launch, daemon=True).start()
        return True, search_url, f"Playing '{search_query}' on YouTube"

    @staticmethod
    def play_spotify(query: str) -> Tuple[bool, str, str]:
        """
        Launches Spotify playback in background thread without freezing the UI.
        Returns immediately (< 1ms).
        """
        import threading
        search_query = query.strip()
        encoded = urllib.parse.quote(search_query)

        def _launch():
            try:
                spotify_uri = f"spotify:search:{encoded}"
                os.startfile(spotify_uri)
            except Exception:
                web_url = f"https://open.spotify.com/search/{encoded}"
                webbrowser.open(web_url)

        threading.Thread(target=_launch, daemon=True).start()
        return True, f"spotify:search:{encoded}", f"Playing '{search_query}' on Spotify"
