"""Setpoints: calibrated baselines, crossing bands, hysteresis.

The wake must not flap (blueprint section 4, step 3): enter and exit
thresholds differ, and a band fires exactly once per crossing episode.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from collections.abc import Sequence

from .vitals.channels import Vitals
from .vitals.windows import mean, variance


@dataclass(frozen=True, slots=True)
class Band:
    """direction +1 fires on up-cross of `enter`; -1 on down-cross."""

    channel: str
    direction: int
    enter: float
    exit: float


def calibrate_entropy_band(
    samples: Sequence[Vitals],
    k_sigma: float = 4.0,
    min_width: float = 0.5,
    exit_frac: float = 0.5,
) -> Band:
    """Baseline the focused phase; band = mean + max(k*sigma, floor).
    The absolute floor guards the degenerate near-zero-sigma baseline."""
    vals = [v.attention_entropy for v in samples]
    m = mean(vals)
    sd = math.sqrt(variance(vals))
    width = max(k_sigma * sd, min_width)
    return Band("attention_entropy", +1, m + width, m + width * exit_frac)


def absolute_band(channel: str, direction: int, enter: float, exit_: float) -> Band:
    return Band(channel, direction, enter, exit_)


class Hysteresis:
    """Per-band two-state machine. Deterministic: state depends only on
    the value sequence. Fires exactly once per crossing episode; re-arms
    only after the value exits past the exit threshold."""

    def __init__(self, bands: Sequence[Band]) -> None:
        self._bands: dict[str, Band] = {}
        for b in bands:
            if b.direction not in (1, -1):
                raise ValueError(f"band {b.channel!r}: direction must be +1 or -1")
            if b.channel in self._bands:
                raise ValueError(f"duplicate band for channel {b.channel!r}")
            # exit must sit on the re-arm side of enter, or the band
            # flaps — defeating the one thing hysteresis exists for.
            if b.direction > 0 and b.exit > b.enter:
                raise ValueError(
                    f"band {b.channel!r}: up-cross requires exit <= enter"
                )
            if b.direction < 0 and b.exit < b.enter:
                raise ValueError(
                    f"band {b.channel!r}: down-cross requires exit >= enter"
                )
            self._bands[b.channel] = b
        self._armed = {c: True for c in self._bands}

    def has(self, channel: str) -> bool:
        return channel in self._bands

    def band(self, channel: str) -> Band:
        return self._bands[channel]

    def update(self, channel: str, value: float) -> bool:
        b = self._bands[channel]
        armed = self._armed[channel]
        if b.direction > 0:
            crossed_in = value > b.enter
            crossed_out = value < b.exit
        else:
            crossed_in = value < b.enter
            crossed_out = value > b.exit
        if armed and crossed_in:
            self._armed[channel] = False
            return True
        if not armed and crossed_out:
            self._armed[channel] = True
        return False
