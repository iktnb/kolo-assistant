# Зміни документації — «Коло»

Дата: 2026-10-24. Роль: `doc-agent`; фактичний агент **`/root/documenter`**. Репозиторій: `/home/iknow/goit-projects/personal-assistant`, Ubuntu WSL, гілка `feature/personal-assistant`, HEAD ще немає. Це документація перевіреної локальної версії **1.0.0**; зовнішній реліз / публікація **pending release**, не виконувалися.

## Змінені файли

Documenter змінив лише:

- `README.md` — українська інструкція для користувача й розробника.
- `docs/sdd/personal-assistant/07-doc-diff.md` — цей звіт.

`docs/images/kolo-overview.png` підготував controller до цього етапу; documenter його переглянув і додав посилання з чесним підписом про вигадані демонстраційні дані. Зображення не є знімком особистого сховища. SHA-256 незмінного зображення: `1038fd05c7288d83ceb446c5224b5b78e858ff59527c0c290f31db3f7728dac7`.

## До → після

| Частина | До | Після |
|---|---|---|
| Перший запуск | Початок із підготовки source-середовища через uv | Спочатку точні команди Windows → WSL для вже встановленого `/home/iknow/.local/bin/kolo`, безпечне `demo`, потім власні записи; source setup нижче |
| Меню | Опис доступних можливостей | Короткий покроковий сценарій контакт → список/ID → нотатка → календар; видимі правила Enter, Ctrl+C/Ctrl+D і підтвердження |
| Приклади команд | CRUD з умовними ID у стандартному сховищі | Відокремлений `mktemp`-каталог для навчання; явне прохання підставити створені ID, CRUD/пошук/теги/багаторядковий текст/календар |
| Дані й резервна копія | Шляхи, загальна порада скопіювати файл | Пріоритет шляхів, приватність, копіювання всього каталогу лише після закриття сеансів; приклад `cp -a` |
| Стан якості | Посилання переважно на звіт developer | Актуальні незалежні QA/review, 136 tests / 95.33%; локальна готовність відокремлена від зовнішнього релізу |
| Source / installed copy | Глобальний інструмент ще не потрібен | Пояснено, що `kolo` використовує встановлену копію, а `run.sh` / uv — поточні джерела |

Збережено прийняті правила: повний незмінний ID та однакові імена; формати/межі полів; явне очищення й omission; Unicode-пошук/теги; часовий пояс Kyiv, включний календар 0–366 і правило 29 лютого; скасування без часткових змін; ізоляція demo/data-dir; stdout/stderr і коди 0/1/2/130; обмеження локального сховища.

## Входи та узгодженість архітектури

Прочитано повний generated doc-packet зі shared/role/assignment, PRD, RFC, spec, tasks, README, `run.sh`, `start-kolo.cmd`, актуальні незалежні звіти й controller evidence. Файлових AGENTS.md/CLAUDE.md на WSL ancestor chain не знайдено. Jvers і `.env*` не використовувалися.

- [Spec](02-spec.yaml), SHA-256 `9a7ddf648528e8d645693eb3ef16776734a3c167610d3a7e96c6c9c3221686bf`: `event_contracts: []`, зовнішніх API/Kafka немає; data model — локальний `kolo.sqlite3`, schema v1.
- [Фінальний code review](05-code-review.md): **APPROVED**, SHA-256 `12eff3188a885e535328d6759f240ae34d45249327d15b42762a32f62fb1d108`.
- [Незалежний QA](06-qa-report.md): **PASS**, SHA-256 `ff611dfdb0bc9729b6b75a192700146968895a8a223fc2102d939671d9f0ff37`; 136 tests, 95.33% усього `src/kolo`, всі required quality checks PASS.

Окремого HLD у цьому незалежному проєкті немає. Прийнятий [RFC](01-RFC.md) узгоджений із порожніми event contracts, локальними компонентами, SQLite та потоками даних. Архітектурних змін цього етапу немає; історичний design документ і shipped/production реєстри не переписувалися. AC-16 документовано без розширення продуктового обсягу; правила AC-02—15 відображено в користувацьких інструкціях, їх незалежні assertions наведено в QA-звіті.

## Фактична перевірка documenter

Усі runtime-приклади виконувалися лише на вигаданих тимчасових даних, із fake HOME/XDG або явним `--data-dir`. Особисту стандартну базу не читали й не змінювали. Тимчасові робочі дані після перевірки прибрано.

| Перевірка | Фактичний результат |
|---|---|
| Встановлений `kolo --help` і довідка contacts/notes/add/edit/list/show/delete/birthdays/demo | PASS: прапорці, аргументи й українські приклади звірено з README; help без відкриття сховища |
| 35 окремих CLI-команд | PASS: створення/читання/пошук/редагування/clear/delete контактів і нотаток, теги, UTF-8 file/stdin, birthdays 7/0, очікувані помилки 2, source `run.sh` з іншого cwd |
| Шість навчальних shell-блоків README, виконаних буквально в Bash | PASS: `mktemp`, лапки/змінні, CRUD, file/stdin pipeline, календар; умовні ID замінено на фактично створені, як пояснено користувачеві |
| Точний shell-блок резервної копії | PASS на fake HOME: `cp -a` створив копію каталогу, bytes SQLite збігаються; особистий шлях не використовувався |
| Source identity до/після runtime-перевірок | PASS: всі 30 файлів незмінні до документування; після README всі решта 29 byte-identical |
| Форматування README | PASS: `uv run --no-sync --project /home/iknow/goit-projects/personal-assistant ruff format /home/iknow/goit-projects/personal-assistant/README.md` → `1 file left unchanged` |

Evidence documenter: `/tmp/kolo-doc-verification-4vvuxl_t/results.json`, `readme-shell-examples.json`, `after-source.json`. Перший запуск shell-перевіряча зупинився до виконання команд через помилкове очікування 7 навчальних блоків; виправлено лічильник на фактичні 6. Подальший запуск перевірив усі 6 плюс окремий блок backup, без послаблення поведінкових assertions.

Повний pytest/lint/types/security/audit/build не повторювався documenter: незалежні QA та фінальний reviewer вже перевірили той самий незмінний application/test/config/lock snapshot. Це використаний QA execution evidence, не заявлений власний запуск documenter. Після збереження обох owned файлів виконано `uv run --no-sync --project /home/iknow/goit-projects/personal-assistant ruff format /home/iknow/goit-projects/personal-assistant/README.md /home/iknow/goit-projects/personal-assistant/docs/sdd/personal-assistant/07-doc-diff.md` → PASS, `2 files left unchanged`; із кореня репозиторію `uv run --no-sync ruff format --check .` → PASS, `35 files already formatted`. Інші файли formatter не змінював.

## Перевірений локальний запуск: controller evidence

Файли `/home/iknow/.local/state/codex-sdd/feature-a994053c553c/personal-assistant/installed-verification.json` і `controller-acceptance-results.json` прочитано без змін. Вони фіксують:

- Встановлення локального wheel **1.0.0**, SHA-256 `28d4c5c492c388134edb4d21db7b15a89b26f7ee704737e8af9c651b6b15b1b5`, offline із перевіреними locked runtime constraints; 12 встановлених модулів byte-identical джерелам.
- Фактичні installed `--version` / `--help`, 97 ізольованих end-to-end assertions — PASS.
- Справжній звичайний PTY-сеанс 1850 і demo PTY-сеанс 81134 завершилися 0; нове стандартне сховище мало 0 контактів / 0 нотаток, права каталогу `0700`, файлу `0600`. Demo прибрано, особисті дані не змінені.
- Перевірене Windows CMD → WSL передавання аргументів для `start-kolo.cmd --help`; literal GUI double-click не спостерігався й не позначається PASS.

Ці запуски виконав **controller**, а не documenter. Login Bash знаходить `kolo`; прямий WSL exec може не містити `~/.local/bin` у PATH, тому Windows quickstart використовує перевірений абсолютний шлях.

## Source identity та передача

Алгоритм source fingerprint: відсортоване relative filename UTF-8 + NUL + raw bytes 30 manifest-файлів source/config/README/launchers/tests; design/reports/state/image/caches/venv/dist поза цим fingerprint.

- До документації: `0876e9602502d7d8c390fd9b8ba1076f5322f013c3aaf749d773d04efbdfe917`.
- Після README: `2f87516716259e65b1e95dd5e4fea38224ad1525ad7332d436d440856b7ac7eb`.
- Змінився лише README; **29/29 інших manifest-файлів byte-identical**, зокрема всі production modules, tests, config, lock і launchers.
- README до: `12ce8e64f9cecaf073486e99dd54f70aa7775c518b4c3afdb65aa19f7717caf7`.
- Поточний README: **`d8151930735c109b48113a91c74e7e22050257b3e403538eeb71deb9df5a0c3a`**.

**Documentation verdict: COMPLETE; locally verified, pending external release.** Робочий локальний застосунок і технічні gates підтверджено. Після README controller володіє фінальним rebuild/reinstall для оновлення package metadata та завершенням аудиту/global state; documenter цього не виконував і не заявляє виконаним. Немає commit, push, публікації, deployment чи дозволу на них. Підсумкова перевірка форматування пройшла; writer slot цих двох файлів повернено controller.

## Остаточне оновлення контролера — 2026-10-24

Після завершеного етапу documenter контролер `/root` виправив у README лише підсумковий лічильник **136 → 142 тести**. Команди, правила, зображення й структура інструкції незмінні. Фінальна вузька правка довідки пройшла незалежний review (`ee95929aab1709171b208569af22aed0937ef15fc5d8285b2dcc88e274c43cb9`) та свіжий повний QA (`85f9c5587aeb9761beb0fa1eec735b5f5fd0732f5e2ecf1b1a62bcb4c8757ea3`): **142 PASS, 95.33%, усі 11 required gates PASS**. Вкладені help-заголовки й шість скопійованих команд відновлення перевірені окремо.

Поточний README SHA-256: `5be02543471162f91f2b0f016443df2cfc558334585a96f6795f4342d808f572`. Повний поточний30-file source: `b1df830005d7957221c2402cd52cc36118df7a7f6d25b83d8e2f7777211fd74f`; усі29 інших файлів byte-identical до reviewed/QA snapshot `aa6f3661c46aa68ae09ced610c3c1dec150b711621f07945ba2528572b21b5aa`. Контролер самостійно порівняв кожен файл і точний Git file set; source/tests/config/lock/launchers після QA не змінено.

Фінальний offline build виконано після README. Wheel SHA-256 `9a6ed57cd4c0a891073771eb3d3f6067d7e26e66976a7a19e5d7edb43fa996ad`: усі12 модулів дорівнюють джерелам, embedded README metadata дорівнює поточній інструкції. Перевстановлено тільки власний `kolo-assistant`1.0.0 з цим wheel і тими самими locked runtime constraints; усі5 installed package versions перевірено. Після перевстановлення metadata README та12 installed modules знову byte-identical; жодних нових залежностей.

Остаточний installed наскрізний сценарій: **97 assertions PASS** із тимчасовими даними. Вкладена installed довідка має один «Використання». Фактичний звичайний terminal-сеанс12128 завершився0; особиста книга лишається порожньою для користувача, дані розміщені у `/home/iknow/.local/share/kolo`, directory0700/database0600. Це controller execution, не приписаний documenter запуск. Evidence: `final-state-verification.json`, `wheel-verification.json`, `installed-verification.json`, `controller-acceptance-results.json` поруч із зовнішнім SDD journal.

**Фінальний стан: локально встановлено, працює й перевірено.** Зовнішній реліз не входив у доручення; commit/push/GitLab/publication/deployment не виконувалися. Попередні counts/hashes у звіті вище залишено як історію конкретного завершеного етапу документації; цей розділ фіксує остаточну локальну передачу.