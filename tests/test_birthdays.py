from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from kolo.birthdays import local_today, upcoming
from kolo.models import Contact


def person(number: int, name: str, born: str | None) -> Contact:
    return Contact(f"c_{number:012x}", name, birthday=date.fromisoformat(born) if born else None)


def test_inclusive_year_rollover_and_sort() -> None:
    contacts = [
        person(3, "Яна", "2000-01-02"),
        person(2, "Анна", "2000-01-02"),
        person(1, "Аня", "2000-01-03"),
        person(4, "Сьогодні", "2000-12-30"),
        person(5, "Без дати", None),
    ]
    values = upcoming(contacts, date(2026, 12, 30), 3)
    assert [item.contact.id for item in values] == [contacts[3].id, contacts[1].id, contacts[0].id]
    assert [item.days_until for item in values] == [0, 3, 3]
    assert len(upcoming(contacts, date(2026, 12, 30), 0)) == 1
    assert len(upcoming(contacts, date(2026, 12, 30), 366)) == 4


def test_leap_policy_and_immutable_original() -> None:
    contact = person(1, "Леся", "2000-02-29")
    assert upcoming([contact], date(2025, 2, 28), 0)[0].anniversary == date(2025, 2, 28)
    assert upcoming([contact], date(2028, 2, 28), 0) == []
    assert upcoming([contact], date(2028, 2, 28), 1)[0].anniversary == date(2028, 2, 29)
    assert upcoming([contact], date(2028, 3, 1), 366)[0].anniversary == date(2029, 2, 28)
    assert contact.birthday == date(2000, 2, 29)


def test_local_clock_and_invalid_naive() -> None:
    def clock() -> datetime:
        return datetime(2026, 10, 23, 22, 30, tzinfo=UTC)

    assert local_today(ZoneInfo("Europe/Kyiv"), clock) == date(2026, 10, 24)
    assert local_today(ZoneInfo("UTC"), clock) == date(2026, 10, 23)
    with pytest.raises(ValueError):
        local_today(ZoneInfo("UTC"), lambda: datetime(2026, 1, 1))
