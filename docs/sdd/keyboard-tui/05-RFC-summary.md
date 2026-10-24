# keyboard-tui: стислий RFC

Дата: 2026-10-24. architect-agent `/root/tui_architect`. Статус: дизайн для незалежного огляду; реалізація NOT RUN.

## Мета

- Повноекранне українське «Коло»: Up/Down вибирають дії й записи, Enter відкриває, Back/Esc повертає зі збереженим контекстом.

## Змінюваний компонент

- **personal-assistant**: нові Textual app/screens/forms/TCSS; router у cli.py, isolated demo, runtime dependency/lock, тести й README. Assistant/SQLite/domain API без змін.
- Немає нової інфраструктури, мережі, schema migration чи нових бізнес-функцій. Jvers registry N/A; це незалежний GoIT repo.

## Ключові рішення

1. Textual native widgets і спільні semantic styles; read-only дані через render.safe. Редактори лишають raw текст. Локальний ADR-TUI-01 і відхилені Rich-only/ручний curses — [RFC §7](01-RFC.md).
2. Default kolo/demo — TUI; глобальний --line-mode перед командою зберігає числовий інтерфейс. --plain/NO_COLOR прибирають кольори, зберігаючи full-screen/focus. Scriptable CLI й nonTTY guards незмінні.
3. Стек зберігає query/tag/sort/ID/index/scroll/focus. Save повертає до origin list/saved record; filtered-out status, nearest після delete, empty Enter без дії.
4. Один serialized thread adapter навколо чинного Assistant/Store; startup Store також за recoverable TUI boundary. Busy не блокує event loop; duplicate save й cancellation committed write заборонені.
5. Draft порівнюється з initialized widget snapshot; raw body зберігається окремо. Canonical LF TextArea + raw-span/SequenceMatcher save projection зберігає untouched mixed/Unicode/trailing separators; newly inserted breaks LF, helper у worker. Unchanged body/fields UNSET, optional clear None/(). Field/save errors лишають draft. Confirmations safe default; Ctrl+C/Ctrl+Q також guarded, terminal відновлюється.
6. Clock snapshot на refresh, resume/apply й60s date-change check через existing injected today. Calendar не застаріває після midnight/year rollover.

## Ризики й перевірки

- Native Ctrl+Q/Ctrl+C, TextArea Enter/Tab і mixed-EOL normalization, controls у editor, stale worker result, 60×20 clipping — конкретні Pilot+fault tests у [чеклісті](03-test-checklist.md).
- Усі TUI-AC-01—11 мають assertions і задачі; старі numeric PTY отримують явний line-mode зі збереженням assertions. Новий default PTY перевіряє actual terminal restore.
- Baseline переданий контролером:142 PASS/95.33% всього src. Вимоги: full Ruff/mypy/pytest, coverage>=80% без exclusions і прозоре порівняння, Bandit, аудит runtime+dev lock, offline/sentinel tests.
- Textual8.2.8 — перевірений PyPI кандидат, не перевірена сумісність; developer фіксує точну pin після resolver/audit. Version1.1.0, TCSS у wheel, clean installed-wheel запуск із іншого cwd обов'язкові.
- [Задачі](04-tasks.md): dependency/router → vertical slice/forms → filters/calendar/errors → regression gates → independent review/QA → український README та працююче локальне встановлення.
- Матеріальних продуктових питань немає. Source/code read-only на цьому етапі; commit/push/GitLab/publication не дозволені.
