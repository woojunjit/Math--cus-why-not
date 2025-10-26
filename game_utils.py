import json
import random
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

PLAYER_DATA_PATH = Path("player_data.json")
LESSON_DATA_PATH = Path("lesson_data.json")
QUIZ_DATA_PATH = Path("quiz_data.json")
LEADERBOARD_DATA_PATH = Path("leaderboard_data.json")

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
    "Ratio Reef",
    "Algebra Archipelago",
    "Probability Peaks",
    "Logic Lagoon",
]

DEFAULT_SLOTS = ["Slot 1", "Slot 2", "Slot 3"]

DAILY_CHALLENGE_QUESTION_COUNT = 5
DAILY_CHALLENGE_BONUS_XP = 25
DAILY_CHALLENGE_BADGE = "Daily Star"

RETRY_MAX_HEARTS = 3
RETRY_COOLDOWN_MINUTES = 5

LEADERBOARD_MAX_ENTRIES = 10


def daily_challenge_defaults() -> Dict:
    return {
        "date_generated": None,
        "land": None,
        "question_ids": [],
        "bonus_xp": DAILY_CHALLENGE_BONUS_XP,
        "badge_reward": DAILY_CHALLENGE_BADGE,
        "completed": False,
        "reward_claimed": False,
        "completion_timestamp": None,
        "completion_time_seconds": None,
    }


def daily_stats_defaults() -> Dict:
    return {
        "streak_current": 0,
        "streak_best": 0,
        "last_completion_date": None,
        "fastest_completion_seconds": None,
        "total_completions": 0,
    }


def retry_defaults() -> Dict:
    return {
        "hearts": RETRY_MAX_HEARTS,
        "last_depleted_at": None,
    }


def merge_defaults(data: Dict | None, template: Dict) -> Dict:
    merged = template.copy()
    if not data:
        return merged
    for key, value in data.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_defaults(value, merged[key])
        else:
            merged[key] = value
    return merged

DEFAULT_PROFILE_TEMPLATE = {
    "player_name": None,
    "level": 1,
    "xp": 0,
    "badges": [],
    "unlocked_lands": [LANDS[0]],
    "hint_tokens": {land: MAX_HINTS_PER_TOPIC for land in LANDS},
    "last_hint_reset": None,
    "avatar": None,
    "daily_challenge": daily_challenge_defaults(),
    "daily_stats": daily_stats_defaults(),
    "daily_history": [],
    "retry_status": retry_defaults(),
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, data):
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


def leaderboard_defaults() -> Dict:
    return {
        "updated_at": None,
        "entries": [],
    }


def load_leaderboard() -> Dict:
    if not LEADERBOARD_DATA_PATH.exists():
        return leaderboard_defaults()
    try:
        return load_json(LEADERBOARD_DATA_PATH)
    except (json.JSONDecodeError, OSError):  # pragma: no cover - defensive
        return leaderboard_defaults()


def save_leaderboard(data: Dict) -> None:
    save_json(LEADERBOARD_DATA_PATH, data)


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
    sanitized["daily_challenge"] = merge_defaults(profile.get("daily_challenge") if profile else None, daily_challenge_defaults())
    sanitized["daily_stats"] = merge_defaults(profile.get("daily_stats") if profile else None, daily_stats_defaults())
    sanitized["daily_history"] = profile.get("daily_history") or []
    sanitized["retry_status"] = merge_defaults(profile.get("retry_status") if profile else None, retry_defaults())
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
    sync_leaderboard(store)


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


def ensure_daily_structures(profile: Dict):
    profile["daily_challenge"] = merge_defaults(profile.get("daily_challenge"), daily_challenge_defaults())
    profile["daily_stats"] = merge_defaults(profile.get("daily_stats"), daily_stats_defaults())
    profile.setdefault("daily_history", [])


def ensure_retry_status(profile: Dict):
    profile["retry_status"] = merge_defaults(profile.get("retry_status"), retry_defaults())


def refresh_retry_status(profile: Dict) -> Dict:
    ensure_retry_status(profile)
    status = profile["retry_status"]
    hearts = status.get("hearts", RETRY_MAX_HEARTS)
    last_depleted = status.get("last_depleted_at")
    if hearts == 0 and last_depleted:
        try:
            last_dt = datetime.fromisoformat(last_depleted)
        except ValueError:
            last_dt = None
        if last_dt and datetime.utcnow() >= last_dt + timedelta(minutes=RETRY_COOLDOWN_MINUTES):
            status["hearts"] = RETRY_MAX_HEARTS
            status["last_depleted_at"] = None
    return status


def get_retry_hearts(profile: Dict) -> int:
    status = refresh_retry_status(profile)
    return int(status.get("hearts", RETRY_MAX_HEARTS))


def consume_retry_heart(profile: Dict) -> int:
    status = refresh_retry_status(profile)
    hearts = int(status.get("hearts", RETRY_MAX_HEARTS))
    if hearts <= 0:
        return hearts
    hearts -= 1
    status["hearts"] = hearts
    if hearts <= 0:
        status["last_depleted_at"] = utc_now_iso()
    return hearts


def retry_cooldown_remaining(profile: Dict) -> int:
    status = refresh_retry_status(profile)
    hearts = int(status.get("hearts", RETRY_MAX_HEARTS))
    if hearts > 0:
        return 0
    last_depleted = status.get("last_depleted_at")
    if not last_depleted:
        return 0
    try:
        last_dt = datetime.fromisoformat(last_depleted)
    except ValueError:
        return 0
    elapsed = datetime.utcnow() - last_dt
    remaining = (timedelta(minutes=RETRY_COOLDOWN_MINUTES) - elapsed).total_seconds()
    return max(0, int(remaining))


def utc_today() -> datetime.date:
    return datetime.utcnow().date()


def utc_now_iso() -> str:
    return datetime.utcnow().isoformat()


def utc_today_iso() -> str:
    return utc_today().isoformat()


def sync_leaderboard(store: Dict) -> Dict:
    entries = []
    slots = store.get("slots", {}) if isinstance(store, dict) else {}
    for slot_name, profile in slots.items():
        if not profile:
            continue
        sanitized = sanitize_profile(profile)
        daily_stats = sanitized.get("daily_stats", {})
        entry = {
            "slot": slot_name,
            "player_name": sanitized.get("player_name") or slot_name,
            "level": sanitized.get("level", 1),
            "xp": sanitized.get("xp", 0),
            "badge_count": len(sanitized.get("badges", [])),
            "streak_best": daily_stats.get("streak_best", 0),
            "total_dailies": daily_stats.get("total_completions", 0),
        }
        entries.append(entry)

    entries.sort(
        key=lambda item: (
            -item["level"],
            -item["xp"],
            -item["streak_best"],
            -item["total_dailies"],
            item["player_name"].lower(),
        )
    )

    leaderboard = {
        "updated_at": utc_now_iso(),
        "entries": entries[:LEADERBOARD_MAX_ENTRIES],
    }
    save_leaderboard(leaderboard)
    return leaderboard


def refresh_daily_challenge(profile: Dict, quiz_bank: Dict[str, List[Dict]], question_count: int = DAILY_CHALLENGE_QUESTION_COUNT) -> Dict:
    ensure_daily_structures(profile)
    challenge = profile["daily_challenge"]
    today = utc_today_iso()
    if challenge.get("date_generated") == today and challenge.get("land"):
        return challenge
    unlocked = profile.get("unlocked_lands") or [LANDS[0]]
    land = random.choice(unlocked)
    pool = quiz_bank.get(land, [])
    indices = list(range(len(pool)))
    if indices:
        random.shuffle(indices)
        count = min(len(indices), question_count)
        challenge["question_ids"] = indices[:count]
    else:
        challenge["question_ids"] = []
    challenge["land"] = land
    challenge["date_generated"] = today
    challenge["completed"] = False
    challenge["reward_claimed"] = False
    challenge["completion_timestamp"] = None
    challenge["completion_time_seconds"] = None
    challenge["bonus_xp"] = DAILY_CHALLENGE_BONUS_XP
    challenge["badge_reward"] = DAILY_CHALLENGE_BADGE
    return challenge


def get_daily_challenge_questions(profile: Dict, quiz_bank: Dict[str, List[Dict]]) -> Tuple[str | None, List[Dict]]:
    ensure_daily_structures(profile)
    challenge = profile["daily_challenge"]
    land = challenge.get("land")
    if not land:
        return None, []
    pool = quiz_bank.get(land, [])
    if not pool:
        return land, []
    selected: List[Dict] = []
    for index in challenge.get("question_ids", []):
        if 0 <= index < len(pool):
            selected.append(pool[index])
    if not selected:
        count = min(len(pool), DAILY_CHALLENGE_QUESTION_COUNT)
        selected = pool[:count]
    return land, selected


def mark_daily_completion(profile: Dict, seconds_taken: int | None = None) -> bool:
    ensure_daily_structures(profile)
    challenge = profile["daily_challenge"]
    if challenge.get("completed"):
        return False
    stats = profile["daily_stats"]
    today = utc_today()
    today_iso = today.isoformat()
    challenge["completed"] = True
    challenge["completion_timestamp"] = utc_now_iso()
    challenge["completion_time_seconds"] = seconds_taken
    last_completion = stats.get("last_completion_date")
    previous_streak = stats.get("streak_current", 0)
    if last_completion:
        try:
            last_date = datetime.fromisoformat(last_completion).date()
        except ValueError:
            last_date = None
    else:
        last_date = None
    if last_date == today:
        streak = previous_streak or 1
    elif last_date == today - timedelta(days=1):
        streak = (previous_streak or 0) + 1
    else:
        streak = 1
    stats["streak_current"] = streak
    stats["streak_best"] = max(stats.get("streak_best", 0), streak)
    stats["last_completion_date"] = today_iso
    stats["total_completions"] = stats.get("total_completions", 0) + 1
    if seconds_taken is not None:
        fastest = stats.get("fastest_completion_seconds")
        if fastest is None or seconds_taken < fastest:
            stats["fastest_completion_seconds"] = seconds_taken
    profile["daily_history"].append(
        {
            "date": today_iso,
            "land": challenge.get("land"),
            "seconds": seconds_taken,
            "bonus_xp": challenge.get("bonus_xp"),
            "badge_reward": challenge.get("badge_reward"),
        }
    )
    return True


def claim_daily_reward(profile: Dict) -> Tuple[int, str | None] | None:
    ensure_daily_structures(profile)
    challenge = profile["daily_challenge"]
    if not challenge.get("completed") or challenge.get("reward_claimed"):
        return None
    bonus = int(challenge.get("bonus_xp") or 0)
    badge = challenge.get("badge_reward")
    leveled = False
    if bonus:
        _, leveled = apply_xp_change(profile, bonus)
    awarded_badge = None
    if badge and badge not in profile["badges"]:
        profile["badges"].append(badge)
        awarded_badge = badge
    challenge["reward_claimed"] = True
    return bonus, awarded_badge


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
