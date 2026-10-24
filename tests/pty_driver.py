import fcntl
import os
import select
import signal
import struct
import subprocess
import sys
import termios
import time
from pathlib import Path


class Terminal:
    def __init__(
        self, args: list[str], *, width: int = 80, height: int = 40, environment: dict[str, str] | None = None
    ) -> None:
        self.line_mode = "--line-mode" in args
        self.last_write_output = 0
        self.master, slave = os.openpty()
        self.slave = slave
        self.initial_termios = termios.tcgetattr(slave)
        self.restored = False
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", height, width, 0, 0))

        def controlling_terminal() -> None:
            os.setsid()
            fcntl.ioctl(slave, termios.TIOCSCTTY, 0)

        env = os.environ.copy()
        env.update({"TERM": "xterm-256color", "NO_COLOR": "1"})
        env.update(environment or {})
        self.process = subprocess.Popen(
            [sys.executable, "-m", "kolo", *args],
            stdin=slave,
            stdout=slave,
            stderr=slave,
            env=env,
            preexec_fn=controlling_terminal,
        )
        self.output = ""
        self.cursor = 0

    def send(self, value: str) -> None:
        if self.line_mode:
            deadline = time.monotonic() + 10
            while len(self.output) <= self.last_write_output or not self.output.endswith("> "):
                if time.monotonic() >= deadline:
                    raise AssertionError(f"PTY input prompt was not ready: {self.output!r}")
                self.drain(min(0.02, deadline - time.monotonic()))
            self.last_write_output = len(self.output)
        os.write(self.master, value.encode())

    def expect(self, text: str, timeout: float = 10) -> str:
        deadline = time.monotonic() + timeout
        while text not in self.output[self.cursor :]:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AssertionError(f"PTY expected {text!r}; got {self.output!r}")
            readable, _, _ = select.select([self.master], [], [], min(remaining, 0.2))
            if readable:
                try:
                    chunk = os.read(self.master, 65536)
                except OSError as error:
                    raise AssertionError(f"PTY ended waiting for {text!r}: {self.output!r}") from error
                self.output += chunk.decode("utf-8", errors="replace")
        self.cursor = self.output.index(text, self.cursor) + len(text)
        return self.output

    def resize(self, width: int, height: int) -> None:
        fcntl.ioctl(self.slave, termios.TIOCSWINSZ, struct.pack("HHHH", height, width, 0, 0))
        os.killpg(self.process.pid, signal.SIGWINCH)

    def drain(self, timeout: float = 0.1) -> str:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            readable, _, _ = select.select([self.master], [], [], max(0, deadline - time.monotonic()))
            if not readable:
                break
            try:
                self.output += os.read(self.master, 65536).decode("utf-8", errors="replace")
            except OSError:
                break
        return self.output

    def finish(self) -> int:
        try:
            result = self.process.wait(timeout=10)
            self.drain(0.05)
            self.restored = termios.tcgetattr(self.slave) == self.initial_termios
            return result
        finally:
            os.close(self.master)
            os.close(self.slave)

    def close(self) -> None:
        if self.process.poll() is None:
            os.killpg(self.process.pid, signal.SIGKILL)
            self.process.wait(timeout=5)
        try:
            os.close(self.master)
        except OSError:
            pass
        try:
            os.close(self.slave)
        except OSError:
            pass


def terminal_args(directory: Path) -> list[str]:
    return ["--data-dir", str(directory), "--plain", "--line-mode"]
