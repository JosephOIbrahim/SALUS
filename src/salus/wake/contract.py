"""Cognitive contract: type + range + authority + temporal validity.

Typed failure is what makes supervision buildable; prose failure isn't
detectable (blueprint section 6).
"""

from __future__ import annotations

from dataclasses import dataclass


class ContractError(Exception):
    """Base class for typed contract failures."""


class OutOfRangeError(ContractError):
    pass


class ExpiredError(ContractError):
    pass


@dataclass(frozen=True, slots=True)
class WakeContract:
    kind: str
    lo: float
    hi: float
    authority: str
    valid_from_tick: int
    valid_until_tick: int

    def as_dict(self) -> dict[str, str | float | int]:
        return {
            "kind": self.kind,
            "lo": self.lo,
            "hi": self.hi,
            "authority": self.authority,
            "valid_from_tick": self.valid_from_tick,
            "valid_until_tick": self.valid_until_tick,
        }


def validate(contract: WakeContract, value: float, now: int) -> bool:
    if now < contract.valid_from_tick or now > contract.valid_until_tick:
        raise ExpiredError(f"contract expired at t={now}: {contract}")
    if not (contract.lo <= value <= contract.hi):
        raise OutOfRangeError(f"value {value} outside [{contract.lo}, {contract.hi}]")
    return True
