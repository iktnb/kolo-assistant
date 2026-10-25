# Посібник розробника

[Документація](README.md) · [Архітектура](architecture.md) · [Вимоги й докази](requirements-coverage.md)

Цей документ описує підготовку, структуру й перевірки коду. Користування інтерфейсом — у [посібнику користувача](user-guide.md).

## Середовище

Linux або Ubuntu WSL; Python 3.12 (`>=3.12,<3.13`), [uv](https://docs.astral.sh/uv/). Після клонування [репозиторію](https://github.com/iktnb/kolo-assistant) виконайте з його кореня:

```sh
uv sync --locked --all-groups
uv run --no-sync kolo --version
uv run --no-sync kolo --help
uv run --no-sync python -m kolo --help
uv run --no-sync kolo demo
```

`uv.lock` фіксує залежності, `--locked` перевіряє відповідність проєкту lock-файлу. Runtime використовує Textual 8.2.8 і Rich; SQLite входить до Python. Перша підготовка та аудит залежностей можуть потребувати мережі; runtime — офлайн. Успішний `--help` не замінює перевірки справжнього TTY.

`run.sh` і `start-kolo.cmd` — зручні [локальні launchers](../run.sh), налаштовані на конкретні абсолютні шляхи Ubuntu автора. Для іншої машини використовуйте наведені переносні `uv`-команди. `kolo` поза `uv run` може запускати іншу встановлену копію: звіряйте `--version`.

## Чисте встановлення Python-пакета

Пакет визначено в `pyproject.toml`: build backend `hatchling`, пакет `src/kolo`, console entrypoint `kolo = kolo.cli:main`. Для перевірки не потрібні абсолютні шляхи автора. У Linux/Ubuntu WSL з Python 3.12 та uv:

```sh
KOLO_CHECK=$(mktemp -d)
git clone https://github.com/iktnb/kolo-assistant.git "$KOLO_CHECK/source"
cd "$KOLO_CHECK/source"
uv build --out-dir "$KOLO_CHECK/dist"
uv export --locked --no-dev --no-emit-project --format requirements-txt --output-file "$KOLO_CHECK/runtime.txt"
uv venv --python 3.12 "$KOLO_CHECK/venv"
uv pip install --python "$KOLO_CHECK/venv/bin/python" --require-hashes -r "$KOLO_CHECK/runtime.txt"
uv pip install --python "$KOLO_CHECK/venv/bin/python" --no-deps "$KOLO_CHECK/dist/kolo_assistant-1.1.0-py3-none-any.whl"
uv pip check --python "$KOLO_CHECK/venv/bin/python"
export PATH="$KOLO_CHECK/venv/bin:$PATH"
cd /tmp
kolo --version
kolo --help
python -I -m kolo --help
python -I -c 'import kolo; print(kolo.__file__)'
kolo demo
```

`kolo.__file__` має вказувати на `venv/lib/python3.12/site-packages/kolo`, а не на checkout `source/src/kolo`. Це звичайне встановлення wheel без `-e`; `tui.tcss` також входить до wheel. Runtime-залежності встановлюються окремо з lock-файлу; dev-інструментів на цьому етапі немає. `demo` запускають у справжньому терміналі. Для локальних непублічних змін замініть крок клонування копією свого checkout.

`export PATH` діє в поточному сеансі й дозволяє викликати `kolo` з будь-якого каталогу. Для постійного встановлення оберіть постійний каталог середовища та додавайте його `bin` до PATH під час активації; це не публікація пакета на PyPI.

Для перевірки команд після встановлення перейдіть у довільний каталог, створіть окремий каталог даних і виконайте [CRUD-приклади](user-guide.md#команди-на-окремих-навчальних-даних). Наприклад:

```sh
KOLO_DATA=$(mktemp -d)
kolo --data-dir "$KOLO_DATA" contacts add --name "Перевірка пакета" --phone "+380671234567"
kolo --data-dir "$KOLO_DATA" contacts list --search "пакета"
kolo --data-dir "$KOLO_DATA" notes add --title "План" --body "Перевірити встановлення" --tag навчання
kolo --data-dir "$KOLO_DATA" notes list --tag навчання --sort tags
kolo --data-dir "$KOLO_DATA" birthdays --days 7
```

Перед повним прогоном тестів встановіть dev-залежності у це саме середовище, не замінюючи встановлений пакет на editable:

```sh
uv export --project "$KOLO_CHECK/source" --locked --all-groups --no-emit-project --format requirements-txt --output-file "$KOLO_CHECK/all.txt"
uv pip install --python "$KOLO_CHECK/venv/bin/python" --require-hashes -r "$KOLO_CHECK/all.txt"
cd /tmp
python -m pytest -c "$KOLO_CHECK/source/pyproject.toml" "$KOLO_CHECK/source/tests" --cov=kolo --cov-report=term-missing --cov-fail-under=80
```

Тести імпортують установлений wheel, а їхні CLI/PTY-процеси користуються тим самим інтерпретатором. [Окрема перевірка зауважень ментора](mentor-verification.md) містить межі та фактичні результати повторної перевірки.

## Де що змінювати

| Частина | Файли | Відповідальність |
| --- | --- | --- |
| Вхід і CLI | [cli.py](../src/kolo/cli.py), [__main__.py](../src/kolo/__main__.py) | argparse, українська довідка, глобальні опції, вибір режиму, коди виходу |
| Повноекранний інтерфейс | [tui.py](../src/kolo/tui.py), [tui_screens.py](../src/kolo/tui_screens.py), [tui_forms.py](../src/kolo/tui_forms.py), [tui.tcss](../src/kolo/tui.tcss) | екрани, фокус/контекст, форми, підтвердження, серіалізований I/O, оформлення |
| Інші оболонки | [interactive.py](../src/kolo/interactive.py), [render.py](../src/kolo/render.py), [demo.py](../src/kolo/demo.py) | явний рядковий режим, безпечний вивід, тимчасова демонстрація |
| Домен | [models.py](../src/kolo/models.py), [services.py](../src/kolo/services.py), [validation.py](../src/kolo/validation.py), [birthdays.py](../src/kolo/birthdays.py) | моделі/patch, CRUD, нормалізація, пошук/теги, календар |
| Зберігання | [storage.py](../src/kolo/storage.py) | SQLite, схема 1, транзакції, перевірка й приватні шляхи |
| Перевірки | [tests](../tests) | домен, CLI/процеси, SQLite, Textual Pilot і справжні PTY |

Інтерфейс викликає `Assistant`, а не виконує SQL самостійно. Спільні правила діють у CLI, TUI й рядковому режимі. Додавання можливості починайте з відповідної вимоги, доменного правила та спостережуваного сценарію; зберігайте чинні ID, формат даних і правила помилок. [Потік даних та рішення](architecture.md).

## Обов’язкові перевірки

Виконуйте з кореня репозиторію. Форматування, lint і типи перевіряються по всьому проєкту, включно з тестами.

```sh
uv run --no-sync ruff format --check .
uv run --no-sync ruff check .
uv run --no-sync mypy .
uv run --no-sync pytest --cov=src/kolo --cov-report=term-missing --cov-fail-under=80
uv run --no-sync bandit -r src/kolo
```

Аудит усіх зафіксованих runtime і dev-залежностей та збирання:

```sh
KOLO_AUDIT=$(mktemp /tmp/kolo-audit.XXXXXX)
uv export --frozen --all-groups --no-emit-project --format requirements-txt --output-file "$KOLO_AUDIT"
uv run --no-sync pip-audit --requirement "$KOLO_AUDIT" --no-deps --disable-pip --require-hashes
uv build
```

`uv build` створює sdist і wheel у `dist/`. Після змін перевіряйте не лише вихідний каталог, а й установлений wheel з іншого каталогу: версію, entrypoint, TCSS, залежності та default/demo в справжньому терміналі.

Тести користуються тимчасовими каталогами й підставними HOME/XDG, fault injection і перевіркою SQLite. Не запускайте експерименти на особистому сховищі. Для ручного CLI використовуйте явний `--data-dir`, як у [посібнику](user-guide.md).

## Які сценарії захищають тести

- Домен і календар: нормалізація/межі полів, дублікати, комбінований пошук, порядок тегів, включені межі 0–366, 29 лютого та перехід року.
- SQLite: перезапуск, права, зв’язки й видалення, справжня відмова commit, відсутність часткового запису, пошкоджена/невідома база.
- CLI: окремі процеси, різні каталоги, повні ID, UTF-8 файл/stdin, stdout/stderr/exit codes, відмова невалідного add/edit.
- TUI: native клавіші, видимий фокус, Back-контекст, точний багаторядковий текст, збереження чернетки, безпечні підтвердження, відкладений вихід під час запису.
- PTY й розміри: справжній термінал, відновлення налаштувань, 120×36 / 80×24 / 60×20, resize і demo-ізоляція.

Локальний тест одного випадку допомагає ремонту, але не замінює повний поведінковий прогін після зміни функціонального коду. Не зменшуйте поріг чи область покриття для проходження перевірки.

## Попередні зафіксовані результати 1.1.0

| Перевірка | Хто виконав і що підтверджено | Доступний документ |
| --- | --- | --- |
| Повний набір | Розробник: **227 PASS, 95.54%** усього `src/kolo`; поріг 80%. Контролер і незалежний QA звірили точний стан коду та результати | [Звіт розробки](sdd/keyboard-tui/05-development-report.md) |
| Приймальні сценарії | Незалежний QA: **30 PASS**, включно з реальними PTY, вузькими вікнами, чернетками та збоями | [QA](sdd/keyboard-tui/06-qa-report.md) |
| Початкове завдання GoIT | Додатковий незалежний аудит: **15 тестів PASS і 10 CLI-спостережень PASS**; зокрема чотири випадки валідації add/edit | [Матриця вимог](requirements-coverage.md) |
| Установлений пакет | Контролер: 1.1.0, **97 CLI-перевірок**, справжні default/demo PTY, точні assets і залежності | [Локальна передача](sdd/keyboard-tui/08-local-delivery.md) |
| Аналіз і збирання | Ruff format/lint, строгий mypy, Bandit, повний lock-аудит і wheel/sdist пройдено | [Незалежний огляд](sdd/keyboard-tui/05-code-review.md) |

Це атрибуція виконаних перевірок, а не твердження, що кожен учасник повторив усі команди. 30 приймальних випадків, аудит 15/10 та 97 спостережень не додаються до числа 227. Історичні SDD-звіти зберігають стан на час етапу; пізніший [головний README](../README.md) відображає публікацію на GitHub. На етапі початкового доповнення змінювалася тільки документація й повторно використовувалися незмінні поведінкові та security-результати. Нове доопрацювання 25 жовтня має [окрему поточну перевірку](mentor-verification.md).

## Межі змін

Формат SQLite 1 не мігрується автоматично; невідома версія відхиляється. У проєкті немає HTTP API, подій, сервера чи ML. Зміна схеми або додавання такого компонента потребуватиме окремого рішення, сумісності й тестів, а не прихованої модифікації поточного контракту.

Залежності зберігайте узгодженими між `pyproject.toml` і `uv.lock`. Зміни запуску перевіряйте і без TTY, і в TTY; зміни вводу — на native клавішах, із помилками та повторною спробою. Окремо перевіряйте, що успіх показано після commit, а не до нього.
