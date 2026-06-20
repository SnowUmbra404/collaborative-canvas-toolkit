from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LamportClock:
    counter: int = 0

    def tick(self) -> int:
        self.counter += 1
        return self.counter

    def update(self, received: int) -> int:
        self.counter = max(self.counter, received) + 1
        return self.counter
