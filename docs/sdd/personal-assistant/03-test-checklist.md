# «Коло» — перевірки та докази

Автор: architect-agent `/root/architect_resume`, 2026-10-24. Контракт: [PRD](00-prd-delta.md), [spec](02-spec.yaml). Нижче заплановані assertions; це не звіт про виконані тести. Baseline: репозиторій без HEAD, застосунку, `pyproject.toml` та тестів; якісні перевірки **NOT RUN**, а не PASS.

## Ізоляція й метод

- Усі тести використовують `tmp_path`, вигадані дані та явний `--data-dir`; HOME/XDG підміняються тимчасовими каталогами із sentinel. Особисті дані й `.env*` не читаються. Перевіряти fingerprints sentinel до/після.
- Чисті правила — unit tests; збереження — справжній stdlib SQLite; командний контракт — окремі subprocess; взаємодія — WSL stdlib `pty` із bounded timeout, `TIOCSWINSZ` і сигналами. Не замінювати PTY-перевірку Ctrl+C простим викликом функції.
- Фіксовані clock/ID передавати в код через параметри. Не додавати production-прапорці для тестових дат або аварій. SQL failure ін’єктувати на межі connection/transaction у тесті.
- Мережеві connect у in-process runtime-тестах заборонені. Перевірка встановлення/аудит залежностей може користуватися мережею.

## AC → конкретні assertions

Назви тестів орієнтовні; розробник/QA фіксують фактичні імена у звіті без втрати перевірок.

| AC | Файл тестів | Обов’язковий доказ |
|---|---|---|
| 01 | `tests/test_interactive.py` | PTY нового data-dir: «Коло», 0/0, блок 7 днів, 1/2/3/4/0; зайти/назад у кожен розділ; невідомий пункт лишає меню живим; порожній розділ пояснює додавання. |
| 02 | `tests/test_storage.py`, `tests/test_cli.py` | Мінімальний і повний Contact roundtrip у новому процесі; дублікати name/phone/email між контактами не зливаються; IDs різні та повністю видимі; forced ID collision повторюється без втрати попереднього. |
| 03 | `tests/test_validation.py`, `tests/test_services.py`, `tests/test_interactive.py` | Межі name 0/1/120/121, address 500/501; phone 9/10/15/16 цифр, ASCII/Unicode digits, + у середині, tabs, formatted duplicate; email межі/крапки/домен; дата invalid/future. Edit address+invalid email не змінює нічого. PTY виправляє лише email, зберігши name/phones. |
| 04 | `tests/test_services.py`, `tests/test_cli.py` | Український casefold у name/address/email; formatted phone substring; trim/empty query; 0 matches відрізняється від empty store. Edit з тим самим ID, omission зберігає, clear прибирає optional, phone list повністю замінений; value+clear -> 2. |
| 05 | `tests/test_cli.py`, `tests/test_interactive.py` | Delete без --yes завершується 2 без читання stdin/зміни запису; --yes видаляє після restart. PTY Enter/«ні»/Ctrl+C скасовує, «так» підтверджує з видимими ID+label. Невідомий ID show/edit/delete для обох типів -> 2, інші записи незмінні. |
| 06 | `tests/test_birthdays.py` | today=2026-12-30,N=3: 01-02 входить, 01-03 ні; N=0 лише today; N=366 кожен контакт не більше разу; без birthday пропуск; порядок дата/name.casefold/ID. -1/367/1.5/«x» -> 2 у CLI. |
| 07 | `tests/test_birthdays.py` | 2000-02-29: 2025-02-28,N=0 входить; 2028-02-28,N=0 ні,N=1 так; після річниці наступний рік; stored birthday лишається 2000-02-29. Clock 2026-10-23T22:30Z дає 24 жовтня в Kyiv/23 у UTC; invalid KOLO_TIMEZONE -> 2 без storage access. |
| 08 | `tests/test_validation.py`, `tests/test_storage.py`, `tests/test_cli.py` | Note CRUD/restart, duplicate titles з різними ID; title 0/120/121, body whitespace/1/10000/10001; multiline Unicode з початковим/кінцевим LF зберігається. Invalid multi-field edit атомарний; --body-file UTF-8/«-», invalid UTF-8/missing file -> 2 без запису. |
| 09 | `tests/test_services.py` | «Робота»+« робота » -> один «робота»; empty відкинуто, max40 до casefold, Unicode expansion зчитується; comma literal; clear tags. Search title/body AND exact normalized tag; tags sort на [«а»], [«а»,«б»], [«б»], [] та title/ID tie-break; title sort за замовчуванням. |
| 10 | `tests/test_interactive.py` | PTY Ctrl+C у create/edit/multiline/delete повертає до панелі, restart не бачить draft; EOF у menu/form/confirmation -> 0; exit -> 0. Невалідний body повторює тільки body; `.`/`..` escaping та edit Enter/!clear/!!clear працюють. |
| 11 | `tests/test_storage.py`, `tests/test_cli.py` | Окремі subprocess з різними cwd читають ті самі IDs/fields; absolute/relative explicit data-dir, absolute XDG/default/fallback paths перевірені у fake HOME. Немає success до commit; помилка commit не повертає candidate як accepted. |
| 12 | `tests/test_storage.py`, `tests/test_cli.py` | Fault після parent write/перед commit -> rollback, reopen бачить весь попередній стан, без «Збережено». Corrupt/zero-byte/unknown application_id/version/schema/FK/domain -> 1, абсолютний safe path у stderr, hash незмінний. Permission/read failure/3s lock -> 1 без traceback/reset. Crash першого initialization до commit/перед link лишає final відсутнім і наступний startup працює; після link final уже валідний. Окремі crash тести нижче. |
| 13 | `tests/test_cli.py` | Повний subprocess add→list/search→show→edit→новий процес→delete для contacts/notes; усі рівні help українські, не відкривають DB. Missing arguments/unknown action/invalid enum -> 2; success stdout/errors stderr, redirected обидва без ANSI. No-command/demo без TTY -> 2 з bounded timeout; команди не питають нічого. KeyboardInterrupt командного шляху -> 130. |
| 14 | `tests/test_demo.py`, `tests/test_interactive.py` | PTY demo показує banner/тимчасовий path, synthetic contacts/notes/tags/today anniversary; зміни видно тільки в ньому. Fixture birthday=today.replace(year=min(2000,today.year)): за clock today=2028-02-29 точно 2000-02-29, валідний і дає days_until=0; demo стартує. Дата раніше 2000 лишається today. Другий demo починається з fixtures. Особисті fake HOME/XDG fingerprints незмінні, path resolver особистого каталогу не викликається; demo+explicit --data-dir -> 2 до filesystem access; EOF/exit прибирає власний temp-dir. |
| 15 | `tests/test_render.py`, `tests/test_interactive.py` | 60/80/120 columns: меню/help/форма/list/details, довгі українські значення, full ID/шлях до деталей, семантика без кольору. `[bold]` буквальний; ESC/OSC/CSI/C0/C1/Cf/bidi не виконуються, unsafe chars escaped; у multiline LF і tab policy. Перевірити user strings також у confirmations/errors/paths; --plain/NO_COLOR/non-TTY без ANSI. |
| 16 | `tests/test_cli.py` + QA запуск | lock sync/build, console+module entrypoints, run.sh з іншого cwd, README-команди, PTY demo; tool --help якщо tool установлений. Зафіксувати actual command/result/source fingerprint; не називати непроведений запуск PASS. |

## Crash-safe перша ініціалізація

`tests/test_storage.py`: у порожньому tmp data-dir subprocess виконує справжній initialization; тестовий wrapper завершує процес через `os._exit`/SIGKILL (1) після DDL перед першим commit, (2) після commit/close/fsync перед os.link, (3) після os.link до unlink temp. Без production crash flags. У випадках 1/2 `kolo.sqlite3` відсутній; private temp/journal може лишитися. Наступний звичайний запуск без ручного cleanup створює валідну порожню v1, CLI CRUD працює. У випадку 3 final уже має correct app/version/tables і проходить startup. Перевірити 0600 та незмінність sentinel/залишкового temp під час повторного startup. Окремий race/injected FileExistsError на link: існуючий unknown final має незмінний hash, code1, немає replace/fallback. Всі test files лише в tmp-dir.

## Вузька перевірка hot rollback

`tests/test_storage.py`: створити валідну v1 базу з кількома сторінками й committed записами. Child subprocess відкриває SQLite із малим cache, `BEGIN IMMEDIATE`, змінює достатньо сторінок для spill і повідомляє readiness через pipe; завершити його до commit через `os._exit`/SIGKILL. Assert існує hot journal, readonly читання дає `SQLITE_READONLY_ROLLBACK`, header app/version відомі. Звичайне відкриття Kolo має дозволити лише native rollback, пройти повну перевірку, повернути точний останній committed набір і не прийняти частковий edit. Не симулювати recovery лише monkeypatch-кодом помилки. Використовувати синтетичні великі дані тільки тут, cleanup у tmp-dir.

Окремо невідомий header/version із залишковим `-journal`: hash оригіналу незмінний, жодного application reset/replacement. Якщо native rollback не може відновити справжній recognized файл, повернути 1 і лишити матеріали для ручного розбору; backup/restore subsystem не вводиться. Несправний носій/fsync не моделюється як гарантія.

## Повний gate (WSL, із кореня репозиторію)

У `pyproject.toml` встановити strict mypy на весь Python repo/tests та coverage всього `src/kolo` без UI/CLI виключень. Команди запускаються послідовно; зберегти stdout/stderr і exit code кожної, невдалу не приховувати.

```sh
/home/iknow/.local/bin/uv sync --locked --all-groups
/home/iknow/.local/bin/uv run --no-sync ruff format --check .
/home/iknow/.local/bin/uv run --no-sync ruff check .
/home/iknow/.local/bin/uv run --no-sync mypy .
/home/iknow/.local/bin/uv run --no-sync pytest --cov=src/kolo --cov-report=term-missing --cov-fail-under=80
/home/iknow/.local/bin/uv run --no-sync bandit -r src/kolo
/home/iknow/.local/bin/uv export --frozen --all-groups --no-emit-project --format requirements-txt --output-file /tmp/kolo-audit-requirements.txt
/home/iknow/.local/bin/uv run --no-sync pip-audit --requirement /tmp/kolo-audit-requirements.txt --no-deps --disable-pip --require-hashes
/home/iknow/.local/bin/uv build
/home/iknow/.local/bin/uv run --no-sync kolo --help
/home/iknow/.local/bin/uv run --no-sync python -m kolo --help
```

Аудит охоплює всі resolved runtime/dev/transitive пакети з lock. Немає blanket ignore/skip/coverage omission. Якщо аудит чи інший required check недоступний — NOT RUN і gate не пройдено. Warning/finding потребує конкретної оцінки й виправлення, не замовчування.

Після gate QA окремо виконує `uv sync`, `uv run kolo --help`, `uv run kolo demo` у PTY, запуск `run.sh` з іншого cwd та візуальний огляд transcript 60/80/120. Якщо controller встановлює локальний tool — `/home/iknow/.local/bin/kolo --help` і isolated CRUD. На 10 000 синтетичних сутностей записати disk size/list-search elapsed без вигаданого SLA; це вимір місткості, не нова runtime-функція.

## Форма звіту

Source: branch/HEAD або unborn HEAD, SHA-256 змінених файлів/lock, input spec hash. Для кожної команди — PASS/FAIL/NOT RUN і причина; measured coverage; AC→actual test assertions; PTY evidence/widths; дефекти з файлом/рядком/repro; окремий verdict QA та reviewer. Не оголошувати готовність за самими документами.
