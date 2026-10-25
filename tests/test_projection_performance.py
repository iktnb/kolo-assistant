import json
import subprocess
import sys

import pytest

from kolo.tui_forms import BodyProjection

PREFIX = "[bold]\x1b]0;ATTACK\x07\u202e\n"
MAX_BODY = PREFIX + "я" * (10000 - len(PREFIX))


@pytest.mark.parametrize(
    "raw, current, expected",
    [
        ("", MAX_BODY, MAX_BODY),
        ("Текст\x1b]0;ATTACK\x07\u202e\n" + "я" * 9970, MAX_BODY, MAX_BODY),
        ("Повтор\r\n" * 1250, "Повтор\n" * 1250, "Повтор\r\n" * 1250),
    ],
    ids=["new-maximum-body", "edit-maximum-lf-body", "unchanged-mixed-body"],
)
def test_large_body_restoration_finishes_within_five_seconds(raw: str, current: str, expected: str) -> None:
    script = (
        "import json, sys; from kolo.tui_forms import BodyProjection; "
        "raw, current = json.load(sys.stdin); "
        "sys.stdout.write(BodyProjection.from_raw(raw).restore(current))"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", script],
        input=json.dumps([raw, current]).encode(),
        capture_output=True,
        timeout=5,
        check=True,
    )
    assert result.stdout == expected.encode() and result.stderr == b""


@pytest.mark.parametrize(
    "current, expected",
    [("A\nA\n", "A\r\nA\n"), ("X\nA\nA\n", "X\r\nA\nA\r")],
)
def test_ambiguous_repeated_edits_keep_earliest_original_separator_spans(current: str, expected: str) -> None:
    projection = BodyProjection.from_raw("A\r\nA\nA\r")
    assert projection.restore(current) == expected
