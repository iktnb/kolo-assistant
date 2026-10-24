import os
import socket
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Never

import pytest

from kolo.services import Assistant
from kolo.storage import Store

TODAY = date(2026, 10, 24)


@pytest.fixture(autouse=True)
def offline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def deny(*args: object, **kwargs: object) -> Never:
        raise AssertionError("Runtime must not connect to the network")

    monkeypatch.setattr(socket.socket, "connect", deny)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_DATA_HOME", str(home / "data"))
    monkeypatch.delenv("KOLO_TIMEZONE", raising=False)


@pytest.fixture
def assistant(tmp_path: Path) -> Assistant:
    return Assistant(Store(tmp_path / "data", TODAY), lambda: TODAY)


@dataclass
class Runner:
    directory: Path
    home: Path

    def __call__(
        self, *args: str, stdin: str = "", cwd: Path | None = None, extra_env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.update({"HOME": str(self.home), "XDG_DATA_HOME": str(self.home / "xdg")})
        environment.update(extra_env or {})
        return subprocess.run(
            [sys.executable, "-m", "kolo", "--data-dir", str(self.directory), *args],
            input=stdin,
            text=True,
            capture_output=True,
            timeout=15,
            cwd=cwd,
            env=environment,
        )


@pytest.fixture
def runner(tmp_path: Path) -> Runner:
    home = tmp_path / "isolated-home"
    home.mkdir()
    (home / "sentinel").write_text("unchanged", encoding="utf-8")
    return Runner(tmp_path / "cli-data", home)
