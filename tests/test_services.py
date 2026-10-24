from datetime import date

import pytest

from kolo.errors import InputError, StorageError
from kolo.models import ContactPatch, NotePatch
from kolo.services import Assistant


def test_contacts_duplicate_search_and_atomic_edit(assistant: Assistant) -> None:
    first = assistant.add_contact(" Олена ", ("+38 (067) 123-45-67",), "ЛЬВІВ", "Olena@Example.com", "1990-01-01")
    duplicate = assistant.add_contact("Олена", first.phones, first.address, first.email)
    assert first.id != duplicate.id
    assert len(assistant.contacts("  оЛЕНА ")) == 2
    assert assistant.contacts("Львів") == [value for value in assistant.contacts()]
    assert len(assistant.contacts("(067) 123")) == 2
    assert len(assistant.contacts("example.COM")) == 2
    assert len(assistant.contacts(" ")) == 2
    assert assistant.contacts("missing") == []
    with pytest.raises(InputError):
        assistant.edit_contact(first.id, ContactPatch(address="нова", email="bad"))
    assert assistant.contact(first.id) == first
    updated = assistant.edit_contact(first.id, ContactPatch(phones=("0123456789",), email=None, birthday=""))
    assert updated.id == first.id and updated.name == "Олена" and updated.address == "ЛЬВІВ"
    assert updated.phones == ("0123456789",) and updated.email is None and updated.birthday is None
    assistant.delete_contact(duplicate.id)
    assert assistant.contacts() == [updated]
    for operation in (assistant.contact, assistant.delete_contact):
        with pytest.raises(InputError):
            operation(duplicate.id)


def test_note_crud_normalized_edit_and_expanded_tags(assistant: Assistant) -> None:
    note = assistant.add_note("Ідеї", "\nДумка\n", ("ß" * 40,))
    changed = assistant.edit_note(note.id, NotePatch(title="Нові ідеї"))
    assert changed.tags == ("ss" * 40,) and changed.body == note.body
    changed = assistant.edit_note(note.id, NotePatch(tags=("Робота", " робота ")))
    assert changed.tags == ("робота",)
    with pytest.raises(InputError):
        assistant.edit_note(note.id, NotePatch(title="Зміна", body=" "))
    assert assistant.note(note.id) == changed
    assert assistant.edit_note(note.id, NotePatch(tags=())).tags == ()
    assistant.delete_note(note.id)
    with pytest.raises(InputError):
        assistant.edit_note(note.id, NotePatch(title="Немає"))


def test_note_search_and_tuple_sort(assistant: Assistant) -> None:
    a = assistant.add_note("Б", "ДУМКА", ("а",))
    ab = assistant.add_note("А", "Думка", ("а", "б"))
    b = assistant.add_note("В", "Інше", ("б",))
    untagged = assistant.add_note("А", "думка")
    duplicate = assistant.add_note("А", "інакше")
    assert assistant.notes("думка", " А ") == [ab, a]
    assert assistant.notes("думка", "б") == [ab]
    assert assistant.notes(sort="tags")[:3] == [a, ab, b]
    assert set(value.id for value in assistant.notes(sort="tags")[3:]) == {untagged.id, duplicate.id}
    assert assistant.notes() == sorted(assistant.notes(), key=lambda value: (value.title.casefold(), value.id))
    for tag, sort in ((" ", "title"), (None, "bad")):
        with pytest.raises(InputError):
            assistant.notes(tag=tag, sort=sort)


def test_collision_retry_exhaustion_and_midnight(assistant: Assistant) -> None:
    assistant.id_factory = lambda: "000000000001"
    first = assistant.add_contact("Перший")
    with pytest.raises(StorageError, match="5"):
        assistant.add_contact("Другий")
    identifiers = iter(["000000000001", "000000000002"])
    assistant.id_factory = lambda: next(identifiers)
    second = assistant.add_contact("Другий")
    assert {value.id for value in assistant.contacts()} == {first.id, second.id}
    clock = [date(2026, 10, 24)]
    assistant.today = lambda: clock[0]
    clock[0] = date(2026, 10, 25)
    assistant.id_factory = lambda: "000000000003"
    newborn = assistant.add_contact("Новий день", birthday="2026-10-25")
    assert assistant.contact(newborn.id) == newborn
    assert assistant.birthdays(0)[0].contact == newborn
