import os
import sqlite3
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from urllib.parse import quote

from kolo import validation
from kolo.errors import DuplicateId, InputError, StorageError
from kolo.models import Contact, Note

APPLICATION_ID = 0x4B4F4C4F
SCHEMA_VERSION = 1
DDL = (
    "CREATE TABLE contacts (id TEXT PRIMARY KEY NOT NULL, name TEXT NOT NULL, address TEXT, email TEXT, birthday TEXT)",
    "CREATE TABLE contact_phones (contact_id TEXT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE, "
    "position INTEGER NOT NULL CHECK(position >= 0), phone TEXT NOT NULL, digits TEXT NOT NULL, "
    "PRIMARY KEY(contact_id, position), UNIQUE(contact_id, digits))",
    "CREATE TABLE notes (id TEXT PRIMARY KEY NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL)",
    "CREATE TABLE note_tags (note_id TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE, "
    "tag TEXT NOT NULL, PRIMARY KEY(note_id, tag))",
)
COLUMNS = {
    "contacts": (
        ("id", "TEXT", 1, None, 1),
        ("name", "TEXT", 1, None, 0),
        ("address", "TEXT", 0, None, 0),
        ("email", "TEXT", 0, None, 0),
        ("birthday", "TEXT", 0, None, 0),
    ),
    "contact_phones": (
        ("contact_id", "TEXT", 1, None, 1),
        ("position", "INTEGER", 1, None, 2),
        ("phone", "TEXT", 1, None, 0),
        ("digits", "TEXT", 1, None, 0),
    ),
    "notes": (("id", "TEXT", 1, None, 1), ("title", "TEXT", 1, None, 0), ("body", "TEXT", 1, None, 0)),
    "note_tags": (("note_id", "TEXT", 1, None, 1), ("tag", "TEXT", 1, None, 2)),
}
UNIQUE = {
    "contacts": {("id",)},
    "contact_phones": {("contact_id", "position"), ("contact_id", "digits")},
    "notes": {("id",)},
    "note_tags": {("note_id", "tag")},
}


def data_directory(explicit: str | None = None) -> Path:
    if explicit is not None:
        if not explicit.strip():
            raise InputError("--data-dir: вкажіть непорожній шлях.")
        return Path(explicit).expanduser().resolve()
    xdg = os.environ.get("XDG_DATA_HOME", "")
    base = Path(xdg) if xdg and Path(xdg).is_absolute() else Path.home() / ".local" / "share"
    return (base / "kolo").resolve()


def _text(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("Expected stored text")
    return value


def _optional(value: object) -> str | None:
    return None if value is None else _text(value)


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _private_directories(path: Path) -> None:
    missing: list[Path] = []
    current = path
    while not current.exists():
        missing.append(current)
        current = current.parent
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)


class Store:
    def __init__(self, directory: Path, today: date) -> None:
        self.path = directory / "kolo.sqlite3"
        self.today = today
        try:
            if not self.path.exists():
                self._initialize()
            self._preflight()
        except (sqlite3.Error, OSError, ValueError, InputError) as error:
            raise self._error(error) from error

    def _error(self, error: Exception) -> StorageError:
        if isinstance(error, sqlite3.OperationalError) and "locked" in str(error):
            reason = "базу заблоковано; закрийте інший процес і повторіть."
        elif isinstance(error, PermissionError):
            reason = "немає дозволу на читання або запис."
        elif isinstance(error, FileExistsError):
            reason = "файл уже створено іншим процесом; повторіть запуск."
        else:
            reason = "не вдалося безпечно прочитати або зберегти дані; перевірте доступ і формат бази v1."
        return StorageError(f"Сховище {self.path}: {reason}")

    def _connect(self, mode: str) -> sqlite3.Connection:
        uri = f"file:{quote(str(self.path), safe='/')}?mode={mode}"
        connection = sqlite3.connect(uri, uri=True, timeout=3, isolation_level=None)
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=3000")
            return connection
        except BaseException:
            connection.close()
            raise

    def _initialize(self) -> None:
        _private_directories(self.path.parent)
        descriptor, filename = tempfile.mkstemp(prefix=".kolo-init-", dir=self.path.parent)
        os.close(descriptor)
        temporary = Path(filename)
        try:
            self._initialize_private(temporary)
            with temporary.open("rb") as stream:
                os.fsync(stream.fileno())
            os.link(temporary, self.path)
            _sync_directory(self.path.parent)
            temporary.unlink()
            _sync_directory(self.path.parent)
        finally:
            temporary.unlink(missing_ok=True)
            Path(f"{temporary}-journal").unlink(missing_ok=True)

    def _initialize_private(self, path: Path) -> None:
        connection = sqlite3.connect(path, isolation_level=None)
        try:
            connection.execute("PRAGMA journal_mode=DELETE")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("BEGIN IMMEDIATE")
            for statement in DDL:
                connection.execute(statement)
            connection.execute(f"PRAGMA application_id={APPLICATION_ID}")
            connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
            connection.commit()
        finally:
            connection.close()

    def _preflight(self) -> None:
        try:
            self._validate_readonly()
        except sqlite3.OperationalError as error:
            if error.sqlite_errorcode != sqlite3.SQLITE_READONLY_ROLLBACK or not self._recognized_header():
                raise
            connection = self._connect("rw")
            try:
                connection.execute("SELECT count(*) FROM sqlite_master").fetchone()
            finally:
                connection.close()
            self._validate_readonly()

    def _recognized_header(self) -> bool:
        with self.path.open("rb") as stream:
            header = stream.read(100)
        return (
            len(header) == 100
            and header[:16] == b"SQLite format 3\x00"
            and int.from_bytes(header[60:64], "big") == SCHEMA_VERSION
            and int.from_bytes(header[68:72], "big") == APPLICATION_ID
        )

    def _validate_readonly(self) -> None:
        connection = self._connect("ro")
        try:
            self._validate_schema(connection)
            if connection.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
                raise ValueError("Integrity check failed")
            if connection.execute("PRAGMA foreign_key_check").fetchall():
                raise ValueError("Foreign key check failed")
            self.contacts(connection)
            self.notes(connection)
        finally:
            connection.close()

    def _validate_schema(self, connection: sqlite3.Connection) -> None:
        if connection.execute("PRAGMA application_id").fetchone() != (APPLICATION_ID,):
            raise ValueError("Unknown application")
        if connection.execute("PRAGMA user_version").fetchone() != (SCHEMA_VERSION,):
            raise ValueError("Unknown schema version")
        objects = connection.execute("SELECT type, name FROM sqlite_master WHERE name NOT GLOB 'sqlite_*'").fetchall()
        if set(objects) != {("table", name) for name in COLUMNS}:
            raise ValueError("Unexpected schema objects")
        for table, expected in COLUMNS.items():
            columns = connection.execute('SELECT name,type,"notnull",dflt_value,pk FROM pragma_table_info(?)', (table,))
            if tuple(columns.fetchall()) != expected:
                raise ValueError("Unexpected columns")
            self._validate_constraints(connection, table)

    def _validate_constraints(self, connection: sqlite3.Connection, table: str) -> None:
        foreign = connection.execute("SELECT * FROM pragma_foreign_key_list(?)", (table,)).fetchall()
        parent = {"contact_phones": ("contacts", "contact_id"), "note_tags": ("notes", "note_id")}.get(table)
        expected_foreign = (
            [] if parent is None else [(0, 0, parent[0], parent[1], "id", "NO ACTION", "CASCADE", "NONE")]
        )
        if foreign != expected_foreign:
            raise ValueError("Unexpected foreign keys")
        indexes = connection.execute('SELECT name FROM pragma_index_list(?) WHERE "unique"=1', (table,)).fetchall()
        unique = {
            tuple(row[0] for row in connection.execute("SELECT name FROM pragma_index_info(?)", (name,)))
            for (name,) in indexes
        }
        if unique != UNIQUE[table]:
            raise ValueError("Unexpected uniqueness constraints")
        if table == "contact_phones":
            sql = _text(connection.execute("SELECT sql FROM sqlite_master WHERE name=?", (table,)).fetchone()[0])
            if "check(position>=0)" not in "".join(sql.lower().split()):
                raise ValueError("Missing position constraint")

    @contextmanager
    def connection(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect("rw")
            if write:
                connection.execute("PRAGMA journal_mode=DELETE")
                connection.execute("PRAGMA synchronous=FULL")
                connection.execute("BEGIN IMMEDIATE")
            yield connection
            if write:
                connection.commit()
        except (sqlite3.Error, OSError, ValueError) as error:
            raise self._error(error) from error
        finally:
            if connection is not None:
                try:
                    if connection.in_transaction:
                        connection.rollback()
                finally:
                    connection.close()

    def contacts(self, connection: sqlite3.Connection, today: date | None = None) -> list[Contact]:
        result: list[Contact] = []
        for row in connection.execute("SELECT id,name,address,email,birthday FROM contacts"):
            identifier, name, address, email, birthday = row
            children = connection.execute(
                "SELECT position,phone,digits FROM contact_phones WHERE contact_id=? ORDER BY position", (identifier,)
            ).fetchall()
            if [child[0] for child in children] != list(range(len(children))):
                raise ValueError("Invalid phone positions")
            if any(_text(phone).removeprefix("+") != digits for _, phone, digits in children):
                raise ValueError("Invalid phone digits")
            value = Contact(
                _text(identifier),
                _text(name),
                tuple(_text(child[1]) for child in children),
                _optional(address),
                _optional(email),
                date.fromisoformat(_text(birthday)) if birthday is not None else None,
            )
            try:
                valid = validation.contact(value, today or self.today) == value
            except InputError as error:
                raise ValueError("Invalid stored contact") from error
            if not valid or (
                birthday is not None and value.birthday is not None and value.birthday.isoformat() != birthday
            ):
                raise ValueError("Noncanonical contact")
            result.append(value)
        return result

    def notes(self, connection: sqlite3.Connection) -> list[Note]:
        result: list[Note] = []
        for identifier, title, body in connection.execute("SELECT id,title,body FROM notes"):
            tags = connection.execute("SELECT tag FROM note_tags WHERE note_id=? ORDER BY tag", (identifier,))
            value = Note(_text(identifier), _text(title), _text(body), tuple(_text(row[0]) for row in tags))
            try:
                valid = validation.note(value, stored=True) == value
            except InputError as error:
                raise ValueError("Invalid stored note") from error
            if not valid:
                raise ValueError("Noncanonical note")
            result.append(value)
        return result

    def save_contact(self, connection: sqlite3.Connection, value: Contact, *, new: bool = False) -> None:
        if new:
            try:
                connection.execute(
                    "INSERT INTO contacts(id,name,address,email,birthday) VALUES(?,?,?,?,?)",
                    (
                        value.id,
                        value.name,
                        value.address,
                        value.email,
                        value.birthday.isoformat() if value.birthday else None,
                    ),
                )
            except sqlite3.IntegrityError as error:
                if error.sqlite_errorcode == sqlite3.SQLITE_CONSTRAINT_PRIMARYKEY:
                    raise DuplicateId from error
                raise
        else:
            connection.execute(
                "UPDATE contacts SET name=?,address=?,email=?,birthday=? WHERE id=?",
                (
                    value.name,
                    value.address,
                    value.email,
                    value.birthday.isoformat() if value.birthday else None,
                    value.id,
                ),
            )
        connection.execute("DELETE FROM contact_phones WHERE contact_id=?", (value.id,))
        connection.executemany(
            "INSERT INTO contact_phones(contact_id,position,phone,digits) VALUES(?,?,?,?)",
            [(value.id, position, phone, phone.removeprefix("+")) for position, phone in enumerate(value.phones)],
        )

    def save_note(self, connection: sqlite3.Connection, value: Note, *, new: bool = False) -> None:
        if new:
            try:
                connection.execute(
                    "INSERT INTO notes(id,title,body) VALUES(?,?,?)", (value.id, value.title, value.body)
                )
            except sqlite3.IntegrityError as error:
                if error.sqlite_errorcode == sqlite3.SQLITE_CONSTRAINT_PRIMARYKEY:
                    raise DuplicateId from error
                raise
        else:
            connection.execute("UPDATE notes SET title=?,body=? WHERE id=?", (value.title, value.body, value.id))
        connection.execute("DELETE FROM note_tags WHERE note_id=?", (value.id,))
        connection.executemany(
            "INSERT INTO note_tags(note_id,tag) VALUES(?,?)", [(value.id, tag) for tag in value.tags]
        )
