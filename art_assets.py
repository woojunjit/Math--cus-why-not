try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
except ImportError:  # pragma: no cover - optional dependency
    Console = None
    Panel = None
    Table = None
    Text = None


RICH_ENABLED = Console is not None
console = Console() if RICH_ENABLED else None

COLOR_PALETTES = {
    "Fractions Forest": {
        "primary": "green",
        "accent": "yellow",
        "emoji": "🌲"
    },
    "Decimal Desert": {
        "primary": "tan",
        "accent": "cyan",
        "emoji": "🏜️"
    },
    "Geometry Galaxy": {
        "primary": "magenta",
        "accent": "blue",
        "emoji": "🌌"
    },
    "Measurement Mountain": {
        "primary": "white",
        "accent": "purple",
        "emoji": "🏔️"
    },
    "Word Problem World": {
        "primary": "orange",
        "accent": "teal",
        "emoji": "📜"
    }
}

LAND_STATUS_STYLES = {
    True: "bold bright_green",
    False: "grey54"
}

TITLE_BANNER = r"""
 __  __       _   _   ____                  _   ____             _   
|  \/  | __ _| |_| |_|  _ \ _   _ _ __ _ __| |_|  _ \  ___   ___| |_ 
| |\/| |/ _` | __| __| |_) | | | | '__| '__| __| | | |/ _ \ / __| __|
| |  | | (_| | |_| |_|  __/| |_| | |  | |  | |_| |_| | (_) | (__| |_ 
|_|  |_|\__,_|\__|\__|_|    \__,_|_|  |_|   \__|____/ \___/ \___|\__|
"""

MAP_TEMPLATE = r"""
                🗺️  MathQuest6: Adventure Awaits!  🗺️
================================================================
{lands}
================================================================
"""

LAND_LINE_TEMPLATE = "{status} {emoji} {name}"

BATTLE_HEADER = r"""
╔══════════════════════════════════════════════════════════════╗
║                        Quiz Battle!                          ║
╚══════════════════════════════════════════════════════════════╝
"""

LESSON_HEADER = r"""
╔════════════════════════════════════╗
║            Story Lesson            ║
╚════════════════════════════════════╝
"""

RESULTS_HEADER = r"""
╔════════════════════════════════════╗
║           Quest Results            ║
╚════════════════════════════════════╝
"""

SUCCESS_EMOJIS = ["🎉", "✅", "👏", "🔥"]
FAILURE_EMOJIS = ["❌", "😵", "🔁", "🧊"]
HINT_EMOJI = "💡"
XP_EMOJI = "✨"
LEVEL_EMOJI = "🆙"
BADGE_EMOJI = "🏅"
HP_EMOJI = "❤️"

PROGRESS_BAR_TEMPLATE = "[{filled}{empty}] {percentage}%"

AVATAR_OPTIONS = [
    "🧙 Wizard of Numbers",
    "🧝 Forest Fractioneer",
    "🛰️ Geometry Navigator",
    "🏇 Measurement Scout",
    "🧚 Word Problem Whisperer"
]


def fancy_print(text="", style=None, justify="left"):
    if RICH_ENABLED:
        console.print(text, style=style, justify=justify)
    else:
        print(text)


def render_title_banner():
    if RICH_ENABLED and Text:
        fancy_print(Text(TITLE_BANNER, style="bold deep_sky_blue1"), justify="center")
    else:
        print(TITLE_BANNER)


def render_battle_header():
    if RICH_ENABLED and Panel:
        console.print(Panel.fit("Quiz Battle!", border_style="magenta", style="bold white"))
    else:
        print(BATTLE_HEADER)


def render_lesson_header():
    if RICH_ENABLED and Panel:
        console.print(Panel.fit("Story Lesson", border_style="cyan", style="bold"))
    else:
        print(LESSON_HEADER)


def render_results_header():
    if RICH_ENABLED and Panel:
        console.print(Panel.fit("Quest Results", border_style="gold1", style="bold"))
    else:
        print(RESULTS_HEADER)


def format_land_line(status, emoji, name, unlocked):
    text = LAND_LINE_TEMPLATE.format(status=status, emoji=emoji, name=name)
    if RICH_ENABLED:
        style = LAND_STATUS_STYLES[unlocked]
        return f"[{style}]{text}[/{style}]"
    return text


def render_map_panel(lines):
    body = "\n".join(lines)
    if RICH_ENABLED and Panel:
        console.print(Panel(body, title="Quest Map", border_style="yellow", expand=False))
    else:
        print(MAP_TEMPLATE.format(lands=body))


def render_results_table(rows):
    if RICH_ENABLED and Table:
        table = Table(show_header=False, box=None, pad_edge=False)
        for label, value, style in rows:
            table.add_row(f"[bold]{label}[/bold]", f"[{style}]{value}[/{style}]")
        console.print(table)
    else:
        for label, value, _ in rows:
            print(f"{label}: {value}")
