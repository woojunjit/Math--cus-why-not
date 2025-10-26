import os
import sys
from pathlib import Path
from time import perf_counter

from art_assets import (
    AVATAR_OPTIONS,
    BADGE_EMOJI,
    HINT_EMOJI,
    HP_EMOJI,
    SUCCESS_EMOJIS,
    FAILURE_EMOJIS,
    XP_EMOJI,
    LEVEL_EMOJI,
    COLOR_PALETTES,
    render_title_banner,
    render_battle_header,
    render_lesson_header,
    render_results_header,
    format_land_line,
    render_map_panel,
    render_results_table,
)
from game_utils import (
    LESSON_DATA_PATH,
    QUIZ_DATA_PATH,
    ensure_player_profile,
    save_profiles,
    load_json,
    reset_hint_tokens,
    spend_hint,
    award_badge,
    apply_xp_change,
    unlock_next_land,
    pick_feedback,
    summarize_results,
    XP_CORRECT,
    XP_INCORRECT,
    XP_LEVEL_THRESHOLD,
    list_slots,
    set_active_slot,
    default_profile,
    LANDS,
    refresh_daily_challenge,
    get_daily_challenge_questions,
    mark_daily_completion,
    claim_daily_reward,
    RETRY_MAX_HEARTS,
    get_retry_hearts,
    consume_retry_heart,
    retry_cooldown_remaining,
    load_leaderboard,
    sync_leaderboard,
)

LAND_ORDER = LANDS

HP_PER_QUIZ = 3


def clear_console():
    os.system("cls" if os.name == "nt" else "clear")


def press_enter():
    input("\nPress Enter to continue...")


def display_title():
    clear_console()
    render_title_banner()
    print("Welcome to MathQuest6: The Adventure of Numbers!\n")


def show_leaderboard(store):
    sync_leaderboard(store)
    board = load_leaderboard()
    entries = board.get("entries", [])
    clear_console()
    print("🏆 MathQuest6 Leaderboard 🏆\n")
    if not entries:
        print("No adventurers recorded yet. Complete quests to claim a spot!\n")
        press_enter()
        return
    print(f"Updated: {board.get('updated_at', 'N/A')}\n")
    print("Rank | Adventurer       | Lv | XP  | Badges | Best Streak | Daily Clears")
    print("-----+-------------------+----+-----+--------+-------------+--------------")
    for index, entry in enumerate(entries, start=1):
        name = entry.get("player_name", "Hero")[:17].ljust(17)
        level = str(entry.get("level", 1)).rjust(2)
        xp = str(entry.get("xp", 0)).rjust(4)
        badges = str(entry.get("badge_count", 0)).rjust(6)
        streak = str(entry.get("streak_best", 0)).rjust(11)
        clears = str(entry.get("total_dailies", 0)).rjust(12)
        print(f"{index:>4} | {name} | {level} | {xp} | {badges} | {streak} | {clears}")
    press_enter()


def attempt_daily_challenge(store, profile, quiz_bank):
    hearts = get_retry_hearts(profile)
    cooldown_seconds = retry_cooldown_remaining(profile) if hearts <= 0 else 0
    if hearts <= 0 and cooldown_seconds > 0:
        minutes = cooldown_seconds // 60
        seconds = cooldown_seconds % 60
        print(
            "\nDaily challenge unavailable. All retry hearts are depleted."
            f" Rest for {minutes:02d}:{seconds:02d} before trying again.\n"
        )
        press_enter()
        return None
    refresh_daily_challenge(profile, quiz_bank)
    land, questions = get_daily_challenge_questions(profile, quiz_bank)
    if not land:
        print("\nDaily challenge is not ready yet. Come back later!\n")
        press_enter()
        return None
    if not questions:
        print("\nDaily challenge has no questions configured right now. Try again after updating quiz data.\n")
        press_enter()
        return None
    print("\nEmbarking on today's daily challenge!\n")
    start_time = perf_counter()
    success = battle_quiz(profile, land, questions)
    elapsed_seconds = int(perf_counter() - start_time)
    if success:
        newly_completed = mark_daily_completion(profile, elapsed_seconds)
        save_profiles(store)
        if newly_completed:
            print("\nDaily challenge complete! Visit the map to claim your reward.\n")
        else:
            print("\nDaily challenge already marked as complete for today.\n")
    else:
        print("\nDaily challenge attempt ended early. Regroup and try again!\n")
        remaining_hearts = consume_retry_heart(profile)
        save_profiles(store)
        if remaining_hearts > 0:
            print(f"Retry hearts remaining: {remaining_hearts}/{RETRY_MAX_HEARTS}.")
        else:
            cooldown_seconds = retry_cooldown_remaining(profile)
            minutes = cooldown_seconds // 60
            seconds = cooldown_seconds % 60
            print(
                "All retry hearts spent. Rest for "
                f"{minutes:02d}:{seconds:02d} before your next attempt."
            )
    press_enter()
    return success


def claim_daily_reward_console(store, profile):
    reward = claim_daily_reward(profile)
    if reward is None:
        print("\nNo reward available to claim. Complete the daily challenge first.\n")
        press_enter()
        return
    bonus, badge = reward
    if bonus:
        print(f"\n{XP_EMOJI} Bonus XP awarded: +{bonus}!")
    if badge:
        print(f"{BADGE_EMOJI} Special badge earned: {badge}!")
    if not bonus and not badge:
        print("\nReward claimed! (No additional bonus configured today.)")
    else:
        print("Reward claimed! Keep the streak going.")
    save_profiles(store)
    press_enter()


def select_profile_slot(store):
    while True:
        slots = list_slots(store)
        clear_console()
        render_title_banner()
        print("Choose a save slot:\n")
        for idx, slot in enumerate(slots, start=1):
            profile = store["slots"][slot]
            if profile:
                name = profile.get("player_name") or "Hero"
                summary = f"{name} (Lv {profile.get('level', 1)})"
            else:
                summary = "Empty"
            print(f"{idx}. {slot} - {summary}")
        print("\nEnter a number to load a slot.")
        print("Type 'reset <number>' to clear a slot.")
        choice = input("\nSelection: ").strip().lower()
        if choice.startswith("reset"):
            parts = choice.split()
            if len(parts) == 2 and parts[1].isdigit():
                index = int(parts[1]) - 1
                if 0 <= index < len(slots):
                    target = slots[index]
                    store["slots"][target] = default_profile()
                    save_profiles(store)
                    print(f"{target} reset.")
                else:
                    print("Select a valid slot to reset.")
            else:
                print("Use 'reset <number>'.")
            press_enter()
            continue
        if choice.isdigit():
            index = int(choice) - 1
            if 0 <= index < len(slots):
                profile = set_active_slot(store, slots[index])
                save_profiles(store)
                return profile
        print("Please enter a valid option.")
        press_enter()


def pick_avatar(profile):
    picked = profile.get("avatar")
    if picked:
        return
    print("Choose an avatar to represent your math hero:\n")
    for idx, avatar in enumerate(AVATAR_OPTIONS, start=1):
        print(f"{idx}. {avatar}")
    while True:
        choice = input("\nEnter the number for your favorite avatar: ")
        if choice.isdigit() and 1 <= int(choice) <= len(AVATAR_OPTIONS):
            profile["avatar"] = AVATAR_OPTIONS[int(choice) - 1]
            break
        print("Please choose a valid option.")


def show_profile(profile):
    clear_console()
    print("🧭 Adventurer Profile 🧭\n")
    print(f"Name     : {profile['player_name']}")
    print(f"Avatar   : {profile.get('avatar', 'Unassigned')}")
    print(f"Level    : {profile['level']}")
    print(f"XP       : {profile['xp']} / {XP_LEVEL_THRESHOLD}")
    print(f"Badges   : {', '.join(profile['badges']) if profile['badges'] else 'None yet'}")
    print(f"Lands    : {', '.join(profile['unlocked_lands'])}")
    press_enter()


def render_map(profile):
    lines = []
    for land in LAND_ORDER:
        unlocked = land in profile["unlocked_lands"]
        status = "✅" if unlocked else "🔒"
        emoji = COLOR_PALETTES[land]["emoji"]
        lines.append(format_land_line(status, emoji, land, unlocked))
    clear_console()
    render_map_panel(lines)


def list_options(options):
    for key, value in options.items():
        print(f"  {key}) {value}")


def get_player_answer(options):
    valid = set(options.keys())
    while True:
        choice = input("Your answer: ").lower().strip()
        if choice in valid:
            return choice
        print("Choose one of the given options.")


def maybe_use_hint(profile, land, question):
    if profile["hint_tokens"].get(land, 0) <= 0:
        print("No hint tokens left for this land today!\n")
        return
    use_hint = input("Need a hint? (y/n): ").strip().lower()
    if use_hint == "y":
        if spend_hint(profile, land):
            print(f"{HINT_EMOJI} Hint: {question['hint']}\n")
        else:
            print("No hint tokens remaining.\n")


def battle_quiz(profile, land, questions):
    clear_console()
    render_battle_header()
    print(f"You face the challenges of {land}!\n")

    hp = HP_PER_QUIZ
    correct_answers = 0
    for number, question in enumerate(questions, start=1):
        print(f"Challenge {number}: {question['creature']} appears!\n")
        print(question["prompt"])
        list_options(question["options"])
        maybe_use_hint(profile, land, question)
        answer = get_player_answer(question["options"])

        if answer == question["answer"]:
            correct_answers += 1
            print(f"\n{pick_feedback(True, SUCCESS_EMOJIS, FAILURE_EMOJIS)} {question['explanation']}")
            current_xp, leveled = apply_xp_change(profile, XP_CORRECT)
            print(f"{XP_EMOJI} +{XP_CORRECT} XP (XP: {current_xp}/{XP_LEVEL_THRESHOLD})")
            if leveled:
                print(f"{LEVEL_EMOJI} Level up! You reached level {profile['level']}!\n")
        else:
            hp -= 1
            print(f"\n{pick_feedback(False, SUCCESS_EMOJIS, FAILURE_EMOJIS)} The correct answer was {question['options'][question['answer']]}. {question['explanation']}")
            current_xp, leveled = apply_xp_change(profile, XP_INCORRECT)
            print(f"{XP_EMOJI} {XP_INCORRECT} XP (XP: {current_xp}/{XP_LEVEL_THRESHOLD})")
            if leveled:
                print(f"{LEVEL_EMOJI} Level up! You reached level {profile['level']}!\n")
            print(f"{HP_EMOJI} Remaining hearts: {hp}\n")
            if hp <= 0:
                print("Your hearts are depleted! Retreat to the map and regain strength.\n")
                break
        press_enter()
        clear_console()
        render_battle_header()

    accuracy, mood = summarize_results(correct_answers, len(questions))
    clear_console()
    render_results_header()
    rows = [
        ("Correct Answers", f"{correct_answers}/{len(questions)}", "bright_green"),
        ("Accuracy", f"{accuracy * 100:.0f}%", "cyan"),
        ("Mood", mood, "magenta"),
    ]
    render_results_table(rows)

    badge_awarded = award_badge(profile, land, accuracy)
    if badge_awarded:
        print(f"{BADGE_EMOJI} New Badge Earned: {badge_awarded}!")

    next_land = None
    if accuracy >= 0.6 and hp > 0:
        next_land = unlock_next_land(profile, LAND_ORDER, land)
        if next_land:
            print(f"\nYou unlocked {next_land}! 🎉")

    press_enter()
    return hp > 0


def read_lessons_and_quizzes():
    lessons = load_json(LESSON_DATA_PATH)
    quiz_bank = load_json(QUIZ_DATA_PATH)
    return lessons, quiz_bank


def show_lesson(lessons, land):
    lesson = lessons.get(land)
    if not lesson:
        print("No lesson data available for this land.\n")
        return
    clear_console()
    render_lesson_header()
    palette = COLOR_PALETTES[land]
    print(f"{palette['emoji']} {land} Story")
    print("==============================")
    print(f"{lesson['story']}\n")
    print("Learning Objectives:")
    for objective in lesson["learning_objectives"]:
        print(f" - {objective}")
    print("\nExample Walkthrough:")
    print(lesson["example_walkthrough"])
    press_enter()


def choose_land(profile):
    while True:
        render_map(profile)
        challenge = profile.get("daily_challenge") or {}
        stats = profile.get("daily_stats") or {}
        land = challenge.get("land")
        emoji = COLOR_PALETTES.get(land, {}).get("emoji", "⭐") if land else "⭐"
        hearts_available = get_retry_hearts(profile)
        cooldown_seconds = retry_cooldown_remaining(profile) if hearts_available == 0 else 0
        if cooldown_seconds:
            minutes = cooldown_seconds // 60
            seconds = cooldown_seconds % 60
            cooldown_text = f"Cooldown {minutes:02d}:{seconds:02d}"
        else:
            cooldown_text = "Ready"
        if land:
            status_parts = ["Completed" if challenge.get("completed") else "Ready"]
            status_parts.append("Reward claimed" if challenge.get("reward_claimed") else "Reward pending")
            status_text = ", ".join(status_parts)
        else:
            status_text = "Not generated yet"
        bonus = challenge.get("bonus_xp", 0)
        streak_current = stats.get("streak_current", 0)
        streak_best = stats.get("streak_best", 0)
        print(
            "\nDaily Challenge: "
            f"{emoji} {land or 'TBD'} — {status_text} | Bonus XP {bonus}"
            f" | Streak {streak_current} (best {streak_best})"
        )
        print(f"Retry Hearts: {hearts_available}/{RETRY_MAX_HEARTS} — {cooldown_text}")
        print("Commands: number to enter land, 'daily' to attempt, 'claim' to collect reward, 'profile' to review, 'quit' to exit.")
        print("\nSelect a land to explore or choose a command:")
        for idx, land in enumerate(LAND_ORDER, start=1):
            locked = land not in profile["unlocked_lands"]
            label = f"{idx}. {land}{' (locked)' if locked else ''}"
            print(label)
        choice = input("\nEnter number or command: ").strip().lower()
        if choice == "profile":
            show_profile(profile)
            continue
        if choice == "daily":
            return "daily", None
        if choice == "claim":
            return "claim", None
        if choice == "leaderboard":
            show_leaderboard(store)
            continue
        if choice == "quit":
            return "quit", None
        if choice.isdigit():
            index = int(choice) - 1
            if 0 <= index < len(LAND_ORDER):
                land_name = LAND_ORDER[index]
                if land_name in profile["unlocked_lands"]:
                    return "land", land_name
                print("That land is still locked. Complete earlier quests first!\n")
            else:
                print("Please choose a valid land number.\n")
        else:
            print("Type a number or 'profile'.\n")
        press_enter()


def main():
    display_title()
    store, profile = ensure_player_profile()
    profile = select_profile_slot(store)
    reset_hint_tokens(profile)
    save_profiles(store)

    if not profile.get("player_name"):
        profile["player_name"] = input("Adventurer, what is your name? ").strip() or "Hero"
    pick_avatar(profile)
    save_profiles(store)

    lessons, quizzes = read_lessons_and_quizzes()

    while True:
        action, payload = choose_land(profile)
        if action == "land" and payload:
            land = payload
            show_lesson(lessons, land)
            success = battle_quiz(profile, land, quizzes[land])
            save_profiles(store)
            if not success:
                print("Take a break, review lessons, and return stronger!\n")
                press_enter()
            continue
        if action == "daily":
            attempt_daily_challenge(store, profile, quizzes)
            continue
        if action == "claim":
            claim_daily_reward_console(store, profile)
            continue
        if action == "quit":
            break

    print("\nThanks for playing MathQuest6! Keep your adventurous spirit alive!\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nFarewell, adventurer!")
        sys.exit(0)
