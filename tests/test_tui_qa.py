from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from test_tui import app_for, replace, settle, text
from textual.containers import VerticalScroll
from textual.geometry import Region
from textual.widgets import Footer, Input

from kolo.models import Contact
from kolo.services import Assistant
from kolo.tui_forms import FormScreen
from kolo.tui_screens import RecordsScreen


@pytest.mark.parametrize("size", [(80, 24), (60, 20)])
@pytest.mark.parametrize("field,value", [("name", ""), ("email", "wrong")])
def test_qa_field_error_reason_and_focus_visible(
    assistant: Assistant, size: tuple[int, int], field: str, value: str, tmp_path: Path
) -> None:
    app = app_for(assistant)

    async def journey() -> None:
        async with app.run_test(size=size) as pilot:
            await settle(pilot)
            await pilot.press("enter")
            await settle(pilot)
            assert isinstance(app.screen, RecordsScreen)
            await pilot.press("f2", *"Чернетка")
            assert isinstance(app.screen, FormScreen)
            form = app.screen
            await replace(pilot, "address", "Адреса без втрат")
            await replace(pilot, field, value)
            draft = form.values()
            await pilot.press("ctrl+s")
            await settle(pilot)
            assert app.screen is form and app.focused is form.query_one(f"#{field}", Input)
            assert text(form) and assistant.contacts() == [] and form.values() == draft
            await pilot.pause()
            (tmp_path / "field-error.svg").write_text(app.export_screenshot(), encoding="utf-8")
            viewport = form.query_one("#content").region
            assert app.focused.region.intersection(viewport).height > 0
            assert (
                app.focused.region.intersection(form.query_one("#content").scrollable_content_region).height
                == app.focused.region.height
            )
            reason = form.query_one("#status")
            available = Region(0, 0, size[0], form.query_one(Footer).region.y)
            assert reason.region.intersection(available).height == reason.region.height, (
                f"Error reason {text(form)!r} at {reason.region}; viewport {viewport}; focused {app.focused.region}"
            )

    asyncio.run(journey())


def test_qa_contact_edit_commit_failure_rolls_back_children_and_retries(
    assistant: Assistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    import hashlib
    import sqlite3
    import subprocess
    import sys

    from test_tui import activate

    from kolo.storage import Store

    original = assistant.add_contact("Оригінал", ("1111111111", "2222222222"), "Стара адреса", "old@example.com")
    before = hashlib.sha256(assistant.store.path.read_bytes()).hexdigest()
    native_connect = Store._connect
    failing = [True]
    commits: list[bool] = []

    class CommitFailure(sqlite3.Connection):
        def commit(self) -> None:
            commits.append(failing[0])
            if failing[0]:
                raise sqlite3.OperationalError("synthetic private commit failure")
            super().commit()

    def connect(store: Store, mode: str) -> sqlite3.Connection:
        if mode == "rw":
            connection = sqlite3.connect(store.path, factory=CommitFailure, isolation_level=None)
            connection.execute("PRAGMA foreign_keys=ON")
            return connection
        return native_connect(store, mode)

    monkeypatch.setattr(Store, "_connect", connect)
    app = app_for(assistant)

    async def journey() -> None:
        async with app.run_test(size=(80, 24)) as pilot:
            await settle(pilot)
            await pilot.press("enter")
            await settle(pilot)
            await pilot.press("enter")
            await settle(pilot)
            await pilot.press("enter")
            assert isinstance(app.screen, FormScreen)
            form = app.screen
            await replace(pilot, "name", "Оновлена людина")
            await replace(pilot, "phones", "3333333333\n4444444444")
            await replace(pilot, "address", "Нова адреса")
            draft = form.values()
            await activate(pilot, "save")
            assert app.screen is form and form.values() == draft
            assert "Сховище" in text(form) and "Збережено" not in text(form)
            assert "synthetic private" not in text(form)
            assert assistant.contact(original.id) == original
            assert hashlib.sha256(assistant.store.path.read_bytes()).hexdigest() == before
            assert commits == [True]
            failing[0] = False
            await pilot.press("enter")
            await settle(pilot)
            assert isinstance(app.screen, RecordsScreen) and app.screen.context.selected_id == original.id
            changed = assistant.contact(original.id)
            assert changed.name == "Оновлена людина" and changed.phones == ("3333333333", "4444444444")
            assert changed.address == "Нова адреса" and changed.email == original.email
            assert commits == [True, False] and len(assistant.contacts()) == 1

    asyncio.run(journey())
    result = subprocess.run(
        [sys.executable, "-m", "kolo", "--data-dir", str(assistant.store.path.parent), "contacts", "show", original.id],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0 and result.stderr == ""
    assert all(
        value in result.stdout for value in (original.id, "Оновлена людина", "3333333333", "4444444444", "Нова адреса")
    )
    with sqlite3.connect(assistant.store.path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (1,)
        assert connection.execute("SELECT phone FROM contact_phones ORDER BY position").fetchall() == [
            ("3333333333",),
            ("4444444444",),
        ]


@pytest.mark.parametrize("owner", ["home", "records"])
def test_qa_suspended_home_or_list_read_failure_keeps_help_and_recovers(
    assistant: Assistant, monkeypatch: pytest.MonkeyPatch, owner: str
) -> None:
    import threading

    from kolo.errors import StorageError
    from kolo.models import Note
    from kolo.tui_screens import HelpScreen, HomeScreen

    record = assistant.add_note("Синтетичний запис", "Текст")
    native_notes = Assistant.notes
    started, release = threading.Event(), threading.Event()
    armed = [owner == "home"]
    failures = [0]

    def notes(service: Assistant, query: str = "", tag: str | None = None, sort: str = "title") -> list[Note]:
        if armed[0]:
            started.set()
            assert release.wait(10)
            failures[0] += 1
            raise StorageError(f"Сховище {service.store.path}: синтетичний збій.")
        return native_notes(service, query, tag, sort)

    monkeypatch.setattr(Assistant, "notes", notes)
    app = app_for(assistant)

    async def journey() -> None:
        async with app.run_test(size=(80, 24)) as pilot:
            if owner == "records":
                await settle(pilot)
                armed[0] = True
                await pilot.press("down", "enter")
            for _ in range(100):
                await pilot.pause(0.01)
                if started.is_set():
                    break
            assert started.is_set()
            origin = app.screen
            await pilot.press("f1")
            assert isinstance(app.screen, HelpScreen)
            help_screen = app.screen
            release.set()
            await settle(pilot)
            assert app.screen is help_screen and failures == [1]
            assert origin in app.screen_stack
            armed[0] = False
            await pilot.press("escape")
            await settle(pilot)
            assert app.screen is origin
            if owner == "home":
                assert isinstance(origin, HomeScreen) and "Нотаток: 1" in text(origin, "#summary")
            else:
                assert isinstance(origin, RecordsScreen) and origin.rows == [record] and origin.ready
                await pilot.press("enter")
                await settle(pilot)
                from kolo.tui_screens import DetailScreen

                assert isinstance(app.screen, DetailScreen) and app.screen.identifier == record.id

    try:
        asyncio.run(journey())
    finally:
        release.set()


@pytest.mark.parametrize(
    "today,days,expected",
    [
        ("2025-02-28", "0", [("Високосний", "28.02.2025", "0"), ("Звичайний", "28.02.2025", "0")]),
        ("2028-02-28", "0", [("Звичайний", "28.02.2028", "0")]),
        ("2028-02-28", "1", [("Звичайний", "28.02.2028", "0"), ("Високосний", "29.02.2028", "1")]),
        ("2026-12-30", "3", [("Сьогодні", "30.12.2026", "0"), ("Січень", "02.01.2027", "3")]),
    ],
)
def test_qa_live_calendar_exact_leap_and_year_boundaries(
    assistant: Assistant, today: str, days: str, expected: list[tuple[str, str, str]]
) -> None:
    from datetime import date

    from test_tui import activate
    from textual.widgets import ListView, Static

    from kolo.tui_screens import DetailScreen

    assistant.today = lambda: date.fromisoformat(today)
    for name, birthday in (
        ("Звичайний", "2000-02-28"),
        ("Високосний", "2000-02-29"),
        ("Сьогодні", "2000-12-30"),
        ("Січень", "2000-01-02"),
    ):
        assistant.add_contact(name, birthday=birthday)
    app = app_for(assistant)

    async def journey() -> None:
        async with app.run_test(size=(80, 24)) as pilot:
            await settle(pilot)
            await pilot.press("down", "down", "enter")
            await settle(pilot)
            assert isinstance(app.screen, RecordsScreen)
            origin = app.screen
            await replace(pilot, "days", days)
            await activate(pilot, "apply")
            assert [value.name for value in origin.rows if isinstance(value, Contact)] == [
                value[0] for value in expected
            ]
            rows = origin.query_one("#records", ListView).children
            for row, (name, anniversary, until) in zip(rows, expected, strict=True):
                visible = "\n".join(str(widget.content) for widget in row.query(Static))
                assert name in visible and anniversary in visible and f"через {until} дн." in visible
            await pilot.press(*(["down"] * (len(expected) - 1)), "enter")
            await settle(pilot)
            assert isinstance(app.screen, DetailScreen) and app.screen.value == origin.rows[-1]
            await pilot.press("escape")
            await settle(pilot)
            assert app.screen is origin and origin.query_one("#days", Input).value == days

    asyncio.run(journey())


def test_qa_combined_filters_and_far_selection_context_survive_back(assistant: Assistant, tmp_path: Path) -> None:
    from test_tui import activate
    from textual.widgets import ListView, Select

    from kolo.tui_screens import DetailScreen

    for number in range(18):
        assistant.add_note(f"Подорож {number:02d}", "Море", ("робота", f"тег{number:02d}"))
    assistant.add_note("Подорож поза тегом", "Море", ("дім",))
    app = app_for(assistant)

    async def journey() -> None:
        async with app.run_test(size=(60, 20)) as pilot:
            await settle(pilot)
            await pilot.press("down", "enter")
            await settle(pilot)
            assert isinstance(app.screen, RecordsScreen)
            origin = app.screen
            await replace(pilot, "query", "МОРЕ")
            await replace(pilot, "tag", " РОБОТА ")
            for _ in range(20):
                if app.focused and app.focused.id == "sort":
                    break
                await pilot.press("tab")
            await pilot.press("enter", "down", "enter")
            await activate(pilot, "apply")
            assert origin.rows == assistant.notes("МОРЕ", "РОБОТА", "tags")
            await pilot.press(*(["down"] * 14))
            await pilot.pause()
            target = origin.rows[14]
            view = origin.query_one("#records", ListView)
            assert view.index == 14 and view.scroll_y > 0
            scroll = view.scroll_y
            await pilot.press("enter")
            await settle(pilot)
            assert isinstance(app.screen, DetailScreen) and app.screen.identifier == target.id
            await pilot.press("escape")
            await settle(pilot)
            assert app.screen is origin and app.focused is view
            assert origin.context.selected_id == target.id and view.index == 14
            assert view.scroll_y == scroll
            assert origin.query_one("#query", Input).value == "МОРЕ"
            assert origin.query_one("#tag", Input).value == " РОБОТА "
            assert origin.query_one("#sort", Select).value == "tags"
            for _ in range(20):
                await pilot.pause(0.05)
                if view.children[14].region.intersection(origin.query_one("#content").region).height >= 3:
                    break
            (tmp_path / "restored-far-selection.svg").write_text(app.export_screenshot(), encoding="utf-8")
            assert view.children[14].region.intersection(origin.query_one("#content").region).height >= 3, (
                view.region,
                view.children[14].region,
                origin.query_one("#content").region,
                view.scroll_y,
            )

    asyncio.run(journey())


@pytest.mark.parametrize("size", [(120, 36), (80, 24), (60, 20)])
def test_qa_screen_matrix_visible_keyboard_focus_and_preserved_long_draft(
    assistant: Assistant, size: tuple[int, int], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from test_tui import activate
    from textual.widgets import Button, ListView, Static, TextArea

    from kolo.errors import StorageError
    from kolo.tui_forms import ConfirmScreen, ReadErrorScreen
    from kolo.tui_screens import DetailScreen, HomeScreen

    note = assistant.add_note("[bold] " + "Українська назва " * 6, "Текст\x1b]0;ATTACK\x07\u202e\n" + "я" * 9970)
    app = app_for(assistant, plain=True)
    artifacts: list[str] = []

    async def capture(pilot: object, name: str) -> None:
        await asyncio.sleep(0)
        focused = app.focused
        assert focused is not None and focused.has_focus
        available = (
            Region(0, 0, app.size.width, app.screen.query_one(Footer).region.y)
            if not isinstance(app.screen, (ConfirmScreen, ReadErrorScreen))
            else app.screen.region
        )
        assert focused.region.intersection(available).height > 0, (name, focused, focused.region, available)
        clipped = available
        for ancestor in focused.ancestors:
            if isinstance(ancestor, VerticalScroll):
                clipped = clipped.intersection(ancestor.scrollable_content_region)
        visible = focused.region.intersection(clipped)
        assert visible.height > 0, (name, focused, focused.region, clipped)
        if isinstance(focused, (Button, Input)):
            assert visible.height == focused.region.height, (name, focused, focused.region, clipped)
        if isinstance(focused, (Button, Input, TextArea, ListView)):
            assert focused.styles.border_top[0] == "double", (name, focused, focused.styles.border_top)
        path = tmp_path / f"{name}-{size[0]}x{size[1]}.svg"
        path.write_text(app.export_screenshot(), encoding="utf-8")
        artifacts.append(name)

    async def journey() -> None:
        async with app.run_test(size=size) as pilot:
            await settle(pilot)
            assert isinstance(app.screen, HomeScreen)
            await capture(pilot, "home")
            await pilot.press("down", "down", "down", "down")
            await pilot.pause()
            menu = app.screen.query_one("#menu", ListView)
            assert menu.index == 4
            assert menu.children[4].region.intersection(app.screen.query_one("#content").region).height > 0
            await pilot.press("up", "up", "up", "up", "enter")
            await settle(pilot)
            assert isinstance(app.screen, RecordsScreen) and not app.screen.rows
            await capture(pilot, "empty-list")
            await activate(pilot, "add")
            assert isinstance(app.screen, FormScreen)
            await capture(pilot, "contact-form")
            await pilot.press(*"Чернетка", "escape")
            assert isinstance(app.screen, ConfirmScreen)
            await capture(pilot, "dirty-confirm")
            await pilot.press("escape")
            assert isinstance(app.screen, FormScreen) and app.screen.query_one("#name", Input).value == "Чернетка"
            await pilot.press("escape", "tab", "enter")
            await settle(pilot)
            await pilot.press("escape", "down", "enter")
            await settle(pilot)
            assert isinstance(app.screen, RecordsScreen) and app.screen.rows == [note]
            await capture(pilot, "filled-list")
            selected = app.screen.query_one("#records", ListView).children[0]
            assert selected.region.intersection(app.screen.query_one("#content").region).height >= 3
            await pilot.press("enter")
            await settle(pilot)
            assert isinstance(app.screen, DetailScreen)
            assert "[bold]" in text(app.screen, "#details") and "\\x1b" in text(app.screen, "#details")
            assert "\\u202e" in text(app.screen, "#details") and "\x1b" not in text(app.screen, "#details")
            await capture(pilot, "detail")
            await activate(pilot, "delete")
            assert isinstance(app.screen, ConfirmScreen)
            assert any(note.id in str(widget.content) for widget in app.screen.query(Static))
            await capture(pilot, "delete-confirm")
            await pilot.press("enter")
            assert assistant.note(note.id) == note
            await activate(pilot, "edit")
            assert isinstance(app.screen, FormScreen)
            form = app.screen
            await replace(pilot, "title", "Змінена назва")
            prefix = "[bold]\x1b]0;ATTACK\x07\u202e\n"
            await replace(pilot, "body", prefix + "я" * (10000 - len(prefix)))
            draft = form.values()
            assert len(draft["body"]) == 10000
            await capture(pilot, "note-form")
            await pilot.resize_terminal(60, 20)
            await pilot.resize_terminal(80, 24)
            await pilot.resize_terminal(*size)
            assert form.values() == draft and form.dirty
            for _ in range(20):
                if app.focused and app.focused.id == "save":
                    break
                await pilot.press("tab")
            await pilot.pause()
            await capture(pilot, "save-reachable-after-resize")
            assert app.focused is form.query_one("#save")
            await pilot.press("shift+tab")
            assert app.focused is form.query_one("#tags")
            from kolo.models import Note, NotePatch

            def failed_edit(service: Assistant, identifier: str, patch: NotePatch) -> Note:
                raise StorageError(f"Сховище {service.store.path}: синтетичний збій запису.")

            with monkeypatch.context() as failure:
                failure.setattr(Assistant, "edit_note", failed_edit)
                await pilot.press("ctrl+s")
                await settle(pilot)
                assert app.screen is form and form.values() == draft and "Збережено" not in text(form)
                assert "Сховище" in text(form) and assistant.note(note.id) == note
                await capture(pilot, "write-error")
            await pilot.press("escape", "tab", "enter")
            await settle(pilot)
            assert isinstance(app.screen, DetailScreen)
            await pilot.press("escape")
            await settle(pilot)
            await pilot.press("escape")
            await settle(pilot)
            assert isinstance(app.screen, HomeScreen)
            await pilot.press("escape")
            assert isinstance(app.screen, ConfirmScreen)
            await capture(pilot, "exit-confirm")
            await pilot.press("escape")
            native_contacts = Assistant.contacts
            fail = [True]

            def contacts(service: Assistant, query: str = "", *, today: object = None) -> list[Contact]:
                if fail[0]:
                    raise StorageError(f"Сховище {service.store.path}: синтетичний збій читання.")
                return native_contacts(service, query)

            monkeypatch.setattr(Assistant, "contacts", contacts)
            await pilot.press("up", "enter")
            await settle(pilot)
            assert isinstance(app.screen, ReadErrorScreen)
            assert str(assistant.store.path) in str(app.screen.query_one("#read-error", Static).content)
            await capture(pilot, "read-error")
            fail[0] = False
            await pilot.press("enter")
            await settle(pilot)
            assert isinstance(app.screen, RecordsScreen) and app.screen.ready
            assert assistant.note(note.id) == note
        assert len(artifacts) == 12

    asyncio.run(journey())


@pytest.mark.parametrize("raw", ["\nУкраїна\r\nДругий\rТретій\tрядок\n", "А\u2028Б\u0085"])
def test_qa_cli_seed_native_edit_and_reopen_preserve_exact_body(assistant: Assistant, raw: str, tmp_path: Path) -> None:
    import re
    import sqlite3
    import subprocess
    import sys

    from textual.widgets import TextArea

    from kolo.tui_screens import DetailScreen

    source = tmp_path / "source.txt"
    source.write_bytes(raw.encode("utf-8"))
    command = [sys.executable, "-m", "kolo", "--data-dir", str(assistant.store.path.parent)]
    created = subprocess.run(
        [*command, "notes", "add", "--title", "Початковий", "--body-file", str(source)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert created.returncode == 0 and created.stderr == ""
    match = re.search(r"n_[0-9a-f]{12}", created.stdout)
    assert match is not None
    identifier = match.group()
    app = app_for(assistant)

    async def journey() -> None:
        async with app.run_test(size=(60, 20)) as pilot:
            await settle(pilot)
            await pilot.press("down", "enter")
            await settle(pilot)
            await pilot.press("enter")
            await settle(pilot)
            await pilot.press("enter")
            assert isinstance(app.screen, FormScreen) and not app.screen.dirty
            await pilot.press("escape")
            assert isinstance(app.screen, DetailScreen)
            await pilot.press("enter")
            await replace(pilot, "title", "Змінений заголовок")
            await pilot.resize_terminal(80, 24)
            await pilot.press("ctrl+s")
            await settle(pilot)
            assert isinstance(app.screen, RecordsScreen) and assistant.note(identifier).body == raw
            await pilot.press("enter")
            await settle(pilot)
            await pilot.press("enter", "tab")
            assert isinstance(app.screen, FormScreen) and app.focused is app.screen.query_one("#body", TextArea)
            if raw.startswith("\n"):
                await pilot.press("ctrl+home", "down", "right", "right", "right", "right", "enter")
            else:
                await pilot.press("ctrl+home", "down", "delete", "В")
            await pilot.press("ctrl+s")
            await settle(pilot)
            assert isinstance(app.screen, RecordsScreen)

    asyncio.run(journey())
    expected = raw.replace("Україна", "Укра\nїна") if raw.startswith("\n") else raw.replace("Б", "В")
    shown = subprocess.run([*command, "notes", "show", identifier], capture_output=True, text=True, timeout=10)
    assert shown.returncode == 0 and identifier in shown.stdout and "Змінений заголовок" in shown.stdout
    with sqlite3.connect(assistant.store.path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (1,)
        stored = connection.execute("SELECT id,body FROM notes").fetchall()
        assert stored == [(identifier, expected)]
        assert stored[0][1].encode("utf-8") == expected.encode("utf-8")
    from kolo.tui import KoloApp

    reopened = KoloApp(lambda: assistant, assistant.store.path)

    async def check_reopen() -> None:
        async with reopened.run_test() as pilot:
            await settle(pilot)
            await pilot.press("down", "enter")
            await settle(pilot)
            await pilot.press("enter")
            await settle(pilot)
            assert isinstance(reopened.screen, DetailScreen)
            assert reopened.screen.identifier == identifier and reopened.screen.value == assistant.note(identifier)

    asyncio.run(check_reopen())


@pytest.mark.parametrize("size", [(120, 36), (80, 24), (60, 20)])
def test_qa_long_write_error_keeps_save_reason_and_draft_visible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, size: tuple[int, int]
) -> None:
    import hashlib
    from datetime import date

    from test_tui import activate
    from textual.widgets import Button

    from kolo.errors import StorageError
    from kolo.models import Note, NotePatch
    from kolo.storage import Store

    directory = tmp_path / ("legitimate-long-directory-" + "x" * 80)
    assistant = Assistant(Store(directory, date(2026, 10, 24)), lambda: date(2026, 10, 24))
    original = assistant.add_note("Збережений заголовок", "Оригінальний текст", ("тег",))
    before = hashlib.sha256(assistant.store.path.read_bytes()).hexdigest()
    app = app_for(assistant)

    def fail(service: Assistant, identifier: str, patch: NotePatch) -> Note:
        raise StorageError(f"Сховище {service.store.path}: синтетичний збій запису.")

    monkeypatch.setattr(Assistant, "edit_note", fail)

    async def journey() -> None:
        async with app.run_test(size=size) as pilot:
            await settle(pilot)
            await pilot.press("down", "enter")
            await settle(pilot)
            await pilot.press("enter")
            await settle(pilot)
            await pilot.press("enter")
            assert isinstance(app.screen, FormScreen)
            form = app.screen
            await replace(pilot, "body", "Чернетка\n[bold] без втрат")
            draft = form.values()
            await activate(pilot, "save")
            for _ in range(20):
                await pilot.pause(0.05)
            assert app.screen is form and form.values() == draft
            assert assistant.note(original.id) == original
            assert hashlib.sha256(assistant.store.path.read_bytes()).hexdigest() == before
            reason = form.query_one("#status")
            assert str(assistant.store.path) in text(form) and "Збережено" not in text(form)
            available = Region(0, 0, size[0], form.query_one(Footer).region.y)
            assert reason.region.intersection(available).height == reason.region.height
            save = form.query_one("#save", Button)
            assert app.focused is save and save.styles.border_top[0] == "double"
            viewport = form.query_one("#content").scrollable_content_region
            (tmp_path / "long-write-error.svg").write_text(app.export_screenshot(), encoding="utf-8")
            assert save.region.intersection(viewport).height == save.region.height, (
                f"Save {save.region}; actual ancestor clip {viewport}; reason {reason.region}"
            )

    asyncio.run(journey())
