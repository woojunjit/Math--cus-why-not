import os
import sys
from pathlib import Path

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
        print("\nSelect a land to explore or type 'profile' to review your hero:")
        for idx, land in enumerate(LAND_ORDER, start=1):
            locked = land not in profile["unlocked_lands"]
            label = f"{idx}. {land}{' (locked)' if locked else ''}"
            print(label)
        choice = input("\nEnter number or command: ").strip().lower()
        if choice == "profile":
            show_profile(profile)
            continue
        if choice.isdigit():
            index = int(choice) - 1
            if 0 <= index < len(LAND_ORDER):
                land_name = LAND_ORDER[index]
                if land_name in profile["unlocked_lands"]:
                    return land_name
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
        land = choose_land(profile)
        show_lesson(lessons, land)
        success = battle_quiz(profile, land, quizzes[land])
        save_profiles(store)
        if not success:
            print("Take a break, review lessons, and return stronger!\n")
            press_enter()

        again = input("Return to map for another quest? (y/n): ").strip().lower()
        if again != "y":
            break

    print("\nThanks for playing MathQuest6! Keep your adventurous spirit alive!\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nFarewell, adventurer!")
        sys.exit(0)
