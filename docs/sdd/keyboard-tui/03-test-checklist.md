# keyboard-tui: конкретні перевірки

Статус нових перевірок: NOT RUN; це план assertions, не звіт PASS. Вхід — TUI-AC-01—11 та чинні базові AC. Baseline контролера: 142 PASS, 95.33% всього src; HEAD немає. Власник реалізації: developer; незалежне приймання: QA.

## Правила доказів

- Нові keyboard journeys використовують `App.run_test(size=(w,h))` і справжні `Pilot.press`; не викликати action/save/handler замість ключової дії. Дані setup і fault injection можна задавати напряму. Без pytest-asyncio достатньо синхронного тесту з `asyncio.run`; не додавати зайвий test dependency.
- Після keys чекати повідомлення/worker completion, не довільні великі sleep. Перевіряти модель/SQLite й focused widget, не тільки наявність напису. Імена тестів нижче — очікувані сценарії, дозволені еквівалентні назви з тією самою assertion.
- Всі старі PTY journeys числового меню явно отримують `--line-mode` через helper або аргументи; зберегти всі assertions, Ctrl+C/EOF і no-ANSI перевірки. Окремі нові PTY запускають default без цього прапорця.
- Усі дані тільки tmp_path/TemporaryDirectory. Зберігати sentinel HOME/XDG та перевіряти незмінність; дані користувача не читати.
- Screenshot/viewport evidence доповнює behavioral assertions; alone скріншот не доводить клавіші, focus чи persistence.

## AC → assertion → реалізаційна задача

| AC | Заплановані перевірки | Задача |
|---|---|---|
| 01 | `test_tui_home_keys_and_routes`: Home counts+7days, first visible focus; Down/Up/Enter відкривають menu; help українською. `test_cli_modes`: nonTTY menu/demo=2 до filesystem, plain не line-mode; командні stdout/stderr/codes незмінні. | T1,T2,T6 |
| 02 | `test_tui_list_context`: створити два однакових labels, Down/Enter відкриває другий ID; Escape відновлює query/tag/sort/ID/scroll/focus. Empty Enter не відкриває; delete middle/last і save-matches/nonmatches мають правильний ID/статус. | T2,T3,T4 |
| 03 | `test_tui_focus_and_editor_keys`: реальними Tab/Shift+Tab пройти кожну дію, focus visible; надрукувати a/e/d/q без дій; Left/Right у Input, Up/Down у TextArea, Enter newline без save; Tab з TextArea переходить до наступного control. | T2,T3,T5 |
| 04 | `test_tui_contact_journey`: Add, кілька phone lines, details всі поля, edit+optional clear, той самий ID і normalized values через новий CLI process. `test_tui_field_error_draft`: invalid email з новою адресою не змінює DB/інші draft поля; correct+save проходить. | T3,T6 |
| 05 | `test_tui_note_journey`: multiline Unicode, leading/trailing newlines, tags-per-line normalize/clear, details full body; CLI/restart exact equality. Mixed-EOL/body projection regression нижче обов'язковий. Unchanged normalized tag length80 від початкового ß×40 не руйнується edit іншого поля; changed too-long tag відхиляється. | T3,T6 |
| 06 | `test_tui_filters`: клавіатурою query+exact tag+обидва sort, порядок = Assistant, clear усі дані; empty vs no-match різні. Після нового query Enter не відкриває невидимий старий ID, зокрема при затриманому читанні. | T2,T4 |
| 07 | `test_tui_birthdays`: Apply0/7/366, row→contact→Back з interval; invalid -1/367/1.5/x залишає raw і previous interval label. Injected dates2026-12-30,2027-01-01,2025-02-28,2028-02-28; expected Jan2/leap порядок; timer/resume refresh після зміни дня. | T4 |
| 08 | `test_tui_storage_faults`: initial/read/detail/refresh failure показують absolute path+Retry/Back/Quit, original DB hash/rows незмінні; retry після усунення fault. Inject save failure перед commit — draft+ID/rows незмінні, no success, explicit retry один commit. Committed save+refresh failure не викликає save повторно. Focus після error повертається до поля/control; raw map/widget draft з mixed separators лишаються для retry. | T3,T5 |
| 09 | `test_tui_safe_confirmations`: delete default Enter/Esc лишає запис; Tab до Delete+Enter видаляє. Dirty Back/Esc/Ctrl+Q/Ctrl+C default Enter/Esc зберігає draft, explicit discard відкидає; clean/HomeEsc exit confirmation повертає0. `test_tui_pending_io`: double-save не дублює; quit під blocked write чекає outcome й safe exit. | T3,T5,T6 |
| 10 | `test_tui_size_matrix`: усі перелічені нижче стани на всіх трьох розмірах, wrapped long Ukrainian label, body10000, keyboard до Save/Back, focus у viewport; resize dirty form без втрат. `test_tui_safe_text`: literal [bold], ESC/OSC/C0/C1/Cf у labels/path/details/editor без виконання; DB raw не переписано escaped-текстом; trailing U+2028/U+0085 не губляться при edit/resize. | T2,T3,T5,T6 |
| 11 | `test_tui_cli_v1_roundtrip`: існуюча SQLite1 → TUI edit → CLI read і навпаки після reopen; schema/IDs ті самі. `test_tui_demo`: default demo banner/path, fake seed, edit→exit cleanup→reseed, HOME/XDG sentinels unchanged; reject demo+data-dir before path resolution. Wheel+installed smoke і README commands. | T1,T6,T7 |

## Lossless body regression [AC05,08,10; T3,T6]

Через CLI --body-file створити exact existing fixture `\\nУкраїна\\r\\nДругий\\rТретій\\tрядок\\n` і Unicode fixture `А\\u2028Б\\u0085` (кінцевий separator). Усі escapes тут означають відповідні code points. Pilot клавішами відкриває Edit → Esc: без dirty prompt; повторно змінює лише title → Save, CLI/SQLite raw text/UTF-8 bytes exact. На fresh fixture клавішами замінити `Другий` на `Інший`: expected raw = початковий із цією єдиною заміною, усі separator spans exact. Окремо Enter всередині `Україна` після `Укра`: expected `Укра\\nїна`, решта raw незмінна. Unicode fixture: change Б→В з незмінними U+2028 і кінцевим U+0085; title-only і no-key cancel також exact/clean. Error+retry і resize зберігають widget draft/raw map. Вставлені нові breaks LF; чистий helper окремо перевіряє delete/replace, repeated-text deterministic tie (raw A\r\nA\n → canonical A\n дає raw A\r\n), consecutive/trailing CR/CRLF/Unicode separators та raw10000 boundary (canonical може бути коротшим). Не підміняти ці keyboard journeys прямим handler/helper викликом.

## Матриця розмірів і реальний термінал

Для кожного 120×36 / 80×24 / 60×20 зафіксувати: Home; empty і filled list; full detail; contact і note forms; read/write error; delete/dirty/exit confirm. Є visible title/focus, не обрізана поточна дія, footer hints або доступний help; довгі дані прокручуються. Tab доводить до Save/Back і зворотного control. Показати докази кольорового та `--plain`/NO_COLOR focus. Відкрита dirty note form120×36 →60×20 →80×24 з exact draft. Короткі кнопки при60×20 можуть переноситися, але досягаються.

Розширити `tests/pty_driver.py`: параметр height (поточний hardcoded40 не перевіряє20/24/36), resize через TIOCSWINSZ+SIGWINCH, bounded drain/read, утримувати slave descriptor для порівняння termios до/після exit. Новий `tests/test_tui_pty.py`: TTY default та demo, escape sequences Up/Down/Enter, safe quit/exit0, terminal echo/canonical restored, cleanup. Textual змінює екран ANSI навіть при plain; no-ANSI assertion стосується line-mode/redirected CLI, не fullscreen control sequences.

## Повний gate після останньої зміни

З repo `/home/iknow/goit-projects/personal-assistant`, UV=`/home/iknow/.local/bin/uv`:

```sh
/home/iknow/.local/bin/uv sync --locked
/home/iknow/.local/bin/uv run --no-sync ruff format --check .
/home/iknow/.local/bin/uv run --no-sync ruff check .
/home/iknow/.local/bin/uv run --no-sync mypy
/home/iknow/.local/bin/uv run --no-sync pytest --cov --cov-report=term-missing
/home/iknow/.local/bin/uv run --no-sync bandit -r src
/home/iknow/.local/bin/uv export --locked --all-groups --no-emit-project --format requirements-txt --output-file /tmp/kolo-tui-audit.txt
/home/iknow/.local/bin/uv run --no-sync pip-audit --requirement /tmp/kolo-tui-audit.txt --disable-pip
/home/iknow/.local/bin/uv build
```

Audit input містить runtime+dev lock dependencies; не звужувати. Ruff/mypy охоплюють tests. Coverage source весь `src/kolo`, без exclude/no-cover/threshold changes; >=80%, порівняти з95.33% і пояснити зміну. Fault tests перевіряють rollback, не створюють production bypass.

Установити побудований wheel в окреме чисте середовище, перевірити metadata dependencies/version, наявність TCSS, `kolo --help` з іншого cwd та PTY default/demo. Після технічних воріт — дозволене контролером локальне оновлення `uv tool install --force --python 3.12 <wheel>`, перевірений `/home/iknow/.local/bin/kolo`, `run.sh` та README. Не заявляти встановлення до фактичного виконання.

## Звіт

Для кожного AC: test/evidence path, PASS/FAIL/NOT RUN, точна причина прогалини; окремо baseline/current source fingerprint, команди, повний test count/coverage, dependency pin/audit, wheel/PTY/visual/installed результати. Waiver лише від користувача, не автоматичний PASS. Продуктові дані та вихідні docs/sdd/personal-assistant незмінні.
