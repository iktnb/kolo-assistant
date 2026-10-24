from dataclasses import dataclass
from datetime import date
from enum import Enum


class Unset(Enum):
    VALUE = "UNSET"


UNSET = Unset.VALUE


@dataclass(frozen=True)
class Contact:
    id: str
    name: str
    phones: tuple[str, ...] = ()
    address: str | None = None
    email: str | None = None
    birthday: date | None = None


@dataclass(frozen=True)
class Note:
    id: str
    title: str
    body: str
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class ContactPatch:
    name: str | Unset = UNSET
    phones: tuple[str, ...] | Unset = UNSET
    address: str | None | Unset = UNSET
    email: str | None | Unset = UNSET
    birthday: str | date | None | Unset = UNSET


@dataclass(frozen=True)
class NotePatch:
    title: str | Unset = UNSET
    body: str | Unset = UNSET
    tags: tuple[str, ...] | Unset = UNSET
