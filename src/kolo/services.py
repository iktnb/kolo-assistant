from collections.abc import Callable, Sequence
from datetime import date
from uuid import uuid4

from kolo import validation
from kolo.birthdays import Birthday, upcoming
from kolo.errors import DuplicateId, InputError, StorageError
from kolo.models import Contact, ContactPatch, Note, NotePatch, Unset
from kolo.storage import Store


def random_id() -> str:
    return uuid4().hex[:12]


def find[Entity: (Contact, Note)](values: Sequence[Entity], identifier: str) -> Entity:
    for value in values:
        if value.id == identifier:
            return value
    raise InputError(f"Запис {identifier} не знайдено. Перевірте повний ID у списку.")


class Assistant:
    def __init__(self, store: Store, today: Callable[[], date], id_factory: Callable[[], str] = random_id) -> None:
        self.store = store
        self.today = today
        self.id_factory = id_factory

    def contacts(self, query: str = "", *, today: date | None = None) -> list[Contact]:
        snapshot = today or self.today()
        with self.store.connection() as connection:
            values = self.store.contacts(connection, snapshot)
        q = query.strip().casefold()
        digits = query.strip().translate(validation.PHONE_REMOVE).removeprefix("+")
        phone_query = bool(digits) and digits.isascii() and digits.isdigit()
        result = [
            value
            for value in values
            if not q
            or any(q in field.casefold() for field in (value.name, value.address or "", value.email or ""))
            or (phone_query and any(digits in phone for phone in value.phones))
        ]
        return sorted(result, key=lambda value: (value.name.casefold(), value.id))

    def contact(self, identifier: str) -> Contact:
        validation.identifier(identifier, "c")
        return find(self.contacts(), identifier)

    def add_contact(
        self,
        name: str,
        phones: tuple[str, ...] = (),
        address: str | None = None,
        email: str | None = None,
        birthday: str | date | None = None,
    ) -> Contact:
        today = self.today()
        born = validation.birthday(birthday, today)
        for _ in range(5):
            candidate = validation.contact(Contact(f"c_{self.id_factory()}", name, phones, address, email, born), today)
            try:
                with self.store.connection(write=True) as connection:
                    self.store.save_contact(connection, candidate, new=True)
                return candidate
            except DuplicateId:
                continue
        raise StorageError(f"Сховище {self.store.path}: не вдалося створити унікальний ID після 5 спроб.")

    def edit_contact(self, identifier: str, patch: ContactPatch) -> Contact:
        validation.identifier(identifier, "c")
        today = self.today()
        with self.store.connection(write=True) as connection:
            old = find(self.store.contacts(connection, today), identifier)
            candidate = validation.contact(
                Contact(
                    old.id,
                    old.name if isinstance(patch.name, Unset) else patch.name,
                    old.phones if isinstance(patch.phones, Unset) else patch.phones,
                    old.address if isinstance(patch.address, Unset) else patch.address,
                    old.email if isinstance(patch.email, Unset) else patch.email,
                    old.birthday if isinstance(patch.birthday, Unset) else validation.birthday(patch.birthday, today),
                ),
                today,
            )
            self.store.save_contact(connection, candidate)
        return candidate

    def delete_contact(self, identifier: str) -> None:
        validation.identifier(identifier, "c")
        with self.store.connection(write=True) as connection:
            find(self.store.contacts(connection, self.today()), identifier)
            connection.execute("DELETE FROM contacts WHERE id=?", (identifier,))

    def notes(self, query: str = "", tag: str | None = None, sort: str = "title") -> list[Note]:
        if tag is not None and not tag.strip():
            raise InputError("Тег пошуку не може бути порожнім.")
        if sort not in {"title", "tags"}:
            raise InputError("Сортування: title або tags.")
        with self.store.connection() as connection:
            values = self.store.notes(connection)
        q = query.strip().casefold()
        normalized_tag = tag.strip().casefold() if tag is not None else None
        result = [
            value
            for value in values
            if (not q or q in value.title.casefold() or q in value.body.casefold())
            and (normalized_tag is None or normalized_tag in value.tags)
        ]
        if sort == "tags":
            return sorted(
                result, key=lambda value: (not bool(value.tags), value.tags, value.title.casefold(), value.id)
            )
        return sorted(result, key=lambda value: (value.title.casefold(), value.id))

    def note(self, identifier: str) -> Note:
        validation.identifier(identifier, "n")
        return find(self.notes(), identifier)

    def add_note(self, title: str, body: str, tags: tuple[str, ...] = ()) -> Note:
        for _ in range(5):
            candidate = validation.note(Note(f"n_{self.id_factory()}", title, body, tags))
            try:
                with self.store.connection(write=True) as connection:
                    self.store.save_note(connection, candidate, new=True)
                return candidate
            except DuplicateId:
                continue
        raise StorageError(f"Сховище {self.store.path}: не вдалося створити унікальний ID після 5 спроб.")

    def edit_note(self, identifier: str, patch: NotePatch) -> Note:
        validation.identifier(identifier, "n")
        with self.store.connection(write=True) as connection:
            old = find(self.store.notes(connection), identifier)
            candidate = validation.note(
                Note(
                    old.id,
                    old.title if isinstance(patch.title, Unset) else patch.title,
                    old.body if isinstance(patch.body, Unset) else patch.body,
                    old.tags if isinstance(patch.tags, Unset) else validation.tags(patch.tags),
                ),
                stored=True,
            )
            self.store.save_note(connection, candidate)
        return candidate

    def delete_note(self, identifier: str) -> None:
        validation.identifier(identifier, "n")
        with self.store.connection(write=True) as connection:
            find(self.store.notes(connection), identifier)
            connection.execute("DELETE FROM notes WHERE id=?", (identifier,))

    def birthdays(self, days: int = 7, *, today: date | None = None) -> list[Birthday]:
        snapshot = today or self.today()
        return upcoming(self.contacts(today=snapshot), snapshot, days)
