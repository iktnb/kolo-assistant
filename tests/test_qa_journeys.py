import hashlib
import io
import os
import re
import sqlite3
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
from pty_driver import Terminal, terminal_args

from kolo import cli
from kolo.services import Assistant
from kolo.storage import Store

TODAY = date(2026, 10, 24)


def answer(session: Terminal, prompt: str, value: str) -> None:
    session.expect(prompt)
    session.send(value + "\n")


def reopen(directory: Path) -> Assistant:
    return Assistant(Store(directory, TODAY), lambda: TODAY)


@pytest.mark.parametrize("width", [60, 80, 120])
def test_qa_real_pty_note_complete_journey(tmp_path: Path, width: int) -> None:
    directory = tmp_path / "notes"
    session = Terminal(terminal_args(directory), width=width)
    try:
        answer(session, "Оберіть розділ", "4")
        session.expect("Підказки")
        answer(session, "Оберіть розділ", "3")
        answer(session, "Кількість днів", "0")
        session.expect("найближчі 0 днів")
        answer(session, "Оберіть розділ", "2")
        answer(session, "Оберіть дію", "3")
        title = "Подорож [bold] Україною " + "дорога " * 8
        answer(session, "Заголовок *", title)
        session.expect("Текст:")
        session.send(" \n.\n")
        session.expect("введіть непорожній текст")
        session.send("\n..початок\nРядок другий\n\n.\n")
        answer(session, "Тег", "Робота")
        answer(session, "Тег", " робота ")
        answer(session, "Тег", "дім,сад")
        answer(session, "Тег", "")
        session.expect("Збережено нотатку n_")
        session.expect("Оберіть дію")
        identifiers = re.findall(r"n_[0-9a-f]{12}", session.output)
        assert identifiers
        identifier = identifiers[0]
        original = reopen(directory).note(identifier)
        assert original.title == title.strip()
        assert original.body == "\n.початок\nРядок другий\n"
        assert original.tags == ("дім,сад", "робота")
        assert session.output.count("Заголовок *") == 1
        assert "[bold]" in session.output
        session.send("4\n")
        answer(session, "Повний ID", identifier)
        session.expect("Оберіть дію")
        assert identifier in session.output and ".початок" in session.output
        session.send("2\n")
        answer(session, "Пошук (", "ПОДОРОЖ")
        answer(session, "Точний тег", " РОБОТА ")
        answer(session, "Сортувати за тегами?", "т")
        session.expect("Оберіть дію")
        assert identifier in session.output[session.output.rfind("Нотатки · 1") :]
        session.send("2\n")
        answer(session, "Пошук (", "немає-збігу")
        answer(session, "Точний тег", "")
        answer(session, "Сортувати за тегами?", "")
        session.expect("Нічого не знайдено")
        session.expect("Оберіть дію")
        session.send("6\n")
        answer(session, "Повний ID", identifier)
        answer(session, "Підтвердження", "")
        session.expect("Видалення скасовано")
        session.expect("Оберіть дію")
        assert reopen(directory).note(identifier) == original
        session.send("5\n")
        answer(session, "Повний ID", identifier)
        answer(session, "Заголовок *", "")
        answer(session, "Змінити текст?", "так")
        session.expect("Текст:")
        session.send("..\nНовий текст\n.\n")
        answer(session, "Тег", "!clear")
        session.expect("Збережено нотатку")
        session.expect("Оберіть дію")
        edited = reopen(directory).note(identifier)
        assert edited.id == original.id and edited.title == original.title
        assert edited.body == ".\nНовий текст" and edited.tags == ()
        session.send("6\n")
        answer(session, "Повний ID", identifier)
        answer(session, "Підтвердження", " ТАК ")
        session.expect("Видалено нотатку")
        session.expect("Оберіть дію")
        session.send("1\n")
        answer(session, "Сортувати за тегами?", "")
        session.expect("Нотаток поки немає")
        session.expect("Оберіть дію")
        session.send("0\n")
        answer(session, "Оберіть розділ", "0")
        assert session.finish() == 0
        assert reopen(directory).notes() == []
        assert "\x1b" not in session.output
    finally:
        (tmp_path / f"note-journey-{width}.txt").write_text(session.output, encoding="utf-8")
        session.close()


@pytest.mark.parametrize("stage", ["body", "tags", "confirmation"])
@pytest.mark.parametrize("interruption", ["interrupt", "eof"])
def test_qa_real_pty_note_cancel_and_reopen(
    assistant: Assistant, stage: str, interruption: str, tmp_path: Path
) -> None:
    note = assistant.add_note("Збережена нотатка", "Попередній\nтекст", ("старий",))
    contact = assistant.add_contact("Збережений контакт")
    session = Terminal(terminal_args(assistant.store.path.parent))
    try:
        answer(session, "Оберіть розділ", "2")
        answer(session, "Оберіть дію", "6" if stage == "confirmation" else "5")
        answer(session, "Повний ID", note.id)
        if stage == "confirmation":
            session.expect("Підтвердження")
            assert note.id in session.output and note.title in session.output
        else:
            answer(session, "Заголовок *", "Чернетка")
            answer(session, "Змінити текст?", "так" if stage == "body" else "")
            if stage == "body":
                session.expect("Текст:")
                session.send("Чернетка тексту\n")
            else:
                answer(session, "Тег", "новий")
                session.expect("\r\nТег\r\n> ")
        session.send("\x03" if interruption == "interrupt" else "\x04")
        if interruption == "interrupt":
            session.expect("Дію скасовано")
            answer(session, "Оберіть розділ", "0")
        else:
            session.expect("Сеанс завершено")
        assert session.finish() == 0
        restored = reopen(assistant.store.path.parent)
        assert restored.notes() == [note] and restored.contacts() == [contact]
    finally:
        (tmp_path / f"note-cancel-{stage}-{interruption}.txt").write_text(session.output, encoding="utf-8")
        session.close()


@pytest.mark.parametrize(
    "command", [[], ["demo"], ["contacts", "delete", "c_000000000001"], ["notes", "delete", "n_000000000001"]]
)
def test_qa_rejection_never_waits_for_open_stdin(tmp_path: Path, command: list[str]) -> None:
    directory = tmp_path / "not-opened"
    process = subprocess.Popen(
        [sys.executable, "-m", "kolo", "--data-dir", str(directory), *command],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        assert process.wait(timeout=5) == 2
        output, errors = process.communicate(timeout=5)
        assert output == b"" and "Помилка вводу" in errors.decode("utf-8")
        assert not directory.exists()
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=5)


@pytest.mark.parametrize("entity", ["contacts", "notes"])
def test_qa_real_commit_failure_cli_has_no_success_and_fresh_reopen(
    assistant: Assistant, monkeypatch: pytest.MonkeyPatch, entity: str
) -> None:
    contact = assistant.add_contact("Попереднє ім’я", ("1234567890",), "Адреса", "a@example.com")
    note = assistant.add_note("Попередній заголовок", "Текст", ("старий",))
    before = hashlib.sha256(assistant.store.path.read_bytes()).hexdigest()
    original_connect = Store._connect
    commits: list[str] = []

    class FailedCommit(sqlite3.Connection):
        def commit(self) -> None:
            commits.append("failed")
            raise sqlite3.OperationalError("private synthetic commit failure")

    def connect(store: Store, mode: str) -> sqlite3.Connection:
        if mode == "rw":
            connection = sqlite3.connect(store.path, factory=FailedCommit, isolation_level=None)
            connection.execute("PRAGMA foreign_keys=ON")
            return connection
        return original_connect(store, mode)

    output, errors = io.StringIO(), io.StringIO()
    with monkeypatch.context() as patch:
        patch.setattr(Store, "_connect", connect)
        patch.setattr(sys, "stdout", output)
        patch.setattr(sys, "stderr", errors)
        fields = (
            [contact.id, "--name", "Не прийнято", "--phone", "12345678901"]
            if entity == "contacts"
            else [note.id, "--title", "Не прийнято", "--tag", "новий"]
        )
        result = cli.main(["--data-dir", str(assistant.store.path.parent), entity, "edit", *fields])
    assert result == 1 and commits == ["failed"]
    assert output.getvalue() == "" and "Збережено" not in errors.getvalue()
    assert "Сховище" in errors.getvalue() and str(assistant.store.path) in errors.getvalue()
    assert "private synthetic" not in errors.getvalue() and "Не прийнято" not in errors.getvalue()
    assert hashlib.sha256(assistant.store.path.read_bytes()).hexdigest() == before
    restored = reopen(assistant.store.path.parent)
    assert restored.contacts() == [contact] and restored.notes() == [note]


@pytest.mark.parametrize("xdg", ["absolute", "relative", "empty", "unset"])
def test_qa_actual_default_paths_with_fake_home_only(tmp_path: Path, xdg: str) -> None:
    home = tmp_path / "fake-home"
    home.mkdir()
    sentinel = home / "sentinel"
    sentinel.write_bytes(b"unchanged synthetic home")
    environment = os.environ.copy()
    environment["HOME"] = str(home)
    environment.pop("XDG_DATA_HOME", None)
    if xdg != "unset":
        environment["XDG_DATA_HOME"] = (
            str(tmp_path / "xdg") if xdg == "absolute" else "relative-xdg" if xdg == "relative" else ""
        )
    expected = tmp_path / "xdg" / "kolo" if xdg == "absolute" else home / ".local" / "share" / "kolo"
    command = [sys.executable, "-m", "kolo"]
    created = subprocess.run(
        [*command, "contacts", "add", "--name", "Вигадана людина"],
        capture_output=True,
        text=True,
        timeout=10,
        env=environment,
        cwd=tmp_path,
    )
    assert created.returncode == 0 and "Збережено контакт" in created.stdout and created.stderr == ""
    assert (expected / "kolo.sqlite3").exists()
    match = re.search(r"c_[0-9a-f]{12}", created.stdout)
    assert match is not None
    shown = subprocess.run(
        [*command, "contacts", "show", match.group()],
        capture_output=True,
        text=True,
        timeout=10,
        env=environment,
        cwd=home,
    )
    assert shown.returncode == 0 and "Вигадана людина" in shown.stdout and match.group() in shown.stdout
    assert sentinel.read_bytes() == b"unchanged synthetic home"
    assert not (tmp_path / "relative-xdg").exists()
    assert not (home / "relative-xdg").exists()
    assert not (home / ".local" / "share" / "kolo").exists() if xdg == "absolute" else not (tmp_path / "xdg").exists()


def test_qa_untrusted_path_and_error_are_literal_and_private(tmp_path: Path) -> None:
    directory = tmp_path / "[bold]path\nline\ttab\x1b]0;title\x07\u202e"
    directory.mkdir()
    database = directory / "kolo.sqlite3"
    database.write_bytes(b"broken")
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    result = subprocess.run(
        [sys.executable, "-m", "kolo", "--data-dir", str(directory), "notes", "list"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 1 and result.stdout == ""
    assert "[bold]" in result.stderr and "\\x0a" in result.stderr and "\\x09" in result.stderr
    assert "\\x1b" in result.stderr and "\\x07" in result.stderr and "\\u202e" in result.stderr
    assert all(character not in result.stderr for character in ("\x1b", "\x07", "\t", "\u202e"))
    assert "Traceback" not in result.stderr and hashlib.sha256(database.read_bytes()).hexdigest() == before
