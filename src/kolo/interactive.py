from collections.abc import Callable

from kolo import validation
from kolo.errors import InputError, StorageError
from kolo.models import UNSET, Contact, ContactPatch, Note, NotePatch, Unset
from kolo.render import Renderer
from kolo.services import Assistant

YES = {"т", "так", "y", "yes"}
INSTRUCTIONS = "Ctrl+C — скасувати до панелі; Ctrl+D — вийти без збереження чернетки."
EDIT_INSTRUCTIONS = "Enter — залишити; !clear — очистити необов’язкове; !! на початку — буквальний !."


class Forms:
    def __init__(self, render: Renderer) -> None:
        self.render = render

    def ask(self, prompt: str) -> str:
        if prompt:
            self.render.message(prompt)
        return input("> ")

    def field[Value](
        self,
        label: str,
        parse: Callable[[str], Value],
        old: Value,
        *,
        edit: bool = False,
        optional: bool = False,
        display: object = None,
    ) -> Value:
        if edit:
            self.render.field(f"Поточне · {label}", display)
        while True:
            raw = self.ask(label)
            if edit and raw == "":
                return old
            if edit and raw == "!clear":
                if not optional:
                    self.render.message("Обов’язкове поле не можна очистити.", error=True)
                    continue
                raw = ""
            elif edit and raw.startswith("!!"):
                raw = raw[1:]
            try:
                return parse(raw)
            except InputError as error:
                self.render.message(error, error=True)

    def tags(self, old: tuple[str, ...] = (), *, edit: bool = False) -> tuple[str, ...] | Unset:
        self.render.message("Теги — по одному рядку, порожній рядок завершує. Кома є частиною тегу.")
        if edit:
            self.render.field("Поточні теги", ", ".join(old) or None)
        result: list[str] = []
        while True:
            raw = self.ask("Тег")
            if not result and edit and raw == "!clear":
                return ()
            if raw == "":
                return UNSET if edit and not result else tuple(result)
            if edit and raw.startswith("!!"):
                raw = raw[1:]
            try:
                validation.tags((raw,))
                result.append(raw)
            except InputError as error:
                self.render.message(error, error=True)

    def body(self) -> str:
        self.render.message("Текст: завершіть окремим рядком .; для початкової крапки введіть ..")
        while True:
            lines: list[str] = []
            while True:
                line = self.ask("")
                if line == ".":
                    break
                lines.append(line[1:] if line.startswith("..") else line)
            try:
                return validation.body("\n".join(lines))
            except InputError as error:
                self.render.message(error, error=True)

    def contact(self, assistant: Assistant, old: Contact | None = None) -> None:
        self.render.message(INSTRUCTIONS)
        if old is not None:
            self.render.message(EDIT_INSTRUCTIONS)
        today = assistant.today()
        name = self.field(
            "Ім’я * (1–120 символів)",
            lambda raw: validation.required_text(raw, "Ім’я"),
            old.name if old else "",
            edit=old is not None,
            display=old.name if old else None,
        )
        phone = self.field(
            "Телефони (через ;, 10–15 цифр)",
            lambda raw: validation.phones(tuple(raw.split(";")) if raw else ()),
            old.phones if old else (),
            edit=old is not None,
            optional=True,
            display="; ".join(old.phones) if old else None,
        )
        address = self.field(
            "Адреса (до 500 символів)",
            validation.address,
            old.address if old else None,
            edit=old is not None,
            optional=True,
            display=old.address if old else None,
        )
        email = self.field(
            "Email (name@example.com)",
            validation.email,
            old.email if old else None,
            edit=old is not None,
            optional=True,
            display=old.email if old else None,
        )
        born = self.field(
            "Дата народження (РРРР-ММ-ДД)",
            lambda raw: validation.birthday(raw, today),
            old.birthday if old else None,
            edit=old is not None,
            optional=True,
            display=old.birthday if old else None,
        )
        value = (
            assistant.edit_contact(old.id, ContactPatch(name, phone, address, email, born))
            if old
            else assistant.add_contact(name, phone, address, email, born)
        )
        self.render.message(f"Збережено контакт {value.id}.", success=True)
        self.render.details(value)

    def note(self, assistant: Assistant, old: Note | None = None) -> None:
        self.render.message(INSTRUCTIONS)
        if old is not None:
            self.render.message(EDIT_INSTRUCTIONS)
        title = self.field(
            "Заголовок * (1–120 символів)",
            lambda raw: validation.required_text(raw, "Заголовок"),
            old.title if old else "",
            edit=old is not None,
            display=old.title if old else None,
        )
        change_body = old is None or self.ask("Змінити текст? [т/Н]").strip().casefold() in YES
        body = self.body() if change_body else old.body if old is not None else ""
        tags = self.tags(old.tags if old else (), edit=old is not None)
        value = (
            assistant.edit_note(old.id, NotePatch(title, body, tags))
            if old
            else assistant.add_note(title, body, () if isinstance(tags, Unset) else tags)
        )
        self.render.message(f"Збережено нотатку {value.id}.", success=True)
        self.render.details(value)

    def delete(self, assistant: Assistant, *, contacts: bool) -> None:
        self.render.message(INSTRUCTIONS)
        identifier = self.ask("Повний ID запису для видалення")
        value = assistant.contact(identifier) if contacts else assistant.note(identifier)
        label = value.name if isinstance(value, Contact) else value.title
        self.render.message(f"Видалити {identifier} · {label}?")
        if self.ask("Підтвердження [так/Н]").strip().casefold() not in YES:
            self.render.message("Видалення скасовано. Запис залишено.")
            return
        if contacts:
            assistant.delete_contact(identifier)
        else:
            assistant.delete_note(identifier)
        self.render.message(f"Видалено {'контакт' if contacts else 'нотатку'} {identifier}.", success=True)


def _submenu(assistant: Assistant, render: Renderer, forms: Forms, *, contacts: bool) -> None:
    while True:
        render.heading("Контакти" if contacts else "Нотатки", "Список, пошук і впорядкування ваших записів.")
        render.menu(
            (
                ("1", "Список"),
                ("2", "Пошук"),
                ("3", "Додати"),
                ("4", "Деталі за ID"),
                ("5", "Редагувати за ID"),
                ("6", "Видалити за ID"),
                ("0", "Назад"),
            )
        )
        choice = forms.ask("Оберіть дію").strip()
        if choice == "0":
            return
        if choice in {"1", "2"}:
            _list(assistant, render, forms, contacts=contacts, search=choice == "2")
        elif choice == "3":
            forms.contact(assistant) if contacts else forms.note(assistant)
        elif choice in {"4", "5"}:
            identifier = forms.ask("Повний ID запису")
            if contacts:
                contact = assistant.contact(identifier)
                render.details(contact) if choice == "4" else forms.contact(assistant, contact)
            else:
                note = assistant.note(identifier)
                render.details(note) if choice == "4" else forms.note(assistant, note)
        elif choice == "6":
            forms.delete(assistant, contacts=contacts)
        else:
            render.message("Невідомий пункт. Оберіть цифру з меню.", error=True)


def _list(assistant: Assistant, render: Renderer, forms: Forms, *, contacts: bool, search: bool) -> None:
    query = forms.ask("Пошук (Enter — усі записи)") if search else ""
    if contacts:
        render.contacts(assistant.contacts(query), query=query)
    else:
        tag = forms.ask("Точний тег (Enter — без фільтра)") if search else ""
        order = forms.ask("Сортувати за тегами? [т/Н]").strip().casefold()
        values = assistant.notes(query, tag or None, "tags" if order in YES else "title")
        render.notes(values, query=query or (f"тег {tag}" if tag else None))


def _birthday_days(raw: str) -> int:
    try:
        return validation.days(int(raw))
    except ValueError as error:
        raise InputError("Введіть ціле число від 0 до 366.") from error


def help_screen(render: Renderer) -> None:
    render.heading("Підказки", "Коло зберігає дані локально та працює без мережі.")
    for line in (
        "Контакти: додайте ім’я, решта полів необов’язкові. Дата — РРРР-ММ-ДД.",
        "Нотатки: текст може містити кілька рядків; окремий . завершує ввід.",
        "У списках є повний ID; «Деталі» відкривають усі поля.",
        INSTRUCTIONS,
        EDIT_INSTRUCTIONS,
        "Команди: kolo contacts list · kolo notes list · kolo birthdays --days 7",
        "Повна командна довідка: kolo --help",
    ):
        render.message(line)


def _dashboard(assistant: Assistant, render: Renderer) -> None:
    snapshot = assistant.today()
    contacts = assistant.contacts(today=snapshot)
    notes = assistant.notes()
    render.dashboard(len(contacts), len(notes), assistant.birthdays(today=snapshot))


def run_interactive(assistant: Assistant, render: Renderer) -> int:
    forms = Forms(render)
    while True:
        try:
            _dashboard(assistant, render)
        except StorageError as error:
            render.message(error, error=True)
            return 1
        try:
            choice = forms.ask("Оберіть розділ").strip()
            if choice == "0":
                render.message("До зустрічі в Колі!")
                return 0
            if choice in {"1", "2"}:
                _submenu(assistant, render, forms, contacts=choice == "1")
            elif choice == "3":
                days = forms.field("Кількість днів (0–366)", _birthday_days, 7)
                render.birthdays(assistant.birthdays(days), days)
            elif choice == "4":
                help_screen(render)
            else:
                render.message("Невідомий пункт. Оберіть 1, 2, 3, 4 або 0.", error=True)
        except KeyboardInterrupt:
            render.message("Дію скасовано. Незбережену чернетку відкинуто.")
        except EOFError:
            render.message("Сеанс завершено. Незбережену чернетку відкинуто.")
            return 0
        except (InputError, StorageError) as error:
            render.message(error, error=True)
