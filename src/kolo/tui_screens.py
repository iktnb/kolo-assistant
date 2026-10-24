from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Input, Label, ListItem, ListView, Select, Static

from kolo import validation
from kolo.birthdays import Birthday
from kolo.errors import InputError
from kolo.models import Contact, Note
from kolo.render import safe
from kolo.services import Assistant
from kolo.tui import KoloScreen
from kolo.tui_forms import ConfirmScreen, FormScreen, ReadErrorScreen, error_text

Kind = Literal["contacts", "notes", "birthdays"]
Record = Contact | Note


class RecordRow(ListItem):
    def __init__(self, value: Record, secondary: str = "") -> None:
        super().__init__()
        self.value, self.secondary = value, secondary

    def compose(self) -> ComposeResult:
        label = self.value.name if isinstance(self.value, Contact) else self.value.title
        yield Static(safe(label), classes="row-title")
        yield Static(safe(self.secondary or "Немає додаткових даних"), classes="muted")
        yield Static(safe(self.value.id), classes="row-id")


class HomeScreen(KoloScreen):
    def compose(self) -> ComposeResult:
        yield from self.chrome("Ваш особистий простір")
        with VerticalScroll(id="content"):
            yield Static("Контакти, думки та важливі дати — поруч.", classes="muted")
            yield Static("Читаємо дані…", id="summary")
            yield Static("", id="status")
            yield ListView(
                *(ListItem(Label(text)) for text in ("Контакти", "Нотатки", "Дні народження", "Довідка", "Вийти")),
                id="menu",
            )
            yield Button("Повторити читання", id="retry")
        yield self.footer()

    def on_mount(self) -> None:
        self.loading = False
        self.refresh_on_return = False
        self.query_one("#menu", ListView).focus()
        self.refresh_data()

    def on_screen_resume(self) -> None:
        if self.is_mounted and self.refresh_on_return:
            self.refresh_on_return = False
            self.query_one("#menu", ListView).focus()
            self.refresh_data()

    def refresh_data(self) -> None:
        if self.loading:
            return
        self.loading = True
        self.kolo.launch(self._load())

    async def _load(self) -> None:
        def read(assistant: Assistant) -> tuple[int, int, list[Birthday], date]:
            today = assistant.today()
            return len(assistant.contacts(today=today)), len(assistant.notes()), assistant.birthdays(today=today), today

        try:
            contacts, notes, birthdays, today = await self.kolo.io.call(read)
        except Exception as error:
            if not self.owns_view():
                return
            self.status("Дані недоступні. Повторіть читання або вийдіть.", error=True)
            self.query_one("#summary", Static).update("Не оновлено")
            self.query_one("#retry", Button).display = True
            self.kolo.push_screen(ReadErrorScreen(error_text(error), str(self.kolo.path)), self._read_answer)
        else:
            if not self.owns_view():
                return
            self.kolo.last_day = today
            lines = [f"Контактів: {contacts}  ·  Нотаток: {notes}", "Дні народження · найближчі 7 днів"]
            lines.extend(
                f"{item.contact.name} · {item.anniversary:%d.%m} · через {item.days_until} дн." for item in birthdays
            )
            if not birthdays:
                lines.append("Найближчих днів народження немає.")
            self.query_one("#summary", Static).update(safe("\n".join(lines), multiline=True))
            self.query_one("#retry", Button).display = False
            self.status("↑ ↓ — обрати розділ · Enter — відкрити")
        finally:
            self.loading = False

    def _read_answer(self, answer: str | None) -> None:
        if answer == "retry":
            self.refresh_data()
        elif answer == "quit":
            self.kolo.action_safe_quit()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.refresh_on_return = True
        index = event.list_view.index
        if index in (0, 1, 2):
            self.kolo.push_screen(RecordsScreen(("contacts", "notes", "birthdays")[index]))
        elif index == 3:
            self.kolo.push_screen(HelpScreen())
        elif index == 4:
            self.kolo.action_safe_quit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.refresh_data()

    def leave(self) -> None:
        self.kolo.action_safe_quit()


@dataclass
class ListContext:
    selected_id: str | None = None
    selected_index: int = 0
    focus_id: str = "records"
    scroll: float = 0


class RecordsScreen(KoloScreen):
    BINDINGS = [*KoloScreen.BINDINGS, Binding("f2", "add", "Додати")]

    def __init__(self, kind: Kind) -> None:
        super().__init__()
        self.kind = kind
        self.context = ListContext()
        self.rows: list[Record] = []
        self.generation = 0
        self.loading = False
        self.reload_requested = False
        self.ready = False
        self.refresh_on_return = False
        self.applied_days = 7
        self.saved_id: str | None = None
        self.notice = ""

    def compose(self) -> ComposeResult:
        yield from self.chrome({"contacts": "Контакти", "notes": "Нотатки", "birthdays": "Дні народження"}[self.kind])
        with VerticalScroll(id="content"):
            if self.kind == "birthdays":
                yield Label("Кількість днів · ціле число 0–366")
                yield Input("7", id="days")
            else:
                yield Label(
                    "Пошук · ім’я, телефон, адреса, email" if self.kind == "contacts" else "Пошук у заголовку й тексті"
                )
                yield Input(id="query")
            if self.kind == "notes":
                yield Label("Точний тег · порожнє поле — усі")
                yield Input(id="tag")
                yield Select([("Заголовок", "title"), ("Теги", "tags")], value="title", allow_blank=False, id="sort")
            with Horizontal(classes="actions"):
                yield Button("Застосувати", id="apply")
                if self.kind != "birthdays":
                    yield Button("Очистити фільтри", id="clear")
            yield Static("Читаємо дані…", id="status")
            yield ListView(id="records")
            with Horizontal(classes="actions"):
                if self.kind != "birthdays":
                    yield Button("Додати", id="add", variant="primary")
                yield Button("Назад", id="back")
        yield self.footer()

    def on_mount(self) -> None:
        self.refresh_data()

    def remember(self) -> None:
        self.refresh_on_return = True
        view = self.query_one("#records", ListView)
        self.context.scroll = float(view.scroll_y)
        self.context.focus_id = self.focused.id if self.focused and self.focused.id else "records"

    def on_screen_resume(self) -> None:
        if self.is_mounted and self.refresh_on_return:
            self.refresh_on_return = False
            self.refresh_data()

    def refresh_data(self) -> None:
        self.generation += 1
        self.ready = False
        self.query_one("#records", ListView).disabled = True
        self.query("#add").set(disabled=True)
        if self.loading:
            self.reload_requested = True
            return
        self.loading = True
        self.status("Читаємо дані…")
        self.kolo.launch(self._load(self.generation))

    def request(self) -> tuple[str, str | None, str, int]:
        if self.kind == "birthdays":
            raw = self.query_one("#days", Input).value
            try:
                days = validation.days(int(raw))
            except (ValueError, InputError) as error:
                raise InputError(
                    f"Введіть ціле число від 0 до 366. Попередній інтервал {self.applied_days} днів."
                ) from error
            return "", None, "title", days
        query = self.query_one("#query", Input).value
        tag = self.query_one("#tag", Input).value.strip() if self.kind == "notes" else ""
        sort = str(self.query_one("#sort", Select).value) if self.kind == "notes" else "title"
        return query, tag or None, sort, self.applied_days

    async def _load(self, generation: int) -> None:
        try:
            query, tag, sort, days = self.request()

            def read(assistant: Assistant) -> tuple[list[Record], list[str], date]:
                today = assistant.today()
                if self.kind == "birthdays":
                    birthdays = assistant.birthdays(days, today=today)
                    return (
                        list(item.contact for item in birthdays),
                        [f"{item.anniversary:%d.%m.%Y} · через {item.days_until} дн." for item in birthdays],
                        today,
                    )
                values: list[Record] = (
                    list(assistant.contacts(query, today=today))
                    if self.kind == "contacts"
                    else list(assistant.notes(query, tag, sort))
                )
                secondary = [
                    " · ".join(value.phones) or value.email or "Телефон не вказано"
                    if isinstance(value, Contact)
                    else ", ".join(value.tags) or value.body[:100]
                    for value in values
                ]
                return values, secondary, today

            values, secondary, today = await self.kolo.io.call(read)
            if generation != self.generation or not self.owns_view():
                return
            self.kolo.last_day = today
            self.applied_days = days
            await self._render_rows(values, secondary, bool(query.strip() or tag))
        except InputError as error:
            if generation != self.generation or not self.owns_view():
                return
            self.status(str(error), error=True)
            self.query_one("#days" if self.kind == "birthdays" else "#query", Input).focus()
        except Exception as error:
            if generation == self.generation and self.owns_view():
                self.status(f"{self.notice} Не оновлено; дії із записами недоступні.", error=True)
                self.kolo.push_screen(ReadErrorScreen(error_text(error), str(self.kolo.path)), self._read_answer)
        finally:
            self.loading = False
            if self.reload_requested:
                self.reload_requested = False
                if self.owns_view():
                    self.refresh_data()

    async def _render_rows(self, values: list[Record], secondary: list[str], filtered: bool) -> None:
        view = self.query_one("#records", ListView)
        await view.clear()
        await view.extend(RecordRow(value, detail) for value, detail in zip(values, secondary, strict=True))
        self.rows, self.ready = values, True
        target = self.saved_id or self.context.selected_id
        index = next(
            (index for index, value in enumerate(values) if value.id == target),
            min(self.context.selected_index, max(0, len(values) - 1)),
        )
        self.context.selected_id = values[index].id if values else None
        self.context.selected_index = index
        view.index = index if values else None
        view.disabled = False
        self.query("#add").set(disabled=False)
        message = f"Записів: {len(values)} · ↑ ↓ — обрати · Enter — деталі"
        if not values:
            message = (
                "Нічого не знайдено. Змініть або очистіть фільтри."
                if filtered
                else "Контактів поки немає. Додайте перший контакт."
                if self.kind == "contacts"
                else "Нотаток поки немає. Додайте першу нотатку."
                if self.kind == "notes"
                else f"Немає днів народження за {self.applied_days} днів."
            )
        if self.saved_id and not any(value.id == self.saved_id for value in values):
            self.notice += " Збережений запис не відповідає поточному фільтру."
        self.status(f"{self.notice}\n{message}".strip())
        self.saved_id = None
        focus = self.context.focus_id
        if not values and focus == "records":
            focus = "days" if self.kind == "birthdays" else "add"
        self.set_focus(self.query_one(f"#{focus}"), scroll_visible=False)
        self.call_after_refresh(self._restore_viewport, self.generation, focus)

    def _restore_viewport(self, generation: int, focus: str) -> None:
        if generation != self.generation or not self.owns_view():
            return
        view = self.query_one("#records", ListView)
        view.scroll_to(y=self.context.scroll, animate=False, force=True, immediate=True)
        if focus == "records" and view.index is not None:
            view.scroll_to_region(
                view.children[view.index].virtual_region_with_margin, animate=False, force=True, immediate=True
            )
        self._reveal_after_inner_layout(generation, focus)

    def _reveal_after_inner_layout(self, generation: int, focus: str) -> None:
        self.call_after_refresh(self._reveal_focus, generation, focus)

    def _reveal_focus(self, generation: int, focus: str) -> None:
        if generation != self.generation or not self.owns_view() or self.focused is not self.query_one(f"#{focus}"):
            return
        view = self.query_one("#records", ListView)
        if focus == "records" and view.index is not None:
            content = self.query_one("#content", VerticalScroll)
            row = view.children[view.index]
            # Convert screen geometry to outer virtual coordinates without changing the inner list offset.
            region = row.region.translate(content.scroll_offset - content.scrollable_content_region.offset)
            content.scroll_to_region(region, animate=False, force=True, immediate=True, x_axis=False)
        else:
            self.query_one(f"#{focus}").scroll_visible(animate=False, immediate=True, force=True)

    def _read_answer(self, answer: str | None) -> None:
        if answer == "retry":
            self.refresh_data()
        elif answer == "back":
            self.kolo.pop_screen()
        elif answer == "quit":
            self.kolo.action_safe_quit()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if isinstance(event.item, RecordRow) and self.ready:
            self.context.selected_id = event.item.value.id
            self.context.selected_index = event.list_view.index or 0
            if self.focused is event.list_view:
                self.call_after_refresh(self._reveal_after_inner_layout, self.generation, "records")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if self.ready and isinstance(event.item, RecordRow) and event.item.value in self.rows:
            self.remember()
            self.kolo.push_screen(DetailScreen(self, event.item.value.id, isinstance(event.item.value, Contact)))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.context.focus_id = "records"
        self.refresh_data()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        action = event.button.id
        if action in {"apply", "clear"}:
            if action == "clear":
                for widget in self.query(Input):
                    widget.value = ""
                if self.kind == "notes":
                    self.query_one("#sort", Select).value = "title"
            self.context = ListContext()
            self.notice = ""
            self.refresh_data()
        elif action == "add":
            self.action_add()
        elif action == "back":
            self.action_back()

    def action_add(self) -> None:
        if self.ready and self.kind != "birthdays":
            self.remember()
            self.kolo.push_screen(FormScreen(self))


class DetailScreen(KoloScreen):
    def __init__(self, origin: RecordsScreen, identifier: str, contact: bool) -> None:
        super().__init__()
        self.origin, self.identifier, self.contact = origin, identifier, contact
        self.value: Record | None = None
        self.loading = False

    def compose(self) -> ComposeResult:
        yield from self.chrome("Деталі контакту" if self.contact else "Деталі нотатки")
        with VerticalScroll(id="content"):
            yield Static("Читаємо дані…", id="details")
        yield Static("", id="status")
        with Horizontal(id="detail-actions", classes="actions"):
            yield Button("Редагувати", id="edit", variant="primary", disabled=True)
            yield Button("Видалити", id="delete", variant="error", disabled=True)
            yield Button("Назад", id="back")
        yield self.footer()

    def on_mount(self) -> None:
        self.refresh_data()

    def on_screen_resume(self) -> None:
        if self.is_mounted and self.kolo.screen is self and (self.refresh_on_return or self.value is None):
            self.refresh_on_return = False
            self.refresh_data()

    def refresh_data(self) -> None:
        if not self.loading:
            self.loading = True
            self.query("#edit, #delete").set(disabled=True)
            self.kolo.launch(self._load())

    async def _load(self) -> None:
        try:
            value = await self.kolo.io.call(
                lambda assistant: (
                    assistant.contact(self.identifier) if self.contact else assistant.note(self.identifier)
                )
            )
        except InputError as error:
            if not self.owns_view():
                return
            self.origin.notice = str(error)
            await self.kolo.pop_screen()
            self.origin.refresh_data()
        except Exception as error:
            if not self.owns_view():
                return
            self.status("Не оновлено; дії недоступні.", error=True)
            self.kolo.push_screen(ReadErrorScreen(error_text(error), str(self.kolo.path)), self._read_answer)
        else:
            if not self.owns_view():
                return
            self.value = value
            self.query_one("#details", Static).update(safe(self.detail_text(value), multiline=True))
            self.query("#edit, #delete").set(disabled=False)
            self.query_one("#edit", Button).focus(scroll_visible=False)
        finally:
            self.loading = False

    @staticmethod
    def detail_text(value: Record) -> str:
        if isinstance(value, Contact):
            return (
                f"{value.name}\n\nID  {value.id}\nТелефони\n"
                + ("\n".join(value.phones) or "Не вказано")
                + (
                    f"\n\nАдреса  {value.address or 'Не вказано'}"
                    f"\nEmail  {value.email or 'Не вказано'}"
                    f"\nДата народження  {value.birthday or 'Не вказано'}"
                )
            )
        return f"{value.title}\n\nID  {value.id}\nТеги  {', '.join(value.tags) or 'Немає'}\n\n{value.body}"

    def _read_answer(self, answer: str | None) -> None:
        if answer == "retry":
            self.refresh_data()
        elif answer == "back":
            self.kolo.pop_screen()
        elif answer == "quit":
            self.kolo.action_safe_quit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.action_back()
        elif self.value is not None and event.button.id == "edit":
            self.kolo.push_screen(FormScreen(self.origin, self.value))
        elif self.value is not None and event.button.id == "delete":
            label = self.value.name if isinstance(self.value, Contact) else self.value.title
            kind = "контакт" if self.contact else "нотатку"
            self.kolo.push_screen(
                ConfirmScreen(f"Видалити {kind}?", "Залишити", "Видалити", f"{label}\n{self.value.id}"),
                self._delete_answer,
            )

    def _delete_answer(self, confirmed: bool | None) -> None:
        if confirmed and not self.loading:
            self.loading = True
            self.query("#edit, #delete, #back").set(disabled=True)
            self.status("Видаляємо…")
            self.kolo.launch(self._delete(), write=True)

    async def _delete(self) -> None:
        try:
            await self.kolo.io.call(
                lambda assistant: (
                    assistant.delete_contact(self.identifier)
                    if self.contact
                    else assistant.delete_note(self.identifier)
                )
            )
        except InputError as error:
            self.origin.context.selected_id = None
            self.origin.context.focus_id = "records"
            self.origin.notice = str(error)
            await self.kolo.pop_screen()
            self.origin.refresh_data()
        except Exception as error:
            self.status(error_text(error), error=True)
            self.query("#edit, #delete, #back").set(disabled=False)
            self.query_one("#delete", Button).focus()
            self.loading = False
        else:
            self.origin.context.selected_id = None
            self.origin.notice = f"Видалено {self.identifier}."
            await self.kolo.pop_screen()
            self.origin.refresh_data()


class HelpScreen(KoloScreen):
    def compose(self) -> ComposeResult:
        yield from self.chrome("Довідка")
        with VerticalScroll(id="content"):
            yield Static(
                (
                    "Коло працює локально й без мережі.\n\n"
                    "↑ ↓ — вибір у меню та списках; Enter — відкрити.\n"
                    "Tab / Shift+Tab — наступний / попередній елемент.\n"
                    "Esc або «Назад» — повернутися.\n"
                    "Ctrl+S — зберегти форму; F2 — додати у списку.\n"
                    "У тексті стрілки рухають курсор, Enter додає рядок; F7 — вибрати весь текст.\n"
                    "Телефони й теги — по одному на рядок.\n"
                    "Ctrl+Q / Ctrl+C — безпечний вихід із підтвердженням.\n\n"
                    "--line-mode — попереднє числове меню.\n--plain — без кольорів.\n"
                    "Командна довідка: kolo --help"
                ),
                id="help-text",
            )
            yield Button("Назад", id="back")
        yield self.footer()

    def on_mount(self) -> None:
        self.query_one("#back", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.action_back()
