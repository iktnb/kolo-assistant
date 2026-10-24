import io
from pathlib import Path

import pytest
from pty_driver import Terminal, terminal_args

from kolo.interactive import Forms, run_interactive
from kolo.render import Renderer, make_console
from kolo.services import Assistant


def scripted(monkeypatch: pytest.MonkeyPatch, values: list[str | BaseException]) -> Renderer:
    sequence = iter(values)

    def read(prompt: str = "") -> str:
        value = next(sequence)
        if isinstance(value, BaseException):
            raise value
        return value

    monkeypatch.setattr("builtins.input", read)
    return Renderer(make_console(io.StringIO(), plain=True, width=60))


def test_in_process_full_menu_forms_and_preserved_expanded_tags(
    assistant: Assistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    render = scripted(
        monkeypatch,
        [
            "wrong",
            "1",
            "1",
            "3",
            "Олена",
            "1234567890",
            "Львів",
            "bad",
            "a@example.com",
            "",
            "0",
            "2",
            "3",
            "Ідеї",
            "",
            ".",
            "",
            "..крапка",
            "",
            ".",
            "ß" * 40,
            "",
            "0",
            "3",
            "bad",
            "0",
            "4",
            "0",
        ],
    )
    assert run_interactive(assistant, render) == 0
    contact = assistant.contacts()[0]
    note = assistant.notes()[0]
    assert contact.name == "Олена" and contact.phones == ("1234567890",) and contact.email == "a@example.com"
    assert note.body == "\n.крапка\n" and note.tags == ("ss" * 40,)
    text = render.console.file.getvalue() if isinstance(render.console.file, io.StringIO) else ""
    assert text.count("Ім’я *") == 1 and text.count("Email (name") == 2
    assert "Невідомий пункт" in text and "Ctrl+C" in text
    forms = Forms(scripted(monkeypatch, ["!clear", "!!clear", "", "", "!clear", ""]))
    forms.contact(assistant, contact)
    changed = assistant.contact(contact.id)
    assert changed.name == "!clear" and changed.phones == contact.phones and changed.email is None
    forms = Forms(scripted(monkeypatch, ["Нова назва", "", ""]))
    forms.note(assistant, note)
    assert assistant.note(note.id).tags == ("ss" * 40,)
    forms = Forms(scripted(monkeypatch, ["", "", "Робота", " робота ", ""]))
    forms.note(assistant, assistant.note(note.id))
    assert assistant.note(note.id).tags == ("робота",)


def test_in_process_submenu_actions_search_edit_and_delete(
    assistant: Assistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    contact = assistant.add_contact("Олена")
    note = assistant.add_note("Ідеї", "Думка", ("робота",))
    render = scripted(
        monkeypatch,
        [
            "1",
            "2",
            "ОЛЕНА",
            "4",
            contact.id,
            "5",
            contact.id,
            "",
            "",
            "",
            "",
            "",
            "6",
            contact.id,
            "ні",
            "6",
            contact.id,
            "так",
            "0",
            "2",
            "1",
            "т",
            "2",
            "думка",
            "робота",
            "",
            "4",
            note.id,
            "5",
            note.id,
            "",
            "т",
            "Новий текст",
            ".",
            "!clear",
            "6",
            note.id,
            "yes",
            "0",
            "0",
        ],
    )
    assert run_interactive(assistant, render) == 0
    assert assistant.contacts() == [] and assistant.notes() == []


@pytest.mark.parametrize("interruption", [KeyboardInterrupt(), EOFError()])
def test_in_process_cancel_no_draft(
    assistant: Assistant, monkeypatch: pytest.MonkeyPatch, interruption: BaseException
) -> None:
    values: list[str | BaseException] = ["1", "3", "Незбережене", interruption]
    if isinstance(interruption, KeyboardInterrupt):
        values.append("0")
    assert run_interactive(assistant, scripted(monkeypatch, values)) == 0
    assert assistant.contacts() == []


@pytest.mark.parametrize("width", [60, 80, 120])
def test_real_pty_dashboard_navigation_and_retry(tmp_path: Path, width: int) -> None:
    session = Terminal(terminal_args(tmp_path / "pty-data"), width=width)
    try:
        session.expect("Оберіть розділ")
        assert "Контактів: 0" in session.output and "Нотаток: 0" in session.output and "7 днів" in session.output
        session.send("невідоме\n")
        session.expect("Невідомий пункт")
        session.expect("Оберіть розділ")
        session.send("1\n")
        session.expect("Оберіть дію")
        session.send("3\n")
        session.expect("Ім’я *")
        session.send("Олена\n")
        session.expect("Телефони (")
        session.send("1234567890\n")
        session.expect("Адреса (")
        session.send("Львів\n")
        session.expect("Email (name")
        session.send("bad\n")
        session.expect("Email:")
        session.expect("Email (name")
        session.send("olena@example.com\n")
        session.expect("Дата народження (")
        session.send("\n")
        session.expect("Оберіть дію")
        assert "Збережено контакт c_" in session.output
        assert session.output.count("Ім’я *") == 1
        session.send("0\n")
        session.expect("Оберіть розділ")
        session.send("0\n")
        assert session.finish() == 0
    finally:
        session.close()


@pytest.mark.parametrize("stage", ["create", "edit", "multiline", "delete"])
def test_real_pty_ctrl_c_returns_dashboard_without_mutation(assistant: Assistant, stage: str) -> None:
    contact = assistant.add_contact("Залишити")
    note = assistant.add_note("Залишити", "Текст")
    session = Terminal(terminal_args(assistant.store.path.parent))
    try:
        session.expect("Оберіть розділ")
        session.send("2\n" if stage == "multiline" else "1\n")
        session.expect("Оберіть дію")
        session.send("6\n" if stage == "delete" else "5\n" if stage == "edit" else "3\n")
        if stage in {"edit", "delete"}:
            session.expect("Повний ID")
            session.send(contact.id + "\n")
        if stage == "delete":
            session.expect("Підтвердження")
        elif stage == "multiline":
            session.expect("Заголовок *")
            session.send("Незбережена\n")
            session.expect("Текст:")
            session.send("Незбережений текст\n")
        else:
            session.expect("Ім’я *")
            session.send("Незбережене\n")
            session.expect("Телефони (")
        session.send("\x03")
        session.expect("Дію скасовано")
        session.expect("Оберіть розділ")
        session.send("0\n")
        assert session.finish() == 0
        assert assistant.contacts() == [contact] and assistant.notes() == [note]
    finally:
        session.close()


@pytest.mark.parametrize("stage", ["menu", "form", "confirmation"])
def test_real_pty_eof_exits_zero(assistant: Assistant, stage: str) -> None:
    contact = assistant.add_contact("Залишити")
    session = Terminal(terminal_args(assistant.store.path.parent))
    try:
        session.expect("Оберіть розділ")
        if stage != "menu":
            session.send("1\n")
            session.expect("Оберіть дію")
            session.send("3\n" if stage == "form" else "6\n")
            session.expect("Ім’я *" if stage == "form" else "Повний ID")
            if stage == "confirmation":
                session.send(contact.id + "\n")
                session.expect("Підтвердження")
        session.send("\x04")
        session.expect("Сеанс завершено")
        assert session.finish() == 0 and assistant.contacts() == [contact]
    finally:
        session.close()
