from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static, TextArea

from kolo import validation
from kolo.errors import FieldError, InputError, StorageError
from kolo.models import UNSET, Contact, ContactPatch, Note, NotePatch
from kolo.render import safe
from kolo.services import Assistant
from kolo.tui import KoloScreen

if TYPE_CHECKING:
    from kolo.tui_screens import RecordsScreen

SEPARATORS = frozenset("\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029")
FIELD_IDS = {
    "Ім’я": "name",
    "Телефони": "phones",
    "Адреса": "address",
    "Email": "email",
    "Дата народження": "birthday",
    "Заголовок": "title",
    "Текст": "body",
    "Теги": "tags",
}


@dataclass(frozen=True)
class BodyProjection:
    canonical: str
    spans: tuple[str, ...]

    @classmethod
    def from_raw(cls, raw: str) -> BodyProjection:
        spans: list[str] = []
        index = 0
        while index < len(raw):
            span = raw[index : index + 2] if raw[index : index + 2] == "\r\n" else raw[index]
            spans.append(span)
            index += len(span)
        canonical = "".join("\n" if span[0] in SEPARATORS else span for span in spans)
        return cls(canonical, tuple(spans))

    def restore(self, current: str) -> str:
        canonical = self.from_raw(current).canonical
        result: list[str] = []
        matcher = SequenceMatcher(None, self.canonical, canonical, autojunk=False)
        for operation, old_start, old_end, new_start, new_end in matcher.get_opcodes():
            if operation == "equal":
                result.extend(self.spans[old_start:old_end])
            elif operation != "delete":
                result.append(canonical[new_start:new_end])
        return "".join(result)


def error_text(error: Exception) -> str:
    if isinstance(error, InputError | StorageError):
        return str(error)
    return "Не вдалося виконати дію. Спробуйте ще раз; дані не скинуто."


class ConfirmScreen(ModalScreen[bool]):
    BINDINGS = [Binding("escape", "keep", "Залишити")]

    def __init__(self, title: str, keep: str, confirm: str, detail: str = "") -> None:
        super().__init__()
        self.heading, self.keep_label, self.confirm_label, self.detail = title, keep, confirm, detail

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="dialog"):
            yield Static(safe(self.heading), classes="dialog-title")
            if self.detail:
                yield Static(safe(self.detail, multiline=True))
            yield Button(self.keep_label, id="keep", variant="primary")
            yield Button(self.confirm_label, id="confirm", variant="error")

    def on_mount(self) -> None:
        self.query_one("#keep", Button).focus()

    def action_keep(self) -> None:
        self.dismiss(False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")


class ReadErrorScreen(ModalScreen[str]):
    BINDINGS = [Binding("escape", "back", "Назад")]

    def __init__(self, message: str, path: str) -> None:
        super().__init__()
        self.message, self.path = message, path

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="dialog"):
            yield Static("Не вдалося прочитати дані", classes="dialog-title")
            yield Static(safe(f"{self.message}\n{self.path}", multiline=True), id="read-error", classes="error")
            yield Button("Повторити", id="retry", variant="primary")
            yield Button("Назад", id="back")
            yield Button("Вийти", id="quit")

    def on_mount(self) -> None:
        self.query_one("#retry", Button).focus()

    def action_back(self) -> None:
        self.dismiss("back")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id or "back")


class FormScreen(KoloScreen):
    BINDINGS = [*KoloScreen.BINDINGS, Binding("ctrl+s", "save", "Зберегти")]

    def __init__(self, origin: RecordsScreen, old: Contact | Note | None = None) -> None:
        super().__init__()
        self.origin, self.old = origin, old
        self.contact_form = isinstance(old, Contact) or origin.kind == "contacts"
        self.initial: dict[str, str] = {}
        self.projection = BodyProjection.from_raw(old.body if isinstance(old, Note) else "")
        self.busy = False

    def compose(self) -> ComposeResult:
        yield from self.chrome("Редагування" if self.old else "Новий контакт" if self.contact_form else "Нова нотатка")
        with VerticalScroll(id="content"):
            yield Static("Tab — наступне поле · Ctrl+S — зберегти · Esc — назад", classes="muted")
            if self.contact_form:
                yield from self.contact_fields()
            else:
                yield from self.note_fields()
            with Horizontal(classes="actions"):
                yield Button("Зберегти", id="save", variant="primary")
                yield Button("Назад", id="back")
        yield Static("", id="status")
        yield self.footer()

    def contact_fields(self) -> ComposeResult:
        old = self.old if isinstance(self.old, Contact) else None
        fields = [
            ("Ім’я * · 1–120 символів", "name", old.name if old else ""),
            ("Адреса · до 500 символів", "address", old.address or "" if old else ""),
            ("Email · name@example.com", "email", old.email or "" if old else ""),
            ("Дата народження · РРРР-ММ-ДД", "birthday", old.birthday.isoformat() if old and old.birthday else ""),
        ]
        for label, identifier, value in fields:
            yield Label(label)
            yield Input(value, id=identifier)
            if identifier == "name":
                yield Label("Телефони · один номер на рядок, 10–15 цифр")
                yield TextArea("\n".join(old.phones) if old else "", id="phones", tab_behavior="focus")

    def note_fields(self) -> ComposeResult:
        old = self.old if isinstance(self.old, Note) else None
        yield Label("Заголовок * · 1–120 символів")
        yield Input(old.title if old else "", id="title")
        yield Label("Текст * · до 10000 символів · Enter додає рядок")
        yield TextArea(self.projection.canonical, id="body", tab_behavior="focus", soft_wrap=True)
        yield Label("Теги · один тег на рядок, до 40 символів; порожнє поле очищає")
        yield TextArea("\n".join(old.tags) if old else "", id="tags", tab_behavior="focus")

    def on_mount(self) -> None:
        self.initial = self.values()
        self.query_one("#name" if self.contact_form else "#title", Input).focus()

    def values(self) -> dict[str, str]:
        result = {widget.id: widget.value for widget in self.query(Input) if widget.id is not None}
        result.update({widget.id: widget.text for widget in self.query(TextArea) if widget.id is not None})
        return result

    @property
    def dirty(self) -> bool:
        return self.values() != self.initial

    def leave(self) -> None:
        if self.dirty:
            self.app.push_screen(
                ConfirmScreen("Відкинути незбережену чернетку?", "Продовжити редагування", "Відкинути"), self._discard
            )
        else:
            self.app.pop_screen()

    def _discard(self, confirmed: bool | None) -> None:
        if confirmed:
            self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.action_save()
        elif event.button.id == "back":
            self.action_back()

    def action_save(self) -> None:
        if self.busy:
            return
        self.busy = True
        self.status("Зберігаємо…")
        draft = self.values()
        for widget in self.query("Input, TextArea, Button"):
            widget.disabled = True
        self.kolo.launch(self._save(draft), write=True)

    def mutation(self, draft: dict[str, str]) -> Callable[[Assistant], Contact | Note]:
        def operation(assistant: Assistant) -> Contact | Note:
            if self.contact_form:
                phones = tuple(line for line in draft["phones"].splitlines() if line.strip())
                if isinstance(self.old, Contact):

                    def changed(field: str) -> bool:
                        return draft[field] != self.initial[field]

                    patch = ContactPatch(
                        draft["name"] if changed("name") else UNSET,
                        phones if changed("phones") else UNSET,
                        (draft["address"] or None) if changed("address") else UNSET,
                        (draft["email"] or None) if changed("email") else UNSET,
                        (draft["birthday"] or None) if changed("birthday") else UNSET,
                    )
                    return assistant.edit_contact(self.old.id, patch)
                return assistant.add_contact(draft["name"], phones, draft["address"], draft["email"], draft["birthday"])
            tags = tuple(line for line in draft["tags"].splitlines() if line.strip())
            if isinstance(self.old, Note):
                patch_note = NotePatch(
                    draft["title"] if draft["title"] != self.initial["title"] else UNSET,
                    self.validated_body(draft["body"]) if draft["body"] != self.initial["body"] else UNSET,
                    tags if draft["tags"] != self.initial["tags"] else UNSET,
                )
                return assistant.edit_note(self.old.id, patch_note)
            return assistant.add_note(draft["title"], self.validated_body(draft["body"]), tags)

        return operation

    def validated_body(self, current: str) -> str:
        canonical = validation.body(BodyProjection.from_raw(current).canonical)
        return validation.body(self.projection.restore(canonical))

    def _reveal_error_focus(self, identifier: str) -> None:
        if not self.is_mounted or not self.kolo.is_running or self.kolo.screen is not self:
            return
        field = self.query_one(f"#{identifier}")
        if self.focused is not field:
            return
        content = self.query_one("#content", VerticalScroll)
        region = field.region.translate(content.scroll_offset - content.scrollable_content_region.offset)
        content.scroll_to_region(region, animate=False, force=True, immediate=True, x_axis=False)

    async def _save(self, draft: dict[str, str]) -> None:
        try:
            value = await self.kolo.io.call(self.mutation(draft))
        except Exception as error:
            self.status(error_text(error), error=True)
            self.busy = False
            for widget in self.query("Input, TextArea, Button"):
                widget.disabled = False
            identifier = FIELD_IDS.get(error.field) if isinstance(error, FieldError) else "save"
            if identifier:
                self.set_focus(self.query_one(f"#{identifier}"), scroll_visible=False)
                self.call_after_refresh(self._reveal_error_focus, identifier)
            return
        self.origin.context.focus_id = "records"
        self.origin.saved_id = value.id
        self.origin.notice = f"Збережено {'контакт' if isinstance(value, Contact) else 'нотатку'} {value.id}."
        while self.kolo.screen is not self.origin:
            await self.kolo.pop_screen()
        self.origin.refresh_data()
