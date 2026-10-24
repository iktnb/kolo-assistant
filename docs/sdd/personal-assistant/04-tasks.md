# «Коло» — порядок реалізації

Автор: architect-agent `/root/architect_resume`, 2026-10-24. Входи: [PRD](00-prd-delta.md), [spec](02-spec.yaml), [test checklist](03-test-checklist.md). Планувальник може уточнити розмір задач без зміни контракту. Усі шляхи нижче від кореня `/home/iknow/goit-projects/personal-assistant`.

Порядок: **T01 → T02 → T03 → T04 → T05 → T06 → T07 → T08**. Тести відповідної поведінки додаються разом із кодом; повний gate після інтеграції. Немає іншого сервісу, Jvers-доступу, commit/push чи publication. Технічний reviewer погоджує дизайн до T01.

## personal-assistant

### T01 — відтворюваний пакет і запуск

- Власник: developer. Створити `pyproject.toml`, `uv.lock`, `.gitignore`, `.python-version` (3.12), `src/kolo/__init__.py`, `src/kolo/__main__.py`, початок `src/kolo/cli.py`, `tests/conftest.py`.
- Python >=3.12,<3.13, hatchling/src-layout, `kolo = kolo.cli:main`, runtime лише Rich. Dev groups: Ruff/mypy/pytest/pytest-cov/Bandit/pip-audit. Strict mypy включно з tests, coverage всього `src/kolo` >=80%; без blanket suppressions.
- `--help`/`--version` українською без filesystem/data-dir/clock side effects. Записати чесний baseline: app/tests раніше відсутні.
- Готово: locked sync і console/module help працюють; конфігурація покриває весь repo. AC-13,16.

### T02 — типізовані правила й календар

- Власник: developer; після T01. Створити `src/kolo/models.py`, `validation.py`, `errors.py`, `birthdays.py`; `tests/test_validation.py`, `tests/test_birthdays.py`.
- Immutable Contact/Note, помилки поля/відсутнього ID/storage, повні правила телефонів/email/дат/tag casefold; відрізняти omitted від explicit clear. ID-generation injectable, exact full ID.
- Inject aware clock, ZoneInfo Europe/Kyiv, optional KOLO_TIMEZONE; без зміни ОС. Birthday interval inclusive, leap policy та deterministic order як у spec.
- Готово: межі/негативні валідації, Kyiv-vs-UTC midnight, N0/366, year rollover і leap assertions checklist. AC-02,03,04,06,07,08,09.

### T03 — одне локальне сховище

- Власник: developer; після T02. Створити `src/kolo/storage.py`, `tests/test_storage.py`; схему тримати тут, без migration framework.
- Path resolution/ізоляція, нові 0700/0600, чотири таблиці DDL spec, application_id/user_version. Ініціалізувати лише private tempfile в тому самому data-dir: commit/close/fsync, atomic no-clobber os.link на final, fsync dir, unlink own temp, fsync dir; не використовувати os.replace. Crash leftovers ігнорувати, існуючий final ніколи не перезаписувати. Наявний zero-byte/unknown/corrupt/schema-invalid файл відхиляти без reset. Quoted URI mode=ro preflight; вузький recognized-header SQLITE_READONLY_ROLLBACK → native mode=rw rollback → повторна readonly validation.
- BEGIN IMMEDIATE/DELETE journal/FULL sync/3s busy timeout, parameter-bound SQL, atomic parent+children, rollback на failure; success тільки після commit. Жодного глобального connection/cache чи backup/restore subsystem.
- Готово: roundtrip/new process; FK/phone order/tag validity; faults після parent/перед commit, corrupt fingerprints, lock/permission diagnostics; справжні subprocess crashes першого initialization до commit/перед publication/після link із повторним startup без cleanup, no-clobber race та окремий child-crash hot journal test. AC-02,03,05,08,11,12.

### T04 — спільні операції

- Власник: developer; після T03. Створити `src/kolo/services.py`, `tests/test_services.py`.
- CRUD за ID, повний candidate merge/validate до SQL; Unicode search/sort у Python, phone digits, normalized exact tag AND query; missing ID user error; ID collision retry <=5.
- Не дублювати правила в CLI/формах. Дата одна на операцію, storage/render не питають користувача.
- Готово: duplicates лишаються окремо, clear/omission, atomic invalid edit, search і tuple sort assertions. AC-02—09,11,12.

### T05 — команди й безпечне відображення

- Власник: developer; після T04. Завершити `src/kolo/cli.py`, створити `src/kolo/render.py`, `tests/test_cli.py`, `tests/test_render.py`.
- Точне дерево/flags spec: contacts/notes CRUD, search/tag/sort, birthdays; --body/--body-file і stdin «-»; no hidden prompts, delete --yes. Localize argparse diagnostics; stdout/stderr і 0/1/2/130.
- Shared Rich Theme/Console та єдиний safe Text sanitizer для даних, шляхів і помилок. NO_COLOR/--plain/non-TTY, ширини <80/80..119/>=120, повний ID й доступ до повних деталей.
- Готово: subprocess full lifecycle/restart, invalid arguments/missing ID/stream/no-TTY; literal markup/control та width tests. AC-02—09,11—13,15,16.

### T06 — українська взаємодія й демонстрація

- Власник: developer; після T05. Створити `src/kolo/interactive.py`, `demo.py`, `tests/test_interactive.py`, `tests/test_demo.py`.
- Dashboard/submenus, keyboard-only navigation, empty/no-match states. Draft/per-field retry, edit Enter/!clear/!!clear, multiline dot escaping, explicit delete confirmation; Ctrl+C повертає меню, EOF завершує 0 без draft.
- `demo` тільки у TTY, TemporaryDirectory/вигадані приклади/banner/path. Birthday одного fixture = today.replace(year=min(2000,today.year)) із snapshot clock: високосний anchor 2000, для раніших дат today. Reject explicit --data-dir до будь-якого filesystem access. Особистий path не resolve/читати.
- Готово: реальні PTY assertions 60/80/120, Ctrl+C/EOF, retry, isolated/reseeded demo; fixed today=2028-02-29 запускається, birthday=2000-02-29/days_until=0; дата до2000 валідна, sentinel fingerprints незмінні. AC-01,03,05,10,14,15.

### T07 — інтегрований gate та незалежні перевірки

- Власник: developer для виправлень; reviewer і QA окремо перевіряють та звітують у призначені controller шляхи. Цей файл не надає їм дозволу змінювати production код.
- Усі команди `03-test-checklist.md`, повний pytest/coverage >=80%, strict whole-repo mypy, Bandit source, audit усіх locked deps, build; synthetic 10k measurement. Не замінювати full suite focused tests.
- QA: actual AC→assertion, subprocess/PTY/recovery/width evidence. Reviewer: відповідність контракту, транзакції/термінальний вивід/ізоляція/пакет. Дефекти developer виправляє й повторює відповідні та фінальний full gate, коли зміна робить попередній результат неактуальним.
- Готово: незалежні verdicts, немає невирішених матеріальних дефектів; required NOT RUN блокує готовність. Усі AC.

### T08 — запуск, README і передача

- Власник: developer створює `run.sh` та опційний `start-kolo.cmd`; documenter завершує `README.md` після звірки фактичного коду/QA. Лише українські користувацькі інструкції.
- `run.sh` визначає свій repo path, передає аргументи без втрати quoting, запускає абсолютний uv через `run --no-sync --project`; працює з іншого cwd без sync/мережі. Windows launcher лише відкриває цей WSL repo, не змінює системні налаштування.
- README: install/sync/launch, data paths/privacy, Kyiv/KOLO_TIMEZONE, формати/clear/multiline, CLI приклади, demo, expected errors/limits. Controller після QA може виконати локальний `uv tool install --python 3.12 .`; це не publication.
- Готово: фактично `uv sync`, `uv run kolo --help`, PTY `uv run kolo demo`, launcher з іншого cwd; installed absolute `kolo --help`, якщо встановлений. Фінальний звіт відокремлює PASS/NOT RUN. AC-16 та повторна перевірка AC-11,13—15.

## Межі передачі

Завдання архітектора завершуються цими п’ятьма файлами. Архітектурний огляд/планувальник/реалізація та QA лишаються окремими етапами, якими керує controller; цей план не стверджує, що вони виконані.
