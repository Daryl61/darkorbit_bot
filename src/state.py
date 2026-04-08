from __future__ import annotations

from enum import Enum, auto
from dataclasses import dataclass, field
import time

from .utils import setup_logger

logger = setup_logger("state")


class BotState(Enum):
    IDLE = auto()
    COLLECTING = auto()
    MOVING = auto()
    FLEEING = auto()
    DEAD = auto()
    PAUSED = auto()
    STOPPED = auto()


@dataclass
class BotStats:
    boxes_collected: int = 0
    distance_moved: float = 0.0
    deaths: int = 0
    flee_count: int = 0
    start_time: float = field(default_factory=time.time)

    def reset(self):
        self.boxes_collected = 0
        self.distance_moved = 0.0
        self.deaths = 0
        self.flee_count = 0
        self.start_time = time.time()

    @property
    def runtime_seconds(self) -> float:
        return time.time() - self.start_time

    @property
    def runtime_str(self) -> str:
        secs = int(self.runtime_seconds)
        h, rem = divmod(secs, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"


class StateManager:
    """Tracks the bot's current state and accumulated statistics."""

    VALID_TRANSITIONS: dict[BotState, set[BotState]] = {
        BotState.STOPPED: {BotState.IDLE},
        BotState.IDLE: {BotState.COLLECTING, BotState.MOVING, BotState.FLEEING, BotState.PAUSED, BotState.STOPPED},
        BotState.COLLECTING: {BotState.IDLE, BotState.MOVING, BotState.FLEEING, BotState.DEAD, BotState.PAUSED, BotState.STOPPED},
        BotState.MOVING: {BotState.IDLE, BotState.COLLECTING, BotState.FLEEING, BotState.DEAD, BotState.PAUSED, BotState.STOPPED},
        BotState.FLEEING: {BotState.IDLE, BotState.DEAD, BotState.PAUSED, BotState.STOPPED},
        BotState.DEAD: {BotState.IDLE, BotState.STOPPED},
        BotState.PAUSED: {BotState.IDLE, BotState.COLLECTING, BotState.MOVING, BotState.STOPPED},
    }

    def __init__(self):
        self._state = BotState.STOPPED
        self._prev_state = BotState.STOPPED
        self._last_change = time.time()
        self.stats = BotStats()

    @property
    def state(self) -> BotState:
        return self._state

    @property
    def previous_state(self) -> BotState:
        return self._prev_state

    @property
    def time_in_state(self) -> float:
        return time.time() - self._last_change

    def transition(self, new_state: BotState) -> bool:
        if new_state == self._state:
            return True

        allowed = self.VALID_TRANSITIONS.get(self._state, set())
        if new_state not in allowed:
            logger.warning(
                "Invalid transition: %s -> %s (allowed: %s)",
                self._state.name,
                new_state.name,
                [s.name for s in allowed],
            )
            return False

        logger.info("State: %s -> %s", self._state.name, new_state.name)
        self._prev_state = self._state
        self._state = new_state
        self._last_change = time.time()
        return True

    def is_running(self) -> bool:
        return self._state not in (BotState.STOPPED, BotState.PAUSED, BotState.DEAD)

    def pause(self):
        if self._state not in (BotState.STOPPED, BotState.DEAD):
            self.transition(BotState.PAUSED)

    def resume(self):
        if self._state == BotState.PAUSED:
            self.transition(self._prev_state if self._prev_state != BotState.PAUSED else BotState.IDLE)

    def stop(self):
        self.transition(BotState.STOPPED)

    def start(self):
        if self._state == BotState.STOPPED:
            self.stats.reset()
            self.transition(BotState.IDLE)
