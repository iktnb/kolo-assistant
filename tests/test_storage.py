import hashlib
import os
import sqlite3
import stat
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from kolo.errors import StorageError
from kolo.models import Contact, ContactPatch, NotePatch
from kolo.services import Assistant
from kolo.storage import APPLICATION_ID, Store, data_directory

TODAY = date(2026, 10, 24)


def fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_roundtrip_permissions_and_cascade(assistant: Assistant) -> None:
    contact = assistant.add_contact("Ім’я", ("+1234567890", "12345678901"), "Адреса", "a@example.com", "2000-02-29")
    note = assistant.add_note("Нотатка", "\nУкраїна\n", ("ß" * 40, "а"))
    reopened = Assistant(Store(assistant.store.path.parent, TODAY), lambda: TODAY)
    assert reopened.contact(contact.id) == contact and reopened.note(note.id) == note
    assert stat.S_IMODE(assistant.store.path.stat().st_mode) == 0o600
    assert stat.S_IMODE(assistant.store.path.parent.stat().st_mode) == 0o700
    reopened.delete_contact(contact.id)
    reopened.delete_note(note.id)
    with reopened.store.connection() as connection:
        assert connection.execute("SELECT count(*) FROM contact_phones").fetchone() == (0,)
        assert connection.execute("SELECT count(*) FROM note_tags").fetchone() == (0,)


def test_path_resolution_and_existing_permissions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert data_directory("relative") == tmp_path / "relative"
    assert data_directory("~/other") == Path.home() / "other"
    monkeypatch.setenv("XDG_DATA_HOME", "relative-xdg")
    assert data_directory() == Path.home() / ".local/share/kolo"
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    assert data_directory() == tmp_path / "xdg/kolo"
    with pytest.raises(Exception, match="непорожній"):
        data_directory(" ")
    tmp_path.chmod(0o755)
    Store(tmp_path, TODAY)
    assert stat.S_IMODE(tmp_path.stat().st_mode) == 0o755


@pytest.mark.parametrize(
    "kind", ["zero", "garbage", "application", "version", "schema", "foreign", "domain", "position", "digits"]
)
def test_unknown_corrupt_and_invalid_database_is_unchanged(tmp_path: Path, kind: str) -> None:
    store = Store(tmp_path, TODAY)
    app = Assistant(store, lambda: TODAY)
    contact = app.add_contact("Олена", ("1234567890",))
    if kind in {"zero", "garbage"}:
        store.path.write_bytes(b"" if kind == "zero" else b"This is not a database")
    else:
        with sqlite3.connect(store.path) as connection:
            statements = {
                "application": "PRAGMA application_id=1",
                "version": "PRAGMA user_version=2",
                "schema": "ALTER TABLE contacts ADD COLUMN surprise TEXT",
                "foreign": "INSERT INTO note_tags VALUES('n_000000000001','orphan')",
                "domain": "UPDATE contacts SET name=''",
                "position": "UPDATE contact_phones SET position=2",
                "digits": "UPDATE contact_phones SET digits='wrong'",
            }
            connection.execute(statements[kind])
    before = fingerprint(store.path)
    with pytest.raises(StorageError, match=str(store.path)):
        Store(tmp_path, TODAY)
    assert fingerprint(store.path) == before
    assert contact.id.startswith("c_")


def test_failed_parent_write_and_commit_rollback(assistant: Assistant, monkeypatch: pytest.MonkeyPatch) -> None:
    contact = assistant.add_contact("Попереднє", ("1234567890",))
    note = assistant.add_note("До", "текст", ("старий",))
    original = assistant.store.save_contact

    def fail_parent(connection: sqlite3.Connection, value: Contact, *, new: bool = False) -> None:
        original(connection, value, new=new)
        raise sqlite3.OperationalError("synthetic failure after parent and children")

    monkeypatch.setattr(assistant.store, "save_contact", fail_parent)
    with pytest.raises(StorageError):
        assistant.edit_contact(contact.id, ContactPatch(name="Не збережено", phones=("12345678901",)))
    assert assistant.contact(contact.id) == contact
    original_connect = assistant.store._connect

    class CommitFailure(sqlite3.Connection):
        def commit(self) -> None:
            raise sqlite3.OperationalError("synthetic commit failure")

    def connect(mode: str) -> sqlite3.Connection:
        if mode == "rw":
            connection = sqlite3.connect(assistant.store.path, factory=CommitFailure, isolation_level=None)
            connection.execute("PRAGMA foreign_keys=ON")
            return connection
        return original_connect(mode)

    monkeypatch.setattr(assistant.store, "_connect", connect)
    with pytest.raises(StorageError):
        assistant.edit_note(note.id, NotePatch(title="Не прийнято", tags=("новий",)))
    assert assistant.note(note.id) == note


def test_locked_store_and_permission_diagnostics(assistant: Assistant, tmp_path: Path) -> None:
    with sqlite3.connect(assistant.store.path) as blocker:
        blocker.execute("BEGIN EXCLUSIVE")
        with pytest.raises(StorageError, match="заблоковано"):
            assistant.add_note("Не буде", "текст")
    blocked = tmp_path / "unwritable"
    blocked.mkdir()
    blocked.chmod(0o500)
    try:
        with pytest.raises(StorageError, match=str(blocked)):
            Store(blocked, TODAY)
    finally:
        blocked.chmod(0o700)
    assert not list(blocked.iterdir())


@pytest.mark.parametrize("phase", ["before-commit", "before-link", "after-link"])
def test_real_initialization_crash_restart_without_cleaning_leftovers(tmp_path: Path, phase: str) -> None:
    script = r"""
import os, sqlite3, sys
from datetime import date
from pathlib import Path
import kolo.storage as storage
phase=sys.argv[2]
original_connect=sqlite3.connect
class CrashConnection(sqlite3.Connection):
    def execute(self, sql, parameters=()):
        result=super().execute(sql, parameters)
        if phase=='before-commit' and sql.startswith('PRAGMA user_version='):
            os._exit(9)
        return result
if phase=='before-commit':
    def connect(*args, **kwargs):
        return original_connect(*args, factory=CrashConnection, **kwargs)
    storage.sqlite3.connect=connect
original_link=os.link
if phase in ('before-link','after-link'):
    def link(source, target):
        if phase=='after-link': original_link(source,target)
        os._exit(9)
    storage.os.link=link
storage.Store(Path(sys.argv[1]), date(2026,10,24))
"""
    process = subprocess.run([sys.executable, "-c", script, str(tmp_path), phase], capture_output=True, timeout=10)
    assert process.returncode == 9, process.stderr
    final = tmp_path / "kolo.sqlite3"
    assert final.exists() is (phase == "after-link")
    leftovers = {path: fingerprint(path) for path in tmp_path.iterdir() if path.name.startswith(".kolo-init-")}
    assert leftovers
    store = Store(tmp_path, TODAY)
    with store.connection() as connection:
        assert store.contacts(connection) == [] and store.notes(connection) == []
    assert {path: fingerprint(path) for path in leftovers} == leftovers


def test_initialization_no_clobber_and_unsupported_link(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tmp_path = tmp_path / "store"
    tmp_path.mkdir()
    original_link = os.link
    final = tmp_path / "kolo.sqlite3"

    def race(source: Path, target: Path) -> None:
        final.write_bytes(b"unknown concurrent final")
        original_link(source, target)

    monkeypatch.setattr(os, "link", race)
    with pytest.raises(StorageError):
        Store(tmp_path, TODAY)
    assert final.read_bytes() == b"unknown concurrent final"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["kolo.sqlite3"]
    other = tmp_path / "other"

    def unsupported(source: Path, target: Path) -> None:
        raise OSError("hard links unsupported")

    monkeypatch.setattr(os, "link", unsupported)
    with pytest.raises(StorageError):
        Store(other, TODAY)
    assert not list(other.iterdir())


def test_real_hot_journal_native_recovery(tmp_path: Path) -> None:
    assistant = Assistant(Store(tmp_path, TODAY), lambda: TODAY)
    for index in range(40):
        assistant.add_note(f"Нотатка {index}", "а" * 9000)
    original = assistant.notes()
    script = r"""
import os, sqlite3, sys
connection=sqlite3.connect(sys.argv[1],isolation_level=None)
connection.execute('PRAGMA cache_size=3')
connection.execute('PRAGMA synchronous=FULL')
connection.execute('BEGIN IMMEDIATE')
connection.execute("UPDATE notes SET body=?", ('b'*9000,))
os._exit(9)
"""
    process = subprocess.run([sys.executable, "-c", script, str(assistant.store.path)], capture_output=True, timeout=10)
    assert process.returncode == 9
    journal = Path(f"{assistant.store.path}-journal")
    assert journal.stat().st_size > 512
    assert assistant.store._recognized_header()
    connection = sqlite3.connect(f"file:{assistant.store.path}?mode=ro", uri=True)
    try:
        with pytest.raises(sqlite3.OperationalError) as error:
            connection.execute("SELECT * FROM notes").fetchall()
        assert error.value.sqlite_errorcode == sqlite3.SQLITE_READONLY_ROLLBACK
    finally:
        connection.close()
    recovered = Assistant(Store(tmp_path, TODAY), lambda: TODAY)
    assert recovered.notes() == original
    assert not journal.exists()
    assert APPLICATION_ID == 0x4B4F4C4F


def test_failure_between_parent_and_children_rolls_back(assistant: Assistant, monkeypatch: pytest.MonkeyPatch) -> None:
    previous = assistant.add_contact("Попереднє", ("1234567890",))

    original_connect = assistant.store._connect

    def connect(mode: str) -> sqlite3.Connection:
        connection = original_connect(mode)

        def authorizer(
            action: int, first: str | None, second: str | None, database: str | None, trigger: str | None
        ) -> int:
            return (
                sqlite3.SQLITE_DENY
                if action == sqlite3.SQLITE_DELETE and first == "contact_phones"
                else sqlite3.SQLITE_OK
            )

        connection.set_authorizer(authorizer)
        return connection

    monkeypatch.setattr(assistant.store, "_connect", connect)
    with pytest.raises(StorageError):
        assistant.edit_contact(previous.id, ContactPatch(name="Частковий запис", phones=("12345678901",)))
    assert assistant.contact(previous.id) == previous


def test_unknown_header_with_real_hot_journal_is_preserved(tmp_path: Path) -> None:
    app = Assistant(Store(tmp_path, TODAY), lambda: TODAY)
    for number in range(12):
        app.add_note(f"Текст {number}", "а" * 9000)
    script = """
import os, sqlite3, sys
c=sqlite3.connect(sys.argv[1],isolation_level=None)
c.execute('PRAGMA cache_size=3')
c.execute('BEGIN IMMEDIATE')
c.execute('UPDATE notes SET body=?',('x'*9000,))
os._exit(9)
"""
    child = subprocess.run([sys.executable, "-c", script, str(app.store.path)], capture_output=True, timeout=10)
    assert child.returncode == 9
    journal = Path(f"{app.store.path}-journal")
    assert journal.stat().st_size > 512
    with app.store.path.open("r+b") as stream:
        stream.seek(60)
        stream.write((2).to_bytes(4, "big"))
    before = fingerprint(app.store.path), fingerprint(journal)
    with pytest.raises(StorageError):
        Store(tmp_path, TODAY)
    assert (fingerprint(app.store.path), fingerprint(journal)) == before


@pytest.mark.parametrize(
    "statement",
    [
        "CREATE TRIGGER sqliteXdiscard AFTER INSERT ON notes BEGIN DELETE FROM notes WHERE id=NEW.id; END",
        "CREATE TABLE sqliteXextra(id TEXT)",
        "CREATE INDEX sqliteXindex ON notes(title)",
    ],
)
def test_sqlite_like_unknown_objects_refused_readonly(assistant: Assistant, statement: str) -> None:
    existing = assistant.add_note("Збережена", "Текст")
    with sqlite3.connect(assistant.store.path) as connection:
        connection.execute(statement)
    before = fingerprint(assistant.store.path)
    with pytest.raises(StorageError):
        Store(assistant.store.path.parent, TODAY)
    assert fingerprint(assistant.store.path) == before
    with sqlite3.connect(assistant.store.path) as connection:
        assert connection.execute("SELECT id,title,body FROM notes").fetchall() == [
            (existing.id, existing.title, existing.body)
        ]
