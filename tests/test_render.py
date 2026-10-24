import io
from datetime import date

import pytest

from kolo.birthdays import Birthday
from kolo.models import Contact, Note
from kolo.render import Renderer, make_console, safe
from kolo.services import Assistant


@pytest.mark.parametrize("width", [60, 80, 120])
def test_responsive_literal_rendering_full_details(width: int) -> None:
    output = io.StringIO()
    render = Renderer(make_console(output, plain=True, width=width))
    dangerous = "[bold]Людина[/bold]\x1b]0;danger\x07\u202e\nновий"
    contact = Contact(
        "c_000000000001",
        dangerous,
        ("+1234567890", "12345678901"),
        "Довга адреса " * 25,
        "name@example.com",
        date(2000, 1, 1),
    )
    note = Note("n_000000000001", "Нотатка [red]" * 6, "\nРядок\tДругий\n[bold]\x1b[31m\x9b\u200d", ("тег",))
    render.contacts([contact])
    render.notes([note])
    render.details(contact)
    render.details(note)
    render.dashboard(1, 1, [Birthday(contact, date(2026, 1, 1), 0)])
    render.contacts([], query="Немає [bold]")
    render.notes([], query="Немає")
    render.contacts([])
    render.notes([])
    render.birthdays([])
    text = output.getvalue()
    assert contact.id in text and note.id in text
    assert "[bold]" in text and "\\x1b" in text and "\\u202e" in text
    assert "\x1b" not in text and "\x07" not in text and "\u202e" not in text
    assert "+1234567890" in text and "12345678901" in text and "name@example.com" in text
    assert "Не вказано" not in text
    assert "Нічого не знайдено" in text and "поки немає" in text
    assert all(len(line) <= width for line in text.splitlines())


def test_control_policy_no_color_and_missing_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    assert safe("a\n\tb\x1b\u200e").plain == "a\\x0a\\x09b\\x1b\\u200e"
    assert safe("a\n\tb", multiline=True).plain == "a\n    b"

    class Terminal(io.StringIO):
        def isatty(self) -> bool:
            return True

    for plain, no_color in ((True, False), (False, True)):
        if no_color:
            monkeypatch.setenv("NO_COLOR", "")
        stream = Terminal()
        render = Renderer(make_console(stream, plain=plain))
        render.details(Contact("c_000000000001", "Ім’я"))
        render.message("Помилка", error=True)
        assert "\x1b" not in stream.getvalue() and "Не вказано" in stream.getvalue()


@pytest.mark.parametrize("width", [60, 80, 120])
def test_single_line_fields_heading_and_current_values_escape_lf_tab(
    assistant: Assistant, monkeypatch: pytest.MonkeyPatch, width: int
) -> None:
    from kolo.interactive import Forms

    name = "Alpha\nInjected\tTab"
    title = "Title\nInjected\tTab"
    address = "Address\nInjected\tTab"
    tag = "tag\nline\ttab"
    body = "Body\nPreserved\tTab\n"
    contact = assistant.add_contact(name, ("1234567890", "12345678901"), address)
    note = assistant.add_note(title, body, (tag,))
    assert assistant.contact(contact.id).name == name and assistant.contact(contact.id).address == address
    assert assistant.note(note.id).title == title and assistant.note(note.id).tags == (tag,)
    assert assistant.note(note.id).body == body
    output = io.StringIO()
    render = Renderer(make_console(output, plain=True, width=width))
    render.details(assistant.contact(contact.id))
    render.details(assistant.note(note.id))
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    forms = Forms(render)
    for label, value in (("Ім’я", name), ("Заголовок", title), ("Адреса", address), ("Теги", tag)):
        assert forms.field(label, lambda raw: raw, value, edit=True, display=value) == value
    render.heading("Header\nSecond\tTab", "Subtitle\nSecond\tTab")
    render.heading("Program", "First\nSecond", multiline=True)
    text = output.getvalue()
    for value in (name, title, address, tag, "Header\nSecond\tTab", "Subtitle\nSecond\tTab"):
        assert value not in text
        assert safe(value).plain in text
    assert "Body\nPreserved    Tab\n" in text
    assert "1234567890\n12345678901" in text
    assert "First" in text and "Second" in text and "First\\x0aSecond" not in text
