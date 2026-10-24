from collections.abc import Callable
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from kolo.interactive import run_interactive
from kolo.render import Renderer, safe
from kolo.services import Assistant
from kolo.storage import Store


def seed(assistant: Assistant, today: date) -> None:
    assistant.add_contact(
        "Олена Квіткова",
        ("+380671234501",),
        "Львів, вулиця Сонячна, 12",
        "olena@example.com",
        today.replace(year=min(2000, today.year)),
    )
    assistant.add_contact("Марко Добрянський", ("+380931234502",), "Київ, вулиця Садова, 8", "marko@example.com")
    assistant.add_contact(
        "Софія Вербова", ("+380501234503",), email="sofiia@example.com", birthday=min(date(1998, 12, 31), today)
    )
    assistant.add_note(
        "Вихідні біля озера", "Взяти термос і книжку.\nПокликати друзів на прогулянку.", ("Відпочинок", "Друзі")
    )
    assistant.add_note("Ідея маленького проєкту", "Зібрати улюблені рецепти родини в один зошит.", ("Ідеї", "Дім"))


def run_demo(render: Renderer, today: Callable[[], date], *, line_mode: bool = False, plain: bool = False) -> int:
    snapshot = today()
    with TemporaryDirectory(prefix="kolo-demo-") as directory:

        def factory() -> Assistant:
            assistant = Assistant(Store(Path(directory), snapshot), today)
            seed(assistant, snapshot)
            return assistant

        if not line_mode:
            from kolo.tui import run_tui

            return run_tui(factory, Path(directory) / "kolo.sqlite3", plain=plain, demo=True)
        assistant = factory()
        render.heading(
            "Демонстрація",
            f"Тимчасові вигадані дані · {safe(directory).plain}\n"
            "Усі зміни лише тут; наступний запуск починається заново.",
            multiline=True,
        )
        return run_interactive(assistant, render)
