# keyboard-tui - documentation handoff

2026-10-24 - `doc-agent` - actual agent `/root/tui_documenter`.

**Documentation READY; implementation documentation pending release.** The current implementation has independent APPROVED review and PASS technical QA. Final package rebuild, replacement of the globally installed tool, installed-app verification and delivery remain controller-owned next steps. No external release or publication is claimed.

## Scope and inputs

Exclusive assigned checkout writes: [README.md](../../../README.md) and this report. Source, tests, configuration, images, previous reports and historical `docs/sdd/personal-assistant` materials were read-only.

Read the complete doc packet/shared/role instructions, assignment, approved [PRD](00-prd-delta.md), [RFC](01-RFC.md), [specification](02-spec.yaml), [tasks](04-tasks.md), [development report](05-development-report.md), [independent code review](05-code-review.md), [QA report](06-qa-report.md), current source/CLI/launchers and external journal. No applicable on-disk AGENTS.md/CLAUDE.md was found in the repository or checked ancestors; supplied routing/assignment applies.

Evidence directory: `/home/iknow/.local/state/codex-sdd/feature-52b8ff541ca6/keyboard-tui`. Assignment SHA256 `9ad19ae66000eac12630ce2dadf817aaade66df8423b59e02c4a69f28f4bc5c4`; role/shared hashes `3551ca7500cfff8ba10c72c226eaa3ae0ab58ed573abdac89724e44b59a95f6b` / `392d4816e5f52b6b49d545b98d91c44c003933bb344a2d866498ef5efc85dc95`.

| Verified input | SHA256 |
| --- | --- |
| Current developer report | `06c6e14de1d0131beb2e7dea3ca3bc7ee0abc731b99ffc11e868686a08c8a7c5` |
| Independent APPROVED review | `400594226b1ce217d49e6652497c32bd6c7eff7b0e32189c80fb121eaf36748e` |
| Independent PASS implementation QA | `2368ff9377badb3b4e7fe0d7bb442db167490bab512422067e03476bdc5b23e6` |
| Root-provided fictional Home screenshot | `f9e68aa393c8b2c7da6538ddae420be2956473348a3ae5e3f1e7c889282fc303` |

HLD/Kafka/service registries are N/A: this standalone GoIT application has no HLD or distributed-service registry. The accepted specification has empty `event_contracts` and empty `data_model_changes`; SQLite schema 1 and domain contracts are unchanged. Existing RFC describes the TUI components and routes. No production HLD/shipped registry claim was added.

## Before / after

| Area | Before | Current documentation |
| --- | --- | --- |
| Primary screenshot | Old numeric-menu overview | Actual 80x24 full-screen Home capture with explicit fictional-demo caption; root-owned image unchanged |
| Main workflow | Numeric choices, copied typed IDs | Arrows/Enter details without typed IDs; native Tab/Shift+Tab, Esc/Back context, Ctrl+S, scoped F1/F2, multiline Enter, per-line phones/tags and empty optional-field clearing |
| Safety/recovery | Legacy interrupt and field rules in main flow | Current safe defaults for delete/dirty/quit, guarded Ctrl+C/Ctrl+Q, retained draft, retry and read-error actions |
| Legacy compatibility | Old rules presented as default | Compact explicit global `--line-mode` section contains numeric menu, ID entry, `!clear`/`!!`, semicolon phones, period-terminated body and legacy Ctrl+C/Ctrl+D |
| Launch/version | Claim that installed 1.0.0 was current | Project 1.1.0 described; source-first absolute WSL `run.sh` launches, separate installed entrypoint and version check; no premature installed-1.1.0 claim |
| Verification | Historical 142 / 95.33% presented as current | Current developer 227 / 95.54%, QA's own 30 acceptance cases correctly attributed and linked; original 1.0.0 evidence retained as history |

CLI examples, validation, storage locations/permissions, offline behavior, backup instructions, exit codes, source preparation and existing WSL launchers remain documented. `--plain`/`NO_COLOR` explicitly retain full-screen controls and terminal-control sequences.

## Own executed verification

External `doc-commands-check.py` and `doc-commands-evidence.json` preserve exact commands, stdout/stderr, return codes and before/after source hashes. `doc-readme-before.md` and `doc-readme.diff` preserve the actual documentation delta.

**24 isolated subprocess invocations PASS**, including:

- Source `kolo --version` = 1.1.0; top-level and note-edit help; `uv run --no-sync kolo --help` and `uv run --no-sync python -m kolo --help`.
- Absolute `run.sh --help` / `run.sh --version` from `/tmp`; installed absolute `kolo --help` / `--version` observed as **1.0.0**, with no install attempted.
- Current non-TTY default/demo, line-mode and plain guards return 2; demo plus explicit data directory returns 2 before creating that directory.
- All six README CLI-example shell blocks execute with source `kolo` first on PATH. Only documented placeholder IDs were replaced with the IDs actually created. Contact/note creation, show/edit/clear/delete, search/tag/sort, UTF-8 file/stdin body and birthday commands pass; final stored multiline bodies are exact.
- `uv run --no-sync ruff format --check .` PASS: 53 files already formatted. Full repository scope, read-only check, cache directed outside the checkout.

Additional Windows-shell smoke: `start-kolo.cmd --help` PASS, forwarding to the source 1.1.0 help including `--line-mode`. Final checks verified all 13 local Markdown links, balanced code fences, unchanged source/input-report/image hashes; external `doc-final-evidence.json` records final document hashes.

All example mutations used a newly created `/tmp/kolo-practice.*` directory, fake HOME/XDG and offline mode; those temporary data were removed. No personal-store path was opened. One initial harness assertion expected seven example blocks instead of the actual six; the external harness count was corrected and the complete check passed, without product/README changes.

Native interactive journeys, full tests/security/audit/build are not repeated by this documentation role. Current exact-source evidence is reused with attribution: developer **227 PASS / 95.54%** over all `src/kolo`, threshold 80 unchanged; independent QA **30 current acceptance cases PASS / 136.42s**, including real PTYs and current rendered/error-retry checks. See the linked reports for their separate verdicts. Backup execution and global replacement are NOT RUN by documenter; no personal data is needed for documentation verification.

## Identity and handoff

HEAD is absent/unborn; branch `feature/personal-assistant`. The source manifest includes README, so the prose change intentionally changes the 39-file aggregate. The 38-file code/config/test/launcher aggregate remains unchanged throughout documentation and checks.

| Snapshot | SHA256 |
| --- | --- |
| Accepted implementation before documentation, 39 files | `8d306ae7bb64400d96e17e7e8c87f293d16e519070c881206e2dcf0679d6979d` |
| README before | `5be02543471162f91f2b0f016443df2cfc558334585a96f6795f4342d808f572` |
| README after | `6b88de38bfbdace1334bb17410e70048d54eb19c75816ac84df7b31017bffe79` |
| Source manifest after README, 39 files | `d88ce346092f8b82dd328132468e7abb5ce310c9a357e7f0910b9cdb1b977e89` |
| Code/config/tests/launchers without prose, before = after, 38 files | `e8b3fe42aaac16c57626c855497ae6917a732121ff40e19a31f753f2ff4010a7` |

No source/test/config/image/other-report changes, agents spawned, personal-data or `.env*` access, global installation, commit, push, server, deployment or publication. The controller must now rebuild the wheel so its README metadata includes these instructions, install it locally and verify the actual installed command/metadata/assets/PTYs. **Documentation writer RELEASED; local final delivery remains pending.**
