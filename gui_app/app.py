import tkinter as tk
from tkinter import ttk

from art_assets import COLOR_PALETTES
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
        self.show_slot_selection()

    def run(self) -> None:
        self.mainloop()

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
        frame = QuestMapFrame(
            self.container,
            profile=self.profile,
            on_open_land=self.open_lesson,
            on_back=self.show_title_screen,
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
            on_start_battle=self.show_battle_placeholder,
        )
        self.swap_content(frame)

    def show_battle_placeholder(self) -> None:
        land = self.selected_land
        questions = self.quiz_bank.get(land, []) if land else []
        frame = BattlePlaceholderFrame(
            self.container,
            land=land,
            questions=questions,
            on_back=self.open_lesson if land else self.show_quest_map,
            on_finish=self.show_quest_map,
        )
        self.swap_content(frame)

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
    def __init__(self, master: ttk.Frame, profile: dict, on_open_land, on_back) -> None:
        super().__init__(master)
        header = ttk.Label(self, text="Quest Map", style="Header.TLabel")
        header.pack(pady=(0, 16))

        instructions = ttk.Label(
            self,
            text="Select an unlocked land to enter its lesson. Each land becomes available"
            " after you complete the previous quest in story order.",
            style="Body.TLabel",
        )
        instructions.pack(pady=(0, 24))

        grid = ttk.Frame(self)
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


class BattlePlaceholderFrame(ttk.Frame):
    def __init__(self, master: ttk.Frame, land: str | None, questions: list, on_back, on_finish) -> None:
        super().__init__(master)
        header_text = f"{land} Battle Preview" if land else "Battle Preview"
        header = ttk.Label(self, text=header_text, style="Header.TLabel")
        header.pack(pady=(0, 16))

        ttk.Label(
            self,
            text="Interactive battle UI is coming soon. Here's a sneak peek at a challenge!",
            style="Body.TLabel",
        ).pack(pady=(0, 16))

        if questions:
            question = questions[0]
            prompt = question.get("prompt", "")
            ttk.Label(self, text=prompt, style="Body.TLabel").pack(anchor="w", pady=(0, 12))
            options = question.get("options", {})
            for key, value in options.items():
                ttk.Label(self, text=f"{key}) {value}", style="Body.TLabel").pack(anchor="w")
            answer = question.get("answer")
            explanation = question.get("explanation", "")
            ttk.Label(
                self,
                text=f"Correct answer: {answer}\n{explanation}",
                style="Dim.TLabel",
            ).pack(anchor="w", pady=(12, 0))
        else:
            ttk.Label(
                self,
                text="No questions available for this land yet. Add entries to quiz_data.json.",
                style="Body.TLabel",
            ).pack()

        button_row = ttk.Frame(self)
        button_row.pack(pady=(24, 0))

        back_btn = ttk.Button(button_row, text="Back to Lesson", command=lambda: on_back(land) if callable(on_back) else on_finish())
        back_btn.pack(side="left", padx=(0, 12))

        finish_btn = ttk.Button(button_row, text="Return to Map", command=on_finish)
        finish_btn.pack(side="left")


def summarise_slot(slot_name: str, profile: dict | None) -> str:
    if profile is None:
        return f"{slot_name} — Empty"
    name = profile.get("player_name") or "Hero"
    level = profile.get("level", 1)
    lands = len(profile.get("unlocked_lands", []))
    return f"{slot_name} — {name} (Lv {level}, {lands} lands)"
