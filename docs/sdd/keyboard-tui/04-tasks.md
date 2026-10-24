# keyboard-tui: план реалізації

Вхід: approved PRD і незалежно перевірені RFC/spec; цей план ще не означає виконання. Порядок залежностей: T1 → T2 → T3 → T4/T5 → T6 → незалежні review/QA → T7. Один checkout writer за раз; T4/T5 — логічно незалежні блоки, без одночасних checkout edits. Тести додаються разом із кожним блоком.

## personal-assistant

Назва — явний verified override призначення для автономного repo `/home/iknow/goit-projects/personal-assistant`; services.yaml тут N/A. Власник T1—T6: developer, T7: documenter/контролер у межах їхніх призначень; reviewer/QA перевіряють незалежно.

### T1. Залежність, маршрути й isolated demo [AC01,11]

- `pyproject.toml`, `uv.lock`: додати точну сумісну Textual runtime pin (8.2.8 — перевірений кандидат), не знімати чинне Rich/Python обмеження; resolver, imports та всі lock-групи audit. Версія 1.1.0 також у `src/kolo/__init__.py`.
- `src/kolo/cli.py`: global `--line-mode`, українська help; залишити nonTTY і demo+explicit-dir guard до filesystem. Default route запускає TUI з Assistant factory/path; line-mode — existing run_interactive. Commands лишаються direct, line_mode додати до `_prepare` excluded options; no-field edit лишається code2.
- `src/kolo/demo.py`: обрати shell явно; temporary lifetime/seed незмінні, banner/path у TUI; не resolve personal data_directory. Рядкова форма і її semantics не переписуються.
- Тести `tests/test_cli.py`, `test_demo.py`: routing/guards/no-op edit з новою global option; старі demo assertions явно line-mode, новий default demo тест окремо. Hatch wheel включає `tui.tcss`.

### T2. Спільна оболонка, навігація й вертикальний шлях [AC01,02,03,06,10]

- Новий `src/kolo/tui.py`: KoloApp, типізований ListContext, navigation origin, один серіалізований I/O adapter на asyncio.to_thread; startup factory у worker; typed result/error в event loop. Не ділити sqlite connections між threads.
- `src/kolo/tui_screens.py`: Home + Help, contacts/notes list, Detail; native widgets зі стійким ID, query+Apply, row→detail→Esc. Зберігати context/focus/scroll, generation stale-read protection, empty/no-match та no-hidden-selection.
- `src/kolo/tui.tcss`: одна палітра semantic roles, native focus/selected style, короткі українські hints; scroll/wrap 60×20/80×24/120×36, no-color видимий фокус. Передавати safe Rich Text, не markup.
- `tests/test_tui_navigation.py`: Pilot keys для Home/menu/detail/back, duplicates, query/focus restore, empty Enter, native editor ключі на ранньому прототипі. Вертикальний шлях працює до додавання решти екранів.

### T3. Контактні й нотаткові форми, запис і delete [AC02,03,04,05,08,09,10]

- `src/kolo/tui_forms.py`: labelled prefilled Input/TextArea, single Save/Back; phones/tags one per line; body з lossless raw-span adapter нижче. Tab з TextArea — focus traversal, Enter — newline; немає глобальних letters/Enter/arrow shortcuts.
- Використати існуючі Assistant methods, ContactPatch/NotePatch; unchanged fields UNSET, optional clear None/(). Dirty за initialized widget snapshot (body canonical LF), не raw stored text; domain FieldError.field → focus і inline reason; всі інші draft зберігаються.
- У tui_forms.py чистий body projection helper: зберегти raw_original/map, canonicalize всі Python splitlines separators до LF до load (CRLF один token, final separator лишається), snapshot widget_initial. Unchanged canonical -> UNSET; changed -> SequenceMatcher autojunk=False equal raw spans/delete omit/insert+replace canonical LF. Repeated-text tie як у spec; жодних private widget hooks. Копію current проектувати в serialized worker до доменної перевірки reconstructed raw10000; помилки не стирають map/draft.
- Save busy guard до dispatch, success лише після commit; explicit retry failed save без double-submit; committed save+failed refresh не replay. Після save повернути origin list/saved ID або explanatory filtered-out status.
- Detail Edit/Delete actions; confirmation type+safe label+full ID, default Keep, без typed ID. Delete→nearest selection. Missing record→error+refreshed origin list.
- `tests/test_tui_forms.py`: обидва CRUD journeys, validation+rollback/draft, clearing, multiline10000, stored expanded tag unchanged, lossless CLI mixed-EOL і trailing U+2028/U+0085 fixtures (no-key clean/title-only exact/one-character edit/Enter=LF/fault+retry/raw10000), restart/CLI roundtrip, safe defaults і focus restore.

### T4. Фільтри й календар із живою датою [AC01,02,06,07]

- Notes query AND tag, Select title/tags, Apply/clear через `Assistant.notes`; contacts query через `Assistant.contacts`. Blank tag -> None; context на Back; old selected ID invalidate до completion.
- Birthdays days raw Input + Apply0..366 + row→Contact Detail→Back; invalid зберігає raw і previous interval label. Home counts і7days.
- Один `assistant.today()` snapshot per read; explicit resume/apply, timer60s на зміну local date; injected clock test year rollover/leap. Не перезаписувати draft через timer.
- `tests/test_tui_filters_calendar.py`: клавіатурні apply/sort/clear, zero/366/invalid, duplicates/contact return, injected2026-12-30→2027-01-01, leap, stale-result order.

### T5. Відмови, безпечний exit і short-terminal polish [AC03,08,09,10]

- Read error, включно з startup Store: path/retry/back/quit, no-reset; unavailable Home після startup Back; stale label+disabled mutations. Safe modal restores focus; unknown exceptions без personal traceback/success.
- Перевизначити стандартні Textual Ctrl+Q/Ctrl+C через один guarded exit; dirty/default Continue, clean/HomeEsc confirm; Esc спершу native popup. Pending write не cancel/pop; дочекатися результату, потім requested safe navigation.
- Worker tests з blocked service: event loop responsive, double-save один commit, delayed read не відкриває hidden old ID; exit не очищає demo directory до завершення I/O.
- `tests/test_tui_errors_layout.py`: fault injection до commit, committed-write/read-fault distinction, initial corruption hash, safe controls/markup у editor+display; matrix всіх екранів і resize з exact dirty draft. Зібрати rendered evidence, а не лише dimensions.

### T6. Сумісність, PTY й повний технічний gate [AC01—11]

- `tests/pty_driver.py`: legacy helper явно `--line-mode`; height/resize/drain/termios для default TUI. `test_interactive.py`, `test_qa_journeys.py`, старий demo PTY лишають усі assertions.
- `tests/test_tui_pty.py`: default TTY keys→section→safe quit0, terminal restored, demo isolation/reseed/cleanup. CLI subprocess journeys і direct line-mode tests лишаються.
- SQLite v1 →TUI→CLI і CLI→reopen TUI, stable IDs/schema; offline fixtures/sentinels. Без зміни models/services/storage/validation/business contracts.
- Виконати всі команди `03-test-checklist.md`: whole-repo Ruff, strict mypy incl tests, full pytest/coverage, Bandit, audit all locked groups, build. Без exclusions/suppressions/config weakening; report count/coverage проти142/95.33%.
- Clean wheel install з іншого cwd: imports, TCSS included, version1.1.0, help і PTY default/demo. Записати фактичну pin та gap/NOT RUN; передати independent reviewer і QA фактичний source fingerprint/diff.

### T7. Інструкції та працююча локальна версія [AC11]

- Після незалежних воріт `README.md`: українські default arrow/Enter/Back/Tab keys, Save/dirty/delete/quit, TextArea newline, --line-mode numeric compatibility, --plain no-color semantics, unchanged CLI/data/demo, exact WSL commands.
- Оновити screenshot лише з вигаданими даними; не лишати стару картинку як доказ нового TUI. `run.sh`/ `start-kolo.cmd` перевірити, змінювати тільки за потреби.
- Контролер виконує вже дозволене локальне tool reinstall побудованого wheel, підтверджує installed command1.1.0 і real TTY demo; серверу/deploy/publication немає.
- Звіт: changed files, executed checks, AC evidence, remaining limitations; не називати Stage PASS до фактичних review/QA/installation evidence.
