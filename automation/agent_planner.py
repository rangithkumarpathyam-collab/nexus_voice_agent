"""
Agent Mode & Multi-Step Task Planner.
Decomposes complex, heavy user requests (e.g. 'open youtube and play interstellar',
'open notepad and write a summary of AI') into an executable action pipeline.
Uses deterministic pattern decomposition for speed, falling back to local Ollama planner.
"""
import re
import json
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple
import requests

from config import OLLAMA_BASE_URL, OLLAMA_MODEL
from automation.app_launcher import AppLauncher
from automation.media_player import MediaPlayer
from automation.safety_guard import ProposedAction


@dataclass
class PlanStep:
    action_type: str        # 'open_app', 'play_youtube', 'play_spotify', 'open_url', 'type_text', 'press_key', 'wait'
    payload: str            # Target name, URL, query, or text
    description: str        # UI status summary
    requires_approval: bool = False


class AgentPlanner:
    def __init__(self, launcher: AppLauncher):
        self.launcher = launcher

    def plan(self, utterance: str) -> Optional[List[PlanStep]]:
        """
        Inspects utterance. If it represents a compound or media playback task,
        returns an ordered list of PlanSteps. Otherwise returns None.
        """
        text = utterance.strip()
        lowered = text.lower()

        # Clean conversational preambles
        cleaned = re.sub(r'^(?:hey\s+|nexus\s+|jarvis\s+|please\s+|can\s+you\s+)+', '', lowered).strip()
        # Clean all trailing and inline punctuation symbols (. , ! ? " ' ; : `)
        cleaned = re.sub(r'[.,!?"\';:`]', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        # --- 1. DIRECT 'PLAY <SONG> [ON YOUTUBE/SPOTIFY]' ---
        # Example: "play interstellar theme", "play lofi beats on youtube", "play daft punk on spotify", "play munna bhai gaming live"
        play_match = re.match(r'^(?:play|put\s+on|watch|listen\s+to)\s+(.+?)(?:\s+(?:on|in)\s+(youtube|spotify))?$', cleaned)
        if play_match:
            song_query = play_match.group(1).strip()
            destination = (play_match.group(2) or "youtube").strip()

            # Clean leading filler phrases
            song_query = re.sub(r'^(?:the\s+song|the\s+track|the\s+video|some|music)\s+', '', song_query).strip()
            if not song_query or song_query in ["any video", "any song", "something", "a video", "a song"]:
                song_query = "top hits" if destination == "spotify" else "trending"

            if destination == "spotify":
                return [
                    PlanStep(
                        action_type="play_spotify",
                        payload=song_query,
                        description=f"Play '{song_query}' on Spotify",
                        requires_approval=False
                    )
                ]
            else:
                return [
                    PlanStep(
                        action_type="play_youtube",
                        payload=song_query,
                        description=f"Play '{song_query}' on YouTube",
                        requires_approval=False
                    )
                ]

        # --- 2. COMPOUND: YOUTUBE PLAYBACK & CHANNELS ---
        # Examples:
        # "open youtube in browser and play munna bhai gaming live"
        # "open youtube and open Krazy Bro's channel"
        # "open youtube and play any video"
        # "open youtube and watch interstellar"
        # "open youtube and search lofi beats"
        yt_compound = re.match(
            r'^(?:open|launch)\s+youtube(?:\s+in\s+[a-z]+)?\s+(?:and\s+|to\s+)(?:play|watch|open|search(?:\s+for)?|listen\s+to|stream)?\s*(.+)$',
            cleaned
        )
        if yt_compound:
            target = yt_compound.group(1).strip()
            # Clean common filler prefixes
            target = re.sub(r'^(?:the\s+channel|channel|the\s+video|video|song|some|music)\s+', '', target).strip()
            if not target or target in ["any video", "any song", "something", "a video"]:
                target = "trending"
            return [
                PlanStep(
                    action_type="play_youtube",
                    payload=target,
                    description=f"Play '{target}' on YouTube",
                    requires_approval=False
                )
            ]

        # --- 3. COMPOUND: SPOTIFY PLAYBACK ---
        # Examples: "open spotify and any song", "open spotify and play believer", "open spotify to listen to coldplay"
        spotify_compound = re.match(
            r'^(?:open|launch)\s+spotify(?:\s+in\s+[a-z]+)?\s+(?:and\s+|to\s+)(?:play|listen\s+to|stream|search(?:\s+for)?)?\s*(.+)$',
            cleaned
        )
        if spotify_compound:
            target = spotify_compound.group(1).strip()
            target = re.sub(r'^(?:the\s+song|the\s+track|song|music)\s+', '', target).strip()
            if not target or target in ["any song", "a song", "something", "any music"]:
                target = "top hits"
            return [
                PlanStep(
                    action_type="play_spotify",
                    payload=target,
                    description=f"Play '{target}' on Spotify",
                    requires_approval=False
                )
            ]

        # --- 4. COMPOUND: BROWSER SEARCH ---
        # Examples: "open chrome and search for quantum computing", "open browser and search python"
        search_compound = re.match(
            r'^(?:open|launch)\s+(?:chrome|edge|browser|google)\s+(?:and\s+|to\s+)search(?:\s+for)?\s+(.+)$',
            cleaned
        )
        if search_compound:
            query = search_compound.group(1).strip()
            import urllib.parse
            url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
            return [
                PlanStep(
                    action_type="open_url",
                    payload=url,
                    description=f"Search Google for '{query}'",
                    requires_approval=False
                )
            ]

        # --- 5. COMPOUND: 'OPEN NOTEPAD AND (TYPE/WRITE) <TEXT>' ---
        open_and_type = re.match(
            r'^(?:open|launch)\s+(notepad|word|text\s+editor|code)\s+(?:and\s+|to\s+)(?:type|write)\s+(.+)$',
            cleaned
        )
        if open_and_type:
            app = open_and_type.group(1).strip()
            content = open_and_type.group(2).strip()
            return [
                PlanStep(action_type="open_app", payload=app, description=f"Open {app.title()}"),
                PlanStep(action_type="wait", payload="1.5", description="Waiting for window to focus"),
                PlanStep(
                    action_type="type_text",
                    payload=content,
                    description=f"Type into {app.title()}: '{content}'",
                    requires_approval=True # Explicit user approval requirement enforced!
                )
            ]

        # --- 6. COMPOUND 'AND' SPLITTER FOR INDEPENDENT COMMANDS ---
        # Example: "open notepad and open calculator", "launch spotify and open chrome"
        if " and " in cleaned:
            parts = [p.strip() for p in cleaned.split(" and ") if p.strip()]
            steps: List[PlanStep] = []
            for part in parts:
                sub_match = re.match(r'^(?:open|launch|start)\s+(.+)$', part)
                if sub_match:
                    target = sub_match.group(1).strip()
                    app_match = self.launcher.find_app(target)
                    if app_match:
                        steps.append(
                            PlanStep(
                                action_type="open_app",
                                payload=app_match[1],
                                description=f"Launch {app_match[0].title()}"
                            )
                        )
            if len(steps) >= 2:
                return steps

        return None

    def _ask_llm_planner(self, instruction: str) -> Optional[List[PlanStep]]:
        """Invokes local Ollama with a strict JSON planning schema."""
        prompt = f"""
You are an operating system execution planner. Break the user's desktop instruction into sequential steps.
Available actions:
- {{"action": "open_app", "target": "app_name"}}
- {{"action": "play_youtube", "query": "song or video name"}}
- {{"action": "play_spotify", "query": "song or artist name"}}
- {{"action": "open_url", "url": "https://..."}}
- {{"action": "wait", "seconds": 1.5}}
- {{"action": "type_text", "text": "text to type"}}

User Instruction: "{instruction}"

Respond ONLY with a JSON array of actions. No explanations or conversational text.
Example: [{{"action": "open_app", "target": "notepad"}}, {{"action": "wait", "seconds": 1.5}}, {{"action": "type_text", "text": "Hello"}}]
"""
        try:
            url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/generate"
            res = requests.post(
                url,
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "format": "json"},
                timeout=10.0
            )
            if res.status_code == 200:
                raw_json = res.json().get("response", "[]")
                parsed = json.loads(raw_json)
                steps: List[PlanStep] = []
                for item in parsed:
                    act = item.get("action", "")
                    if act in ["open_app", "open_url", "play_youtube", "play_spotify"]:
                        target = item.get("target") or item.get("query") or item.get("url", "")
                        steps.append(PlanStep(action_type=act, payload=target, description=f"{act}: {target}"))
                    elif act == "type_text":
                        text_val = item.get("text", "")
                        steps.append(PlanStep(action_type=act, payload=text_val, description=f"Type: '{text_val}'", requires_approval=True))
                    elif act == "wait":
                        sec = str(item.get("seconds", 1))
                        steps.append(PlanStep(action_type=act, payload=sec, description=f"Wait {sec}s"))
                return steps if steps else None
        except Exception as e:
            print(f"LLM planner exception: {e}")
        return None
