"""Optional .usda emitter — vitals as time-sampled attributes, wakes as
child prims. Stage time is a query (blueprint thesis). Guarded import:
the core never depends on usd-core; install with `pip install .[usd]`."""

from __future__ import annotations

from pathlib import Path

from ..vitals.channels import CHANNELS
from ..wake.predicate import RunResult


def write_stage(path: Path, result: RunResult) -> None:
    try:
        from pxr import Usd, Sdf  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "usd-core not installed; run `pip install .[usd]` to enable .usda emission"
        ) from exc

    stage = Usd.Stage.CreateNew(str(path))
    salus = stage.DefinePrim("/Salus", "Scope")
    for channel in CHANNELS:
        attr = salus.CreateAttribute(f"vitals:{channel}", Sdf.ValueTypeNames.Float)
        for v in result.vitals:
            attr.Set(float(getattr(v, channel)), v.tick)
    stage.DefinePrim("/Salus/Wakes", "Scope")
    for i, e in enumerate(result.events):
        prim = stage.DefinePrim(f"/Salus/Wakes/wake_{i:03d}", "Scope")
        for key, value in e.to_record().items():
            if key == "contract":
                continue
            prim.SetCustomDataByKey(key, value)
        prim.SetCustomDataByKey("contract", dict(e.contract.as_dict()))
    stage.SetStartTimeCode(result.vitals[0].tick if result.vitals else 0)
    stage.SetEndTimeCode(result.vitals[-1].tick if result.vitals else 0)
    stage.GetRootLayer().Save()
