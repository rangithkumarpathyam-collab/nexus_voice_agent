"""
Deterministic Command Router for Desktop Actions.
Intercepts voice commands (e.g., 'open notepad', 'launch brave', 'search google', 'what time is it')
before delegating to the conversational LLM.
"""
import re
import urllib.parse
from datetime import datetime
from typing import Optional, NamedTuple, List
from automation.app_launcher import AppLauncher
from automation.safety_guard import ProposedAction
from automation.agent_planner import AgentPlanner, PlanStep
from automation.media_player import MediaPlayer

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False


class CommandResult(NamedTuple):
    is_command: bool
    spoken_response: str
    display_response: str
    action: Optional[ProposedAction]
    auto_execute: bool = False
    steps: Optional[List[PlanStep]] = None


class CommandRouter:
    def __init__(self):
        self.launcher = AppLauncher()
        self.planner = AgentPlanner(self.launcher)

    def route(self, utterance: str) -> CommandResult:
        text = utterance.strip().lower()

        # Clean leading words like "nexus", "hey nexus", "jarvis", "please", "can you"
        cleaned = re.sub(r'^(?:hey\s+|nexus\s+|jarvis\s+|please\s+|can\s+you\s+)+', '', text).strip()
        # Clean all punctuation symbols (. , ! ? " ' ; : `)
        cleaned = re.sub(r'[.,!?"\';:`]', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        # --- 0. MULTI-STEP / MEDIA PLANNER CHECK (Open & Play, Play Song, Compound Chains) ---
        plan = self.planner.plan(cleaned)
        if plan:
            if len(plan) == 1:
                step = plan[0]
                action = ProposedAction(
                    action_type=step.action_type,
                    description=step.description,
                    payload=step.payload,
                    risk_level="low"
                )
                if step.action_type == "play_spotify":
                    spoken = f"Playing {step.payload} on Spotify."
                    display = f"[PLAY] {step.description}..."
                elif step.action_type == "play_youtube":
                    spoken = f"Playing {step.payload} on YouTube."
                    display = f"[PLAY] {step.description}..."
                elif step.action_type == "open_url":
                    spoken = f"Opening search in browser."
                    display = f"[SEARCH] {step.description}..."
                else:
                    spoken = f"Executing {step.description}."
                    display = f"[ACTION] {step.description}..."

                return CommandResult(
                    is_command=True,
                    spoken_response=spoken,
                    display_response=display,
                    action=action,
                    auto_execute=True,
                    steps=None
                )
            else:
                # Multi-step compound pipeline
                plan_summary = " -> ".join([s.description for s in plan])
                return CommandResult(
                    is_command=True,
                    spoken_response=f"Executing {len(plan)} steps.",
                    display_response=f"[PLAN] **Compound Plan:** {plan_summary}",
                    action=None,
                    auto_execute=True,
                    steps=plan
                )

        # --- 1. OPEN / LAUNCH APPLICATION OR WEBSITE ---
        open_match = re.match(r'^(?:open|launch|start|run|bring\s+up|go\s+to)\s+(?:the\s+)?(.+)$', cleaned)
        if open_match:
            app_target = open_match.group(1).strip()
            # Look up in app index or common sites
            match = self.launcher.find_app(app_target)
            if match:
                matched_name, target_path = match
                action = ProposedAction(
                    action_type="open_app",
                    description=f"Launch application: {matched_name.title()}",
                    payload=target_path,
                    risk_level="low"
                )
                return CommandResult(
                    is_command=True,
                    spoken_response=f"Opening {matched_name.title()}.",
                    display_response=f"Launching **{matched_name.title()}**...",
                    action=action,
                    auto_execute=True
                )
            else:
                # Check if it's a domain name (e.g. "openai.com")
                if "." in app_target and " " not in app_target:
                    url = f"https://{app_target}"
                    return CommandResult(
                        is_command=True,
                        spoken_response=f"Opening {app_target}.",
                        display_response=f"Navigating to **{app_target}**...",
                        action=ProposedAction(action_type="open_url", description=f"Open {url}", payload=url, risk_level="low"),
                        auto_execute=True
                    )

                # Never fall back to unwanted browser searches! Inform the user immediately.
                return CommandResult(
                    is_command=True,
                    spoken_response=f"I couldn't find an application named {app_target}.",
                    display_response=f"Application not found: **{app_target}**",
                    action=None,
                    auto_execute=True
                )

        # --- 2. SEARCH GOOGLE / YOUTUBE ---
        search_match = re.match(r'^(?:search\s+(?:for\s+)?|google\s+)(.+)$', cleaned)
        if search_match:
            query = search_match.group(1).strip()
            encoded = urllib.parse.quote_plus(query)
            url = f"https://www.google.com/search?q={encoded}"
            return CommandResult(
                is_command=True,
                spoken_response=f"Searching Google for {query}.",
                display_response=f"Searching Google for: **{query}**",
                action=ProposedAction(
                    action_type="open_url",
                    description=f"Search Google for {query}",
                    payload=url,
                    risk_level="low"
                ),
                auto_execute=True
            )

        youtube_match = re.match(r'^(?:youtube\s+(?:search\s+)?|play\s+on\s+youtube\s+)(.+)$', cleaned)
        if youtube_match:
            query = youtube_match.group(1).strip()
            encoded = urllib.parse.quote_plus(query)
            url = f"https://www.youtube.com/results?search_query={encoded}"
            return CommandResult(
                is_command=True,
                spoken_response=f"Searching YouTube for {query}.",
                display_response=f"Searching YouTube for: **{query}**",
                action=ProposedAction(
                    action_type="open_url",
                    description=f"Search YouTube for {query}",
                    payload=url,
                    risk_level="low"
                ),
                auto_execute=True
            )

        # --- 3. TIME AND DATE ---
        if re.search(r'\b(what\s+time|current\s+time|tell\s+me\s+the\s+time)\b', cleaned):
            now_str = datetime.now().strftime("%I:%M %p")
            return CommandResult(
                is_command=True,
                spoken_response=f"The time is {now_str}.",
                display_response=f"Current time: **{now_str}**",
                action=None,
                auto_execute=True
            )

        if re.search(r'\b(what\s+date|today\'s\s+date|what\s+day\s+is\s+it)\b', cleaned):
            now_str = datetime.now().strftime("%A, %B %d, %Y")
            return CommandResult(
                is_command=True,
                spoken_response=f"Today is {now_str}.",
                display_response=f"Today: **{now_str}**",
                action=None,
                auto_execute=True
            )

        # --- 4. VOLUME & MEDIA CONTROLS ---
        if re.search(r'\b(headset\s+on|wear\s+headset|put\s+on\s+headset|wear\s+headphones)\b', cleaned):
            return CommandResult(
                is_command=True,
                spoken_response="Equipping cyberpunk headset.",
                display_response="[HEADSET] Headset equipped.",
                action=ProposedAction(action_type="headset_on", description="Equip Cyberpunk Headset", payload="on", risk_level="low"),
                auto_execute=True
            )
        if re.search(r'\b(headset\s+off|remove\s+headset|take\s+off\s+headset|remove\s+headphones)\b', cleaned):
            return CommandResult(
                is_command=True,
                spoken_response="Removing headset.",
                display_response="[HEADSET] Headset removed.",
                action=ProposedAction(action_type="headset_off", description="Remove Cyberpunk Headset", payload="off", risk_level="low"),
                auto_execute=True
            )
        if re.search(r'\b(stop\s+music|pause\s+music|stop\s+playback|pause\s+song|pause)\b', cleaned):
            return CommandResult(
                is_command=True,
                spoken_response="Pausing music.",
                display_response="[PAUSE] Music playback paused.",
                action=ProposedAction(action_type="pause_music", description="Pause Media Playback", payload="playpause", risk_level="low"),
                auto_execute=True
            )
        if re.search(r'\b(next\s+track|next\s+song|skip\s+track|skip\s+song)\b', cleaned):
            return CommandResult(
                is_command=True,
                spoken_response="Skipping to next track.",
                display_response="[NEXT] Next Track",
                action=ProposedAction(action_type="press_key", description="Next Track", payload="nexttrack", risk_level="low"),
                auto_execute=True
            )
        if re.search(r'\b(previous\s+track|previous\s+song|prev\s+track)\b', cleaned):
            return CommandResult(
                is_command=True,
                spoken_response="Going to previous track.",
                display_response="[PREV] Previous Track",
                action=ProposedAction(action_type="press_key", description="Previous Track", payload="prevtrack", risk_level="low"),
                auto_execute=True
            )

        if "volume up" in cleaned or "increase volume" in cleaned:
            return CommandResult(
                is_command=True,
                spoken_response="Increasing volume.",
                display_response="Volume Up",
                action=ProposedAction(action_type="press_key", description="Increase Volume", payload="volumeup", risk_level="low"),
                auto_execute=True
            )
        if "volume down" in cleaned or "decrease volume" in cleaned:
            return CommandResult(
                is_command=True,
                spoken_response="Lowering volume.",
                display_response="Volume Down",
                action=ProposedAction(action_type="press_key", description="Decrease Volume", payload="volumedown", risk_level="low"),
                auto_execute=True
            )
        if "mute" in cleaned:
            return CommandResult(
                is_command=True,
                spoken_response="Muting audio.",
                display_response="Mute Audio",
                action=ProposedAction(action_type="press_key", description="Mute Volume", payload="volumemute", risk_level="low"),
                auto_execute=True
            )

        return CommandResult(is_command=False, spoken_response="", display_response="", action=None)
