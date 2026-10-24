import argparse
import sys
from collections.abc import Iterable, Sequence
from functools import partial
from pathlib import Path
from typing import BinaryIO, Never, TextIO, cast

from kolo import __version__, validation
from kolo.birthdays import local_today, timezone
from kolo.errors import InputError, StorageError
from kolo.models import UNSET, ContactPatch, NotePatch
from kolo.render import Renderer, make_console, safe
from kolo.services import Assistant
from kolo.storage import Store, data_directory


class UkrainianFormatter(argparse.HelpFormatter):
    def add_usage(
        self,
        usage: str | None,
        actions: Iterable[argparse.Action],
        groups: Iterable[argparse._MutuallyExclusiveGroup],
        prefix: str | None = None,
    ) -> None:
        super().add_usage(usage, actions, groups, "Використання: " if prefix is None else prefix)


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise InputError(f"Перевірте аргументи та обов’язкові поля: {self.prog} --help.")

    def _print_message(self, message: str | None, file: object = None) -> None:
        if message:
            make_console(cast(TextIO, sys.stderr if file is sys.stderr else sys.stdout)).print(
                safe(message, multiline=True), end=""
            )


def localize(parser: argparse.ArgumentParser) -> None:
    parser._positionals.title = "Дії та аргументи"
    parser._optionals.title = "Опції"
    parser.add_argument("-h", "--help", action="help", help="показати цю довідку й вийти")


def parser_node(prog: str, description: str, example: str) -> Parser:
    parser = Parser(
        prog=prog,
        description=description,
        epilog=f"Приклад: {example}",
        formatter_class=UkrainianFormatter,
        add_help=False,
    )
    localize(parser)
    return parser


def _example(kind: str, action: str) -> str:
    record_id = "c_0123456789ab" if kind == "contacts" else "n_0123456789ab"
    suffix = {"list": "", "show": record_id, "delete": f"{record_id} --yes"}
    if kind == "contacts":
        suffix.update(
            {"add": '--name "Олена" --phone "+380671234567"', "edit": f"{record_id} --email olena@example.com"}
        )
    else:
        suffix.update(
            {
                "add": '--title "Ідеї" --body "Перша думка" --tag робота',
                "edit": f'{record_id} --title "Новий заголовок"',
            }
        )
    return f"kolo {kind} {action} {suffix[action]}".rstrip()


def make_parser() -> Parser:
    parser = parser_node("kolo", "Коло — локальні контакти, нотатки й дні народження.", "kolo demo")
    parser.add_argument("--version", action="version", version=f"Коло {__version__}", help="версія застосунку")
    parser.add_argument("--data-dir", metavar="ШЛЯХ", help="окремий каталог даних; опція перед командою")
    parser.add_argument("--plain", action="store_true", help="простий вивід без кольору")
    parser.add_argument("--line-mode", action="store_true", help="рядкове меню з числовим вибором")
    sub = parser.add_subparsers(dest="command", title="Команди", metavar="КОМАНДА", parser_class=Parser)
    for kind, label in (("contacts", "Контакти"), ("notes", "Нотатки")):
        group = sub.add_parser(
            kind,
            description=f"{label}: створення, пошук і зміни.",
            help=label,
            epilog=f"Приклад: kolo {kind} list",
            formatter_class=UkrainianFormatter,
            add_help=False,
        )
        localize(group)
        actions = group.add_subparsers(dest="action", required=True, metavar="ДІЯ", title="Дії")
        for action, text in (
            ("list", "Список і пошук"),
            ("show", "Повні деталі"),
            ("add", "Додати запис"),
            ("edit", "Редагувати запис"),
            ("delete", "Видалити запис"),
        ):
            node = actions.add_parser(
                action,
                description=text,
                help=text,
                formatter_class=UkrainianFormatter,
                epilog=f"Приклад: {_example(kind, action)}",
                add_help=False,
            )
            localize(node)
            if action in {"show", "edit", "delete"}:
                node.add_argument("id", metavar="ID", help="повний незмінний ID зі списку")
            if action == "list":
                node.add_argument("--search", default="", metavar="ТЕКСТ", help="пошук без урахування регістру")
                if kind == "notes":
                    node.add_argument("--tag", metavar="ТЕГ", help="точний тег разом із пошуком")
                    node.add_argument("--sort", choices=("title", "tags"), default="title", help="порядок списку")
            if action in {"add", "edit"}:
                _field_arguments(node, kind, edit=action == "edit")
            if action == "delete":
                node.add_argument("--yes", action="store_true", help="явно підтвердити видалення")
    birthday_parser = sub.add_parser(
        "birthdays",
        description="Найближчі дні народження, включно з сьогодні.",
        help="Дні народження",
        epilog="Приклад: kolo birthdays --days 7",
        formatter_class=UkrainianFormatter,
        add_help=False,
    )
    localize(birthday_parser)
    birthday_parser.add_argument("--days", type=int, default=7, metavar="N", help="ціле число від 0 до 366; типово 7")
    demo_parser = sub.add_parser(
        "demo",
        description="Безпечна демонстрація з вигаданими даними.",
        help="Демонстрація",
        epilog="Приклад: kolo demo",
        formatter_class=UkrainianFormatter,
        add_help=False,
    )
    localize(demo_parser)
    return parser


def _field_arguments(parser: argparse.ArgumentParser, kind: str, *, edit: bool) -> None:
    name = "name" if kind == "contacts" else "title"
    parser.add_argument(f"--{name}", required=not edit, metavar="ТЕКСТ", help="обов’язкове поле: 1–120 символів")
    if kind == "contacts":
        for field, help_text in (
            ("phone", "10–15 цифр, повторіть опцію для кількох номерів"),
            ("address", "адреса до 500 символів"),
            ("email", "адреса name@example.com"),
            ("birthday", "дата РРРР-ММ-ДД, не в майбутньому"),
        ):
            group = parser.add_mutually_exclusive_group()
            group.add_argument(
                f"--{field}", action="append" if field == "phone" else "store", metavar="ЗНАЧЕННЯ", help=help_text
            )
            if edit:
                clear = "phones" if field == "phone" else field
                group.add_argument(f"--clear-{clear}", action="store_true", help="очистити поле")
    else:
        body_group = parser.add_mutually_exclusive_group(required=not edit)
        body_group.add_argument("--body", metavar="ТЕКСТ", help="текст до 10000 символів із переносами")
        body_group.add_argument("--body-file", metavar="ШЛЯХ", help="UTF-8 файл; - означає весь stdin")
        tags = parser.add_mutually_exclusive_group()
        tags.add_argument("--tag", action="append", metavar="ТЕГ", help="тег до 40 символів; опцію можна повторити")
        if edit:
            tags.add_argument("--clear-tags", action="store_true", help="очистити всі теги")


def _stdin_text() -> str:
    binary = cast(BinaryIO | None, getattr(sys.stdin, "buffer", None))
    if binary is not None:
        return binary.read().decode("utf-8", errors="strict")
    return sys.stdin.read().encode("utf-8", errors="strict").decode("utf-8")


def _prepare(args: argparse.Namespace) -> None:
    if args.command in {"contacts", "notes"} and args.action == "delete" and not args.yes:
        raise InputError("Для видалення потрібно явно передати --yes. Запис залишено.")
    if args.command == "birthdays":
        validation.days(args.days)
    if args.command == "notes" and args.action in {"add", "edit"} and args.body_file is not None:
        try:
            if args.body_file == "-":
                args.body = _stdin_text()
            else:
                with Path(args.body_file).open("r", encoding="utf-8", newline="") as source:
                    args.body = source.read()
        except (OSError, UnicodeError, ValueError) as error:
            raise InputError(f"Не вдалося прочитати UTF-8 текст із {args.body_file}.") from error
    if args.command in {"contacts", "notes"} and args.action == "edit":
        excluded = {"command", "action", "id", "plain", "data_dir", "line_mode"}
        if not any(
            value is not None and value is not False for key, value in vars(args).items() if key not in excluded
        ):
            raise InputError("Для редагування передайте хоча б одне поле або --clear-….")


def _contact_patch(args: argparse.Namespace) -> ContactPatch:
    return ContactPatch(
        name=args.name if args.name is not None else UNSET,
        phones=() if args.clear_phones else tuple(args.phone) if args.phone is not None else UNSET,
        address=None if args.clear_address else args.address if args.address is not None else UNSET,
        email=None if args.clear_email else args.email if args.email is not None else UNSET,
        birthday=None if args.clear_birthday else args.birthday if args.birthday is not None else UNSET,
    )


def _note_patch(args: argparse.Namespace) -> NotePatch:
    return NotePatch(
        title=args.title if args.title is not None else UNSET,
        body=args.body if args.body is not None else UNSET,
        tags=() if args.clear_tags else tuple(args.tag) if args.tag is not None else UNSET,
    )


def execute(args: argparse.Namespace, assistant: Assistant, render: Renderer) -> None:
    if args.command == "birthdays":
        render.birthdays(assistant.birthdays(args.days), args.days)
    elif args.command == "contacts":
        _contacts(args, assistant, render)
    else:
        _notes(args, assistant, render)


def _contacts(args: argparse.Namespace, assistant: Assistant, render: Renderer) -> None:
    if args.action == "list":
        render.contacts(assistant.contacts(args.search), query=args.search)
    elif args.action == "show":
        render.details(assistant.contact(args.id))
    elif args.action == "delete":
        assistant.delete_contact(args.id)
        render.message(f"Видалено контакт {args.id}.", success=True)
    else:
        value = (
            assistant.add_contact(args.name, tuple(args.phone or ()), args.address, args.email, args.birthday)
            if args.action == "add"
            else assistant.edit_contact(args.id, _contact_patch(args))
        )
        render.message(f"Збережено контакт {value.id}.", success=True)


def _notes(args: argparse.Namespace, assistant: Assistant, render: Renderer) -> None:
    if args.action == "list":
        query = args.search if args.search else f"тег {args.tag}" if args.tag is not None else None
        render.notes(assistant.notes(args.search, args.tag, args.sort), query=query)
    elif args.action == "show":
        render.details(assistant.note(args.id))
    elif args.action == "delete":
        assistant.delete_note(args.id)
        render.message(f"Видалено нотатку {args.id}.", success=True)
    else:
        value = (
            assistant.add_note(args.title, args.body, tuple(args.tag or ()))
            if args.action == "add"
            else assistant.edit_note(args.id, _note_patch(args))
        )
        render.message(f"Збережено нотатку {value.id}.", success=True)


def main(argv: Sequence[str] | None = None) -> int:
    render = Renderer(make_console(), make_console(sys.stderr))
    try:
        args = make_parser().parse_args(argv)
        render = Renderer(make_console(plain=args.plain), make_console(sys.stderr, plain=args.plain))
        if args.command == "demo" and args.data_dir is not None:
            raise InputError("Демонстрація не приймає --data-dir: вона використовує окремі тимчасові дані.")
        if args.command in {None, "demo"} and not (sys.stdin.isatty() and sys.stdout.isatty()):
            raise InputError("Меню та demo потребують термінала. Використайте команди: kolo --help.")
        _prepare(args)
        today = partial(local_today, timezone())
        if args.command == "demo":
            from kolo.demo import run_demo

            return run_demo(render, today, line_mode=args.line_mode, plain=args.plain)
        directory = data_directory(args.data_dir)
        if args.command is None and not args.line_mode:
            from kolo.tui import run_tui

            return run_tui(
                lambda: Assistant(Store(directory, today()), today), directory / "kolo.sqlite3", plain=args.plain
            )
        assistant = Assistant(Store(directory, today()), today)
        if args.command is None:
            from kolo.interactive import run_interactive

            return run_interactive(assistant, render)
        execute(args, assistant, render)
        return 0
    except InputError as error:
        render.message(f"Помилка вводу: {error}", error=True)
        return 2
    except (StorageError, OSError, ValueError) as error:
        render.message(
            str(error) if isinstance(error, StorageError) else "Не вдалося виконати дію через помилку доступу.",
            error=True,
        )
        return 1
    except KeyboardInterrupt:
        render.message("Дію перервано.", error=True)
        return 130
