import tkinter as tk
from tkinter import ttk, messagebox
from time import perf_counter

from art_assets import (
    COLOR_PALETTES,
    SUCCESS_EMOJIS,
    FAILURE_EMOJIS,
    HINT_EMOJI,
    XP_EMOJI,
    LEVEL_EMOJI,
    BADGE_EMOJI,
    HP_EMOJI,
)
from game_utils import (
    LANDS,
    ensure_player_profile,
    save_profiles,
    reset_hint_tokens,
    list_slots,
    set_active_slot,
    default_profile,
    load_json,
    LESSON_DATA_PATH,
    QUIZ_DATA_PATH,
    spend_hint,
    apply_xp_change,
    award_badge,
    unlock_next_land,
    pick_feedback,
    summarize_results,
    refresh_daily_challenge,
    get_daily_challenge_questions,
    mark_daily_completion,
    claim_daily_reward,
    get_retry_hearts,
    retry_cooldown_remaining,
    consume_retry_heart,
    XP_CORRECT,
    XP_INCORRECT,
    XP_LEVEL_THRESHOLD,
    DAILY_CHALLENGE_BONUS_XP,
    DAILY_CHALLENGE_BADGE,
    RETRY_MAX_HEARTS,
)


class MathQuestApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MathQuest6 — GUI Prototype")
        self.geometry("900x600")
        self.minsize(820, 520)
        self.configure(background="#1f1f2e")

        self.store, self.profile = ensure_player_profile()
        reset_hint_tokens(self.profile)
        save_profiles(self.store)

        self.lessons = load_json(LESSON_DATA_PATH)
        self.quiz_bank = load_json(QUIZ_DATA_PATH)
        self.selected_land: str | None = None
        self.daily_attempt_timer: float | None = None
        self.show_daily_card = True

        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("TFrame", background="#1f1f2e")
        self.style.configure("TLabel", background="#1f1f2e", foreground="#f0f0f0")
        self.style.configure("Header.TLabel", font=("Segoe UI", 32, "bold"), foreground="#f7d664")
        self.style.configure("Body.TLabel", font=("Segoe UI", 14), wraplength=760)
        self.style.configure("Accent.TButton", font=("Segoe UI", 14, "bold"))
        self.style.configure("Card.TFrame", background="#2a2a3f", relief="raised")
        self.style.configure("CardHeader.TLabel", font=("Segoe UI", 18, "bold"), background="#2a2a3f")
        self.style.configure("CardBody.TLabel", font=("Segoe UI", 13), background="#2a2a3f", wraplength=320)
        self.style.configure("Dim.TLabel", foreground="#b0b0c0")

        self.container = ttk.Frame(self, padding=32)
        self.container.pack(fill="both", expand=True)

        self.current_frame: ttk.Frame | None = None
        self.ensure_daily_challenge()
        self.show_slot_selection()

    def run(self) -> None:
        self.mainloop()

    def ensure_daily_challenge(self) -> None:
        refresh_daily_challenge(self.profile, self.quiz_bank)
        save_profiles(self.store)

    def swap_content(self, frame: ttk.Frame) -> None:
        if self.current_frame is not None:
            self.current_frame.destroy()
        self.current_frame = frame
        self.current_frame.pack(fill="both", expand=True)

    def show_slot_selection(self) -> None:
        frame = SlotSelectionFrame(
            self.container,
            store=self.store,
            on_select=self.handle_slot_selected,
            on_reset=self.handle_slot_reset,
        )
        self.swap_content(frame)

    def toggle_daily_visibility(self) -> None:
        self.show_daily_card = not self.show_daily_card
        self.show_quest_map()

    def handle_slot_selected(self, slot_name: str) -> None:
        self.profile = set_active_slot(self.store, slot_name)
        reset_hint_tokens(self.profile)
        save_profiles(self.store)
        self.show_title_screen()

    def handle_slot_reset(self, slot_name: str) -> None:
        self.store["slots"][slot_name] = default_profile()
        if self.store.get("active_slot") == slot_name:
            set_active_slot(self.store, slot_name)
        save_profiles(self.store)

    def show_title_screen(self) -> None:
        frame = TitleScreenFrame(
            self.container,
            profile=self.profile,
            on_start=self.show_quest_map,
            on_switch=self.show_slot_selection,
        )
        self.swap_content(frame)

    def show_quest_map(self) -> None:
        self.ensure_daily_challenge()
        frame = QuestMapFrame(
            self.container,
            profile=self.profile,
            on_open_land=self.open_lesson,
            on_back=self.show_title_screen,
            on_open_daily=self.start_daily_challenge,
            on_claim_daily=self.claim_daily_reward_gui,
            on_toggle_daily=self.toggle_daily_visibility,
            show_daily=self.show_daily_card,
        )
        self.swap_content(frame)

    def open_lesson(self, land: str) -> None:
        self.selected_land = land
        lesson = self.lessons.get(land)
        frame = LessonFrame(
            self.container,
            land=land,
            lesson=lesson,
            on_back=self.show_quest_map,
            on_start_battle=self.show_battle,
        )
        self.swap_content(frame)

    def show_battle(self) -> None:
        land = self.selected_land
        questions = self.quiz_bank.get(land, []) if land else []
        frame = BattleFrame(
            self.container,
            profile=self.profile,
            store=self.store,
            land=land,
            questions=questions,
            on_back=self.open_lesson if land else self.show_quest_map,
            on_finish=self.show_quest_map,
        )
        self.swap_content(frame)

    def start_daily_challenge(self) -> None:
        hearts = get_retry_hearts(self.profile)
        cooldown_seconds = retry_cooldown_remaining(self.profile) if hearts <= 0 else 0
        if hearts <= 0 and cooldown_seconds > 0:
            minutes = cooldown_seconds // 60
            seconds = cooldown_seconds % 60
            messagebox.showinfo(
                "Daily Challenge",
                f"Daily challenge unavailable. All retry hearts are depleted. Rest for {minutes:02d}:{seconds:02d} before trying again.",
            )
            return
        self.ensure_daily_challenge()
        land, questions = get_daily_challenge_questions(self.profile, self.quiz_bank)
        if not land:
            messagebox.showinfo("Daily Challenge", "Daily challenge is not ready yet. Come back later!")
            return
        if not questions:
            messagebox.showinfo(
                "Daily Challenge",
                "Daily challenge has no questions configured right now. Try again after updating quiz data.",
            )
            return

        def back_to_map(_land=None):
            self.show_quest_map()

        self.daily_attempt_timer = perf_counter()
        frame = BattleFrame(
            self.container,
            profile=self.profile,
            store=self.store,
            land=land,
            questions=questions,
            on_back=back_to_map,
            on_finish=self.show_quest_map,
            heading=f"Daily Challenge — {land}",
            on_result=self.handle_daily_battle_result,
            back_button_visible=False,
        )
        self.swap_content(frame)

    def handle_daily_battle_result(self, success: bool) -> None:
        elapsed_seconds = None
        if self.daily_attempt_timer is not None:
            elapsed_seconds = int(perf_counter() - self.daily_attempt_timer)
        self.daily_attempt_timer = None
        if success:
            newly_completed = mark_daily_completion(self.profile, elapsed_seconds)
            if newly_completed:
                messagebox.showinfo("Daily Challenge", "Daily challenge complete! Visit the map to claim your reward.")
            else:
                messagebox.showinfo("Daily Challenge", "Daily challenge already marked as complete for today.")
            save_profiles(self.store)
        else:
            remaining_hearts = consume_retry_heart(self.profile)
            if remaining_hearts > 0:
                messagebox.showinfo(
                    "Daily Challenge",
                    f"Daily challenge attempt ended early. Retry hearts remaining: {remaining_hearts}/{RETRY_MAX_HEARTS}.",
                )
            else:
                cooldown_seconds = retry_cooldown_remaining(self.profile)
                minutes = cooldown_seconds // 60
                seconds = cooldown_seconds % 60
                messagebox.showinfo(
                    "Daily Challenge",
                    "All retry hearts spent. Rest for "
                    f"{minutes:02d}:{seconds:02d} before your next attempt.",
                )
            save_profiles(self.store)

    def claim_daily_reward_gui(self) -> None:
        reward = claim_daily_reward(self.profile)
        if reward is None:
            messagebox.showinfo(
                "Daily Challenge",
                "No reward available to claim. Complete the daily challenge first.",
            )
            return
        bonus, badge = reward
        parts: list[str] = []
        if bonus:
            parts.append(f"{XP_EMOJI} Bonus XP awarded: +{bonus}!")
        if badge:
            parts.append(f"{BADGE_EMOJI} Special badge earned: {badge}!")
        if not parts:
            parts.append("Reward claimed! (No additional bonus configured today.)")
        else:
            parts.append("Reward claimed! Keep the streak going.")
        messagebox.showinfo("Daily Challenge", "\n".join(parts))
        save_profiles(self.store)
        self.ensure_daily_challenge()
        self.show_quest_map()

    def show_coming_soon(self) -> None:
        frame = ComingSoonFrame(
            self.container,
            heading="Quest Map",
            body="The interactive quest map is on the way!"
            " We are currently charting the lands for the GUI experience.",
            on_back=self.show_title_screen,
        )
        self.swap_content(frame)


class SlotSelectionFrame(ttk.Frame):
    def __init__(
        self,
        master: ttk.Frame,
        store: dict,
        on_select,
        on_reset,
    ) -> None:
        super().__init__(master)
        self.store = store
        self.on_select = on_select
        self.on_reset = on_reset

        header = ttk.Label(self, text="Choose Your Save Slot", style="Header.TLabel")
        header.pack(pady=(0, 16))

        subtitle = ttk.Label(
            self,
            text="Load an existing adventurer or reset a slot to embark on a new journey.",
            style="Body.TLabel",
        )
        subtitle.pack(pady=(0, 24))

        self.listbox = tk.Listbox(
            self,
            font=("Segoe UI", 14),
            height=6,
            activestyle="none",
            selectbackground="#f7d664",
            selectforeground="#14141d",
        )
        self.listbox.pack(fill="x", pady=(0, 16))
        self.populate_slots()

        button_row = ttk.Frame(self)
        button_row.pack(fill="x", pady=(8, 0))

        select_btn = ttk.Button(
            button_row,
            text="Start Adventure",
            style="Accent.TButton",
            command=self.handle_select,
        )
        select_btn.pack(side="left")

        reset_btn = ttk.Button(
            button_row,
            text="Reset Slot",
            command=self.handle_reset,
        )
        reset_btn.pack(side="left", padx=12)

        self.status = ttk.Label(self, text="", style="Body.TLabel")
        self.status.pack(pady=(18, 0))

        self.listbox.bind("<Double-Button-1>", lambda _evt: self.handle_select())

    def populate_slots(self) -> None:
        self.listbox.delete(0, tk.END)
        slots = list_slots(self.store)
        for index, slot_name in enumerate(slots, start=1):
            profile = self.store["slots"].get(slot_name)
            summary = summarise_slot(slot_name, profile)
            self.listbox.insert(tk.END, f"{index}. {summary}")
        if slots:
            self.listbox.selection_set(0)

    def selected_slot(self) -> str | None:
        selection = self.listbox.curselection()
        if not selection:
            self.status.configure(text="Please select a slot first.")
            return None
        index = selection[0]
        slot_name = list_slots(self.store)[index]
        return slot_name

    def handle_select(self) -> None:
        slot_name = self.selected_slot()
        if slot_name is None:
            return
        self.on_select(slot_name)

    def handle_reset(self) -> None:
        slot_name = self.selected_slot()
        if slot_name is None:
            return
        self.on_reset(slot_name)
        self.populate_slots()
        self.status.configure(text=f"{slot_name} reset. Ready for a fresh quest!")


class TitleScreenFrame(ttk.Frame):
    def __init__(self, master: ttk.Frame, profile: dict, on_start, on_switch) -> None:
        super().__init__(master)
        header = ttk.Label(self, text="MathQuest6", style="Header.TLabel")
        header.pack(pady=(0, 12))

        subtitle = ttk.Label(
            self,
            text="A gamified adventure through Standard 6 mathematics.",
            style="Body.TLabel",
        )
        subtitle.pack(pady=(0, 24))

        info_box = ttk.Frame(self, padding=20)
        info_box.configure(style="TFrame")
        info_box.pack(pady=(0, 32))

        name = profile.get("player_name") or "Hero"
        level = profile.get("level", 1)
        lands = len(profile.get("unlocked_lands", []))
        avatar = profile.get("avatar") or "Choose an avatar in console mode"

        info_lines = [
            f"Adventurer: {name}",
            f"Level: {level}",
            f"Unlocked Lands: {lands}",
            f"Avatar: {avatar}",
        ]
        for line in info_lines:
            ttk.Label(info_box, text=line, style="Body.TLabel").pack(anchor="w")

        action_row = ttk.Frame(self)
        action_row.pack(pady=(0, 12))

        start_btn = ttk.Button(
            action_row,
            text="Enter Quest Map",
            style="Accent.TButton",
            command=on_start,
        )
        start_btn.pack(side="left", padx=(0, 12))

        switch_btn = ttk.Button(
            action_row,
            text="Switch Save Slot",
            command=on_switch,
        )
        switch_btn.pack(side="left")


class ComingSoonFrame(ttk.Frame):
    def __init__(self, master: ttk.Frame, heading: str, body: str, on_back) -> None:
        super().__init__(master)
        title = ttk.Label(self, text=heading, style="Header.TLabel")
        title.pack(pady=(0, 16))

        message = ttk.Label(self, text=body, style="Body.TLabel")
        message.pack(pady=(0, 24))

        back_btn = ttk.Button(self, text="Back", command=on_back)
        back_btn.pack()


class QuestMapFrame(ttk.Frame):
    def __init__(
        self,
        master: ttk.Frame,
        profile: dict,
        on_open_land,
        on_back,
        on_open_daily,
        on_claim_daily,
        on_toggle_daily,
        show_daily: bool,
    ) -> None:
        super().__init__(master)
        header_row = ttk.Frame(self)
        header_row.pack(fill="x", pady=(0, 16))

        ttk.Label(header_row, text="Quest Map", style="Header.TLabel").pack(side="left")
        toggle_text = "Hide Daily Challenge" if show_daily else "Show Daily Challenge"
        ttk.Button(header_row, text=toggle_text, command=on_toggle_daily).pack(side="right")

        challenge = profile.get("daily_challenge") or {}
        stats = profile.get("daily_stats") or {}
        land = challenge.get("land")
        emoji = COLOR_PALETTES.get(land, {}).get("emoji", "⭐") if land else "⭐"
        status_parts = []
        if land:
            status_parts.append("Completed" if challenge.get("completed") else "Ready")
            status_parts.append("Reward claimed" if challenge.get("reward_claimed") else "Reward pending")
        else:
            status_parts.append("Not generated yet")
        status_text = ", ".join(status_parts)
        bonus = challenge.get("bonus_xp", DAILY_CHALLENGE_BONUS_XP)
        badge = challenge.get("badge_reward", DAILY_CHALLENGE_BADGE)
        streak_current = stats.get("streak_current", 0)
        streak_best = stats.get("streak_best", 0)
        hearts = get_retry_hearts(profile)
        cooldown_seconds = retry_cooldown_remaining(profile) if hearts <= 0 else 0
        if cooldown_seconds:
            minutes = cooldown_seconds // 60
            seconds = cooldown_seconds % 60
            cooldown_label = f"Cooldown {minutes:02d}:{seconds:02d}"
        else:
            cooldown_label = "Ready"

        if show_daily:
            daily_card = ttk.Frame(self, padding=18, style="Card.TFrame")
            daily_card.pack(fill="x", pady=(0, 24))
            ttk.Label(
                daily_card,
                text=f"{emoji} Daily Challenge",
                style="CardHeader.TLabel",
            ).pack(anchor="w")
            ttk.Label(
                daily_card,
                text=f"Challenge Land: {emoji} {land if land else 'TBD'}",
                style="CardBody.TLabel",
            ).pack(anchor="w", pady=(6, 0))
            ttk.Label(
                daily_card,
                text=f"Status: {status_text}",
                style="CardBody.TLabel",
            ).pack(anchor="w")
            ttk.Label(
                daily_card,
                text=f"{XP_EMOJI} Bonus XP: {bonus}  |  {BADGE_EMOJI} Badge: {badge}",
                style="CardBody.TLabel",
            ).pack(anchor="w", pady=(0, 2))
            ttk.Label(
                daily_card,
                text=f"Streak: {streak_current} (best {streak_best})",
                style="CardBody.TLabel",
            ).pack(anchor="w")
            ttk.Label(
                daily_card,
                text=f"{HP_EMOJI} Retry Hearts: {hearts}/{RETRY_MAX_HEARTS} — {cooldown_label}",
                style="CardBody.TLabel",
            ).pack(anchor="w", pady=(0, 12))

            button_row = ttk.Frame(daily_card)
            button_row.pack(fill="x")
            can_start = bool(land) and not challenge.get("completed") and hearts > 0
            claim_ready = challenge.get("completed") and not challenge.get("reward_claimed")
            ttk.Button(
                button_row,
                text="Start Daily Challenge",
                style="Accent.TButton",
                command=on_open_daily,
                state=tk.NORMAL if can_start else tk.DISABLED,
            ).pack(side="left")
            ttk.Button(
                button_row,
                text="Claim Reward",
                command=on_claim_daily,
                state=tk.NORMAL if claim_ready else tk.DISABLED,
            ).pack(side="left", padx=12)
        else:
            hidden_notice = ttk.Frame(self, padding=18, style="Card.TFrame")
            hidden_notice.pack(fill="x", pady=(0, 24))
            ttk.Label(
                hidden_notice,
                text="Daily challenge hidden — toggle to view status and rewards.",
                style="CardBody.TLabel",
            ).pack(anchor="w")

        instructions = ttk.Label(
            self,
            text="Select an unlocked land to enter its lesson. Each land becomes available"
            " after you complete the previous quest in story order.",
            style="Body.TLabel",
        )
        instructions.pack(pady=(0, 24))

        canvas = tk.Canvas(self, background="#1f1f2e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        scroll_frame_id = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        def configure_scroll_region(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def resize_frame(event):
            canvas.itemconfigure(scroll_frame_id, width=event.width)

        scroll_frame.bind("<Configure>", configure_scroll_region)
        canvas.bind("<Configure>", resize_frame)
        canvas.configure(yscrollcommand=scrollbar.set)

        mousewheel_bound = False

        def on_mousewheel(event: tk.Event) -> None:
            nonlocal mousewheel_bound
            if event.delta:
                steps = int(event.delta / 120)
                if steps == 0:
                    steps = 1 if event.delta > 0 else -1
                canvas.yview_scroll(-steps, "units")
            elif getattr(event, "num", None) in (4, 5):
                canvas.yview_scroll(-1 if event.num == 4 else 1, "units")

        def bind_mousewheel(_event: tk.Event) -> None:
            nonlocal mousewheel_bound
            if mousewheel_bound:
                return
            canvas.bind_all("<MouseWheel>", on_mousewheel)
            canvas.bind_all("<Button-4>", on_mousewheel)
            canvas.bind_all("<Button-5>", on_mousewheel)
            mousewheel_bound = True

        def unbind_mousewheel(_event: tk.Event) -> None:
            nonlocal mousewheel_bound
            if not mousewheel_bound:
                return
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")
            mousewheel_bound = False

        scroll_frame.bind("<Enter>", bind_mousewheel)
        scroll_frame.bind("<Leave>", unbind_mousewheel)
        scroll_frame.bind("<Destroy>", unbind_mousewheel)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        grid = ttk.Frame(scroll_frame)
        grid.pack(fill="both", expand=True)

        for col in range(3):
            grid.grid_columnconfigure(col, weight=1, uniform="col")

        unlocked_lands = set(profile.get("unlocked_lands", []))
        badges = set(profile.get("badges", []))

        for index, land in enumerate(LANDS):
            row = index // 3
            column = index % 3
            unlocked = land in unlocked_lands
            palette = COLOR_PALETTES.get(land, {})
            emoji = palette.get("emoji", "📘")
            badge_name = f"{land} Master"
            has_badge = badge_name in badges

            card = ttk.Frame(grid, padding=18, style="Card.TFrame")
            card.grid(row=row, column=column, padx=12, pady=12, sticky="nsew")

            title = ttk.Label(card, text=f"{emoji} {land}", style="CardHeader.TLabel")
            title.pack(anchor="w")

            status = "✅ Unlocked" if unlocked else "🔒 Locked"
            status_label = ttk.Label(card, text=status, style="CardBody.TLabel")
            status_label.pack(anchor="w", pady=(6, 4))

            badge_text = "Badge earned!" if has_badge else "Badge pending"
            ttk.Label(card, text=badge_text, style="Dim.TLabel").pack(anchor="w", pady=(0, 8))

            description = ttk.Label(
                card,
                text="Story lesson and battle currently playable in console mode."
                " GUI version coming soon!",
                style="CardBody.TLabel",
            )
            description.pack(anchor="w", pady=(0, 16))

            enter_btn = ttk.Button(
                card,
                text="Enter",
                style="Accent.TButton" if unlocked else "TButton",
                command=lambda l=land: on_open_land(l),
                state=tk.NORMAL if unlocked else tk.DISABLED,
            )
            enter_btn.pack(anchor="w")

        back_btn = ttk.Button(self, text="Back", command=on_back)
        back_btn.pack(pady=(24, 0))


class LessonFrame(ttk.Frame):
    def __init__(self, master: ttk.Frame, land: str, lesson: dict | None, on_back, on_start_battle) -> None:
        super().__init__(master)
        header = ttk.Label(self, text=f"{land} Lesson", style="Header.TLabel")
        header.pack(pady=(0, 16))

        if not lesson:
            ttk.Label(
                self,
                text="Lesson data not found. Please ensure lesson_data.json is available.",
                style="Body.TLabel",
            ).pack(pady=(0, 16))
        else:
            ttk.Label(self, text=lesson.get("story", ""), style="Body.TLabel").pack(pady=(0, 16), anchor="w")

            objectives_frame = ttk.Frame(self)
            objectives_frame.pack(fill="x", pady=(0, 16))
            ttk.Label(objectives_frame, text="Learning Objectives", style="CardHeader.TLabel").pack(anchor="w")
            for objective in lesson.get("learning_objectives", []):
                ttk.Label(
                    objectives_frame,
                    text=f"• {objective}",
                    style="Body.TLabel",
                    wraplength=780,
                ).pack(anchor="w")

            ttk.Label(
                self,
                text=f"Example Walkthrough:\n{lesson.get('example_walkthrough', '')}",
                style="Body.TLabel",
            ).pack(anchor="w")

        button_row = ttk.Frame(self)
        button_row.pack(pady=(24, 0))

        start_btn = ttk.Button(
            button_row,
            text="Preview Battle",
            style="Accent.TButton",
            command=on_start_battle,
        )
        start_btn.pack(side="left", padx=(0, 12))

        back_btn = ttk.Button(button_row, text="Back to Map", command=on_back)
        back_btn.pack(side="left")


class BattleFrame(ttk.Frame):
    HP_PER_BATTLE = 3

    def __init__(
        self,
        master: ttk.Frame,
        profile: dict,
        store: dict,
        land: str | None,
        questions: list,
        on_back,
        on_finish,
        heading: str | None = None,
        on_result=None,
        back_button_visible: bool = True,
    ) -> None:
        super().__init__(master)
        self.profile = profile
        self.store = store
        self.land = land
        self.questions = questions or []
        self.on_back = on_back
        self.on_finish = on_finish
        self.on_result = on_result
        self.result_reported = False
        self.back_button_visible = back_button_visible
        self.total_questions = len(self.questions)
        self.current_index = 0
        self.correct_answers = 0
        self.hp = self.HP_PER_BATTLE
        self.hint_used = False
        self.feedback_history: list[str] = []
        self.battle_over = False

        header_text = heading or (f"{land} Battle" if land else "Battle")
        ttk.Label(self, text=header_text, style="Header.TLabel").pack(pady=(0, 16))

        stats_frame = ttk.Frame(self)
        stats_frame.pack(fill="x", pady=(0, 16))

        self.progress_var = tk.StringVar()
        self.hearts_var = tk.StringVar()
        self.xp_var = tk.StringVar()
        self.hints_var = tk.StringVar()

        ttk.Label(stats_frame, textvariable=self.progress_var, style="Body.TLabel").pack(anchor="w")
        ttk.Label(stats_frame, textvariable=self.hearts_var, style="Body.TLabel").pack(anchor="w")
        ttk.Label(stats_frame, textvariable=self.xp_var, style="Body.TLabel").pack(anchor="w")
        ttk.Label(stats_frame, textvariable=self.hints_var, style="Body.TLabel").pack(anchor="w")

        self.creature_var = tk.StringVar()
        self.question_var = tk.StringVar()
        ttk.Label(self, textvariable=self.creature_var, style="CardHeader.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Label(self, textvariable=self.question_var, style="Body.TLabel").pack(anchor="w", pady=(0, 12))

        self.options_frame = ttk.Frame(self)
        self.options_frame.pack(fill="x")
        self.option_buttons: list[ttk.Button] = []

        control_row = ttk.Frame(self)
        control_row.pack(fill="x", pady=(16, 0))

        self.hint_button = ttk.Button(control_row, text=f"Use Hint {HINT_EMOJI}", command=self.handle_hint)
        self.hint_button.pack(side="left")

        self.next_button = ttk.Button(control_row, text="Next Challenge", command=self.handle_next, state=tk.DISABLED)
        self.next_button.pack(side="left", padx=(12, 0))

        if back_button_visible:
            ttk.Button(control_row, text="Back to Lesson", command=self.handle_back).pack(side="right")

        self.feedback_var = tk.StringVar()
        ttk.Label(self, textvariable=self.feedback_var, style="Dim.TLabel", wraplength=760).pack(anchor="w", pady=(18, 0))

        if not land:
            self.show_unavailable("Select a land to begin the battle.")
            return
        if not self.questions:
            self.show_unavailable("No questions available for this land yet. Add entries to quiz_data.json.")
            return

        self.render_question()

    def show_unavailable(self, message: str) -> None:
        self.progress_var.set("")
        self.hearts_var.set("")
        self.xp_var.set("")
        self.hints_var.set("")
        self.creature_var.set("")
        self.question_var.set(message)
        self.hint_button.configure(state=tk.DISABLED)
        self.next_button.configure(text="Return to Map", state=tk.NORMAL, command=self.finish_without_battle)

    def handle_back(self) -> None:
        if callable(self.on_back) and self.land:
            self.on_back(self.land)
        else:
            self.on_finish()

    def handle_hint(self) -> None:
        if self.battle_over:
            return
        if self.hint_used:
            self.feedback_var.set("Hint already used for this challenge.")
            return
        if spend_hint(self.profile, self.land):
            question = self.questions[self.current_index]
            hint_text = question.get("hint")
            if hint_text:
                self.feedback_var.set(f"{HINT_EMOJI} Hint: {hint_text}")
            else:
                self.feedback_var.set("No hint provided for this challenge.")
            self.hint_used = True
            self.update_stats()
        else:
            self.feedback_var.set("No hint tokens remaining for this land today.")

    def render_question(self) -> None:
        self.hint_used = False
        question = self.questions[self.current_index]
        self.progress_var.set(f"Challenge {self.current_index + 1} of {self.total_questions}")
        creature = question.get("creature")
        self.creature_var.set(f"{creature} appears!" if creature else "A challenge appears!")
        self.question_var.set(question.get("prompt", ""))
        self.feedback_var.set("")
        self.refresh_option_buttons(question)
        self.next_button.configure(state=tk.DISABLED)
        self.update_stats()

    def refresh_option_buttons(self, question: dict) -> None:
        for button in self.option_buttons:
            button.destroy()
        self.option_buttons.clear()
        options = question.get("options", {})
        for key in sorted(options.keys()):
            text = options[key]
            btn = ttk.Button(
                self.options_frame,
                text=f"{key.upper()}) {text}",
                command=lambda choice=key: self.handle_answer(choice),
                style="Accent.TButton",
            )
            btn.pack(fill="x", pady=4)
            self.option_buttons.append(btn)
        self.hint_button.configure(state=tk.NORMAL if self.profile.get("hint_tokens", {}).get(self.land, 0) > 0 else tk.DISABLED)

    def handle_answer(self, choice: str) -> None:
        if self.battle_over:
            return
        question = self.questions[self.current_index]
        correct_choice = question.get("answer")
        is_correct = choice == correct_choice
        explanation = question.get("explanation", "")
        xp_delta = XP_CORRECT if is_correct else XP_INCORRECT
        current_xp, leveled = apply_xp_change(self.profile, xp_delta)
        feedback_prefix = pick_feedback(is_correct, SUCCESS_EMOJIS, FAILURE_EMOJIS)
        messages = [f"{feedback_prefix} {'Correct!' if is_correct else 'Not quite.'}" ]
        if explanation:
            messages.append(explanation)
        if xp_delta:
            sign = '+' if xp_delta > 0 else ''
            messages.append(f"{XP_EMOJI} {sign}{xp_delta} XP (XP: {current_xp}/{XP_LEVEL_THRESHOLD})")
        if leveled:
            messages.append(f"{LEVEL_EMOJI} Level up! You reached level {self.profile['level']}!")

        if is_correct:
            self.correct_answers += 1
        else:
            self.hp -= 1
            messages.append(f"{HP_EMOJI} Remaining hearts: {self.hp}")
            if self.hp <= 0:
                messages.append("Your hearts are depleted! The battle ends here.")

        self.feedback_var.set("\n".join(messages))
        self.update_stats()
        self.disable_options()
        self.next_button.configure(state=tk.NORMAL)
        self.hint_button.configure(state=tk.DISABLED)

    def disable_options(self) -> None:
        for button in self.option_buttons:
            button.configure(state=tk.DISABLED)

    def handle_next(self) -> None:
        if self.battle_over:
            self.finish_and_return()
            return
        if self.hp <= 0 or self.current_index + 1 >= self.total_questions:
            self.finish_battle()
            return
        self.current_index += 1
        self.render_question()

    def finish_battle(self) -> None:
        accuracy, mood = summarize_results(self.correct_answers, self.total_questions)
        badge_awarded = award_badge(self.profile, self.land, accuracy)
        next_land = None
        if accuracy >= 0.6 and self.hp > 0:
            next_land = unlock_next_land(self.profile, LANDS, self.land)
        save_profiles(self.store)

        summary_lines = [
            f"Accuracy: {accuracy * 100:.0f}% — {mood}",
        ]
        if badge_awarded:
            summary_lines.append(f"{BADGE_EMOJI} New Badge Earned: {badge_awarded}!")
        if next_land:
            summary_lines.append(f"You unlocked {next_land}! 🎉")
        if self.hp <= 0:
            summary_lines.append("Regroup and try again when you're ready.")

        for child in self.options_frame.winfo_children():
            child.destroy()
        self.option_buttons.clear()
        self.question_var.set(f"Total Correct: {self.correct_answers}/{self.total_questions}")
        self.creature_var.set("")
        self.feedback_var.set("\n".join(summary_lines))
        self.progress_var.set("")
        self.hint_button.configure(state=tk.DISABLED)
        self.next_button.configure(text="Return to Map", state=tk.NORMAL)
        self.report_result(self.hp > 0)
        self.battle_over = True

    def finish_without_battle(self) -> None:
        self.report_result(False)
        self.handle_finish()

    def finish_and_return(self) -> None:
        if not self.result_reported:
            self.report_result(self.hp > 0)
        self.handle_finish()

    def report_result(self, success: bool) -> None:
        if callable(self.on_result) and not self.result_reported:
            self.result_reported = True
            self.on_result(success)

    def handle_finish(self) -> None:
        save_profiles(self.store)
        self.on_finish()

    def update_stats(self) -> None:
        self.hearts_var.set(f"{HP_EMOJI} Hearts: {self.hp}/{self.HP_PER_BATTLE}")
        xp = self.profile.get("xp", 0)
        level = self.profile.get("level", 1)
        self.xp_var.set(f"{XP_EMOJI} XP: {xp}/{XP_LEVEL_THRESHOLD} — Level {level}")
        hints = self.profile.get("hint_tokens", {}).get(self.land, 0)
        self.hints_var.set(f"{HINT_EMOJI} Hints: {hints}")



def summarise_slot(slot_name: str, profile: dict | None) -> str:
    if profile is None:
        return f"{slot_name} — Empty"
    name = profile.get("player_name") or "Hero"
    level = profile.get("level", 1)
    lands = len(profile.get("unlocked_lands", []))
    return f"{slot_name} — {name} (Lv {level}, {lands} lands)"
