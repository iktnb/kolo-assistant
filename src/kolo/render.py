import os
import sys
import unicodedata
from collections.abc import Sequence
from typing import TextIO

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from kolo.birthdays import Birthday
from kolo.models import Contact, Note

THEME = Theme({"accent": "bold cyan", "muted": "dim", "success": "green", "error": "bold red"})


def safe(value: object, *, multiline: bool = False, style: str = "") -> Text:
    result: list[str] = []
    for character in str(value):
        if multiline and character == "\n":
            result.append(character)
        elif multiline and character == "\t":
            result.append("    ")
        elif unicodedata.category(character) in {"Cc", "Cf"}:
            point = ord(character)
            result.append(f"\\x{point:02x}" if point <= 0xFF else f"\\u{point:04x}")
        else:
            result.append(character)
    return Text("".join(result), style=style, overflow="fold")


def make_console(stream: TextIO | None = None, *, plain: bool = False, width: int | None = None) -> Console:
    stream = stream if stream is not None else sys.stdout
    colored = stream.isatty() and not plain and "NO_COLOR" not in os.environ
    return Console(
        file=stream,
        theme=THEME,
        force_terminal=colored,
        color_system="auto" if colored else None,
        no_color=not colored,
        highlight=False,
        markup=False,
        width=width,
    )


class Renderer:
    def __init__(self, console: Console, errors: Console | None = None) -> None:
        self.console = console
        self.errors = errors if errors is not None else console

    def message(self, value: object, *, error: bool = False, success: bool = False) -> None:
        style = "error" if error else "success" if success else ""
        console = self.errors if error else self.console
        console.print(safe(value, style=style), soft_wrap=not console.is_terminal)

    def heading(self, title: str, subtitle: str = "", *, multiline: bool = False) -> None:
        self.console.print()
        self.console.print(
            Panel(
                safe(subtitle, multiline=multiline),
                title=safe(title, style="accent"),
                border_style="accent",
                padding=(0, 1),
            )
        )

    def menu(self, entries: Sequence[tuple[str, str]]) -> None:
        for key, label in entries:
            self.console.print(Text.assemble((f"  {key}  ", "accent"), safe(label)))
        self.console.print()

    def contacts(self, values: Sequence[Contact], *, query: str | None = None) -> None:
        if not values:
            self.message(
                f"Нічого не знайдено за запитом: {query}" if query else "Контактів поки немає. Додайте перший контакт."
            )
            return
        self.message(f"Контакти · {len(values)}", success=True)
        if self.console.width < 80:
            for value in values:
                self.console.print(Text.assemble((value.id, "accent"), "  ", safe(value.name)))
                self.console.print(safe(f"  {value.phones[0] if value.phones else 'Телефон не вказано'}"))
        else:
            table = Table(expand=True, header_style="accent", show_lines=False)
            for label in ("ID", "Ім’я", "Телефон"):
                table.add_column(label, no_wrap=label == "ID", min_width=14 if label == "ID" else None)
            if self.console.width >= 120:
                table.add_column("Email")
            for value in values:
                row = [safe(value.id), safe(value.name), safe(value.phones[0] if value.phones else "—")]
                if self.console.width >= 120:
                    row.append(safe(value.email or "—"))
                table.add_row(*row)
            self.console.print(table)
        self.message("Повні поля: contacts show ID · у меню оберіть «Деталі».")

    def notes(self, values: Sequence[Note], *, query: str | None = None) -> None:
        if not values:
            self.message(
                f"Нічого не знайдено за запитом: {query}" if query else "Нотаток поки немає. Додайте першу нотатку."
            )
            return
        self.message(f"Нотатки · {len(values)}", success=True)
        if self.console.width < 80:
            for value in values:
                self.console.print(Text.assemble((value.id, "accent"), "  ", safe(value.title)))
                self.console.print(safe(f"  Теги: {', '.join(value.tags) or 'Немає'}"))
        else:
            table = Table(expand=True, header_style="accent")
            table.add_column("ID", min_width=14, no_wrap=True)
            table.add_column("Заголовок")
            table.add_column("Теги")
            if self.console.width >= 120:
                table.add_column("Уривок")
            for value in values:
                row = [safe(value.id), safe(value.title), safe(", ".join(value.tags) or "—")]
                if self.console.width >= 120:
                    row.append(safe(value.body[:90]))
                table.add_row(*row)
            self.console.print(table)
        self.message("Повний текст: notes show ID · у меню оберіть «Деталі».")

    def details(self, value: Contact | Note) -> None:
        title = value.name if isinstance(value, Contact) else value.title
        self.heading("Контакт" if isinstance(value, Contact) else "Нотатка", title)
        self.field("ID", value.id)
        if isinstance(value, Contact):
            self.field("Ім’я", value.name)
            self.field("Телефони", "\n".join(value.phones) or None, multiline=True)
            self.field("Адреса", value.address)
            self.field("Email", value.email)
            self.field("Дата народження", value.birthday)
        else:
            self.field("Заголовок", value.title)
            self.field("Теги", ", ".join(value.tags) or None)
            self.field("Текст", value.body, multiline=True)

    def field(self, label: str, value: object, *, multiline: bool = False) -> None:
        self.console.print(safe(f"{label}:", style="muted"))
        self.console.print(safe("Не вказано" if value is None else value, multiline=multiline))

    def birthdays(self, values: Sequence[Birthday], days: int = 7) -> None:
        self.message(f"Дні народження · найближчі {days} днів", success=True)
        if not values:
            self.message("У цьому проміжку днів народження немає.")
        for value in values:
            self.console.print(safe(f"{value.contact.id}  {value.contact.name}"))
            self.console.print(safe(f"  {value.anniversary.isoformat()} · через {value.days_until} дн."))

    def dashboard(self, contacts: int, notes: int, birthdays: Sequence[Birthday]) -> None:
        self.heading("Коло", "Ваші люди, думки та важливі дати — поруч.")
        self.message(f"Контактів: {contacts}   Нотаток: {notes}")
        self.birthdays(birthdays)
        self.console.print()
        self.menu((("1", "Контакти"), ("2", "Нотатки"), ("3", "Дні народження"), ("4", "Довідка"), ("0", "Вийти")))
