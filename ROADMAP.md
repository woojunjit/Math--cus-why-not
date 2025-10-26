# MathQuest6 Roadmap

## Phase 2: GUI Migration (Tkinter Prototype)

- **Goal**: Deliver a window-based experience that preserves current game mechanics while improving accessibility and visual appeal.
- **Milestones**:
  1. **Wireframe screens**: Title, slot select, map, lesson, battle, results.
  2. **Set up Tkinter app shell** *(completed)*: Main window, navigation controller, shared styles.
  3. **Render quest map** *(completed)*: Replace ASCII map with grid of buttons/cards showing land status.
  4. **Lesson view** *(completed)*: Scrollable text pane with imagery/emoji, next button.
  5. **Battle view**: Multiple choice buttons, hint dialog, animated XP progress.
  6. **Results modal**: Show accuracy, XP bar, badges earned with iconography.
  7. **Persistence bridge**: Reuse JSON save system with background autosave.
  8. **Polish**: Sound cues, animations, color palette alignment with console version.

- **Dependencies**: Tkinter (stdlib), Pillow (optional for image assets), consistent asset naming in `lesson_data.json` and `quiz_data.json`.
- **Risks/Mitigations**:
  - **State management complexity** → introduce controller class managing scenes.
  - **Layout scaling** → use grid/pack with weight configuration and minimum window sizes.
  - **Accessibility** → include keyboard shortcuts, large-font option.

### Phase 2 Progress Snapshot (2025-10-20)

- **Completed**: Slot selection, title screen, quest map cards, lesson detail view, battle preview placeholder, console data loading.
- **Next**: Build interactive battle UI (answer buttons, hint usage, XP bars), results summary modal, Rich styling parity, integrate actual XP/badge updates.
- **Stretch**: Animated transitions between scenes, background music toggle, avatar selection inside GUI.

## Phase 2.5: Daily Challenge System (Console + GUI)

- **Goal**: Introduce rotating daily tasks to encourage repeat play and mastery.
- **Feature Outline**:
  - **Challenge generator**: Picks land/topic and randomizes question set at launch.
  - **Unique rewards**: Daily badge or bonus XP tracked separately in profile.
  - **Cooldown tracking**: Store last completion timestamp per slot to prevent repeats.
  - **Leaderboard-ready data**: Log best streak, fastest completion time placeholders.

- **Implementation Steps**:
  1. Extend `player_data.json` schema: `daily_challenge` object with timestamp, completion flag, reward status.
  2. Add challenge summary to home map (console banner or GUI panel).
  3. Reuse quiz pipeline with challenge flag to adjust XP multiplier.
  4. Reset logic: On app start, refresh challenge if last completion < current day.
  5. Optional: Export challenge results to CSV/JSON for classroom reporting.

- **Dependencies**: `datetime` utilities, potential `pytz` for timezone handling.
- **Risks/Mitigations**:
  - **Time zone inconsistencies** → store UTC dates, convert on display.
  - **Content exhaustion** → build challenge question pools per land with difficulty tiers.

## Phase 3: Future Enhancements (Initiated 2025-10-25)

- **Leaderboards**
  - Implement local `leaderboard_data.json` with top XP, streaks, and completion times.
  - Surface leaderboard in console and GUI (`gui_app/leaderboard_panel.py`) with paging support.
  - Plan hooks for optional cloud sync (Phase 3.2).
- **Narration**
  - Integrate `pyttsx3` wrapper in `audio/narration.py` with configurable voice and rate.
  - Add narration toggles to console settings and GUI title screen.
- **Mini-games**
  - Prototype reflex mini-game in `mini_games/reflex_math.py` reusable in console/GUI.
  - Log mini-game scores to leaderboard for variety metrics.
- **Mobile-ready layout**
  - Begin feasibility spike comparing Tkinter tweaks vs `kivy` starter branch.
  - Document layout constraints and control schemes for touch devices.

---
_Last updated: 2025-10-20_
