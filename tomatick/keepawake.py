"""Keep-awake toggle (caffeine-style), backed by the built-in ``caffeinate``.

``caffeinate -w <pid>`` ties the helper's lifetime to ours, so it can never be
orphaned if Tomatick exits without an explicit ``off()``.
"""

from __future__ import annotations

import os
import subprocess


class KeepAwake:
    def __init__(self):
        self._proc = None

    @property
    def active(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def on(self) -> None:
        if self.active:
            return
        # -d display, -i idle system, -s system sleep (on AC), -w die with us.
        self._proc = subprocess.Popen(
            ["caffeinate", "-d", "-i", "-s", "-w", str(os.getpid())])

    def off(self) -> None:
        if self._proc is not None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=2)  # reap so we don't leave a zombie
            except Exception:  # pragma: no cover - already gone / slow to die
                pass
            self._proc = None

    def toggle(self) -> bool:
        self.off() if self.active else self.on()
        return self.active
