import re
from datetime import date

from kolo.errors import FieldError
from kolo.models import Contact, Note

PHONE_REMOVE = str.maketrans("", "", " ()-")
PHONE_PATTERN = re.compile(r"\+?[0-9]{10,15}\Z")
LOCAL_PATTERN = re.compile(r"[A-Za-z0-9._%+\-]+\Z")
LABEL_PATTERN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?\Z")


def required_text(value: str, field: str) -> str:
    value = value.strip()
    if not 1 <= len(value) <= 120:
        raise FieldError(field, "введіть від 1 до 120 символів.")
    return value


def address(value: str | None) -> str | None:
    result = value.strip() if value is not None else ""
    if len(result) > 500:
        raise FieldError("Адреса", "дозволено не більше 500 символів.")
    return result or None


def phones(values: tuple[str, ...]) -> tuple[str, ...]:
    normalized = tuple(value.translate(PHONE_REMOVE) for value in values)
    if any(not PHONE_PATTERN.fullmatch(value) for value in normalized):
        raise FieldError("Телефони", "потрібно 10–15 цифр; дозволено початковий +, пробіли, ( ), -.")
    if len({value.removeprefix("+") for value in normalized}) != len(normalized):
        raise FieldError("Телефони", "один номер не можна повторювати в контакті.")
    return normalized


def email(value: str | None) -> str | None:
    result = value.strip() if value is not None else ""
    if not result:
        return None
    if len(result) > 254 or not result.isascii() or result.count("@") != 1:
        raise FieldError("Email", "потрібна адреса name@example.com до 254 ASCII-символів.")
    local, domain = result.split("@")
    labels = domain.split(".")
    valid_local = 1 <= len(local) <= 64 and LOCAL_PATTERN.fullmatch(local)
    valid_dots = not local.startswith(".") and not local.endswith(".") and ".." not in local
    if not valid_local or not valid_dots or len(labels) < 2 or not all(LABEL_PATTERN.fullmatch(x) for x in labels):
        raise FieldError("Email", "потрібна адреса name@example.com без порожніх частин і крайніх крапок.")
    return result


def birthday(value: str | date | None, today: date) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            raise FieldError("Дата народження", "формат РРРР-ММ-ДД, наприклад 1995-03-21.")
        try:
            value = date.fromisoformat(value)
        except ValueError as error:
            raise FieldError("Дата народження", "такої календарної дати немає.") from error
    if value > today:
        raise FieldError("Дата народження", "дата не може бути в майбутньому.")
    return value


def body(value: str) -> str:
    if not value.strip() or not 1 <= len(value) <= 10000:
        raise FieldError("Текст", "введіть непорожній текст до 10000 символів.")
    return value


def tags(values: tuple[str, ...]) -> tuple[str, ...]:
    stripped = tuple(value.strip() for value in values if value.strip())
    if any(len(value) > 40 for value in stripped):
        raise FieldError("Теги", "кожен тег — до 40 символів.")
    return tuple(sorted({value.casefold() for value in stripped}))


def contact(value: Contact, today: date) -> Contact:
    identifier(value.id, "c")
    return Contact(
        value.id,
        required_text(value.name, "Ім’я"),
        phones(value.phones),
        address(value.address),
        email(value.email),
        birthday(value.birthday, today),
    )


def note(value: Note, *, stored: bool = False) -> Note:
    identifier(value.id, "n")
    if stored:
        if any(not tag or len(tag) > 120 or tag != tag.strip().casefold() for tag in value.tags):
            raise FieldError("Теги", "неправильний збережений тег.")
        normalized = tuple(sorted(set(value.tags)))
    else:
        normalized = tags(value.tags)
    return Note(value.id, required_text(value.title, "Заголовок"), body(value.body), normalized)


def identifier(value: str, prefix: str) -> str:
    if not re.fullmatch(rf"{prefix}_[0-9a-f]{{12}}", value):
        raise FieldError("ID", f"потрібен повний ID запису з префіксом {prefix}_ та 12 hex-символами.")
    return value


def days(value: int) -> int:
    if not 0 <= value <= 366:
        raise FieldError("Кількість днів", "введіть ціле число від 0 до 366.")
    return value
