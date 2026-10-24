import io
import re
from datetime import date
from pathlib import Path

import pytest
from pty_driver import Terminal

from kolo import cli, demo
from kolo.render import Renderer, make_console
from kolo.services import Assistant


@pytest.mark.parametrize("today", [date(2028, 2, 29), date(1996, 2, 29), date(2026, 10, 24)])
def test_demo_leap_safe_and_reseeded(today: date, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths: list[Path] = []

    def inspect(assistant: Assistant, render: Renderer) -> int:
        paths.append(assistant.store.path.parent)
        assert len(assistant.contacts()) == 3 and len(assistant.notes()) == 2
        birthday = assistant.birthdays(0)[0]
        assert birthday.days_until == 0 and birthday.anniversary == today
        assert birthday.contact.birthday == today.replace(year=min(2000, today.year))
        assistant.add_note("Тільки зараз", "Текст")
        return 0

    monkeypatch.setattr(demo, "run_interactive", inspect)
    render = Renderer(make_console(io.StringIO(), plain=True))
    for _ in range(2):
        assert demo.run_demo(render, lambda: today, line_mode=True) == 0
    assert paths[0] != paths[1] and all(not path.exists() for path in paths)
    assert not (Path.home() / "data").exists()


def test_demo_rejects_explicit_directory_before_filesystem(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> Path:
        raise AssertionError("Must not resolve personal data")

    monkeypatch.setattr(cli, "data_directory", forbidden)
    monkeypatch.setattr(Path, "resolve", forbidden)
    assert cli.main(["--data-dir", "never", "demo"]) == 2
    assert cli.main(["demo"]) == 2
    assert cli.main([]) == 2


def test_real_pty_demo_isolated_cleanup_and_fresh_start(tmp_path: Path) -> None:
    home = tmp_path / "personal"
    home.mkdir()
    sentinel = home / "sentinel"
    sentinel.write_bytes(b"personal unchanged")
    environment = {"HOME": str(home), "XDG_DATA_HOME": str(home / "xdg")}
    paths: list[Path] = []
    for index in range(2):
        session = Terminal(["--plain", "--line-mode", "demo"], width=60, environment=environment)
        try:
            session.expect("Оберіть розділ")
            assert "Демонстрація" in session.output and "Контактів: 3" in session.output
            match = re.search(r"/tmp/kolo-demo-[a-z0-9_]+", session.output)
            assert match is not None
            paths.append(Path(match.group()))
            if index == 0:
                session.send("2\n")
                session.expect("Оберіть дію")
                session.send("3\n")
                session.expect("Заголовок *")
                session.send("Лише в demo\n")
                session.expect("Текст:")
                session.send("текст\n.\n\n")
                session.expect("Оберіть дію")
                session.send("0\n")
                session.expect("Оберіть розділ")
                assert "Нотаток: 3" in session.output
            else:
                assert "Нотаток: 2" in session.output
            session.send("\x04")
            session.expect("Сеанс завершено")
            assert session.finish() == 0
        finally:
            session.close()
    assert all(not path.exists() for path in paths) and paths[0] != paths[1]
    assert sentinel.read_bytes() == b"personal unchanged"
    assert sorted(path.name for path in home.iterdir()) == ["sentinel"]
