"""Run deterministic offline matrix and paired fast/fallback comparison."""
from __future__ import annotations

import json
from pathlib import Path

from bsolver.simulator import make_local_client, random_sources
from bsolver.strategy import run_strategy


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out = root / "outputs" / "offline" / "acceptance"
    out.mkdir(parents=True, exist_ok=True)
    matrix = []
    for mixed in (False, True):
        for count in (10, 13, 16):
            for rep in range(3):
                seed = 20260911 + 1000 * int(mixed) + 100 * count + rep
                specs = random_sources(seed, count, mixed)
                client, inspector = make_local_client(specs, rep)
                result = run_strategy(client, mixed)
                truth = inspector.summary()
                matrix.append({"mixed": mixed, "count": count, "seed": seed,
                               "termination": result.termination.value, "cleared": result.cleared_count,
                               "all_cleared": truth["all_cleared"], "virtual_time_s": result.virtual_time_s,
                               "actions": result.actions})
    paired = []
    for mixed in (False, True):
        for rep in range(6):
            seed = 9811 + 100 * int(mixed) + rep
            specs = random_sources(seed, 13, mixed)
            fast_client, fast_inspector = make_local_client(specs, rep)
            base_client, base_inspector = make_local_client(specs, rep)
            fast = run_strategy(fast_client, mixed, False)
            baseline = run_strategy(base_client, mixed, True)
            paired.append({"mixed": mixed, "case": rep, "seed": seed,
                           "fast_s": fast.virtual_time_s, "fallback_s": baseline.virtual_time_s,
                           "fast_all_cleared": fast_inspector.summary()["all_cleared"],
                           "fallback_all_cleared": base_inspector.summary()["all_cleared"]})
    fast_mean = sum(r["fast_s"] for r in paired) / len(paired)
    fallback_mean = sum(r["fallback_s"] for r in paired) / len(paired)
    evidence = {
        "label": "本地仿真，不是官方成绩",
        "scenario_matrix": matrix,
        "scenario_summary": {"runs": len(matrix), "all_cleared": all(r["all_cleared"] for r in matrix),
                             "max_virtual_time_s": max(r["virtual_time_s"] for r in matrix),
                             "max_actions": max(r["actions"] for r in matrix)},
        "paired_comparison": {"cases": paired, "fast_mean_s": fast_mean, "fallback_mean_s": fallback_mean,
                              "relative_mean_reduction": 1 - fast_mean / fallback_mean,
                              "fast_wins": sum(r["fast_s"] < r["fallback_s"] for r in paired),
                              "all_cleared": all(r["fast_all_cleared"] and r["fallback_all_cleared"] for r in paired)},
    }
    (out / "offline_acceptance.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"scenario_summary": evidence["scenario_summary"],
                      "paired_comparison": {k: v for k, v in evidence["paired_comparison"].items() if k != "cases"}},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
