from __future__ import annotations

import threading
from pathlib import Path

import pytest
from conftest import Runner
from test_tui import activate, app_for, replace, run, settle, text
from textual.widgets import Input, TextArea

from kolo import cli
from kolo.errors import StorageError
from kolo.models import Note
from kolo.services import Assistant
from kolo.tui_forms import FormScreen, ReadErrorScreen
from kolo.tui_screens import DetailScreen, RecordsScreen


@pytest.mark.parametrize("options", [[], ["--plain"], ["--line-mode"], ["--line-mode", "--plain"]])
@pytest.mark.parametrize("command", [[], ["demo"]])
def test_non_tty_modes_never_open_data(runner: Runner, options: list[str], command: list[str]) -> None:
    result = runner(*options, *command)
    assert result.returncode == 2 and result.stdout == "" and "Помилка вводу" in result.stderr
    assert not runner.directory.exists()


def test_global_line_mode_does_not_count_as_edit_field(runner: Runner) -> None:
    result = runner("--line-mode", "contacts", "edit", "c_000000000001")
    assert result.returncode == 2 and "хоча б одне поле" in result.stderr
    assert not runner.directory.exists()


def test_default_plain_route_passes_lazy_factory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import io
    from collections.abc import Callable

    from kolo import tui

    class TTY(io.StringIO):
        def isatty(self) -> bool:
            return True

    monkeypatch.setattr("sys.stdin", TTY())
    monkeypatch.setattr("sys.stdout", TTY())
    directory = tmp_path / "lazy"
    called: list[Path] = []

    def inspect(factory: Callable[[], Assistant], path: Path, *, plain: bool = False, demo: bool = False) -> int:
        assert not directory.exists() and plain and not demo
        called.append(path)
        return 0

    monkeypatch.setattr(tui, "run_tui", inspect)
    assert cli.main(["--data-dir", str(directory), "--plain"]) == 0
    assert called == [directory / "kolo.sqlite3"] and not directory.exists()


def test_committed_write_read_failure_retries_only_read(assistant: Assistant, monkeypatch: pytest.MonkeyPatch) -> None:
    original_add, original_notes = Assistant.add_note, Assistant.notes
    fail = [False]
    mutations: list[str] = []

    def add(service: Assistant, title: str, body: str, tags: tuple[str, ...] = ()) -> Note:
        result = original_add(service, title, body, tags)
        mutations.append(result.id)
        fail[0] = True
        return result

    def notes(service: Assistant, query: str = "", tag: str | None = None, sort: str = "title") -> list[Note]:
        if fail[0]:
            raise StorageError(f"Сховище {service.store.path}: збій читання.")
        return original_notes(service, query, tag, sort)

    monkeypatch.setattr(Assistant, "add_note", add)
    monkeypatch.setattr(Assistant, "notes", notes)
    app = app_for(assistant)

    async def journey() -> None:
        async with app.run_test() as pilot:
            await settle(pilot)
            await pilot.press("down", "enter")
            await settle(pilot)
            origin = app.screen
            await pilot.press("f2", *"Запис")
            await replace(pilot, "body", "Текст")
            await pilot.press("ctrl+s")
            await settle(pilot)
            assert isinstance(app.screen, ReadErrorScreen) and isinstance(origin, RecordsScreen)
            assert "Збережено" in text(origin) and "Не оновлено" in text(origin)
            assert len(mutations) == 1 and origin.query_one("#add").disabled
            fail[0] = False
            await pilot.press("enter")
            await settle(pilot)
            assert app.screen_stack[-1] is origin
            assert isinstance(origin, RecordsScreen) and [row.id for row in origin.rows] == mutations
            assert len(mutations) == 1

    run(journey)


def test_stale_read_cannot_reopen_hidden_record(assistant: Assistant, monkeypatch: pytest.MonkeyPatch) -> None:
    assistant.add_note("Перший", "Один")
    target = assistant.add_note("Другий", "Два")
    original = Assistant.notes
    started, release = threading.Event(), threading.Event()

    def notes(service: Assistant, query: str = "", tag: str | None = None, sort: str = "title") -> list[Note]:
        if query == "відсутнє":
            started.set()
            assert release.wait(5)
        return original(service, query, tag, sort)

    monkeypatch.setattr(Assistant, "notes", notes)
    app = app_for(assistant)

    async def journey() -> None:
        async with app.run_test() as pilot:
            await settle(pilot)
            await pilot.press("down", "enter")
            await settle(pilot)
            assert isinstance(app.screen, RecordsScreen)
            origin = app.screen
            await replace(pilot, "query", "відсутнє")
            for _ in range(20):
                if app.focused and app.focused.id == "apply":
                    break
                await pilot.press("tab")
            await pilot.press("enter")
            await pilot.pause(0.03)
            assert started.is_set() and not origin.ready
            await replace(pilot, "query", "Другий")
            await pilot.press("enter")
            assert not isinstance(app.screen, DetailScreen)
            release.set()
            await settle(pilot)
            assert app.screen is origin and origin.rows == [target]
            await pilot.press("enter")
            await settle(pilot)
            assert isinstance(app.screen, DetailScreen) and app.screen.identifier == target.id

    try:
        run(journey)
    finally:
        release.set()


def test_delete_neighbor_and_missing_id_recovery(assistant: Assistant) -> None:
    first = assistant.add_contact("А")
    middle = assistant.add_contact("Б")
    last = assistant.add_contact("В")
    app = app_for(assistant)

    async def journey() -> None:
        async with app.run_test() as pilot:
            await settle(pilot)
            await pilot.press("enter")
            await settle(pilot)
            await pilot.press("down", "enter")
            await settle(pilot)
            assert isinstance(app.screen, DetailScreen) and app.screen.identifier == middle.id
            await activate(pilot, "delete")
            await pilot.press("tab", "enter")
            await settle(pilot)
            assert isinstance(app.screen, RecordsScreen) and app.screen.context.selected_id == last.id
            assistant.delete_contact(last.id)
            await pilot.press("enter")
            await settle(pilot)
            assert isinstance(app.screen, RecordsScreen) and app.screen.rows == [first]
            assert "не знайдено" in text(app.screen)

    run(journey)


def test_raw_body_limit_applies_after_lossless_reconstruction(assistant: Assistant) -> None:
    raw = "A\r\n" * 3333 + "Z"
    note = assistant.add_note("Ліміт", raw)
    app = app_for(assistant)

    async def journey() -> None:
        async with app.run_test() as pilot:
            await settle(pilot)
            await pilot.press("down", "enter")
            await settle(pilot)
            await pilot.press("enter")
            await settle(pilot)
            await pilot.press("enter", "tab")
            assert isinstance(app.screen, FormScreen)
            form = app.screen
            assert app.focused is form.query_one("#body", TextArea)
            await pilot.press("home", "X", "ctrl+s")
            await settle(pilot)
            assert app.screen is form and "10000" in text(form)
            assert form.query_one("#body", TextArea).text.startswith("XA\n") and assistant.note(note.id).body == raw
            await pilot.press("backspace", "ctrl+s")
            await settle(pilot)
            assert isinstance(app.screen, RecordsScreen) and assistant.note(note.id).body == raw

    run(journey)


def test_literal_control_filter_preserves_cells_styles_and_trusted_segments() -> None:
    from rich.segment import ControlType, Segment
    from rich.style import Style
    from textual.color import Color

    from kolo.tui import LiteralControls

    style = Style(bold=True, reverse=True)
    for width in (60, 80, 120):
        source = [Segment("A" * (width - 1) + "\x1b\u202e\x07\x85" * 50 + "Z", style)]
        result = LiteralControls().apply(source, Color(0, 0, 0))
        assert Segment.get_line_length(result) == Segment.get_line_length(source) == width
        assert result == [Segment("A" * (width - 1) + "Z", style)]
    trusted = Segment("\x1b[2J", control=((ControlType.CLEAR,),))
    assert LiteralControls().apply([trusted], Color(0, 0, 0)) == [trusted]


@pytest.mark.parametrize("raw", ["Alpha\r\nBeta\rGamma\u2028", "Alpha\x85", "Alpha\u2029"])
def test_native_one_character_edit_preserves_original_separators(assistant: Assistant, raw: str) -> None:
    note = assistant.add_note("Точний текст", raw)
    app = app_for(assistant)

    async def journey() -> None:
        async with app.run_test() as pilot:
            await settle(pilot)
            await pilot.press("down", "enter")
            await settle(pilot)
            await pilot.press("enter")
            await settle(pilot)
            await pilot.press("enter", "tab", "right", "X", "ctrl+s")
            await settle(pilot)
            assert isinstance(app.screen, RecordsScreen)
            assert assistant.note(note.id).body == "AX" + raw[1:]

    run(journey)


def test_birthday_contact_edit_returns_to_same_interval(assistant: Assistant) -> None:
    contact = assistant.add_contact("День народження", birthday="2000-10-24")
    app = app_for(assistant)

    async def journey() -> None:
        async with app.run_test() as pilot:
            await settle(pilot)
            await pilot.press("down", "down", "enter")
            await settle(pilot)
            assert isinstance(app.screen, RecordsScreen)
            origin = app.screen
            await replace(pilot, "days", "0")
            await activate(pilot, "apply")
            await pilot.press("enter")
            await settle(pilot)
            await pilot.press("enter")
            assert isinstance(app.screen, FormScreen) and app.screen.contact_form
            await replace(pilot, "name", "Оновлений контакт")
            await pilot.press("ctrl+s")
            await settle(pilot)
            assert app.screen is origin and origin.query_one("#days", Input).value == "0"
            assert origin.context.selected_id == contact.id and origin.rows == [assistant.contact(contact.id)]
            assert assistant.contact(contact.id).name == "Оновлений контакт" and assistant.notes() == []

    run(journey)


@pytest.mark.parametrize("outcome", ["success", "input", "storage"])
def test_late_detail_read_after_back_never_changes_current_screen(
    assistant: Assistant, monkeypatch: pytest.MonkeyPatch, outcome: str
) -> None:
    from kolo.errors import InputError
    from kolo.models import Contact

    contact = assistant.add_contact("Залишити")
    started, release = threading.Event(), threading.Event()
    original = Assistant.contact

    def delayed(service: Assistant, identifier: str) -> Contact:
        started.set()
        assert release.wait(5)
        if outcome == "input":
            raise InputError("Запис не знайдено.")
        if outcome == "storage":
            raise StorageError(f"Сховище {service.store.path}: читання недоступне.")
        return original(service, identifier)

    monkeypatch.setattr(Assistant, "contact", delayed)
    app = app_for(assistant)

    async def journey() -> None:
        async with app.run_test() as pilot:
            await settle(pilot)
            await pilot.press("enter")
            await settle(pilot)
            origin = app.screen
            await pilot.press("enter")
            await pilot.pause(0.03)
            assert started.is_set() and isinstance(app.screen, DetailScreen)
            await pilot.press("escape")
            assert app.screen is origin
            release.set()
            await settle(pilot)
            await app.workers.wait_for_complete()
            assert app.screen_stack[-1] is origin and isinstance(origin, RecordsScreen)
            assert [row.id for row in origin.rows] == [contact.id]

    try:
        run(journey)
    finally:
        release.set()


def test_late_list_failure_after_back_never_opens_modal(assistant: Assistant, monkeypatch: pytest.MonkeyPatch) -> None:
    from kolo.tui_screens import HomeScreen

    assistant.add_note("Запис", "Текст")
    started, release = threading.Event(), threading.Event()
    original = Assistant.notes

    def delayed(service: Assistant, query: str = "", tag: str | None = None, sort: str = "title") -> list[Note]:
        if query == "затримка":
            started.set()
            assert release.wait(5)
            raise StorageError(f"Сховище {service.store.path}: читання недоступне.")
        return original(service, query, tag, sort)

    monkeypatch.setattr(Assistant, "notes", delayed)
    app = app_for(assistant)

    async def journey() -> None:
        async with app.run_test() as pilot:
            await settle(pilot)
            await pilot.press("down", "enter")
            await settle(pilot)
            await replace(pilot, "query", "затримка")
            await pilot.press("enter")
            await pilot.pause(0.03)
            assert started.is_set()
            await pilot.press("escape")
            release.set()
            await settle(pilot)
            await app.workers.wait_for_complete()
            assert isinstance(app.screen, HomeScreen) and "Нотаток: 1" in text(app.screen, "#summary")

    try:
        run(journey)
    finally:
        release.set()


@pytest.mark.parametrize("outcome", ["success", "input", "storage"])
def test_covered_detail_read_preserves_help_and_refreshes_on_resume(
    assistant: Assistant, monkeypatch: pytest.MonkeyPatch, outcome: str
) -> None:
    from kolo.errors import InputError
    from kolo.models import Contact
    from kolo.tui_screens import HelpScreen

    contact = assistant.add_contact("Залишити")
    started, release = threading.Event(), threading.Event()
    original = Assistant.contact

    def delayed(service: Assistant, identifier: str) -> Contact:
        started.set()
        assert release.wait(5)
        if outcome == "input":
            raise InputError("Запис не знайдено.")
        if outcome == "storage":
            raise StorageError(f"Сховище {service.store.path}: читання недоступне.")
        return original(service, identifier)

    monkeypatch.setattr(Assistant, "contact", delayed)
    app = app_for(assistant)

    async def journey() -> None:
        async with app.run_test() as pilot:
            await settle(pilot)
            await pilot.press("enter")
            await settle(pilot)
            origin = app.screen
            await pilot.press("enter")
            await pilot.pause(0.03)
            assert started.is_set()
            await pilot.press("f1")
            assert isinstance(app.screen, HelpScreen)
            help_screen = app.screen
            release.set()
            await settle(pilot)
            await app.workers.wait_for_complete()
            assert app.screen_stack[-1] is help_screen
            await pilot.press("escape")
            await settle(pilot)
            if outcome == "success":
                assert isinstance(app.screen, DetailScreen) and app.screen.value == contact
                assert not app.screen.query_one("#edit").disabled
            elif outcome == "input":
                assert app.screen_stack[-1] is origin and isinstance(origin, RecordsScreen)
                assert "не знайдено" in text(origin)
            else:
                assert isinstance(app.screen, ReadErrorScreen)

    try:
        run(journey)
    finally:
        release.set()


@pytest.mark.parametrize("status", [0, 7])
def test_tui_entrypoint_preserves_native_exit_status(
    assistant: Assistant, monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    from textual.app import App

    from kolo import tui

    class ExitApp(App[int]):
        def on_mount(self) -> None:
            self.exit(return_code=status)

    app = ExitApp()
    native_run = app.run

    def headless_run() -> int | None:
        return native_run(headless=True)

    def factory(*args: object, **kwargs: object) -> App[int]:
        return app

    monkeypatch.setattr(app, "run", headless_run)
    monkeypatch.setattr(tui, "KoloApp", factory)
    assert tui.run_tui(lambda: assistant, assistant.store.path) == status


@pytest.mark.parametrize("change", ["oversize", "title_only"])
def test_note_body_prevalidation_and_unchanged_body_skip_diff(
    assistant: Assistant, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    import hashlib
    from typing import Never

    from kolo import tui_forms

    note = assistant.add_note("Нотатка", "A" * 10000)
    before = hashlib.sha256(assistant.store.path.read_bytes()).hexdigest()
    matches: list[None] = []

    def forbidden_matcher(*args: object, **kwargs: object) -> Never:
        matches.append(None)
        raise AssertionError("Unexpected lossless diff")

    monkeypatch.setattr(tui_forms, "SequenceMatcher", forbidden_matcher)
    app = app_for(assistant)

    async def journey() -> None:
        async with app.run_test() as pilot:
            await settle(pilot)
            await pilot.press("down", "enter")
            await settle(pilot)
            await pilot.press("enter")
            await settle(pilot)
            await pilot.press("enter")
            assert isinstance(app.screen, FormScreen)
            form = app.screen
            if change == "oversize":
                await replace(pilot, "body", "A" * 20000)
            else:
                await replace(pilot, "title", "Оновлена")
            await pilot.press("ctrl+s")
            await settle(pilot)
            assert matches == [] and app.writing == 0
            if change == "oversize":
                assert app.screen is form and not form.busy
                assert "10000" in text(form) and "Збережено" not in text(form)
                assert form.query_one("#body", TextArea).text == "A" * 20000
                assert app.focused is form.query_one("#body", TextArea)
                assert hashlib.sha256(assistant.store.path.read_bytes()).hexdigest() == before
                assert assistant.note(note.id) == note
            else:
                assert isinstance(app.screen, RecordsScreen)
                saved = assistant.note(note.id)
                assert saved.title == "Оновлена" and saved.body == note.body

    run(journey)


@pytest.mark.parametrize("kind", ["contacts", "notes"])
def test_missing_record_during_delete_refreshes_origin_and_nearest_selection(assistant: Assistant, kind: str) -> None:
    values = (
        [assistant.add_contact(label) for label in ("А", "Б", "В")]
        if kind == "contacts"
        else [assistant.add_note(label, "Текст") for label in ("А", "Б", "В")]
    )
    app = app_for(assistant)

    async def journey() -> None:
        async with app.run_test() as pilot:
            await settle(pilot)
            await pilot.press(*(["down", "enter"] if kind == "notes" else ["enter"]))
            await settle(pilot)
            origin = app.screen
            assert isinstance(origin, RecordsScreen)
            await pilot.press("down", "enter")
            await settle(pilot)
            assert isinstance(app.screen, DetailScreen) and app.screen.identifier == values[1].id
            detail = app.screen
            if kind == "contacts":
                assistant.delete_contact(values[1].id)
            else:
                assistant.delete_note(values[1].id)
            await activate(pilot, "delete")
            await pilot.press("tab", "enter")
            await settle(pilot)
            assert app.screen_stack[-1] is origin and detail not in app.screen_stack
            assert isinstance(origin, RecordsScreen)
            assert [row.id for row in origin.rows] == [values[0].id, values[2].id]
            assert origin.context.selected_id == values[2].id and origin.context.selected_index == 1
            assert "не знайдено" in text(origin) and "Видалено" not in text(origin)
            assert not list(origin.query("#edit, #delete"))
            await pilot.press("enter")
            await settle(pilot)
            assert isinstance(app.screen, DetailScreen) and app.screen.identifier == values[2].id

    run(journey)


@pytest.mark.parametrize("kind", ["contacts", "notes"])
def test_delete_storage_failure_remains_retryable(
    assistant: Assistant, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    value = assistant.add_contact("Залишити") if kind == "contacts" else assistant.add_note("Залишити", "Текст")
    method = "delete_contact" if kind == "contacts" else "delete_note"
    original = getattr(Assistant, method)
    attempts: list[str] = []

    def fail_once(service: Assistant, identifier: str) -> None:
        attempts.append(identifier)
        if len(attempts) == 1:
            raise StorageError(f"Сховище {service.store.path}: тимчасова помилка.")
        original(service, identifier)

    monkeypatch.setattr(Assistant, method, fail_once)
    app = app_for(assistant)

    async def journey() -> None:
        async with app.run_test() as pilot:
            await settle(pilot)
            await pilot.press(*(["down", "enter"] if kind == "notes" else ["enter"]))
            await settle(pilot)
            origin = app.screen
            await pilot.press("enter")
            await settle(pilot)
            assert isinstance(app.screen, DetailScreen)
            detail = app.screen
            await activate(pilot, "delete")
            await pilot.press("tab", "enter")
            await settle(pilot)
            assert app.screen is detail and "Сховище" in text(detail) and "Видалено" not in text(detail)
            assert not detail.query_one("#edit").disabled and not detail.query_one("#delete").disabled
            assert attempts == [value.id]
            assert (assistant.contacts() if kind == "contacts" else assistant.notes()) == [value]
            await activate(pilot, "delete")
            await pilot.press("tab", "enter")
            await settle(pilot)
            assert app.screen_stack[-1] is origin and attempts == [value.id, value.id]
            assert (assistant.contacts() if kind == "contacts" else assistant.notes()) == []

    run(journey)
