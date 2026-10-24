# «Коло» — короткий огляд RFC

Автор: architect-agent `/root/architect_resume`, 2026-10-24. Статус: дизайн для незалежного технічного огляду; застосунок і тести ще не реалізовані. Деталі: [RFC](01-RFC.md), [spec](02-spec.yaml), [перевірки](03-test-checklist.md), [задачі](04-tasks.md).

## Мета

- Один локальний український CLI `kolo` для контактів, найближчих днів народження та нотаток із тегами: інтерактивна панель і скриптовані команди над тим самим сховищем.

## Компонент і залежності

- `personal-assistant`: новий Python 3.12 пакет `src/kolo`; argparse, stdlib SQLite/ZoneInfo та Rich як єдина runtime-залежність.
- Немає серверів, мережевого runtime, хмари чи змін Jvers. Автодоповнення/повноекранний UI не потрібні для цифрових меню.
- `pyproject.toml`, `uv.lock`, console/module entrypoints; `run.sh` для WSL, опційний Windows launcher, український README. Локальний tool install перевіряється після QA, без publication.

## Головні рішення

1. Один SQLite-файл у explicit `--data-dir`, інакше absolute XDG_DATA_HOME/kolo або ~/.local/share/kolo; жодного `.env`. Першу базу створити/commit/close/fsync у private tempfile того самого каталогу, опублікувати atomic no-clobber os.link, fsync dir/unlink own temp/fsync dir. Final ніколи не має незавершеного DDL, існуючий файл не замінюється. Батьківський запис/телефони/теги змінюються однією транзакцією, success лише після commit.
2. Повні стабільні IDs `c_`/`n_` +12 hex; duplicate display names і реквізити між контактами дозволено, команда обирає лише точний ID.
3. Unicode casefold пошук/сортування у Python; phone search за цифрами. Теги strip+casefold+deduplicate, точний tag filter AND text search; tuple tags/title/ID sort, безтегові останні.
4. Локальна дата — Europe/Kyiv незалежно від timezone WSL, optional KOLO_TIMEZONE; ін’єктований aware clock. Birthday interval today…today+N inclusive, N0..366; 29 лютого → 28 лише у невисокосний рік.
5. Форми тримають draft до повної перевірки; retry лише помилкового поля, Ctrl+C скасовує до меню, EOF завершує 0. Команди не питають приховано; delete вимагає --yes, interactive — явного підтвердження.
6. Спільний Rich renderer отримує безпечний literal Text, control characters escaped. Full IDs/повні деталі доступні на 60/80/120 колонках; redirected/NO_COLOR/--plain без ANSI.
7. `demo` створює нову TemporaryDirectory з вигаданими даними, не визначає й не читає особистий path; explicit --data-dir із demo — 2. Fixture birthday=today.replace(year=min(2000,today.year)) завжди валідний <=today; за 2028-02-29 це 2000-02-29/days_until=0. Рік2000 високосний, раніші дати залишаються today.

## Дані та зовнішній контракт

- Схема v1: `contacts`, `contact_phones`, `notes`, `note_tags`, PK/UNIQUE/FK з cascade. `application_id=0x4B4F4C4F`, `user_version=1`. Попереднього формату/даних немає; автоматичних migration/downgrade немає.
- Поточний обсяг 0. Оцінка за +10 контактів/+10 нотаток на тиждень: <1/<4/<8 MiB через 1/6/12 місяців; перевірити фактичний розмір/пошук на synthetic 10k. Лише індекси цілісності; їхня відносна частка може бути >20%, абсолютний обсяг малий. ALTER/online-DDL/архівація N/A.
- Команди: contacts/notes list/show/add/edit/delete, birthdays --days, demo; global --data-dir/--plain/--help/--version. HTTP/events відсутні. Коди: 0 success, 2 invalid input/missing ID/unconfirmed deletion, 1 storage failure, 130 command interrupt.

## Ризики та перевірка

- Corrupt/unknown/zero-byte дані відхиляються без reset/replacement. Вузький виняток readonly preflight: SQLITE_READONLY_ROLLBACK + відомий raw header/version дозволяє native SQLite rollback, потім повну перевірку. Жодного generic backup/restore. Реальні subprocess crash тести першого initialization до commit/перед link/після link та повторний startup, окремий committed-base recovery test обов’язкові. Залишки private temp після kill ігноруються; відсутній hard-link/fsync -> error1 без replace fallback; поломка диска/fsync поза гарантією.
- Технічний gate: Ruff format/lint, strict mypy всього Python repo/tests, full pytest із >=80% всього src/kolo, Bandit source, resolved runtime/dev dependency audit, build та реальні CLI/PTY перевірки. Required NOT RUN блокує готовність.
- Відкритих продуктових питань немає. Незалежний architecture review, планувальник, developer, reviewer, QA й documenter ще мають виконати свої етапи. Немає дозволу на commit/push/publication/deploy.
