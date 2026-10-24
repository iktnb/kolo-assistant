import io
import re
from pathlib import Path

import pytest
from conftest import Runner

from kolo import cli
from kolo.services import Assistant


def identifier(output: str) -> str:
    match = re.search(r"[cn]_[0-9a-f]{12}", output)
    assert match is not None, output
    return match.group()


def test_contact_lifecycle_in_new_process_and_different_cwd(runner: Runner, tmp_path: Path) -> None:
    result = runner(
        "contacts",
        "add",
        "--name",
        "Олена",
        "--phone",
        "+38 (067) 123-45-67",
        "--phone",
        "1234567890",
        "--address",
        "Львів",
        "--email",
        "olena@example.com",
        "--birthday",
        "2000-02-29",
    )
    assert result.returncode == 0 and result.stderr == ""
    contact_id = identifier(result.stdout)
    shown = runner("contacts", "show", contact_id, cwd=tmp_path)
    assert shown.returncode == 0
    for text in ("Олена", "+380671234567", "1234567890", "Львів", "olena@example.com", "2000-02-29", contact_id):
        assert text in shown.stdout
    assert contact_id in runner("contacts", "list", "--search", "ОЛЕНА").stdout
    assert "Нічого не знайдено" in runner("contacts", "list", "--search", "немає").stdout
    assert runner("contacts", "edit", contact_id, "--clear-email", "--clear-birthday").returncode == 0
    assert "olena@example.com" not in runner("contacts", "show", contact_id).stdout
    assert runner("contacts", "delete", contact_id).returncode == 2
    assert contact_id in runner("contacts", "list").stdout
    assert runner("contacts", "delete", contact_id, "--yes").returncode == 0
    assert runner("contacts", "show", contact_id).returncode == 2
    assert "поки немає" in runner("contacts", "list").stdout
    assert (runner.home / "sentinel").read_text() == "unchanged"
    assert not (runner.home / "xdg").exists()


def test_note_lifecycle_body_sources_and_tags(runner: Runner, tmp_path: Path) -> None:
    body_file = tmp_path / "body.txt"
    body_file.write_text("\nПерший рядок\nДругий рядок\n", encoding="utf-8")
    created = runner(
        "notes", "add", "--title", "Думки", "--body-file", str(body_file), "--tag", "Робота", "--tag", " робота "
    )
    note_id = identifier(created.stdout)
    assert created.returncode == 0
    detail = runner("notes", "show", note_id)
    assert "Перший рядок\nДругий рядок" in detail.stdout and "робота" in detail.stdout
    assert note_id in runner("notes", "list", "--search", "РЯДОК", "--tag", " РОБОТА ", "--sort", "tags").stdout
    assert runner("notes", "edit", note_id, "--body-file", "-", "--clear-tags", stdin="Новий\nтекст\n").returncode == 0
    assert "Новий\nтекст" in runner("notes", "show", note_id).stdout
    assert runner("notes", "delete", note_id).returncode == 2
    assert runner("notes", "delete", note_id, "--yes").returncode == 0
    bad_utf8 = tmp_path / "bad.txt"
    bad_utf8.write_bytes(b"\xff")
    for path in (str(bad_utf8), str(tmp_path / "missing")):
        result = runner("notes", "add", "--title", "Не буде", "--body-file", path)
        assert result.returncode == 2 and "UTF-8" in result.stderr and result.stdout == ""
    assert "поки немає" in runner("notes", "list").stdout


@pytest.mark.parametrize(
    "args",
    [
        (),
        ("contacts",),
        ("bad",),
        ("contacts", "add"),
        ("contacts", "edit", "c_000000000001"),
        ("contacts", "edit", "c_000000000001", "--email", "a@b.co", "--clear-email"),
        ("notes", "add", "--title", "Т"),
        ("notes", "list", "--sort", "unknown"),
        ("birthdays", "--days", "-1"),
        ("birthdays", "--days", "367"),
        ("birthdays", "--days", "1.5"),
        ("birthdays", "--days", "x"),
    ],
)
def test_invalid_arguments_no_prompt_no_traceback(runner: Runner, args: tuple[str, ...]) -> None:
    result = runner(*args)
    assert result.returncode == 2 and "Помилка вводу" in result.stderr and result.stdout == ""
    assert "Traceback" not in result.stderr and "\x1b" not in result.stderr


@pytest.mark.parametrize("group", ["contacts", "notes"])
@pytest.mark.parametrize("action", ["show", "edit", "delete"])
def test_missing_exact_ids(runner: Runner, group: str, action: str) -> None:
    record_id = "c_000000000001" if group == "contacts" else "n_000000000001"
    options = (
        ("--yes",)
        if action == "delete"
        else ("--name", "Т")
        if group == "contacts" and action == "edit"
        else ("--title", "Т")
        if action == "edit"
        else ()
    )
    result = runner(group, action, record_id, *options)
    assert result.returncode == 2 and "не знайдено" in result.stderr


def test_help_all_levels_no_files_or_timezone(runner: Runner) -> None:
    commands = [(), ("contacts",), ("notes",), ("birthdays",), ("demo",)]
    commands += [
        (group, action) for group in ("contacts", "notes") for action in ("list", "show", "add", "edit", "delete")
    ]
    for command in commands:
        result = runner(*command, "--help", extra_env={"KOLO_TIMEZONE": "Invalid/Zone"})
        assert result.returncode == 0 and "Використання" in result.stdout and "Приклад" in result.stdout
        assert "usage:" not in result.stdout and result.stderr == "" and "\x1b" not in result.stdout
        assert result.stdout.count("Використання: ") == 1
        assert result.stdout.startswith(f"Використання: {' '.join(('kolo', *command))} ")
    assert runner("--version").returncode == 0
    assert not runner.directory.exists()


def test_corrupt_path_error_and_invalid_timezone_are_safe(runner: Runner) -> None:
    runner.directory.mkdir()
    database = runner.directory / "kolo.sqlite3"
    database.write_bytes(b"broken")
    result = runner("contacts", "list")
    assert result.returncode == 1 and str(database) in result.stderr and "Traceback" not in result.stderr
    assert database.read_bytes() == b"broken"
    other = Runner(runner.directory / "unused", runner.home)
    invalid = other("contacts", "list", extra_env={"KOLO_TIMEZONE": "Invalid/Zone"})
    assert invalid.returncode == 2 and "KOLO_TIMEZONE" in invalid.stderr and not other.directory.exists()


def test_in_process_command_routes_and_interrupt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directory = tmp_path / "in-process"
    stdout, stderr = io.StringIO(), io.StringIO()
    monkeypatch.setattr("sys.stdout", stdout)
    monkeypatch.setattr("sys.stderr", stderr)

    def run(*args: str) -> int:
        return cli.main(["--data-dir", str(directory), "--plain", *args])

    assert run("contacts", "add", "--name", "Т", "--phone", "1234567890") == 0
    contact_id = identifier(stdout.getvalue())
    assert run("contacts", "edit", contact_id, "--phone", "12345678901", "--address", "Нова") == 0
    assert run("contacts", "show", contact_id) == 0
    assert run("contacts", "list") == 0
    assert run("birthdays", "--days", "0") == 0
    assert run("notes", "add", "--title", "Т", "--body", "Текст", "--tag", "а") == 0
    note_id = identifier(stdout.getvalue().split("Збережено нотатку")[-1])
    assert run("notes", "edit", note_id, "--body", "Інше", "--tag", "Б") == 0
    assert run("notes", "show", note_id) == 0
    assert run("notes", "list", "--tag", "Б", "--sort", "tags") == 0
    assert run("notes", "delete", note_id, "--yes") == 0
    assert run("contacts", "delete", contact_id, "--yes") == 0

    def interrupt(*args: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "execute", interrupt)
    assert run("contacts", "list") == 130
    assert "\x1b" not in stdout.getvalue() + stderr.getvalue()


def test_expected_commit_error_has_no_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from kolo.errors import StorageError

    def fail(*args: object, **kwargs: object) -> None:
        raise StorageError(f"Сховище {tmp_path}: не вдалося зберегти дані.")

    monkeypatch.setattr(Assistant, "add_note", fail)
    output, errors = io.StringIO(), io.StringIO()
    monkeypatch.setattr("sys.stdout", output)
    monkeypatch.setattr("sys.stderr", errors)
    assert cli.main(["--data-dir", str(tmp_path / "data"), "notes", "add", "--title", "Т", "--body", "Текст"]) == 1
    assert output.getvalue() == "" and "Збережено" not in errors.getvalue() and str(tmp_path) in errors.getvalue()


def test_run_script_from_different_cwd_preserves_arguments(tmp_path: Path) -> None:
    import subprocess

    script = Path(__file__).resolve().parents[1] / "run.sh"
    result = subprocess.run(
        [str(script), "--data-dir", str(tmp_path / "with spaces"), "contacts", "add", "--name", "Ім’я з пробілом"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=15,
    )
    assert result.returncode == 0 and "Збережено контакт" in result.stdout
    shown = subprocess.run(
        [str(script), "--data-dir", str(tmp_path / "with spaces"), "contacts", "list"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=15,
    )
    assert shown.returncode == 0 and "Ім’я з пробілом" in shown.stdout


def test_trigger_schema_refusal_prevents_false_success(runner: Runner) -> None:
    import hashlib
    import sqlite3

    assert runner("notes", "list").returncode == 0
    database = runner.directory / "kolo.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TRIGGER sqliteXdiscard AFTER INSERT ON notes BEGIN DELETE FROM notes WHERE id=NEW.id; END"
        )
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    result = runner("notes", "add", "--title", "Тест", "--body", "Текст")
    assert result.returncode == 1 and result.stdout == "" and "Сховище" in result.stderr
    assert "Збережено" not in result.stderr and hashlib.sha256(database.read_bytes()).hexdigest() == before
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT * FROM notes").fetchall() == []


@pytest.mark.parametrize("action", ["add", "edit"])
@pytest.mark.parametrize("payload", [b"\xff", b"\xed\xa0\x80", b"\xe2\x82"])
def test_binary_stdin_rejects_malformed_utf8_before_storage(runner: Runner, action: str, payload: bytes) -> None:
    import hashlib
    import subprocess
    import sys

    database = runner.directory / "kolo.sqlite3"
    if action == "edit":
        note_id = identifier(runner("notes", "add", "--title", "Оригінал", "--body", "Залишити").stdout)
        before = hashlib.sha256(database.read_bytes()).hexdigest()
        command = ["notes", "edit", note_id, "--title", "Не прийнято", "--body-file", "-"]
    else:
        before = None
        command = ["notes", "add", "--title", "Не прийнято", "--body-file", "-"]
    result = subprocess.run(
        [sys.executable, "-m", "kolo", "--data-dir", str(runner.directory), *command],
        input=payload,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 2 and result.stdout == b"" and "UTF-8" in result.stderr.decode("utf-8")
    assert b"Traceback" not in result.stderr
    if before is None:
        assert not runner.directory.exists()
    else:
        assert hashlib.sha256(database.read_bytes()).hexdigest() == before
        assert "Залишити" in runner("notes", "show", note_id).stdout


def test_binary_stdin_preserves_utf8_and_exact_newlines_independent_of_text_decoder(runner: Runner) -> None:
    import sqlite3
    import subprocess
    import sys

    script = (
        "import sys; from kolo.cli import main; "
        "sys.stdin.reconfigure(encoding='latin-1', errors='replace', newline=None); "
        "raise SystemExit(main(sys.argv[1:]))"
    )
    database = runner.directory / "kolo.sqlite3"
    first = "\nУкраїна\r\nДругий\rТретій\tрядок\n"
    second = "\r\nІнший\rтекст\n"
    created = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            "--data-dir",
            str(runner.directory),
            "notes",
            "add",
            "--title",
            "Текст",
            "--body-file",
            "-",
        ],
        input=first.encode("utf-8"),
        capture_output=True,
        timeout=10,
    )
    assert created.returncode == 0, created.stderr
    note_id = identifier(created.stdout.decode("utf-8"))
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT body FROM notes WHERE id=?", (note_id,)).fetchone() == (first,)
    edited = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            "--data-dir",
            str(runner.directory),
            "notes",
            "edit",
            note_id,
            "--body-file",
            "-",
        ],
        input=second.encode("utf-8"),
        capture_output=True,
        timeout=10,
    )
    assert edited.returncode == 0, edited.stderr
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT body FROM notes WHERE id=?", (note_id,)).fetchone() == (second,)


def test_predecoded_stdin_still_enforces_strict_utf8(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output, errors = io.StringIO(), io.StringIO()
    monkeypatch.setattr("sys.stdout", output)
    monkeypatch.setattr("sys.stderr", errors)
    monkeypatch.setattr("sys.stdin", io.StringIO("\udcff"))
    directory = tmp_path / "predecoded"
    args = ["--data-dir", str(directory), "notes", "add", "--title", "Текст", "--body-file", "-"]
    assert cli.main(args) == 2 and "UTF-8" in errors.getvalue() and not directory.exists()
    monkeypatch.setattr("sys.stdin", io.StringIO("\nУкраїна\r\nТекст\n"))
    assert cli.main(args) == 0


@pytest.mark.parametrize(
    "command, expected_prog",
    [
        (("--unknown",), "kolo"),
        (("contacts",), "kolo contacts"),
        (("contacts", "add"), "kolo contacts add"),
        (("notes", "add"), "kolo notes add"),
        (("birthdays", "--days", "oops"), "kolo birthdays"),
        (("demo", "--unknown"), "kolo"),
    ],
)
def test_parser_error_offers_clean_copyable_help(runner: Runner, command: tuple[str, ...], expected_prog: str) -> None:
    result = runner(*command)
    assert result.returncode == 2 and result.stdout == ""
    assert "Використання:" not in result.stderr
    assert f"{expected_prog} --help." in result.stderr
    help_command = re.search(r": (kolo(?: [a-z]+)*) --help\.", result.stderr)
    assert help_command is not None
    recovered = runner(*help_command.group(1).split()[1:], "--help")
    assert recovered.returncode == 0 and recovered.stdout.count("Використання: ") == 1
