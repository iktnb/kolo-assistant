import calendar
import os
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from kolo import validation
from kolo.errors import InputError
from kolo.models import Contact

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


def timezone() -> ZoneInfo:
    name = os.environ.get("KOLO_TIMEZONE") or "Europe/Kyiv"
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise InputError(
            "Невідомий часовий пояс KOLO_TIMEZONE; використайте IANA-назву, наприклад Europe/Kyiv."
        ) from error


def local_today(zone: ZoneInfo, clock: Clock = utc_now) -> date:
    instant = clock()
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("Clock must return an aware datetime")
    return instant.astimezone(zone).date()


@dataclass(frozen=True)
class Birthday:
    contact: Contact
    anniversary: date
    days_until: int


def anniversary(born: date, year: int) -> date:
    day = 28 if born.month == 2 and born.day == 29 and not calendar.isleap(year) else born.day
    return date(year, born.month, day)


def upcoming(contacts: Iterable[Contact], today: date, days: int = 7) -> list[Birthday]:
    validation.days(days)
    result: list[Birthday] = []
    for contact in contacts:
        if contact.birthday is None:
            continue
        candidate = anniversary(contact.birthday, today.year)
        if candidate < today:
            candidate = anniversary(contact.birthday, today.year + 1)
        difference = (candidate - today).days
        if difference <= days:
            result.append(Birthday(contact, candidate, difference))
    return sorted(result, key=lambda item: (item.anniversary, item.contact.name.casefold(), item.contact.id))
