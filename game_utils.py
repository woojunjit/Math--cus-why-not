import json
import random
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

PLAYER_DATA_PATH = Path("player_data.json")
LESSON_DATA_PATH = Path("lesson_data.json")
QUIZ_DATA_PATH = Path("quiz_data.json")

XP_CORRECT = 10
XP_INCORRECT = -5
XP_LEVEL_THRESHOLD = 100
MAX_HINTS_PER_TOPIC = 3

LANDS = [
    "Fractions Forest",
    "Decimal Desert",
    "Geometry Galaxy",
    "Measurement Mountain",
    "Word Problem World",
]

DEFAULT_SLOTS = ["Slot 1", "Slot 2", "Slot 3"]

DEFAULT_PROFILE_TEMPLATE = {
    "player_name": None,
    "level": 1,
    "xp": 0,
    "badges": [],
    "unlocked_lands": [LANDS[0]],
    "hint_tokens": {land: MAX_HINTS_PER_TOPIC for land in LANDS},
    "last_hint_reset": None,
    "avatar": None,
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, data):
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


def default_profile() -> Dict:
    return deepcopy(DEFAULT_PROFILE_TEMPLATE)


def sanitize_profile(profile: Dict) -> Dict:
    sanitized = default_profile()
    if profile is None:
        return sanitized
    sanitized.update({
        "player_name": profile.get("player_name") or sanitized["player_name"],
        "level": profile.get("level", sanitized["level"]),
        "xp": max(0, profile.get("xp", sanitized["xp"])),
        "badges": profile.get("badges") or sanitized["badges"],
        "unlocked_lands": profile.get("unlocked_lands") or sanitized["unlocked_lands"],
        "last_hint_reset": profile.get("last_hint_reset", sanitized["last_hint_reset"]),
        "avatar": profile.get("avatar") or sanitized["avatar"],
    })

    sanitized["badges"] = list(dict.fromkeys(sanitized["badges"]))
    sanitized["unlocked_lands"] = [land for land in LANDS if land in sanitized["unlocked_lands"]]
    if not sanitized["unlocked_lands"]:
        sanitized["unlocked_lands"].append(LANDS[0])

    hint_tokens = profile.get("hint_tokens", {}) if profile else {}
    sanitized["hint_tokens"] = {land: hint_tokens.get(land, MAX_HINTS_PER_TOPIC) for land in LANDS}
    return sanitized


def ensure_profile_store() -> Dict:
    if not PLAYER_DATA_PATH.exists():
        store = {
            "active_slot": DEFAULT_SLOTS[0],
            "slots": {slot: None for slot in DEFAULT_SLOTS},
        }
        store["slots"][DEFAULT_SLOTS[0]] = default_profile()
        save_json(PLAYER_DATA_PATH, store)
        return store

    data = load_json(PLAYER_DATA_PATH)
    if "slots" not in data:
        migrated = {
            "active_slot": DEFAULT_SLOTS[0],
            "slots": {slot: None for slot in DEFAULT_SLOTS},
        }
        migrated["slots"][DEFAULT_SLOTS[0]] = sanitize_profile(data)
        save_json(PLAYER_DATA_PATH, migrated)
        return migrated

    for slot in DEFAULT_SLOTS:
        data.setdefault("slots", {})
        if slot not in data["slots"]:
            data["slots"][slot] = None

    for slot, profile in data["slots"].items():
        if profile is not None:
            data["slots"][slot] = sanitize_profile(profile)

    if data.get("active_slot") not in data["slots"]:
        data["active_slot"] = DEFAULT_SLOTS[0]

    save_json(PLAYER_DATA_PATH, data)
    return data


def save_profiles(store: Dict):
    save_json(PLAYER_DATA_PATH, store)


def list_slots(store: Dict) -> List[str]:
    return list(store["slots"].keys())


def get_active_profile(store: Dict) -> Dict:
    slot = store.get("active_slot", DEFAULT_SLOTS[0])
    if slot not in store["slots"]:
        slot = DEFAULT_SLOTS[0]
        store["active_slot"] = slot
    if store["slots"][slot] is None:
        store["slots"][slot] = default_profile()
    return store["slots"][slot]


def set_active_slot(store: Dict, slot: str) -> Dict:
    if slot not in store["slots"]:
        raise ValueError(f"Unknown slot {slot}")
    store["active_slot"] = slot
    if store["slots"][slot] is None:
        store["slots"][slot] = default_profile()
    return store["slots"][slot]


def delete_slot(store: Dict, slot: str):
    if slot not in store["slots"]:
        return
    store["slots"][slot] = None
    if store.get("active_slot") == slot:
        for candidate in DEFAULT_SLOTS:
            if store["slots"].get(candidate):
                store["active_slot"] = candidate
                break
        else:
            store["active_slot"] = DEFAULT_SLOTS[0]
            if store["slots"].get(DEFAULT_SLOTS[0]) is None:
                store["slots"][DEFAULT_SLOTS[0]] = default_profile()


def ensure_player_profile():
    store = ensure_profile_store()
    return store, get_active_profile(store)


def reset_hint_tokens(profile: Dict):
    today = datetime.utcnow().date().isoformat()
    if profile.get("last_hint_reset") != today:
        for land in LANDS:
            profile.setdefault("hint_tokens", {})
            profile["hint_tokens"][land] = MAX_HINTS_PER_TOPIC
        profile["last_hint_reset"] = today


def spend_hint(profile: Dict, land: str) -> bool:
    tokens = profile["hint_tokens"].get(land, 0)
    if tokens > 0:
        profile["hint_tokens"][land] = tokens - 1
        return True
    return False


def award_badge(profile: Dict, land: str, accuracy: float):
    if accuracy >= 0.8:
        badge_name = f"{land} Master"
        if badge_name not in profile["badges"]:
            profile["badges"].append(badge_name)
            return badge_name
    return None


def apply_xp_change(profile: Dict, delta: int) -> Tuple[int, bool]:
    profile["xp"] = max(0, profile["xp"] + delta)
    leveled = False
    while profile["xp"] >= XP_LEVEL_THRESHOLD:
        profile["xp"] -= XP_LEVEL_THRESHOLD
        profile["level"] += 1
        leveled = True
    return profile["xp"], leveled


def unlock_next_land(profile: Dict, land_order: List[str], completed_land: str):
    try:
        index = land_order.index(completed_land)
    except ValueError:
        return None
    if index + 1 < len(land_order):
        next_land = land_order[index + 1]
        if next_land not in profile["unlocked_lands"]:
            profile["unlocked_lands"].append(next_land)
            return next_land
    return None


def render_progress_bar(current: int, maximum: int) -> str:
    if maximum <= 0:
        return "[----------] 0%"
    percentage = min(100, max(0, int((current / maximum) * 100)))
    filled_blocks = percentage // 10
    empty_blocks = 10 - filled_blocks
    return f"[{filled_blocks * '#'}{empty_blocks * '-'}] {percentage}%"


def pick_feedback(is_correct: bool, success_list: List[str], failure_list: List[str]) -> str:
    return random.choice(success_list if is_correct else failure_list)


def summarize_results(correct: int, total: int) -> Tuple[float, str]:
    accuracy = correct / total if total else 0
    if accuracy == 1:
        mood = "Legendary victory!"
    elif accuracy >= 0.8:
        mood = "Shining success!"
    elif accuracy >= 0.5:
        mood = "Keep going, adventurer!"
    else:
        mood = "Time to strategize and try again!"
    return accuracy, mood
