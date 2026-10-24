from datetime import date

import pytest

from kolo import validation as v
from kolo.errors import InputError
from kolo.models import Contact, Note


@pytest.mark.parametrize("text", ["", " \t", "a" * 121])
def test_required_rejects_boundaries(text: str) -> None:
    with pytest.raises(InputError):
        v.required_text(text, "Ім’я")


def test_text_limits_and_original_body() -> None:
    assert v.required_text(" а ", "Ім’я") == "а"
    assert len(v.required_text("а" * 120, "Заголовок")) == 120
    assert v.address(" " + "a" * 500 + " ") == "a" * 500
    assert v.address(" ") is None
    with pytest.raises(InputError):
        v.address("a" * 501)
    assert v.body("\nДумка\n") == "\nДумка\n"
    assert v.body("a" * 10000) == "a" * 10000
    for invalid in ("", " \n ", "a" * 10001):
        with pytest.raises(InputError):
            v.body(invalid)


@pytest.mark.parametrize(
    "phone",
    ["123456789", "1" * 16, "１２３４５６７８９０", "12345+67890", "+123\t4567890", "+1234567890x", "++1234567890"],
)
def test_invalid_phones(phone: str) -> None:
    with pytest.raises(InputError):
        v.phones((phone,))


def test_phones_normalization_order_and_duplicates() -> None:
    assert v.phones(("+38 (067) 123-45-67", "0123456789", "1" * 15)) == ("+380671234567", "0123456789", "1" * 15)
    with pytest.raises(InputError):
        v.phones(("+1234567890", "(123) 456-7890"))
    assert v.phones(()) == ()


@pytest.mark.parametrize(
    "email",
    [
        "a@b",
        ".a@b.co",
        "a.@b.co",
        "a..b@c.co",
        "a@@b.co",
        "а@b.co",
        "a@-b.co",
        "a@b-.co",
        "a@b..co",
        "a" * 65 + "@b.co",
        "a b@c.co",
        "a@" + "b" * 250 + ".co",
    ],
)
def test_email_rejects_invalid(email: str) -> None:
    with pytest.raises(InputError):
        v.email(email)


def test_email_valid_limits_and_dates() -> None:
    assert v.email(" A.B+work@Sub-Domain.Example ") == "A.B+work@Sub-Domain.Example"
    assert v.email(" ") is None
    assert v.email(None) is None
    assert v.email("a" * 64 + "@" + "b" * 186 + ".co") is not None
    assert v.birthday("2000-02-29", date(2026, 1, 1)) == date(2000, 2, 29)
    assert v.birthday("", date(2026, 1, 1)) is None
    for text in ("2026-1-01", "2025-02-29", "2027-01-01", "2026-01-01 "):
        with pytest.raises(InputError):
            v.birthday(text, date(2026, 1, 1))


def test_tags_casefold_expansion_and_literal_comma() -> None:
    assert v.tags(("Робота", " робота ", "", "дім,сад")) == ("дім,сад", "робота")
    assert v.tags(("ß" * 40,)) == ("ss" * 40,)
    with pytest.raises(InputError):
        v.tags(("x" * 41,))
    note = Note("n_000000000001", " Т ", "текст", ("ss" * 40,))
    assert v.note(note, stored=True).tags == ("ss" * 40,)
    with pytest.raises(InputError):
        v.note(Note(note.id, "Т", "т", (" Не canonical ",)), stored=True)
    with pytest.raises(InputError):
        v.contact(Contact("c_bad", "Ім’я"), date(2026, 1, 1))
