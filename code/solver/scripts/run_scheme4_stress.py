"""Run Scheme 4's deterministic 240-case guarantee stress matrix offline."""
from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
from pathlib import Path

from bsolver.models import Termination
from bsolver.simulator import SourceSpec, make_local_client
from bsolver.strategy import run_strategy


ERROR_MODELS = ("sin", "uniform", "plus_one", "minus_one", "pm_one")
COUNTS = (10, 13, 16)


def _stable_seed(*parts: object) -> int:
    raw = "|".join(map(str, parts)).encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")


def _scenario(problem: int, error_model: str, radius_mode: str,
              layout: str, count: int, rep: int) -> list[SourceSpec]:
    rng = random.Random(_stable_seed(problem, error_model, radius_mode, layout, count, rep))
    mixed = problem == 4
    specs: list[SourceSpec] = []
    for index, channel in enumerate(rng.sample(range(1, 21), count)):
        if layout == "uniform_disk":
            angle = rng.random() * 2 * math.pi
            distance_m = 1800 * math.sqrt(rng.random())
            kind = "D" if mixed and rng.random() < 0.65 else "O"
            direction = rng.random() * 2 * math.pi
        else:
            angle = 2 * math.pi * index / count + rng.uniform(-0.05, 0.05)
            distance_m = rng.uniform(1700, 1800)
            kind = "D" if mixed else "O"
            direction = angle
        radius_m = 1000.0 if radius_mode == "minimum" else rng.uniform(1000, 1500)
        specs.append(SourceSpec(
            channel=channel,
            position=(distance_m * math.cos(angle), distance_m * math.sin(angle)),
            radius_m=radius_m,
            kind=kind,
            direction_deg=math.degrees(direction),
        ))
    return specs


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "outputs" / "offline" / "scheme4-stress"
    out_dir.mkdir(parents=True, exist_ok=True)
    cases: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []

    for problem in (3, 4):
        for error_model in ERROR_MODELS:
            for radius_mode in ("random", "minimum"):
                for layout in ("uniform_disk", "boundary_outward"):
                    for count in COUNTS:
                        for rep in range(2):
                            specs = _scenario(problem, error_model, radius_mode, layout, count, rep)
                            client, inspector = make_local_client(specs, rep, error_model)
                            result = run_strategy(client, mixed=problem == 4, strategy="b")
                            truth = inspector.summary()
                            case = {
                                "problem": problem,
                                "error_model": error_model,
                                "radius_mode": radius_mode,
                                "layout": layout,
                                "count": count,
                                "rep": rep,
                                "termination": result.termination.value,
                                "cleared": result.cleared_count,
                                "all_cleared": truth["all_cleared"],
                                "virtual_time_s": result.virtual_time_s,
                                "per_source_time_s": result.virtual_time_s / count,
                                "actions": result.actions,
                            }
                            cases.append(case)
                            if result.termination is not Termination.COMPLETED or not truth["all_cleared"]:
                                failures.append(case)

    per_source_times = [float(case["per_source_time_s"]) for case in cases]
    evidence = {
        "label": "本地仿真压力测试，不是官方成绩，未连接官方模拟器",
        "strategy_version": "scheme4",
        "summary": {
            "runs": len(cases),
            "failures": len(failures),
            "all_cleared": not failures,
            "mean_per_source_time_s": statistics.fmean(per_source_times),
            "max_per_source_time_s": max(per_source_times),
            "max_virtual_time_s": max(float(case["virtual_time_s"]) for case in cases),
            "max_actions": max(int(case["actions"]) for case in cases),
        },
        "failures": failures,
        "cases": cases,
    }
    output_path = out_dir / "offline_stress.json"
    output_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence["summary"], ensure_ascii=False))
    if failures:
        raise SystemExit(f"Scheme 4 stress test failed in {len(failures)} case(s); see {output_path}")


if __name__ == "__main__":
    main()
