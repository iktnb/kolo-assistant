# keyboard-tui — developer post-error focus repair

2026-10-24 · `dev-agent` · actual agent `/root/tui_developer` · `personal-assistant`.
**Developer gates PASS; writer released with this report.** Independent review/QA and delivery remain controller-owned.

## Inputs and source identity

Followed the shared/dev/quality contract, approved feature RFC/spec/checklist/tasks, and the controller's bounded QA repair assignment. Current QA report `06-qa-report.md` SHA256: `095d37cfbfee854f6e29e8355a3b3f1a295e82d07a0f88314403c9b53f4469b4`. Native design-system/accessibility/responsive guidance remains applicable.

| Snapshot | Identity |
| --- | --- |
| Original baseline, controller-attributed |30 files; `b1df830005d7957221c2402cd52cc36118df7a7f6d25b83d8e2f7777211fd74f`;142 PASS/95.33% |
| Approved pre-QA implementation, historical |38 files; `88ede3b619cfd38284558fdf9abf6adcc36aec351c23c346a7fae4fee5c19ad6`;203 PASS/95.46% |
| Previous UI repair, historical |39 files; `cd0fb407839598ea168598ce06e1ddd1916233e26f81ca71d5f9e2642639d2e1`;224 PASS/95.63% |
| Strengthened QA input |39 files; `6540c290d174cbbf82db9b8f59799c96abad3e71fceff43d8244fd1b3cc5c272` |
| **Current repaired source** |**39 files; `8d306ae7bb64400d96e17e7e8c87f293d16e519070c881206e2dcf0679d6979d`** |
| Full diff against original baseline |**`b856dd623a541bff2c06b973887de6073296557b57241dc408f9aa82d0c2f6a1`** |

HEAD is absent/unborn. Snapshot method: sorted path+NUL+bytes, including untracked source and excluding docs. Per-file hashes and actual delta are external `developer-source-evidence.json` / `developer-source.diff` under `/home/iknow/.local/state/codex-sdd/feature-52b8ff541ca6/keyboard-tui`.

Only `src/kolo/tui_forms.py` and this development report changed in this bounded repair. **QA test bytes unchanged:** `tests/test_tui_qa.py` SHA256 `cad1add633deacb2064b9e4bfaa8f840532b68949a01c2ebe5c09f3e50868083`. All 103 QA assertion expressions are retained. QA/review reports and README untouched. Domain/SQLite/validation/render/calendar/launchers remain byte-identical to original baseline. No personal data, `.env*`, GitLab, commit/push/publication or global installation work.

## Repair and focused evidence

After a failed save, the pinned Ukrainian reason can wrap and shrink the scrolling fields. Automatic focus scrolling previously used geometry from before that layout, clipping the focused Save button. The error path now sets native focus through public `Screen.set_focus(scroll_visible=False)`, then schedules a public after-refresh reveal using the final focused-control region and current scroll viewport. Guards require the form to remain mounted, the app running, the form to be the actual top screen, and the same control to retain focus. The callback scrolls only the fields viewport; it preserves the complete pinned reason, draft, database, retry and lifecycle behavior.

Focused command:

```text
uv run --no-sync pytest tests/test_tui_qa.py::test_qa_field_error_reason_and_focus_visible tests/test_tui_qa.py::test_qa_screen_matrix_visible_keyboard_focus_and_preserved_long_draft tests/test_tui_qa.py::test_qa_long_write_error_keeps_save_reason_and_draft_visible -q --tb=short
```

**10 PASS in 82.79s**: 4 invalid-name/email cases, 3 full keyboard/resize/10000-character draft matrices, 3 long-path write-error cases at 60×20/80×24/120×36. The strengthened oracle checks actual ancestor clipping, full reason, focused control, unchanged raw draft/database and successful explicit retry. No QA assertion, test delay or configured gate was weakened.

Prior repairs remain unchanged and pass in the current full suite:

- Form reasons remain pinned outside scrolling fields; native caret/Enter/Tab and long-body resize stay usable.
- Back restores exact query/tag/sort/ID/index14/inner-scroll48 and selected-row visibility. The coordinated public focus/inner-layout/outer-reveal path also handles normal Up/Down without resetting native inner scroll. Earlier final-code cold repeats passed 4/4,6.17–6.60s each, in addition to 8 initial repeats; these are historical unchanged-path evidence.
- Native `.-highlight` selectors produce readable dark phone/ID text on teal, with a bold/thick selection marker and no palette inversion in plain mode.
- Canonical body validation precedes diff; reconstructed raw text is validated again, unchanged body skips diff/uses UNSET, and stored mixed/Unicode separators retain exact spans.
- Missing-ID Delete refreshes the nearest origin selection; retryable storage failure and missing-ID form drafts are retained. Actual top-screen ownership prevents late reads from popping Help or changing unrelated screens.
- The existing developer Pilot cleanup handles a driver wait only after verified native shutdown: return value/code 0, app stopped, pending/writing 0, no workers and exactly one persisted contact. Production lifecycle scheduling is unchanged.

## Renewed gates on current source

Repo `/home/iknow/goit-projects/personal-assistant`; uv `/home/iknow/.local/bin/uv`. Commands below actually executed; full test log is external `developer-final-full-pytest.txt`.

| Command / check | Result |
| --- | --- |
| `uv sync --locked --all-groups` |PASS; 48 resolved/47 audited |
| `uv run --no-sync ruff format --check .` |PASS; 53 files |
| `uv run --no-sync ruff check .` |PASS |
| `uv run --no-sync mypy .` |PASS; strict, 31 files including QA |
| `uv run --no-sync pytest --cov=src/kolo --cov-report=term-missing --cov-fail-under=80 -vv --tb=short -o faulthandler_timeout=45` |**227 PASS /425.65s;95.54% whole src/kolo;1703 statements/76 missing** |
| `uv run --no-sync bandit -r src/kolo` |PASS; 2184 LOC; 0 findings/skipped lines |
| `uv export --frozen --all-groups --no-emit-project --format requirements-txt --output-file <external>/developer-audit.txt` |PASS; runtime and all dev groups |
| `uv run --no-sync pip-audit --requirement <external>/developer-audit.txt --no-deps --disable-pip --require-hashes` |PASS; 0 known vulnerabilities |
| `uv build` |PASS; 1.1.0 sdist/wheel,packaged TCSS |
| `uv run --no-sync kolo --help`; `uv run --no-sync python -m kolo --help` |PASS |
| Rebuilt wheel reinstalled in isolated external venv, smoke from `/tmp` |PASS; site-packages 1.1.0/Textual 8.2.8/assets,both help entrypoints,default+demo60×20 real PTY,termios/temp cleanup |

Final 227 comprises 142 baseline + 65 developer + 20 unchanged independent QA cases. Coverage threshold 80 and full source scope remain unchanged; no exclusions/skips/suppressions. The 45s faulthandler option is diagnostic only. The full runner records the exact verbose command and its actual completion. Current wheel SHA256: **`224fe11fad1ee6be60dd1d971f104438f5637a9cc9ff8fc9d26e95341fcf388b`**. Smoke script/environment: external `developer-wheel-smoke.py` / `developer-wheel-venv`.

## AC evidence and handoff

| AC | Current included acceptance evidence |
| --- | --- |
|01 |Home/native menus/help,non-TTY/lazy guards,legacy line mode,default PTY |
|02 |duplicates/stable IDs/neighbors,missing-ID recovery,Back context and outer/inner row visibility |
|03 |native caret/Enter/Tab/Shift+Tab,keyboard actions,visible focused controls/arrow rows |
|04 |contact CRUD/optional clear/phones,actual parent-child rollback/retry,CLI/schema1 roundtrip |
|05 |note CRUD/tags/expanded tags,mixed/Unicode/trailing EOLs,native edits,canonical/raw limits |
|06 |query AND exact tag/Title-Tags sort/clear/no-match/stale reads,far filtered context |
|07 |exact leap/year boundaries/order,0/7/366/invalid intervals,live refresh,birthday contact edit |
|08 |visible full field/write reasons and focused controls,draft retention,true rollback/retry,read recovery |
|09 |safe dirty/delete/quit defaults,blocked-worker single commit/deferred exit,native exit 0/7,PTY restoration |
|10 |all 3 terminal sizes,long 10000 draft/resize/literals,selected contrast/plain marker,ancestor-clipped focus |
|11 |unchanged SQLite 1/IDs/domain,CLI↔TUI,isolated demo/reseed/cleanup,wheel/TCSS/help/PTY |

No known assigned defect remains after the renewed checks. Independent code review/QA verdicts, final rendered-image acceptance, README/screenshots and global tool installation remain their owners' work. The installed global app is still 1.0.0 pending the controller's final reinstall. Earlier 29-assertion EOL developer and 97-assertion controller probes remain attributed historical evidence; they are not substituted for this full run. No broader platform or screen-reader compliance is claimed.
