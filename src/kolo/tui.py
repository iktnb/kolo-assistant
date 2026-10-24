from __future__ import annotations

import asyncio
import os
import unicodedata
from collections.abc import Callable, Coroutine, Sequence
from datetime import date
from pathlib import Path
from typing import cast

from rich.cells import cell_len
from rich.segment import Segment
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.color import Color
from textual.filter import LineFilter, NoColor
from textual.screen import Screen
from textual.theme import Theme
from textual.widgets import Footer, Static

from kolo.render import safe
from kolo.services import Assistant


class LiteralControls(LineFilter):
    def apply(self, segments: list[Segment], background: Color) -> list[Segment]:
        def display(character: str) -> str:
            if unicodedata.category(character) not in {"Cc", "Cf"}:
                return character
            return "�" * cell_len(character)

        return [
            Segment("".join(map(display, segment.text)), segment.style, segment.control)
            if segment.control is None
            else segment
            for segment in segments
        ]


class AssistantIO:
    def __init__(self, factory: Callable[[], Assistant]) -> None:
        self.factory = factory
        self.assistant: Assistant | None = None
        self.lock = asyncio.Lock()

    def _call[Value](self, operation: Callable[[Assistant], Value]) -> Value:
        if self.assistant is None:
            self.assistant = self.factory()
        return operation(self.assistant)

    async def call[Value](self, operation: Callable[[Assistant], Value]) -> Value:
        async with self.lock:
            return await asyncio.to_thread(self._call, operation)


class KoloScreen(Screen[None]):
    BINDINGS = [Binding("escape", "back", "Назад")]
    refresh_on_return = False

    @property
    def kolo(self) -> KoloApp:
        return cast(KoloApp, self.app)

    def chrome(self, title: str) -> ComposeResult:
        yield Static(safe(f"КОЛО  /  {title}"), id="brand")
        if self.kolo.demo:
            yield Static(safe(f"ДЕМОНСТРАЦІЯ · {self.kolo.path.parent}"), id="demo-banner")

    def status(self, message: str, *, error: bool = False) -> None:
        widget = self.query_one("#status", Static)
        widget.update(safe(message, multiline=True))
        widget.set_class(error, "error")

    def owns_view(self) -> bool:
        visible = self.is_mounted and self.kolo.screen is self
        if self.is_mounted and not visible:
            self.refresh_on_return = True
        return visible

    def action_back(self) -> None:
        self.kolo.request_back()

    def leave(self) -> None:
        self.app.pop_screen()

    def footer(self) -> Footer:
        return Footer()


class KoloApp(App[int]):
    CSS_PATH = "tui.tcss"
    TITLE = "Коло"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        Binding("ctrl+q", "safe_quit", "Вийти", priority=True),
        Binding("ctrl+c", "safe_quit", "Вийти", show=False, priority=True),
        Binding("f1", "help", "Довідка"),
    ]

    def __init__(
        self, factory: Callable[[], Assistant], path: Path, *, plain: bool = False, demo: bool = False
    ) -> None:
        super().__init__()
        self.register_theme(
            Theme(
                name="kolo",
                primary="#52c7b8",
                secondary="#9db0be",
                accent="#52c7b8",
                background="#101a23",
                surface="#172631",
                foreground="#ecf3f4",
                error="#ff9f9f",
            )
        )
        self.theme = "kolo"
        self.io = AssistantIO(factory)
        self.path = path.absolute()
        self.plain = plain or "NO_COLOR" in os.environ
        self.demo = demo
        self.pending = 0
        self.writing = 0
        self.deferred: Callable[[], None] | None = None
        self.last_day: date | None = None

    def get_line_filters(self) -> Sequence[LineFilter]:
        filters = [*super().get_line_filters(), LiteralControls()]
        return [*filters, NoColor()] if self.plain else filters

    def on_mount(self) -> None:
        from kolo.tui_screens import HomeScreen

        self.push_screen(HomeScreen())
        self.set_interval(60, self.check_date)

    def launch(self, operation: Coroutine[None, None, None], *, write: bool = False) -> None:
        self.pending += 1
        self.writing += int(write)

        async def finish() -> None:
            try:
                await operation
            finally:
                self.pending -= 1
                self.writing -= int(write)
                if not self.pending and self.deferred is not None:
                    callback, self.deferred = self.deferred, None
                    self.call_after_refresh(callback)

        self.run_worker(finish(), exit_on_error=False)

    def request_back(self) -> None:
        if self.writing:
            self.deferred = self.request_back
        elif isinstance(self.screen, KoloScreen):
            self.screen.leave()

    def action_safe_quit(self) -> None:
        from kolo.tui_forms import ConfirmScreen, FormScreen

        if self.writing:
            self.deferred = self.action_safe_quit
            return
        if isinstance(self.screen, ConfirmScreen):
            return
        dirty = isinstance(self.screen, FormScreen) and self.screen.dirty
        title = "Відкинути чернетку й вийти?" if dirty else "Вийти з Кола?"
        keep = "Продовжити редагування" if dirty else "Залишитися"
        self.push_screen(ConfirmScreen(title, keep, "Відкинути й вийти" if dirty else "Вийти"), self._quit_answer)

    def _quit_answer(self, confirmed: bool | None) -> None:
        if confirmed:
            self.finish_exit()

    def finish_exit(self) -> None:
        if self.pending:
            self.deferred = self.finish_exit
        else:
            self.exit(0)

    def action_help(self) -> None:
        from kolo.tui_forms import FormScreen
        from kolo.tui_screens import HelpScreen

        if not self.writing and not isinstance(self.screen, FormScreen):
            self.push_screen(HelpScreen())

    async def check_date(self) -> None:
        from kolo.tui_screens import HomeScreen, RecordsScreen

        if self.io.assistant is None or self.writing:
            return
        today = self.io.assistant.today()
        if today != self.last_day:
            self.last_day = today
            if isinstance(self.screen, HomeScreen | RecordsScreen):
                if isinstance(self.screen, HomeScreen) or self.screen.kind == "birthdays":
                    self.screen.refresh_data()


def run_tui(factory: Callable[[], Assistant], path: Path, *, plain: bool = False, demo: bool = False) -> int:
    app = KoloApp(factory, path, plain=plain, demo=demo)
    result = app.run()
    return app.return_code if app.return_code else result if result is not None else 0
