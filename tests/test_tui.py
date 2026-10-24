from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from datetime import date

import pytest
from textual.pilot import Pilot
from textual.widgets import Input, Select, Static, TextArea

from kolo.services import Assistant
from kolo.storage import Store
from kolo.tui import KoloApp
from kolo.tui_forms import BodyProjection, ConfirmScreen, FormScreen
from kolo.tui_screens import DetailScreen, HelpScreen, HomeScreen, RecordsScreen


async def settle(pilot: Pilot[int]) -> None:
    for _ in range(10):
        await pilot.pause()
        await asyncio.wait_for(pilot.app.workers.wait_for_complete(), timeout=30)
        await pilot.wait_for_scheduled_animations()
        await pilot.pause()
        if isinstance(pilot.app, KoloApp) and not pilot.app.pending:
            return
    raise AssertionError("TUI did not finish scheduled I/O")


async def activate(pilot: Pilot[int], identifier: str) -> None:
    for _ in range(40):
        if pilot.app.focused is not None and pilot.app.focused.id == identifier:
            await pilot.press("enter")
            await settle(pilot)
            return
        await pilot.press("tab")
    raise AssertionError(f"Keyboard cannot reach {identifier}")


async def replace(pilot: Pilot[int], identifier: str, text: str) -> None:
    for _ in range(40):
        focused = pilot.app.focused
        if focused is not None and focused.id == identifier:
            await pilot.press("ctrl+shift+a" if isinstance(focused, Input) else "f7", "backspace")
            if isinstance(focused, Input):
                await pilot.press(*text)
            else:
                assert isinstance(focused, TextArea)
                focused.insert(text)
            return
        await pilot.press("tab")
    raise AssertionError(f"Keyboard cannot reach field {identifier}")


def run(journey: Callable[[], Coroutine[None, None, None]]) -> None:
    asyncio.run(journey())


def app_for(assistant: Assistant, *, plain: bool = False) -> KoloApp:
    return KoloApp(lambda: assistant, assistant.store.path, plain=plain)


def text(screen: HomeScreen | RecordsScreen | DetailScreen | FormScreen, selector: str = "#status") -> str:
    return str(screen.query_one(selector, Static).content)


def test_home_navigation_duplicate_context_and_help(assistant: Assistant) -> None:
    first = assistant.add_contact("Олена", ("1111111111",))
    second = assistant.add_contact("Олена", ("2222222222",))
    expected = assistant.contacts()
    app = app_for(assistant)

    async def journey() -> None:
        async with app.run_test(size=(80, 24)) as pilot:
            await settle(pilot)
            assert isinstance(app.screen, HomeScreen) and app.focused is app.screen.query_one("#menu")
            assert "Контактів: 2" in text(app.screen, "#summary") and "7 днів" in text(app.screen, "#summary")
            await pilot.press("down", "up", "enter")
            await settle(pilot)
            assert isinstance(app.screen, RecordsScreen)
            origin = app.screen
            assert {first.id, second.id} == {item.id for item in origin.rows}
            await pilot.press("down", "enter")
            await settle(pilot)
            assert isinstance(app.screen, DetailScreen) and app.screen.identifier == expected[1].id
            assert expected[1].phones[0] in text(app.screen, "#details")
            await pilot.press("escape")
            await settle(pilot)
            assert app.screen is origin and origin.context.selected_id == expected[1].id
            assert app.focused is origin.query_one("#records")
            await pilot.press("escape", "down", "down", "down", "enter")
            assert isinstance(app.screen, HelpScreen)
            await pilot.press("escape")
            await settle(pilot)
            await pilot.press("escape")
            assert isinstance(app.screen, ConfirmScreen)
            await pilot.press("enter")
            assert isinstance(app.screen, HomeScreen)
            await pilot.press("ctrl+q", "tab", "enter")
            assert app.return_value == 0

    run(journey)


def test_empty_and_filters_native_sort_no_hidden_selection(assistant: Assistant) -> None:
    one = assistant.add_note("Б", "Шукати море", ("робота",))
    two = assistant.add_note("А", "Море", ("дім",))
    app = app_for(assistant)

    async def journey() -> None:
        async with app.run_test() as pilot:
            await settle(pilot)
            await pilot.press("down", "enter")
            await settle(pilot)
            assert isinstance(app.screen, RecordsScreen)
            origin = app.screen
            await replace(pilot, "query", "МОРЕ")
            await replace(pilot, "tag", " РОБОТА ")
            await activate(pilot, "apply")
            assert [item.id for item in origin.rows] == [one.id]
            await pilot.press("enter")
            await settle(pilot)
            assert isinstance(app.screen, DetailScreen)
            await pilot.press("escape")
            await settle(pilot)
            assert origin.query_one("#tag", Input).value == " РОБОТА "
            await replace(pilot, "query", "відсутнє")
            await activate(pilot, "apply")
            assert origin.rows == [] and "Нічого не знайдено" in text(origin)
            for _ in range(12):
                if app.focused is origin.query_one("#records"):
                    break
                await pilot.press("tab")
            await pilot.press("enter")
            assert app.screen is origin
            await activate(pilot, "clear")
            assert {item.id for item in origin.rows} == {one.id, two.id}
            await replace(pilot, "query", "")
            for _ in range(20):
                if app.focused and app.focused.id == "sort":
                    break
                await pilot.press("tab")
            await pilot.press("enter", "down", "enter")
            await activate(pilot, "apply")
            assert origin.query_one("#sort", Select).value == "tags"
            assert origin.rows == assistant.notes(sort="tags")

    run(journey)


def test_contact_create_validation_clear_and_safe_delete(assistant: Assistant) -> None:
    app = app_for(assistant)

    async def journey() -> None:
        async with app.run_test(size=(60, 20)) as pilot:
            await settle(pilot)
            await pilot.press("enter")
            await settle(pilot)
            assert isinstance(app.screen, RecordsScreen) and "Контактів поки немає" in text(app.screen)
            await pilot.press("f2")
            assert isinstance(app.screen, FormScreen)
            form = app.screen
            await pilot.press(*"Олена")
            await replace(pilot, "phones", "+38 (067) 123-45-67\n1234567890")
            await replace(pilot, "address", "Львів")
            await replace(pilot, "email", "bad")
            await replace(pilot, "birthday", "2000-02-29")
            await pilot.press("ctrl+s")
            await settle(pilot)
            assert app.screen is form and app.focused is form.query_one("#email")
            assert "Email" in text(form) and assistant.contacts() == []
            assert form.query_one("#address", Input).value == "Львів"
            await replace(pilot, "email", "olena@example.com")
            await pilot.press("ctrl+s")
            await settle(pilot)
            assert isinstance(app.screen, RecordsScreen)
            contact = assistant.contacts()[0]
            assert contact.phones == ("+380671234567", "1234567890")
            assert app.screen.context.selected_id == contact.id and "Збережено" in text(app.screen)
            await pilot.press("enter")
            await settle(pilot)
            await pilot.press("enter")
            assert isinstance(app.screen, FormScreen)
            for identifier in ("phones", "address", "email", "birthday"):
                await replace(pilot, identifier, "")
                assert isinstance(app.screen, FormScreen) and app.screen.values()[identifier] == "", app.screen.values()
            await pilot.press("ctrl+s")
            await settle(pilot)
            assert isinstance(app.screen, RecordsScreen), (
                type(app.screen).__name__,
                text(app.screen),
                app.screen.values() if isinstance(app.screen, FormScreen) else "",
            )
            changed = assistant.contact(contact.id)
            assert (
                changed.phones == () and changed.email is None and changed.birthday is None and changed.address is None
            )
            await pilot.press("enter")
            await settle(pilot)
            await activate(pilot, "delete")
            assert isinstance(app.screen, ConfirmScreen)
            assert any(contact.id in str(widget.content) for widget in app.screen.query(Static))
            await pilot.press("enter")
            assert assistant.contact(contact.id) == changed
            await activate(pilot, "delete")
            await pilot.press("escape")
            assert assistant.contact(contact.id) == changed
            await activate(pilot, "delete")
            await pilot.press("tab", "enter")
            await settle(pilot)
            assert assistant.contacts() == [] and isinstance(app.screen, RecordsScreen)

    run(journey)


def test_note_multiline_editor_keys_unchanged_expanded_tags_and_lossless_body(assistant: Assistant) -> None:
    raw = "\r\nA\rB\nC\vD\fE\x1cF\x1dG\x1eH\x85I\u2028J\u2029"
    note = assistant.add_note("Нотатка", raw, ("ß" * 40,))
    app = app_for(assistant)

    async def journey() -> None:
        async with app.run_test(size=(80, 24)) as pilot:
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
            await replace(pilot, "title", "ae dq")
            await pilot.press("left", "X")
            await pilot.press("ctrl+s")
            await settle(pilot)
            assert assistant.note(note.id).body == raw and assistant.note(note.id).tags == ("ss" * 40,)
            await pilot.press("enter")
            await settle(pilot)
            await pilot.press("enter")
            await replace(pilot, "body", "Україна")
            await pilot.press("end", "enter", *"Другий", "left", "right", "up", "down")
            assert isinstance(app.screen, FormScreen)
            form = app.screen
            assert form.query_one("#body", TextArea).text == "Україна\nДругий"
            await pilot.press("tab")
            assert app.focused is form.query_one("#tags")
            await replace(pilot, "tags", "Робота\n робота \nдім,сад")
            await pilot.press("ctrl+s")
            await settle(pilot)
            current = assistant.note(note.id)
            assert current.body == "Україна\r\nДругий" and current.tags == ("дім,сад", "робота")
            reopened = Assistant(Store(assistant.store.path.parent, date(2026, 10, 24)), lambda: date(2026, 10, 24))
            assert reopened.note(note.id) == current

    run(journey)


@pytest.mark.parametrize("raw", ["\r\nA\rB\nC\u2028", "a\x85", "a\u2029", "repeat\r\nrepeat\nrepeat\r"])
def test_body_projection_exact_and_deterministic(raw: str) -> None:
    projection = BodyProjection.from_raw(raw)
    assert projection.restore(projection.canonical) == raw
    assert projection.restore("X" + projection.canonical) == "X" + raw
    assert projection.restore(projection.canonical + "\n") == raw + "\n"
    assert projection.restore("") == ""


@pytest.mark.parametrize("key", ["escape", "ctrl+q", "ctrl+c"])
def test_dirty_safe_defaults_and_discard(assistant: Assistant, key: str) -> None:
    app = app_for(assistant)

    async def journey() -> None:
        async with app.run_test(size=(60, 20)) as pilot:
            await settle(pilot)
            await pilot.press("enter")
            await settle(pilot)
            await pilot.press("f2", *"Чернетка", key)
            assert isinstance(app.screen, ConfirmScreen)
            await pilot.press("enter")
            assert isinstance(app.screen, FormScreen) and app.screen.query_one("#name", Input).value == "Чернетка"
            await pilot.press(key, "escape")
            assert isinstance(app.screen, FormScreen)
            await pilot.press(key, "tab", "enter")
            await settle(pilot)
            assert assistant.contacts() == []
            assert isinstance(app.screen, RecordsScreen) if key == "escape" else app.return_value == 0

    run(journey)
