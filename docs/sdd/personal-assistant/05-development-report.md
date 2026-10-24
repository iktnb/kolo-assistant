# Звіт розробки «Коло»

Дата: 2026-10-24. Роль: dev-agent, фактичний агент `/root/developer`. Єдиний компонент `personal-assistant`; виконано T01–T08 у дозволеній розробнику частині. **Поточний вердикт розробника після фінального виправлення довідки: PASS. Повний repo gate зелений; writer slot звільнено для контролера.** Їхні вердикти та фінальний продуктовий gate належать контролеру; цей звіт їх не замінює.

## Вхід і baseline

Справжній checkout: `/home/iknow/goit-projects/personal-assistant` (Ubuntu WSL). Гілка `feature/personal-assistant`, unborn HEAD, remote відсутній. Перед змінами були лише `.git` і SDD-документи: застосунку, конфігурації перевірок і тестів не існувало. Початкові app/tool checks **NOT RUN**, відсутність тестів не названа green baseline. Перевірено Python 3.12.3, `/home/iknow/.local/bin/uv` 0.8.10; файлових AGENTS.md/CLAUDE.md не знайдено. Прочитано повний dev-packet/shared/role/concrete assignment і `quality.md`.

Схвалений spec SHA-256 `9a7ddf648528e8d645693eb3ef16776734a3c167610d3a7e96c6c9c3221686bf`; tasks `52287c9dc7247b0029e678d7ef453c9af60d46320ec34a5995ad51179d625d64`; independent architecture report `33a1d8aa0cbd1fde3bd827ae630f07e95370f1c0e43865aef20dce21ccf279f0`. RFC/spec/checklist/tasks/summary/architecture-report fingerprints повторно перевірені незмінними після реалізації. Прийняті дизайн і global state розробник не редагував. Комітів, push, Jvers-доступу, публікації, глобальної інсталяції й читання `.env*` не було.

## Реалізація та змінені шляхи

- T01: `.gitignore`, `.python-version`, `pyproject.toml`, `uv.lock`, `src/kolo/__init__.py`, `__main__.py`, `cli.py`, `tests/conftest.py` — src-layout/hatchling, console/module entrypoints, Rich єдина runtime-залежність, strict whole-repo mypy, Ruff і coverage всього source.
- T02: `models.py`, `validation.py`, `errors.py`, `birthdays.py`; `tests/test_validation.py`, `tests/test_birthdays.py` — незмінні моделі, типізовані patch/omission, українські правила, ін’єктований aware clock, Europe/Kyiv/KOLO_TIMEZONE та inclusive/leap календар.
- T03: `storage.py`, `tests/test_storage.py` — private 0600 staging, commit/close/fsync, atomic no-clobber hard link, directory fsync; readonly preflight schema/FK/UNIQUE/domain; вузький recognized-header native hot-journal rollback; BEGIN IMMEDIATE і атомарність parent/children.
- T04: `services.py`, `tests/test_services.py` — спільні CRUD, Unicode/phone search, exact tag AND query, tuple sort, 5 collision attempts, canonical-expanded tags зберігаються при omission; поточний operation snapshot передається materialization, зокрема через північ.
- T05: `cli.py`, `render.py`, `tests/test_cli.py`, `tests/test_render.py` — українське argparse дерево/приклади, body-file/stdin, clear flags, stream/exit contract; спільна тема й literal Text sanitizer, без виконання Cc/Cf/OSC/CSI/bidi; layouts 60/80/120 і повні деталі.
- T06: `interactive.py`, `demo.py`, `tests/test_interactive.py`, `tests/test_demo.py`, `tests/pty_driver.py` — числові меню, per-field retry, edit semantics, multiline escaping, явне delete confirmation, Ctrl+C/EOF; TemporaryDirectory demo з leap-safe anchor2000, без особистого data-dir.
- T07: повні gates, описані нижче. Незалежні reviewer/QA виконуються окремо.
- T08: `README.md`, executable `run.sh`, `start-kolo.cmd`; українські інструкції й реальний запуск run.sh з іншого cwd та шляху з пробілами. Documenter може завершити README після незалежних оглядів.

Усі source-шляхи вище — всередині `src/kolo/`, test-шляхи — у `tests/`. Цей звіт — єдина зміна розробника в `docs/sdd/personal-assistant/`. Оскільки HEAD ще немає, весь код є новими untracked файлами; tracked diff відсутній, це не прихований попередній коміт. `.venv`, caches, coverage і `dist` локальні ignored build artifacts.

## Фактичний фінальний gate

Усі наведені команди повторно виконано з кореня WSL repo після фінального виправлення довідки; кожна завершилася exit0. Source snapshot30 файлів зазначено в поточному manifest. Інші role reports не змінювалися. Позначення `uv` у таблиці означає абсолютний `/home/iknow/.local/bin/uv`.

| Команда | Статус і фактичний результат |
|---|---|
| `uv sync --locked --all-groups` | PASS; resolved45 з локальним project, audited44 установлених non-project packages; lock незмінний |
| `uv run --no-sync ruff format --check .` | PASS;35 files already formatted, без exclusions |
| `uv run --no-sync ruff check .` | PASS; All checks passed |
| `uv run --no-sync mypy .` | PASS; no issues in23 source/test files, strict; без ignores |
| `uv run --no-sync pytest --cov=src/kolo --cov-report=term-missing --cov-fail-under=80 -q` | PASS; **142 passed in15.23s**, **95.33%** all source coverage (963 statements,45 missed), без UI exclusions |
| `uv run --no-sync bandit -r src/kolo` | PASS;1310 lines,0 findings,0 skips/suppressions |
| `uv export --frozen --all-groups --no-emit-project --format requirements-txt --output-file /tmp/kolo-audit-requirements.txt` | PASS; hashed resolved runtime/dev/transitive set |
| `uv run --no-sync pip-audit --requirement /tmp/kolo-audit-requirements.txt --no-deps --disable-pip --require-hashes` | PASS; No known vulnerabilities found |
| `uv build` | PASS; `dist/kolo_assistant-1.0.0.tar.gz` і `dist/kolo_assistant-1.0.0-py3-none-any.whl` |
| `uv run --no-sync kolo --help` | PASS; українське дерево, опції, приклад |
| `uv run --no-sync python -m kolo --help` | PASS; той самий український контракт |

pip-audit надрукував advisory, що `--no-deps` зайвий разом із `--require-hashes`, та загальну пораду fully-hashed pins. Експорт уже містить повні hashes/pins усіх44 non-project runtime/dev/transitive залежностей; `--no-deps` залишений точним checklist command, залежності не пропущені. Немає CVE ignore/skip і немає незакритого finding. Install/audit можуть використовувати мережу; runtime network заборонено autouse assertion у in-process tests.

Source coverage: birthdays95%, cli93%, demo100%, interactive95%, render100%, services98%, storage92%, validation99%, models/errors/init100%. `__main__` має2 missed in-process lines; він фактично запускається subprocess-тестами й окремою командою. Жодного coverage omission не додано.

## AC → фактичні assertions

| AC | Реальні тести й доказ |
|---|---|
| 01 | `test_real_pty_dashboard_navigation_and_retry` (60/80/120): Коло,0/0,7днів, живий unknown choice, контакти/додавання/повернення/exit; `test_in_process_full_menu_forms_and_preserved_expanded_tags`: усі основні розділи й довідка |
| 02 | `test_roundtrip_permissions_and_cascade`, `test_contact_lifecycle_in_new_process_and_different_cwd`, `test_contacts_duplicate_search_and_atomic_edit`: усі поля, phone order, новий процес/ID, duplicates; `test_collision_retry_exhaustion_and_midnight`: PK collision retry/5-attempt failure |
| 03 | `test_required_rejects_boundaries`, `test_text_limits_and_original_body`, `test_invalid_phones`, `test_phones_normalization_order_and_duplicates`, `test_email_rejects_invalid`, `test_email_valid_limits_and_dates`; atomic service edit і PTY email-only retry з name/phone збереженими |
| 04 | `test_contacts_duplicate_search_and_atomic_edit`: Ukrainian casefold/адреса/email/phone digits/trim/no-match, omission/clear/replacement/ID; CLI conflict negative assertions у `test_invalid_arguments_no_prompt_no_traceback` |
| 05 | subprocess lifecycle unconfirmed-delete2/no removal/confirmed delete; `test_missing_exact_ids` (обидві сутності show/edit/delete); `test_in_process_submenu_actions_search_edit_and_delete` (ні/так), actual PTY Ctrl+C confirmation збереження |
| 06 | `test_inclusive_year_rollover_and_sort`: Dec30+3 включаєJan02/виключаєJan03, N0/N366, one occurrence, date/name/ID order; CLI -1/367/1.5/x2 |
| 07 | `test_leap_policy_and_immutable_original`: 2025Feb28,2028Feb28/29,next year, stored original; `test_local_clock_and_invalid_naive`: Kyiv/UTC midnight; CLI invalid timezone2/no storage; service midnight refresh regression |
| 08 | note subprocess lifecycle/restart/body-file/stdin and malformed sources; `test_text_limits_and_original_body`: whitespace/10000/10001/LF; `test_note_crud_normalized_edit_and_expanded_tags`: invalid multi-field edit unchanged |
| 09 | `test_tags_casefold_expansion_and_literal_comma`, `test_note_search_and_tuple_sort`, `test_note_crud_normalized_edit_and_expanded_tags`; interactive40-character ß→80 canonical, title-only preservation й raw uppercase/spaced edit canonicalization |
| 10 | `test_real_pty_ctrl_c_returns_dashboard_without_mutation` (create/edit/multiline/delete), `test_real_pty_eof_exits_zero` (menu/form/confirmation), PTY normalexit0; in-process multiline body retry/leading+trailingLF/dot escape and Enter/!clear/!!clear |
| 11 | separate CLI processes/differentcwd, run.sh absolute launch/space arguments, isolated fakeHOME sentinels; `test_failed_parent_write_and_commit_rollback`, `test_failure_between_parent_and_children_rolls_back`, `test_expected_commit_error_has_no_success` |
| 12 | `test_unknown_corrupt_and_invalid_database_is_unchanged` (zero/garbage/application/version/schema/FK/domain/position/digits), locked/permission, parent/child/commit rollback; `test_real_initialization_crash_restart_without_cleaning_leftovers` (all3 boundaries), no-clobber/unsupported-link, `test_real_hot_journal_native_recovery`, unknown header + real hotjournal byte-identical |
| 13 | CLI contact/note lifecycle, all help levels, no prompt/noTTY/parser errors, stdout/stderr, noANSI; `test_in_process_command_routes_and_interrupt` asserts130; delete confirmation2 before store |
| 14 | `test_demo_leap_safe_and_reseeded` (2028Feb29/1996Feb29/today), `test_demo_rejects_explicit_directory_before_filesystem` patches path resolution to forbidden assertion; actual PTY demo edits isolated/reseed/cleanup/home sentinel fingerprint unchanged |
| 15 | `test_responsive_literal_rendering_full_details` at60/80/120: fullIDs/details/long Ukrainian values, literal markup/control/line widths; `test_control_policy_no_color_and_missing_fields`: NO_COLOR/plain/Cc/Cf/LF/tab; actual PTY widths/navigation/retry |
| 16 | locked sync/build, console/module help, `test_run_script_from_different_cwd_preserves_arguments`; actual WSL PTY demo and exit/EOF; README reflects implemented commands. Global tool install NOT RUN per ownership boundary |

## Crash/reliability evidence

Initial-creation tests launch a real child using the actual Store implementation, then `os._exit(9)` through test-only sqlite/os boundary substitution: before first commit, before link, immediately after link. Final respectively absent/absent/present; normal next startup succeeds without deleting leftovers, left-temp hashes unchanged. No production crash flags exist. No-clobber race preserves unknown final bytes and removes only this invocation’s temp; unsupported hard links fail visibly without replace fallback.

Hot-journal test commits40 valid notes, child runs real SQLite `BEGIN IMMEDIATE` with cache_size3 and UPDATE causing page spill, exits9. Actual readonly query raises SQLite776 (`SQLITE_READONLY_ROLLBACK`); recognized-header Store startup allows native rollback, then reads the exact last committed40 notes and removes journal through SQLite. A second true hot-journal fixture with unknown version2 preserves both DB and journal hashes on refusal. Corrupt fixtures outside narrow recovery are byte-identical. Parent/children faults and failed commit never return accepted candidate or success. Physical medium/fsync failure is not claimed as guaranteed recoverable.

## Terminal and launch evidence

Automated real PTYs use WSL stdlib pty, controlling terminal, TIOCSWINSZ widths60/80/120, bounded waits, actual Ctrl+C/Ctrl+D. They assert the emitted Ukrainian text, visible fullIDs, individual-field retry, cancellation and durable state after interruption. Renderer tests additionally inspect all rows/details at each width; raw ESC/OSC/CSI/bidi never survive sanitized app output. A redirected command remains without ANSI. Tests use temporary HOME/XDG/data dirs and synthetic contacts only.

`run.sh` executable mode is set. A real subprocess from another cwd with a data-dir containing spaces and a name containing spaces creates and subsequently lists the exact record. `start-kolo.cmd` is a small Windows→WSL forwarding launcher; direct double-click of the `.cmd` is **NOT RUN by developer**. The underlying WSL command and run.sh are verified. `/home/iknow/.local/bin/kolo` **NOT RUN/not installed by developer**; controller owns optional local installation after independent gates.

## Capacity measurement

Actual WSL TemporaryDirectory,5000 contacts+5000 notes (each note1800 Unicode characters), one synthetic bulk-seed transaction through storage, no new runtime bulk feature: **10000 entities,22110208 bytes**. Bulk seed0.1231s; combined contacts+notes list0.1473s; combined contact substring4999 search and note body/tag search0.2746s; matches1 and5000. The measurement is not an SLA and does not replace application behavior tests. Temporary data was removed. The projected1040-record/<8MiB estimate remains an estimate, distinct from this10k measurement.

## Limitations and handoff

No known material production defect or remaining developer check failure. Final help repair is verified below; independent role verdict updates remain controller-owned. Independent code reviewer and QA have not provided their verdicts in this development report; controller runs those gates separately. No permissions waiver, suppression, test skip, weaker assertion, or source coverage exclusion was introduced. Runtime is local/offline; plaintext storage, no concurrent shared editing, no migrations/import/export/background reminder per accepted scope. Crash leftovers before publication are intentionally ignored and are not automatically cleaned.

## Історія виправлення незалежного code review R1–R3

Цей розділ фіксує попередній ремонт source9657fa26, включно з тодішньою тимчасовою formatter/report ownership проблемою. Після author-owned re-review вона закрита; поточний повний gate вище PASS. Подальший вузький help fix описано окремо нижче.

Незалежний звіт `05-code-review.md` SHA-256 `bd6f4e74080fdb3da4a170a91d91d42f4745adaf0d4872c28c2959863a9a5df1` мав verdict CHANGES_REQUIRED на попередньому source fingerprint `6d267f733433a5071c22283577e01222974bf219e5c9fb6557f99e2cc74d8613`. Усі три findings відтворювали прогалини в негативних assertions. Контролер повернув розробнику writer ownership тільки для виправлення; accepted design, independent report і global state не змінювалися. Старий звіт/manifest збережено контролером у journal; цей документ описує поточний виправлений source, а не змінює старий незалежний verdict.

| Finding | Production fix | Meaningful regression / actual assertion |
|---|---|---|
| R1 — SQLite LIKE underscore приховував сторонні sqliteX objects | `src/kolo/storage.py`: schema preflight виключає тільки буквальний `sqlite_` prefix через `NOT GLOB 'sqlite_*'`; інші trigger/table/index лишаються в перевіреному наборі й відхиляються readonly | `test_sqlite_like_unknown_objects_refused_readonly` (3 SQL variants): sqliteX trigger/table/index → StorageError, DB SHA незмінний і original row лишається; `test_trigger_schema_refusal_prevents_false_success`: справжній CLI notes add на базі з deleting trigger →1, stdout порожній, без Збережено, DB hash незмінний |
| R2 — stdin text decoder приймав invalid UTF-8 як surrogate | `src/kolo/cli.py`: binary stdin.buffer read + explicit UTF-8 strict decode до Store; injected predecoded streams також проходять strict UTF-8 encode/decode boundary; decode/read errors стають InputError2 | `test_binary_stdin_rejects_malformed_utf8_before_storage` (add/edit × ff, surrogate-sequence, incomplete-sequence):2, UTF-8 diagnosis, add без нового data-dir, edit DB bytes unchanged; `test_binary_stdin_preserves_utf8_and_exact_newlines_independent_of_text_decoder`: actual add/edit subprocess, stdin text layer навмисно latin1/universal-newline, strict binary source все одно зберігає точний Unicode/LF/CRLF/CR/tab; `test_predecoded_stdin_still_enforces_strict_utf8`: surrogate refusal before storage й valid text fallback |
| R3 — details/current/heading трактували LF/tab single-line даних як багаторядковість | `src/kolo/render.py`: field/heading default multiline=False; лише note body, сформований phone list та intentional program block вмикають True. `src/kolo/demo.py`: explicit program multiline, шлях спершу single-line-safe, тому user/path controls не стають layout | `test_single_line_fields_heading_and_current_values_escape_lf_tab` (60/80/120): name/title/address/tags/current values/heading містять literal\x0a/\x09 без raw data LF/tab; actual service roundtrip зберігає оригінали; note body має справжній LF і expanded tab, сформовані телефони — розділовий LF |

Рівно15 нових focused regression cases пройшли окремо: `15 passed in2.22s`. Після цього виконано повний gate на незмінному виправленому source: початково всі11 команд exit0,116 тестів/95.33%, Bandit1310lines/0findings, повний hashed audit без CVE та актуальна збірка. Виявлено, що repository-wide Ruff0.17 також автоматично відформатував fenced Python у independent code-review artifact (лише quotes/line layout). Artifact відновлено з frozen initial-code-review.md byte-for-byte до bd6f4e74; повторний format check тепер FAIL тільки на цьому його preexisting codeblock. Це не waived/suppressed: потрібен author-owned formatting при re-review, після чого повторити repo-wide format check. Інші source gate results стосуються точно current source9657fa26 й лишаються чинними. Точні stdout/stderr/exit-result команди збережено в `/tmp/kolo-repair-gate-tijug81h/01.txt`…`11.txt`; повторна поточна formatter failure у `12-format-restored-review.txt`; немає ignores/suppressions/waivers. Capacity10k повторно виміряно саме на цьому source з результатами розділу вище. Змінено тільки4 production files (`storage.py`, `cli.py`, `render.py`, `demo.py`),3 test files (`test_storage.py`, `test_cli.py`, `test_render.py`) і цей дозволений development report. Інші22 з29 manifest файлів незмінні.

Незалежний повторний reviewer/QA verdict ще належить контролеру; розробник не позначає їх PASS самостійно. Глобальний kolo не встановлювався, Windows double-click не запускався, комітів/публікації немає. Writer slot звільнено контролеру для independent re-review. Контролер доручає автору відформатувати власний report code fence, потім повторює whole-repo format check; source/check evidence незмінного9657fa26 зберігається, без exclusions/waiver чи дублювання full suite тільки через форматування документа.

## Фінальне виправлення довідки та clean recovery command

Вхід перед цим ремонтом:30-file source `2f87516716259e65b1e95dd5e4fea38224ad1525ad7332d436d440856b7ac7eb`, Doc-owned README SHA-256 `d8151930735c109b48113a91c74e7e22050257b3e403538eeb71deb9df5a0c3a`. Контролер відтворив потрійне «Використання:» у `contacts list --help`: formatter примусово додавав heading навіть коли argparse передавав explicit empty prefix для побудови child prog. Це псувало також error recovery command.

Змінено тільки `src/kolo/cli.py`, `tests/test_cli.py` та цей dev report. `UkrainianFormatter.add_usage` тепер задає український default лише для prefix=None; explicit prefix, включно з порожнім, зберігається. Нових залежностей, schema/spec/README змін немає.

`test_help_all_levels_no_files_or_timezone` посилений observable assertions: root, groups, усі10 contact/note actions, birthdays і demo мають рівно один український usage heading та правильний чистий `kolo …` початок. Цей regression запущено до production fix: **FAIL**, group help містив2 headings, що підтвердило actual defect. Після fix він проходить.

Новий `test_parser_error_offers_clean_copyable_help` має6 root/group/action/birthday/demo error scenarios: exit2, без heading у stderr, точний clean prog --help у підказці, витягнута команда реально запускається і показує одну usage heading. Focused результат: **7 passed in2.05s**. Повний фінальний suite, включно з independently authored `tests/test_qa_journeys.py`: **142 passed in15.23s,95.33% всього src**. Усі11 required commands таблиці вище виконані наново й PASS; точні stdout/stderr logs — `/tmp/kolo-help-gate-_tkgxyn5/01.txt`…`11.txt`.

Ruff formatting mutations виконувалися тільки над owned `src/kolo/cli.py` і `tests/test_cli.py`; repo-wide `ruff format --check .` перевірив35 файлів. Strict mypy перевірив23 Python files. Bandit1310lines/0findings/0suppression, повний hashed resolved dependency audit без CVE, поточні wheel/sdist, console/module help PASS. pip-audit видає лише відому advisory про redundant --no-deps при повних hashes; export охоплює всі runtime/dev/transitive dependencies, exclusions/waivers немає.

Doc-owned README незмінний (`d8151930…`), screenshot `docs/images/kolo-overview.png` незмінний SHA-256 `1038fd05c7288d83ceb446c5224b5b78e858ff59527c0c290f31db3f7728dac7`. Інші report artifacts не редагувалися: architecture `33a1d8aa…`, current code-review `12eff3188a885e535328d6759f240ae34d45249327d15b42762a32f62fb1d108`, QA `ff611dfdb0bc9729b6b75a192700146968895a8a223fc2102d939671d9f0ff37`. Ці вердикти мають власних авторів; розробник не привласнює їхнє затвердження нового snapshot. Source writer slot звільнено після передачі, без commit/push/publication/installation.

## Final snapshot manifest

Поточний source snapshot **`aa6f3661c46aa68ae09ced610c3c1dec150b711621f07945ba2528572b21b5aa`**. Алгоритм: SHA-256 sorted relative filename UTF-8 + NUL + raw bytes усіх30 implementation/config/lock/README/launcher/test files нижче. Після початкової29-file реалізації QA додав `tests/test_qa_journeys.py`, Doc оновив README; вони включені, але не змінені розробником під час help fix. Accepted design, report/state, PNG, caches/venv/dist поза source identity, щоб уникнути self-referential report hash.

| Changed/new path | SHA-256 |
|---|---|
| `.gitignore` | `77b01dcd079b62ecc25b17c9bbc6258e586a48a7885b5b043b1de7d0d7721124` |
| `.python-version` | `7b55f8e67b5623c4bef3fa691288da9437d79d3aba156de48d481db32ac7d16d` |
| `README.md` | `d8151930735c109b48113a91c74e7e22050257b3e403538eeb71deb9df5a0c3a` |
| `pyproject.toml` | `f550bb4b8a7dd0d1ab6d058df5f49796aae6d2fc9df81debe33da835f08b982a` |
| `run.sh` | `41322509fc8fbb1d5843324f267ee99278bb690e3d07452ad933ff523704c845` |
| `src/kolo/__init__.py` | `8b77e0c0636adf4128176f17a3b0632b2b62533820a687e7eaf3009d435be02b` |
| `src/kolo/__main__.py` | `e6176eea953698732ede4b8a03937c519d7781ef4d6c5fcbd9f4492872bae322` |
| `src/kolo/birthdays.py` | `0a378c518a3c550cd7c73eb0d327cd79a78c7e69485fd04df3c7e74ea93f6f85` |
| `src/kolo/cli.py` | `983b31ce4b9f5751ecbef21ad4246ef10bc01a00177abc517e1c130ad859ec53` |
| `src/kolo/demo.py` | `71e7a6fcc7be6bacbfd4a811b6607f7f8a3c5c01b2c9a10a3840bf81e472e599` |
| `src/kolo/errors.py` | `043da1a0aeab1cca2f38a1bece4de487aae24a777cc3e2046560f414e01be68f` |
| `src/kolo/interactive.py` | `38e0cc21347174ef67d13361953c3c30caf424f91086c18e255c5f6e2b01b9ee` |
| `src/kolo/models.py` | `bec507ac48bf4ee76ffcba91b60f571419586350bb05ff16ca4db5d45a6464ed` |
| `src/kolo/render.py` | `fe6f20d54914d96174d7c398ceaf56f81167fee20eb9d5133df61f44560e017f` |
| `src/kolo/services.py` | `228f7da9985df861c4beabf1fa668d78feec09d8e5be817e1edfa0186c336510` |
| `src/kolo/storage.py` | `289ef02ced7de953d62ccf96de7b7ced03155c9dbd2054ef5f1aa923a3af0ced` |
| `src/kolo/validation.py` | `85742e912a8dcaeed019e216cb27b0a77090794ea0c683bbacc0ca5d48d06e83` |
| `start-kolo.cmd` | `f677b4f1193dd4a24b1838d3442cdf4a099c039d0ab944f69d9b2d3507d9046c` |
| `tests/conftest.py` | `49195e68ebdab5c79ffe3e7a1ef20551f375c1c801a4b25f805d6d20a57af0fd` |
| `tests/pty_driver.py` | `a4cf744bb5b8859ce5484665b841e9c2033df7b3e13dd3db080a6f989c9f1911` |
| `tests/test_birthdays.py` | `fb068f68be614182e598227d361d825b1ef7006e735d2f138b063abf3764148e` |
| `tests/test_cli.py` | `85e884dbc434427531709dd25c2272d0d63185dcb1ac0d666fbe9a25b16cb96b` |
| `tests/test_demo.py` | `5fa1bddde6113ad065ba9c0d61eff0a08507f2285c3c70fe161d148e230c708c` |
| `tests/test_interactive.py` | `0606fc8a720f241d2afa12c19f05b78284ce40a9a4ca011264933d4226ce4dd6` |
| `tests/test_qa_journeys.py` | `8b39f3e678231b97c3fefe44dc4fa1c65d47ea0c219d5ea6351707653e31b190` |
| `tests/test_render.py` | `86690f2faa26fdd05a4a1b34a2a36f316e6f4c1733ca5c8e808bbfab574ce635` |
| `tests/test_services.py` | `734cb07b754f205e0f5df3ca6699be04ee86727505a726c9c277e3ad0208ec7c` |
| `tests/test_storage.py` | `6fe861bae27c4a670a01bd7dcc2f61caf6883248dd4cd070c068dfee972b645f` |
| `tests/test_validation.py` | `9f4cf345ac6acf8e8d704c63d79490de79773d77aed30a0a4ada7234af2cad3e` |
| `uv.lock` | `3d2e402a7d10b76539e3d356441a8c24111039578d22cd0ea4ef2161570505f9` |
