from __future__ import annotations

import asyncio
import hashlib
import sqlite3
import threading
from datetime import date
from pathlib import Path

import pytest
from test_tui import activate, app_for, replace, run, settle, text
from textual.widgets import Button, Footer, Input, ListView, Static, TextArea

from kolo.models import Contact
from kolo.services import Assistant
from kolo.storage import Store
from kolo.tui import KoloApp
from kolo.tui_forms import ConfirmScreen, FormScreen, ReadErrorScreen
from kolo.tui_screens import DetailScreen, HomeScreen, RecordsScreen


def test_note_create_native_enter_limits_filter_out_and_clear_tags(assistant: Assistant) -> None:
    app = app_for(assistant)

    async def journey() -> None:
        async with app.run_test() as pilot:
            await settle(pilot)
            await pilot.press("down", "enter")
            await settle(pilot)
            await pilot.press("f2", *"Нова")
            await replace(pilot, "body", "Україна")
            await pilot.press("enter", *"Другий")
            await replace(pilot, "tags", "Робота\nДім")
            await activate(pilot, "save")
            note = assistant.notes()[0]
            assert note.body == "Україна\nДругий" and note.tags == ("дім", "робота")
            await replace(pilot, "query", "Нова")
            await activate(pilot, "apply")
            await pilot.press("enter")
            await settle(pilot)
            await pilot.press("enter")
            await replace(pilot, "title", "Інша")
            await replace(pilot, "tags", "X" * 41)
            await pilot.press("ctrl+s")
            await settle(pilot)
            assert isinstance(app.screen, FormScreen) and "Теги" in text(app.screen)
            assert assistant.note(note.id).title == "Нова"
            await replace(pilot, "tags", "")
            await replace(pilot, "body", "я" * 10000)
            await pilot.press("ctrl+s")
            await settle(pilot)
            assert isinstance(app.screen, RecordsScreen)
            assert "не відповідає" in text(app.screen) and app.screen.rows == []
            assert app.screen.query_one("#query", Input).value == "Нова"
            changed = assistant.note(note.id)
            assert changed.title == "Інша" and changed.tags == () and changed.body == "я" * 10000
            await activate(pilot, "clear")
            await pilot.press("enter")
            await settle(pilot)
            assert isinstance(app.screen, DetailScreen) and "я" * 10000 in text(app.screen, "#details")
            await activate(pilot, "delete")
            await pilot.press("tab", "enter")
            await settle(pilot)
            assert assistant.notes() == []

    run(journey)


@pytest.mark.parametrize("key", ["-1", "367", "1.5", "x"])
def test_birthdays_invalid_previous_and_clock_refresh(assistant: Assistant, key: str) -> None:
    days = [date(2026, 12, 30)]
    assistant.today = lambda: days[0]
    january = assistant.add_contact("Січень", birthday="2000-01-02")
    assistant.add_contact("Високосний", birthday="2000-02-29")
    app = app_for(assistant)

    async def journey() -> None:
        async with app.run_test() as pilot:
            await settle(pilot)
            await pilot.press("down", "down", "enter")
            await settle(pilot)
            assert isinstance(app.screen, RecordsScreen) and [row.id for row in app.screen.rows] == [january.id]
            origin = app.screen
            await replace(pilot, "days", "0")
            await activate(pilot, "apply")
            assert origin.rows == [] and origin.applied_days == 0
            await replace(pilot, "days", key)
            await activate(pilot, "apply")
            assert origin.query_one("#days", Input).value == key and "Попередній інтервал 0 днів" in text(origin)
            await replace(pilot, "days", "366")
            await activate(pilot, "apply")
            assert origin.applied_days == 366 and len(origin.rows) == 2
            await pilot.press("enter")
            await settle(pilot)
            assert isinstance(app.screen, DetailScreen)
            await pilot.press("escape")
            await settle(pilot)
            assert app.screen is origin and origin.query_one("#days", Input).value == "366"
            days[0] = date(2027, 1, 1)
            await app.check_date()
            await settle(pilot)
            assert "через 1 дн." in str(origin.query_one("#records", ListView).children[0].children[1].content)

    run(journey)


def test_initial_corrupt_database_retry_back_quit(tmp_path: Path) -> None:
    directory = tmp_path / "corrupt"
    directory.mkdir()
    database = directory / "kolo.sqlite3"
    database.write_bytes(b"broken")
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    app = KoloApp(lambda: Assistant(Store(directory, date(2026, 10, 24)), lambda: date(2026, 10, 24)), database)

    async def journey() -> None:
        async with app.run_test() as pilot:
            await settle(pilot)
            assert isinstance(app.screen, ReadErrorScreen)
            assert str(database) in str(app.screen.query_one("#read-error", Static).content)
            await pilot.press("enter")
            await settle(pilot)
            assert isinstance(app.screen, ReadErrorScreen)
            await pilot.press("escape")
            await settle(pilot)
            assert isinstance(app.screen, HomeScreen) and "Не оновлено" in text(app.screen, "#summary")
            await activate(pilot, "retry")
            assert isinstance(app.screen, ReadErrorScreen)
            await activate(pilot, "quit")
            assert isinstance(app.screen, ConfirmScreen)
            await pilot.press("tab", "enter")
            assert app.return_value == 0
        assert hashlib.sha256(database.read_bytes()).hexdigest() == before

    run(journey)


def test_real_commit_failure_preserves_draft_then_explicit_retry(
    assistant: Assistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = Store._connect
    failing = [True]
    commits: list[str] = []

    class FailedCommit(sqlite3.Connection):
        def commit(self) -> None:
            commits.append("attempt")
            if failing[0]:
                raise sqlite3.OperationalError("private fault")
            super().commit()

    def connect(store: Store, mode: str) -> sqlite3.Connection:
        if mode == "rw":
            connection = sqlite3.connect(store.path, factory=FailedCommit, isolation_level=None)
            connection.execute("PRAGMA foreign_keys=ON")
            return connection
        return original(store, mode)

    monkeypatch.setattr(Store, "_connect", connect)
    before = hashlib.sha256(assistant.store.path.read_bytes()).hexdigest()
    app = app_for(assistant)

    async def journey() -> None:
        async with app.run_test() as pilot:
            await settle(pilot)
            await pilot.press("down", "enter")
            await settle(pilot)
            await pilot.press("f2", *"Чернетка")
            await replace(pilot, "body", "\nТекст\n")
            await pilot.press("ctrl+s")
            await settle(pilot)
            assert isinstance(app.screen, FormScreen)
            form = app.screen
            assert "Сховище" in text(form) and "Збережено" not in text(form) and "private fault" not in text(form)
            assert form.query_one("#body", TextArea).text == "\nТекст\n" and app.focused is form.query_one("#save")
            assert hashlib.sha256(assistant.store.path.read_bytes()).hexdigest() == before and assistant.notes() == []
            failing[0] = False
            await pilot.press("ctrl+s")
            await settle(pilot)
            assert commits == ["attempt", "attempt"] and len(assistant.notes()) == 1
            assert assistant.notes()[0].body == "\nТекст\n"

    run(journey)


def test_pending_write_responsive_single_commit_deferred_exit(
    assistant: Assistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    started, release = threading.Event(), threading.Event()
    original = Assistant.add_contact
    calls: list[str] = []

    def blocked(
        service: Assistant,
        name: str,
        phones: tuple[str, ...] = (),
        address: str | None = None,
        email: str | None = None,
        birthday: str | date | None = None,
    ) -> Contact:
        calls.append(name)
        started.set()
        assert release.wait(5)
        return original(service, name, phones, address, email, birthday)

    monkeypatch.setattr(Assistant, "add_contact", blocked)
    app = app_for(assistant)

    async def journey() -> None:
        async with app.run_test() as pilot:
            await settle(pilot)
            await pilot.press("enter")
            await settle(pilot)
            await pilot.press("f2", *"Один", "ctrl+s")
            await pilot.pause(0.05)
            assert started.is_set() and app.writing == 1
            assert isinstance(app.screen, FormScreen) and app.screen.query_one("#save", Button).disabled
            await pilot.press("ctrl+s", "ctrl+q")
            await pilot.resize_terminal(60, 20)
            assert app.size.width == 60 and app.return_value is None and calls == ["Один"]
            release.set()
            await settle(pilot)
            assert isinstance(app.screen, ConfirmScreen)
            assert app.is_running and app.return_value is None and app.pending == 0 and app.writing == 0
            quit_keys = asyncio.create_task(pilot.press("tab", "enter"))
            try:

                async def stopped() -> None:
                    while app.is_running:
                        await asyncio.sleep(0.01)

                await asyncio.wait_for(stopped(), timeout=10)
                assert app.return_value == 0 and app.return_code == 0
                assert not app.is_running and app.pending == 0 and app.writing == 0 and not list(app.workers)
                assert len(assistant.contacts()) == 1
            finally:
                if not quit_keys.done():
                    quit_keys.cancel()
                try:
                    await quit_keys
                except asyncio.CancelledError:
                    pass

    try:
        run(journey)
    finally:
        release.set()


@pytest.mark.parametrize("size", [(120, 36), (80, 24), (60, 20)])
def test_layout_keyboard_reach_resize_and_literal_data(assistant: Assistant, size: tuple[int, int]) -> None:
    title = "[bold] Українська довга назва " * 3
    raw = "\x1b]0;unsafe\x07\u202e\n" + "я" * 9900
    note = assistant.add_note(title, raw, ("тег",))
    app = app_for(assistant, plain=True)

    async def journey() -> None:
        async with app.run_test(size=size) as pilot:
            await settle(pilot)
            await pilot.press("down", "enter")
            await settle(pilot)
            origin = app.screen
            assert isinstance(origin, RecordsScreen)
            row = origin.query_one("#records", ListView).children[0]
            assert row.region.intersection(origin.query_one("#content").region).height >= 3
            await pilot.press("enter")
            await settle(pilot)
            assert isinstance(app.screen, DetailScreen)
            detail = app.screen
            assert (
                "[bold]" in text(detail, "#details")
                and "\\x1b" in text(detail, "#details")
                and "\\u202e" in text(detail, "#details")
            )
            edit = detail.query_one("#edit", Button)
            assert edit.region.intersection(detail.query_one("#detail-actions").region).height == 3
            assert edit.region.intersection(detail.region).height == 3
            assert edit.region.bottom <= detail.query_one(Footer).region.y
            assert edit.region.y >= detail.query_one("#brand").region.bottom
            await pilot.press("enter")
            assert isinstance(app.screen, FormScreen)
            form = app.screen
            await replace(pilot, "title", "Змінена")
            await pilot.resize_terminal(60, 20)
            await pilot.resize_terminal(80, 24)
            assert form.query_one("#title", Input).value == "Змінена" and form.query_one("#body", TextArea).text == raw
            for _ in range(20):
                if app.focused is form.query_one("#save", Button):
                    break
                await pilot.press("tab")
            save = form.query_one("#save", Button)
            await pilot.pause()
            assert app.focused is save and save.region.intersection(form.query_one("#content").region).height == 3
            await pilot.press("shift+tab")
            assert form.focused is form.query_one("#tags", TextArea)
            await pilot.press("escape")
            assert isinstance(app.screen, ConfirmScreen)
            assert app.focused is app.screen.query_one("#keep")
            await pilot.press("escape")
            assert assistant.note(note.id).body == raw

    run(journey)


@pytest.mark.parametrize("plain", [False, True])
def test_selected_row_secondary_text_contrast_and_plain_marker(
    assistant: Assistant, tmp_path: Path, plain: bool
) -> None:
    assistant.add_contact("Олена", ("1234567890",))
    app = app_for(assistant, plain=plain)

    async def journey() -> None:
        async with app.run_test(size=(80, 24)) as pilot:
            await settle(pilot)
            await pilot.press("enter")
            await settle(pilot)
            assert isinstance(app.screen, RecordsScreen)
            view = app.screen.query_one("#records", ListView)
            row = view.children[0]
            assert app.focused is view and row.has_class("-highlight")
            assert row.styles.border_left[0] == "thick" and row.rich_style.bold and not row.rich_style.reverse
            if not plain:
                background = row.rich_style.bgcolor
                assert background is not None

                def luminance(channels: tuple[int, int, int]) -> float:
                    normalized = [value / 255 for value in channels]
                    linear = [
                        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in normalized
                    ]
                    return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722), strict=True))

                backdrop = luminance(background.get_truecolor())
                for widget in row.query(".muted, .row-id"):
                    foreground = widget.rich_style.color
                    assert foreground is not None
                    ink = luminance(foreground.get_truecolor())
                    assert (max(ink, backdrop) + 0.05) / (min(ink, backdrop) + 0.05) >= 4.5
            (tmp_path / f"selected-row-{'plain' if plain else 'color'}.svg").write_text(
                app.export_screenshot(), encoding="utf-8"
            )

    run(journey)


@pytest.mark.parametrize("kind", ["contacts", "notes"])
def test_arrow_selection_visible_in_both_viewports_and_after_back(assistant: Assistant, kind: str) -> None:
    values = (
        [assistant.add_contact(f"Контакт {number}", ("1234567890",)) for number in range(3)]
        if kind == "contacts"
        else [assistant.add_note(f"Нотатка {number}", "Текст", ("робота",)) for number in range(3)]
    )
    app = app_for(assistant)

    async def journey() -> None:
        async with app.run_test(size=(60, 20)) as pilot:
            await settle(pilot)
            await pilot.press(*(["down", "enter"] if kind == "notes" else ["enter"]))
            await settle(pilot)
            assert isinstance(app.screen, RecordsScreen)
            origin = app.screen
            view = origin.query_one("#records", ListView)
            content = origin.query_one("#content")
            for key, index in ((None, 0), ("down", 1), ("down", 2), ("up", 1), ("up", 0), ("down", 1), ("down", 2)):
                if key:
                    await pilot.press(key)
                    await settle(pilot)
                assert app.focused is view and view.index == index
                visible = view.children[index].region.intersection(view.scrollable_content_region)
                assert visible.intersection(content.scrollable_content_region).height >= 3
            scroll = view.scroll_y
            await pilot.press("enter")
            await settle(pilot)
            assert isinstance(app.screen, DetailScreen) and app.screen.identifier == values[2].id
            await pilot.press("escape")
            await settle(pilot)
            assert app.screen_stack[-1] is origin and app.focused is view and view.scroll_y == scroll
            assert origin.context.selected_id == values[2].id and view.index == 2
            visible = view.children[2].region.intersection(view.scrollable_content_region)
            assert visible.intersection(content.scrollable_content_region).height >= 3

    run(journey)
