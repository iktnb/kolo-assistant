# Фінальне незалежне QA — «Коло» / personal-assistant

## CURRENT verdict: PASS

2026-10-24; `qa-agent` **`/root/qa_engineer`**, окремий від developer `/root/developer` та reviewer `/root/code_reviewer`. Поточний перевірений **30-file source `aa6f3661c46aa68ae09ced610c3c1dec150b711621f07945ba2528572b21b5aa`**. Незалежний fresh full gate: **142 tests passed in14.94s;95.33% усього `src/kolo`**, усі11 required commands exit0. Матеріальних production-дефектів не спостерігалося, findings/waivers/skips/exclusions немає. УсіAC-01—AC-16 зберігають PASS у призначених QA межах; controller окремо володіє фінальними installed/Windows/user handoff actions.

## Renewal scope, identities і зміни

Підстава renewal — виправити конкретний duplicated usage heading у вкладеній довідці та забруднений `prog` у recovery suggestions. Прочитано актуальний review top/diff/test assertions і development gate evidence. Scope не розширювався; QA змінив **тільки цей `06-qa-report.md`**, нових tests/production/config/doc/state changes цього проходу немає. Repo `/home/iknow/goit-projects/personal-assistant`, branch `feature/personal-assistant`, unborn HEAD; `.env*`, особисті дані, Jvers, commit/push/publication не використовувалися.

| Поточний вхід | SHA-256 |
|---|---|
| Accepted `02-spec.yaml` | `9a7ddf648528e8d645693eb3ef16776734a3c167610d3a7e96c6c9c3221686bf` |
| `05-development-report.md` | `970a59e518ea7acf446a61a6e781deac16a9dedbf085529eeee1f9ff17477209` |
| Current APPROVED `05-code-review.md` | `ee95929aab1709171b208569af22aed0937ef15fc5d8285b2dcc88e274c43cb9` |
| Doc-owned `README.md` | `d8151930735c109b48113a91c74e7e22050257b3e403538eeb71deb9df5a0c3a` |
| `src/kolo/cli.py` | `983b31ce4b9f5751ecbef21ad4246ef10bc01a00177abc517e1c130ad859ec53` |
| `tests/test_cli.py` | `85e884dbc434427531709dd25c2272d0d63185dcb1ac0d666fbe9a25b16cb96b` |
| Unchanged QA `tests/test_qa_journeys.py` | `8b39f3e678231b97c3fefe44dc4fa1c65d47ea0c219d5ea6351707653e31b190` |
| Previous QA report before renewal | `ff611dfdb0bc9729b6b75a192700146968895a8a223fc2102d939671d9f0ff37` |

Source fingerprint algorithm залишається sorted relative filename UTF-8 + NUL + raw bytes30 manifest files. Independent comparison із попереднім QA snapshot0876e960 виявив тільки authorized Doc README і2 help code/test files; інші27/30 byte-identical. Власна in-memory reverse заміна одного formatter expression відтворила **точний попередній cli SHA `f3330c3a53cccbcdcfc096da948f28690230351582b01f619e13d1ea9cee2928`**, без запису старого коду. Отже весь production diff — саме збереження explicit `prefix`, український default лише при `prefix is None`. Жодних schema/dependency/storage/UI mutation змін. Усі попередні counts нижче читаються лише як історичні; актуальний count — **142**, попередній —136.

## Actual independent help/error recovery evidence

Fresh actual installed-in-project console subprocesses `kolo` (PATH явно на project `.venv/bin`), temporary fake HOME/XDG, invalid `KOLO_TIMEZONE`, bounded timeouts:

- **15 help paths**: root, contacts/notes groups, усі5 actions кожної групи, birthdays,demo. Кожна команда повернула0, stderr порожній, рівно один `Використання: `, clean expected `kolo …` prefix. Help не створив fake personal-data directory; sentinel незмінний.
- **6 parse error paths**: unknown root flag, contacts group без action, contact add/note add без required fields, invalid birthday integer, unknown demo flag. Кожний повернув2, stdout порожній, stderr без `Використання:`, точний clean suggested command.
- Кожну suggested `kolo … --help` реально extracted/shlex-split і виконано як copyable console command. **Усі6 повернули0 з одним heading**; це actual recovery, не лише substring assertion.
- Direct first lines: `Використання: kolo contacts list [-h] [--search ТЕКСТ]`; `Використання: kolo notes edit [-h] [--title ТЕКСТ]`. Подвоєного heading і забрудненого child prog немає.

Evidence `/tmp/kolo-qa-help-renewal-a8bibe_w/independent-copyable-help.json`. Нові developer tests `tests/test_cli.py::test_parser_error_offers_clean_copyable_help` ×6 та strengthened `test_help_all_levels_no_files_or_timezone` також виконано у fresh full142 suite.

## Current required gate — actual QA execution

Cwd WSL repo; кожний `uv` = `/home/iknow/.local/bin/uv`. Усі commands виконані незалежно цією QA роллю, послідовно; exact argv/exit/time у `/tmp/kolo-qa-help-renewal-a8bibe_w/results.json`, stdout/stderr у `01.txt`—`11.txt`.

| Command | Actual result |
|---|---|
| `uv sync --locked --all-groups` | PASS,exit0,45 resolved/44 installed non-project packages,lock unchanged |
| `uv run --no-sync ruff format --check .` | PASS,exit0,35 files; ще раз після author-only report formatting |
| `uv run --no-sync ruff check .` | PASS,exit0 |
| `uv run --no-sync mypy .` | PASS,exit0,strict23 source/test files |
| `uv run --no-sync pytest --cov=src/kolo --cov-report=term-missing --cov-fail-under=80 -q` | PASS,exit0,**142 passed in14.94s;95.33%,963statements/45missed** |
| `uv run --no-sync bandit -r src/kolo` | PASS,exit0,1310lines/0findings/0skips |
| `uv export --frozen --all-groups --no-emit-project --format requirements-txt --output-file /tmp/kolo-qa-help-renewal-a8bibe_w/audit-requirements.txt` | PASS,exit0,full locked runtime/dev/transitive hashed requirements |
| `uv run --no-sync pip-audit --requirement /tmp/kolo-qa-help-renewal-a8bibe_w/audit-requirements.txt --no-deps --disable-pip --require-hashes` | PASS,exit0,No known vulnerabilities found |
| `uv build` | PASS,exit0,current sdist+wheel |
| `uv run --no-sync kolo --help` | PASS,exit0,clean Ukrainian help |
| `uv run --no-sync python -m kolo --help` | PASS,exit0,clean Ukrainian help |

pip-audit generic no-deps/require-hashes advisories лишилися тими самими disclosed tool advisories, не CVE; actual locked export має повні hashes, ignore не додано. Coverage includes усі modules, у тому числі cli/render/interactive/demo; попередні limitations щодо subprocess-only measurement `__main__` лишаються відкрито зазначеними.

## Current AC mapping, збережені докази й handoff

Повна16-row AC→actual-assertion matrix та реальні PTY/storage/crash/data-integrity/10k evidence початкового QA збережені нижче. Вони застосовуються до незмінної поведінки; fresh142 suite повторно виконав всі попередні136 cases, зокрема реальні PTY60/80/120, retry/Ctrl+C/EOF, SQLite initialization crash/native hot-journal/commit failure/isolation і R1–R3 regressions. Це не звуження до help-only tests. Окремі вже пройдені launcher/demo/capacity probes не дублювалися без потреби; formatter one-line diff не змінює їхні шляхи.

- **AC-13,AC-15,AC-16 renewed PASS**: current all-level help має один heading/clean child prog; code2 error пропонує справді виконувану help command; nonTTY stdout/stderr/no-files assertions виконані. Нові6 recovery cases та15 direct helps дають додаткове precise evidence.
- **AC-01—AC-12,AC-14 PASS retained and re-executed**: all named assertions у full142 suite; зміни не торкалися моделей/storage/services/interactive/render/demo. QA-owned20 journey cases залишилися byte-identical й пройшли знову.
- Current independent reviewer уже схвалив QA test diff і фінальні2 help files. Цей прохід додає лише report, тому нового unreviewed test/code diff від QA немає. Production blockers: **None observed**. Waivers: **None**.
- Optional global tool install/real-user default launch/Windows double-click **NOT RUN цією QA роллю**, лишаються controller-owned final handoff. Немає claimed fresh visual/interactive run поза фактично виконаним. Попередні actual isolated uv demo/run.sh результати нижче чинні для незмінних launch/runtime paths.

Before/after source **aa6f3661c46aa68ae09ced610c3c1dec150b711621f07945ba2528572b21b5aa** і current input hashes перевірено незмінними після report update. Final controller gate не просувався QA. Writer slot звільняється на поверненні результату.

---

<details>
<summary>Початковий QA snapshot0876e960: повна AC matrix та незмінені PTY/storage/crash докази</summary>

Нижче збережено попередній звіт. Його source/count/input hashes належать тодішньому snapshot, а не поточному; current renewal metadata й142-test verdict наведено вище. Сценарії та assertions лишаються чинними й повторно виконані у fresh full suite.

# Незалежний QA Report — «Коло» / personal-assistant

## Verdict: PASS у межах QA

Дата: 2026-10-24. Роль `qa-agent`, фактичний агент `/root/qa_engineer`; developer `/root/developer` і reviewer `/root/code_reviewer` — окремі агенти. Перевірено весь прийнятий обсяг AC-01—AC-16. **136 tests PASS; 95.33% усього `src/kolo`; усі required quality checks PASS. Матеріальних production-дефектів не спостерігалося.** Немає waiver, skip, weakened assertion або coverage exclusion. Це окремий QA verdict; controller зберігає global gate, а reviewer має оглянути доданий QA test file перед остаточним схваленням.

## Reviewed snapshot і входи

Repo `/home/iknow/goit-projects/personal-assistant`, Ubuntu WSL, гілка `feature/personal-assistant`, unborn HEAD (`git rev-parse --verify HEAD` → 128). Новий застосунок не мав попереднього app/test baseline; підготовчі документи не використано як доказ runtime PASS. Прочитано повний `qa-packet.json` shared/role/concrete assignment і `qa-assignment.md`, `quality.md`, PRD, RFC, spec, checklist, tasks, architecture/development/code-review reports. Ancestor `AGENTS.md`/`CLAUDE.md` не знайдено.

- Перед QA: **29-file source `9657fa268dd9b1c224ae2df980919f887d0a7c7c8e167ad7d0e02a19701a0adb`**, точно approved independent review snapshot. Незалежний baseline QA gate: 116 tests, 95.33%, усі 11 команд exit 0.
- Після QA: **30-file source `0876e9602502d7d8c390fd9b8ba1076f5322f013c3aaf749d773d04efbdfe917`**. Алгоритм: sorted relative filename UTF-8 + NUL + raw bytes усіх source/config/README/launcher/tests із development manifest, плюс новий test file; reports/design/state/caches/venv/dist виключено лише з fingerprint, не з repository formatting scope.
- Усі попередні **29/29 файлів byte-identical**. Єдина додана source/test зміна: `tests/test_qa_journeys.py`, SHA-256 **`8b39f3e678231b97c3fefe44dc4fa1c65d47ea0c219d5ea6351707653e31b190`**, 20 нових executed cases. Другий і останній authored repo-path — цей `06-qa-report.md`. Production/config/lock/README/інші ролі/state не змінено.
- Identity evidence: `/tmp/kolo-qa-gate-pk5bz2bz/identity.json`, before/final manifests. Не читалися `.env*`, реальні особисті контакти чи Jvers; commit/push/publication/deployment не виконувалися.

| Вхід у `docs/sdd/personal-assistant/` | Перевірений SHA-256 |
|---|---|
| `00-prd-delta.md` | `9684368f89e3ed8800c74753269dc98feea449bcdd858e849bc3ce1ac8eaafed` |
| `00-project-plan.md` | `bdcc8409dc4e342cc198ac17240db316c7363b9da956f278d603209426704d63` |
| `01-RFC.md` | `2529f02adf18ae7decba1d7a46127b0ecc45784984b49912cd172d2722de8d1a` |
| `02-spec.yaml` | `9a7ddf648528e8d645693eb3ef16776734a3c167610d3a7e96c6c9c3221686bf` |
| `03-test-checklist.md` | `1e210fff0e039d5b9e4d1848a7321aacbb9adcd085e7f9812ffec49e33e42f6d` |
| `04-tasks.md` | `52287c9dc7247b0029e678d7ef453c9af60d46320ec34a5995ad51179d625d64` |
| `05-architecture-review.md` | `33a1d8aa0cbd1fde3bd827ae630f07e95370f1c0e43865aef20dce21ccf279f0` |
| `05-RFC-summary.md` | `b82ec37a805579e28a0a8973de8b638b1ec2f71ec947a0852908f2dc3c71d112` |
| `05-development-report.md` | `23f7e8f8c1da46143d566cd904fd63048c9a429f86fc7e89c4804c5ef4301790` |
| `05-code-review.md` | `97ab5f26d1871e3f654dae2545eb2fde9a4084d77ae96a19f069b96a718e741d` |

Current code-review top verdict APPROVED стосується виправлених R1/R2/R3; історичний CHANGES_REQUIRED у details не є поточним. Старий development formatter FAIL стосувався reviewer-owned fence; незалежний QA перевірив актуальний whole-root PASS, без exclusion/waiver.

## Власні додані tests

`tests/test_qa_journeys.py` додає саме observable assertions, не виправляє production:

- `test_qa_real_pty_note_complete_journey` × 60/80/120: keyboard help/calendar/notes, invalid-body retry зі збереженим title, Unicode/leading/trailing LF/dot escaping, literal markup, normalized/comma tags, details, AND search, no-match, Enter-cancel delete з fresh reopen, edit з omission/clear, explicit yes delete, empty state, normal exit 0.
- `test_qa_real_pty_note_cancel_and_reopen` × body/tags/confirmation × Ctrl+C/EOF: незбережений title/body/tag або deletion не прийнято; code 0, новий Store відновлює точні попередні note і contact.
- `test_qa_rejection_never_waits_for_open_stdin` × 4: no-command/demo/unconfirmed contact/note delete закінчуються 2, поки stdin pipe ще відкритий; storage не створено.
- `test_qa_real_commit_failure_cli_has_no_success_and_fresh_reopen` × contacts/notes: справжня SQLite mutation доходить до injected failing `Connection.commit`; CLI 1, stdout порожній, немає success/приватного SQL/value, DB SHA незмінний, після відновлення connection factory новий Store читає точних parent/children.
- `test_qa_actual_default_paths_with_fake_home_only` × absolute/relative/empty/unset XDG: actual subprocess add/show з різних cwd використовують правильний fake-home path; ID/дані збережені, relative XDG не створено, sentinel незмінний.
- `test_qa_untrusted_path_and_error_are_literal_and_private`: corrupted DB у path з markup/LF/tab/OSC/ESC/bell/bidi; CLI 1, literal escapes у stderr, без raw controls/traceback, original hash незмінний.

Focused QA run: `uv run --no-sync pytest tests/test_qa_journeys.py -q` → **20 passed in 2.39s**. Після додавання виконано final full gate, наведений нижче; focused suite його не замінює.

## AC → фактично виконані assertions

Усі названі tests виконано у final full suite. Скорочення шляхів: `validation` = `tests/test_validation.py`, `storage` = `tests/test_storage.py`, `services` = `tests/test_services.py`, `cli` = `tests/test_cli.py`, `interactive` = `tests/test_interactive.py`, `qa` = `tests/test_qa_journeys.py`. PASS означає конкретні assertions нижче, не лише наявну назву тесту.

| AC | Actual test/assertion evidence | Статус |
|---|---|---|
| 01 | `interactive::test_real_pty_dashboard_navigation_and_retry` ×60/80/120 asserts Коло,0/0,7днів, unknown choice/menu live, create/exit; `test_in_process_full_menu_forms_and_preserved_expanded_tags` проходить усі розділи; `qa::test_qa_real_pty_note_complete_journey` реально відкриває help/calendar/notes і empty state клавіатурою. | PASS |
| 02 | `storage::test_roundtrip_permissions_and_cascade` і `cli::test_contact_lifecycle_in_new_process_and_different_cwd` assert усі поля/обидва phones/stable ID після нового процесу; `services::test_contacts_duplicate_search_and_atomic_edit` залишає duplicates з різними IDs; collision exhaustion/retry asserts попередні records лишилися; мінімальні contacts у services/qa. Full IDs видимі у width/render/PTY assertions. | PASS |
| 03 | `validation::test_required_rejects_boundaries`, `test_text_limits_and_original_body`, `test_invalid_phones`, `test_phones_normalization_order_and_duplicates`, `test_email_rejects_invalid`, `test_email_valid_limits_and_dates`: name0/1/120/121,address500/501,phones9/10/15/16 та ASCII/plus/tab/duplicate,email bounds/dots/domain/invalid+future dates. `services` asserts address+invalid-email edit лишає весь original Contact; actual PTY email-only retry asserts name prompt один раз і збережений phone/name. | PASS |
| 04 | `services::test_contacts_duplicate_search_and_atomic_edit`: Ukrainian casefold/name/address/email, formatted phone digits, trim/empty/no matches; atomic edit з незмінним ID/name/address, phone replacement,email/birthday clear. `cli::test_invalid_arguments_no_prompt_no_traceback` asserts value+clear2; lifecycle й render tests відрізняють no-match від empty. | PASS |
| 05 | CLI lifecycle asserts delete без yes2/record still listed, yes removes/restart show2. Missing exact IDs show/edit/delete обох сутностей2; додатковий actual populated subprocess probe для всіх6 операцій asserts DB SHA незмінний та обидва інші records збережені (`missing-id-populated.json`). `qa` actual note confirmation Enter лишає record після fresh reopen; ТАК видаляє; interactive no/yes і Ctrl+C/EOF confirmations зберігають дані, ID+label видимі. | PASS |
| 06 | `tests/test_birthdays.py::test_inclusive_year_rollover_and_sort`: Dec30,N3 includes Jan02/excludes Jan03, exact days0/3/3, N0, N366 one nearest/contact, missing birthday omitted, ordering. CLI -1/367/1.5/x →2; actual PTY calendar N0 перевірено у qa. | PASS |
| 07 | `test_leap_policy_and_immutable_original`: 2025Feb28,N0 included;2028Feb28,N0 excluded/N1 Feb29; після річниці2029Feb28, stored original2000Feb29. `test_local_clock_and_invalid_naive` asserts Kyiv/UTC midnight dates; CLI invalid zone2/storage absent; service midnight snapshot refresh asserted. | PASS |
| 08 | CLI note subprocess add/show/search/edit/restart/delete, body-file/stdin UTF-8/LF; title/body boundaries й whitespace у validation; service invalid title+body edit лишає original Note. `qa` actual full PTY note lifecycle asserts exact Unicode/initial+final LF/dot/body/tags/stable ID after fresh opens. Existing malformed binary stdin add/edit cases2 before storage, DB byte preservation й exact CRLF/CR/LF/tab positive assertions також виконано. | PASS |
| 09 | `validation::test_tags_casefold_expansion_and_literal_comma`: normalized duplicate,empty,40/41,ß expansion,comma. `services::test_note_search_and_tuple_sort`: title/body casefold AND exact tag; [а],[а,б],[б],[] order/title+ID tie; edit omission/clear. QA PTY asserts duplicate/comma tags, query+tag matches, no-match, tag clear and ID stable. | PASS |
| 10 | Existing real PTY contact create/edit/note multiline/delete Ctrl+C→dashboard and EOF menu/form/confirmation0; QA adds note body/tags/delete confirmation × Ctrl+C/EOF, exact original note/contact after fresh Store. Invalid body retries only body (title prompt count1), exact dot/LF; interactive Enter/!clear/!!clear and expanded-tag preservation asserted; normal exits0. | PASS |
| 11 | CLI separate processes/different cwd stable IDs/all fields; QA actual default fake-HOME/XDG matrices and explicit data isolation. Real failed parent/children/commit tests plus QA actual commit failure through CLI→no success, exact DB hash and fresh reopen previous state. No candidate accepted before commit. | PASS |
| 12 | storage corrupt/zero/unknown app/version/schema/FK/domain/positions/digits hash-preservation; permission/3s lock; parent/children/commit failure rollback. Actual subprocess initialization crashes before commit/before link/after link assert final absent/absent/present and ordinary restart without cleanup, leftovers hashes unchanged. Real hot journal raises SQLite776 before Store recovery then exact committed40 records; unknown-header real journal hashes remain. No-clobber/unsupported link negative assertions. sqliteX trigger/table/index refusal and CLI false-save regression1/no success/unchanged DB executed. | PASS |
| 13 | CLI lifecycle/all help levels/version/no DB access despite invalid zone, missing/invalid args2, streams/no traceback/no ANSI, explicit stdin body sources and malformed bytes. QA holds stdin open while unconfirmed deletes/no-command reject without waiting/storage; command KeyboardInterrupt handler130 in existing in-process assertion. Actual console/module help and uv help independently executed. | PASS |
| 14 | `tests/test_demo.py::test_demo_leap_safe_and_reseeded` asserts 2028Feb29→2000Feb29/today anniversary0, earlier1996 unchanged, fresh dirs/fixtures/cleanup. Explicit data-dir rejects before filesystem resolver. Actual PTY demo mutation/reseed/sentinel test plus independent actual `uv run kolo demo` at60/80/120 assert3contacts/2notes/banner/temp path/today birthday and cleanup/no fake personal data creation. | PASS |
| 15 | `tests/test_render.py` at60/80/120 asserts full IDs/fields, literal markup, no raw ESC/bell/bidi, line widths, body LF/tab policy, no-color/plain. Repaired single-line LF/tab heading/details/current values asserted with original storage unchanged. QA path/error OSC/controls probe and real note long title/markup PTY journeys; actual colored demo menu/help/list/details inspected at all3 widths. Text communicates error/success/actions without color dependence. | PASS |
| 16 | Independent locked sync/build/console+module help, additional exact `uv sync`, `uv run kolo --help`, actual PTY `uv run kolo demo` at all3 widths. Real run.sh from another cwd preserves space-containing path/title and multiline body in add/show. Current Ukrainian README inspected against executed commands/path/date/phone/tag/clear/demo rules. Optional global tool install/normal real-user first launch/Windows double-click NOT RUN by QA; controller owns them after gates. | PASS in assigned scope |

## Required full gate — фактичні QA commands/results

Кожний `uv` нижче = `/home/iknow/.local/bin/uv`; cwd `/home/iknow/goit-projects/personal-assistant`. Commands запускались послідовно, exit/stdout/stderr не приховувалися. Baseline logs `01.txt`—`11.txt`; final logs `/tmp/kolo-qa-gate-pk5bz2bz/final/01.txt`—`11.txt`, exact argv/exit/time у `final/results.json`.

| Команда | QA actual result |
|---|---|
| `uv sync --locked --all-groups` | PASS, exit0;45 resolved/44 installed non-project audited, lock unchanged |
| `uv run --no-sync ruff format --check .` | PASS, exit0 whole repo; ще раз виконано після author-owned report formatting |
| `uv run --no-sync ruff check .` | PASS, exit0, All checks passed |
| `uv run --no-sync mypy .` | PASS, exit0,23 source/test files strict |
| `uv run --no-sync pytest --cov=src/kolo --cov-report=term-missing --cov-fail-under=80 -q` | PASS, exit0, **136 passed in14.76s;95.33%,963 statements/45 missed** |
| `uv run --no-sync bandit -r src/kolo` | PASS, exit0,1310 lines,0findings/0skips/0suppressions |
| `uv export --frozen --all-groups --no-emit-project --format requirements-txt --output-file /tmp/kolo-qa-gate-pk5bz2bz/final/audit-requirements.txt` | PASS, exit0, all resolved runtime/dev/transitive hashed pins |
| `uv run --no-sync pip-audit --requirement /tmp/kolo-qa-gate-pk5bz2bz/final/audit-requirements.txt --no-deps --disable-pip --require-hashes` | PASS, exit0, No known vulnerabilities found |
| `uv build` | PASS, exit0, sdist `kolo_assistant-1.0.0.tar.gz` + wheel `kolo_assistant-1.0.0-py3-none-any.whl` |
| `uv run --no-sync kolo --help` | PASS, exit0, Ukrainian command tree/options/example |
| `uv run --no-sync python -m kolo --help` | PASS, exit0, same help contract |

pip-audit emitted generic advisories that no-deps is redundant with require-hashes and fully hashed pins are preferable. Actual export already has complete locked hashes; no dependency/CVE ignored. These advisories are disclosed, not unresolved vulnerabilities. Network permitted only for dependency preparation/audit; runtime code has no network operations, in-process runtime tests deny socket connect.

Coverage includes every module, including cli93%,interactive95%,render100%,demo100%,storage92%. `__main__.py` two lines remain unmeasured in-process (0%), but real subprocess/module-entrypoint assertions execute them; no exclusion conceals them. Threshold80% remains unchanged.

## Real launches, terminal evidence, storage evidence

Additional QA launches, all exit0: `uv sync`; `uv run kolo --help`; colored real-PTY `uv run kolo demo` at60/80/120; absolute `run.sh --data-dir TEMP notes add/show` from other cwd with spaces and exact multiline body. `actual-launch-results.json` and `actual-run-sh.txt` retain results. `actual-uv-demo-{60,80,120}.raw/.txt` retain raw ANSI terminal and readable transcripts; inspected menu/help/contact list/full details, IDs/phone/email/date remain accessible at every width. All demo paths were absent after normal exit; fake HOME sentinel and fake personal-data locations unchanged.

New PTY tests also retain note journey/cancellation transcripts under pytest temporary directories. Original suite uses actual WSL controlling terminals, TIOCSWINSZ, Ctrl+C/Ctrl+D and bounded waits. Existing init crashes use real child SQLite/os boundary interception and os._exit9, not production crash flags. Hot-journal fixture performs true BEGIN IMMEDIATE/cache spill/child exit, verifies readonly776, then actual Store native recovery; it is not just a mocked error code. All runtime data synthetic and temporary; no personal default store was inspected or changed.

Additional populated missing-ID subprocess probe checks all6 show/edit/delete operations with contact and note already present:2,stdout empty,DB hash unchanged and original records still listed. Evidence `missing-id-populated.json`. QA reran the repaired R1/R2/R3 regressions as part of full suite: unknown sqliteX objects are refused without false save, malformed stdin2 before storage, single-line LF/tab escaped while body LF survives.

## Capacity — вимірювання, не SLA

Fresh WSL TemporaryDirectory, one synthetic bulk-seed transaction using Store,5000 contacts +5000 notes, note body1800 Unicode characters, followed by ordinary Store validation/Assistant list/search. Actual **10000 parent entities,21,962,752bytes**, seed0.1070s, combined list0.0931s, combined search0.1267s; matches1contact/5000notes. `qa-capacity.json` stores the measurement. Temporary data removed. This differs from a projected1040-record/<8MiB estimate; no hard latency SLA was invented.

## Blockers, coverage limits, regression risk і передача

Production blockers: **None observed**. All16AC have executed assertions above. Threshold coverage95.33% does not mean every implementation branch is covered; expected hardware/fsync failures are outside approved durability guarantees. Plaintext storage, no shared concurrent editing/migrations/import/export/background reminders remain accepted scope. Actual lock/error and no-clobber concurrency paths are covered.

Optional installed `/home/iknow/.local/bin/kolo`, real user's normal default launch, and Windows GUI/double-click launch are **NOT RUN by QA**; no installation or real contact inspection was performed. They are controller-owned final handoff actions, not disguised PASS. Test environments deliberately use fake HOME/XDG or explicit temporary data-dir.

Renewed independent review is required for **`tests/test_qa_journeys.py`**. Reviewer should inspect all20 added cases and final30-file identity; no production changes require repair. If later code/docs/installation changes invalidate results, controller reruns affected gates. This report and new test file are the only QA-authored paths. Writer slot is released to controller on return; QA does not advance global state or authorize publication.
</details>
