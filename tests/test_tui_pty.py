import re
from pathlib import Path

import pytest
from pty_driver import Terminal

from kolo.services import Assistant


@pytest.mark.parametrize("size", [(120, 36), (80, 24), (60, 20)])
def test_default_fullscreen_pty_keys_resize_restore(tmp_path: Path, size: tuple[int, int]) -> None:
    session = Terminal(["--data-dir", str(tmp_path / "data"), "--plain"], width=size[0], height=size[1])
    try:
        session.expect("Контактів: 0")
        session.send("\r")
        session.expect("Пошук")
        session.expect("Контактів поки немає")
        session.resize(60, 20)
        session.drain()
        session.send("\x1b")
        session.expect("Контактів: 0")
        session.send("\x11")
        session.expect("Вийти з Кола?")
        session.send("\t\r")
        session.drain()
        assert session.finish() == 0 and session.restored
        assert "\x1b[?1049h" in session.output and "\x1b[?1049l" in session.output
        colors = set(range(30, 39)) | set(range(40, 49)) | set(range(90, 98)) | set(range(100, 108))
        for parameters in re.findall(r"\x1b\[([0-9;]*)m", session.output):
            assert not ({int(value) for value in parameters.split(";") if value} & colors)
    finally:
        session.close()


def test_default_demo_pty_cleanup_and_reseed(tmp_path: Path) -> None:
    home, temporary = tmp_path / "demo-home", tmp_path / "temp"
    home.mkdir()
    temporary.mkdir()
    sentinel = home / "sentinel"
    sentinel.write_bytes(b"unchanged")
    environment = {"HOME": str(home), "XDG_DATA_HOME": str(home / "data"), "TMPDIR": str(temporary)}
    for _ in range(2):
        session = Terminal(["--plain", "demo"], width=80, height=24, environment=environment)
        try:
            session.expect("ДЕМОНСТРАЦІЯ")
            session.expect("Контактів: 3")
            assert "Нотаток: 2" in session.output and list(temporary.glob("kolo-demo-*"))
            session.send("\x03")
            session.expect("Вийти з Кола?")
            session.send("\t\r")
            session.drain()
            assert session.finish() == 0 and session.restored
        finally:
            session.close()
        assert list(temporary.iterdir()) == []
    assert sentinel.read_bytes() == b"unchanged" and list(home.iterdir()) == [sentinel]


def test_editor_never_emits_untrusted_terminal_control(assistant: Assistant) -> None:
    note = assistant.add_note("[bold]Назва\u202e", "unsafe\x1b]0;ATTACK\x07\u202e\nТекст")
    session = Terminal(["--data-dir", str(assistant.store.path.parent), "--plain"], width=80, height=24)
    try:
        session.expect("Контактів: 0")
        session.send("\x1b[B\r")
        session.expect("Пошук у заголовку")
        session.expect(note.id)
        session.send("\r")
        session.expect(f"ID  {note.id}")
        session.expect("unsafe\\x1b")
        session.send("\r")
        session.expect("Заголовок *")
        session.send("\t")
        session.drain(0.2)
        assert "\x1b]0;ATTACK\x07" not in session.output
        assert "\x1b]0;ATTACK" not in session.output
        assert "\u202e" not in session.output
        assert "[bold]" in session.output
        session.send("\x11")
        session.expect("Вийти з Кола?")
        session.send("\t\r")
        session.drain()
        assert session.finish() == 0 and session.restored
        assert assistant.note(note.id) == note
    finally:
        session.close()
