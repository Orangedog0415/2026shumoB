from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from .geometry import intersect_halfplanes, online_envelope, wedge_halfplanes
from .question2 import design_second_station
from .reporting import plot_region, plot_second_station, write_json, write_run_outputs
from .simulator import make_local_client, random_sources
from .strategy import run_strategy

ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_run_output(args: argparse.Namespace) -> Path:
    if args.output_dir is not None:
        return args.output_dir
    if args.mode == "official":
        raise SystemExit("official mode requires a unique --output-dir under outputs\\official")
    return ROOT / "outputs" / "offline" / args.command


def _q1(args: argparse.Namespace) -> int:
    data = _load_json(args.input)
    observations = [((float(o["x"]), float(o["y"])), float(o["svd_deg"])) for o in data["observations"]]
    planes = [hp for station, bearing in observations for hp in wedge_halfplanes(station, bearing)]
    pure = intersect_halfplanes(planes)
    online = online_envelope(observations)
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "result.json", {"pure_bearing_region": pure.to_dict(),
                                         "online_conservative_envelope": {"vertices": online, "disk_sides": 64},
                                         "parameters": {"bearing_error_deg": 1.005}})
    plot_region(output / "localization_region.png", pure.vertices, online, observations)
    print(output / "result.json")
    return 0


def _q2(args: argparse.Namespace) -> int:
    data = _load_json(args.input)
    p = data["first_station"]
    result = design_second_station((float(p["x"]), float(p["y"])), data.get("measure_result", "direction"), data.get("svd_deg"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.output_dir / "result.json", result.to_dict())
    plot_second_station(args.output_dir / "score_heatmap_and_candidates.png", result.score_rows,
                        result.candidate_circles, result.nominal_point)
    print(args.output_dir / "result.json")
    return 0 if result.status != "GEOMETRY_INPUT_ERROR" else 2


def _run_problem(args: argparse.Namespace) -> int:
    problem = int(args.command[1])
    mixed = problem == 4
    args.output_dir = _resolve_run_output(args)
    config = {"problem": problem, "mode": args.mode, "seed": args.seed, "source_count": args.count,
              "strategy": args.strategy.upper(),
              "strategy_version": "scheme4" if args.strategy == "b" else "scheme1",
              "force_fallback": args.force_fallback,
              "base_url": args.base_url}
    inspector = None
    if args.mode == "offline":
        client, inspector = make_local_client(random_sources(args.seed, args.count, mixed), args.seed % 17)
    else:
        if not args.robot_id:
            raise SystemExit("official mode requires --robot-id")
        from .transport import OfficialHttpClient
        client = OfficialHttpClient(args.base_url, args.robot_id, args.output_dir / "transport")
    result = run_strategy(client, mixed, args.force_fallback, args.strategy)
    truth = inspector.summary() if inspector is not None else None
    write_run_outputs(args.output_dir, result, client.action_log, problem, config, truth,
                      getattr(client, "transport_log", None))
    print(json.dumps({"termination": result.termination.value, "cleared": result.cleared_count,
                      "virtual_time_s": result.virtual_time_s}, ensure_ascii=False))
    return 0 if result.termination.value == "COMPLETED" else 2


def _selftest(args: argparse.Namespace) -> int:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    source_script = ROOT.parent / "baseline" / "方案一_最终方案验证.py"
    baseline_dir = args.output_dir / "baseline_reproduction"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    copied = baseline_dir / source_script.name
    shutil.copy2(source_script, copied)
    baseline = subprocess.run([sys.executable, str(copied)], text=True, capture_output=True)
    (baseline_dir / "stdout.txt").write_text(baseline.stdout + baseline.stderr, encoding="utf-8")
    pytest_temp = args.output_dir / "pytest-temp"
    tests = subprocess.run([sys.executable, "-m", "pytest", "-p", "no:cacheprovider",
                            "--basetemp", str(pytest_temp)], cwd=ROOT, text=True, capture_output=True)
    (args.output_dir / "pytest.txt").write_text(tests.stdout + tests.stderr, encoding="utf-8")
    write_json(args.output_dir / "environment.json", {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "dependencies": {name: importlib.metadata.version(name) for name in ("matplotlib", "requests", "pytest")},
    })
    print(tests.stdout)
    return 0 if baseline.returncode == 0 and tests.returncode == 0 else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="2026 国赛 B 题定位清除求解器")
    subs = parser.add_subparsers(dest="command", required=True)
    for name in ("q1", "q2"):
        cmd = subs.add_parser(name)
        cmd.add_argument("--input", type=Path, required=True)
        cmd.add_argument("--output-dir", type=Path, default=ROOT / "outputs" / "offline" / name)
        cmd.set_defaults(func=_q1 if name == "q1" else _q2)
    for name in ("q3", "q4"):
        cmd = subs.add_parser(name)
        cmd.add_argument("--mode", choices=("offline", "official"), default="offline")
        cmd.add_argument("--robot-id")
        cmd.add_argument("--base-url", default="http://127.0.0.1:2026")
        cmd.add_argument("--seed", type=int, default=20260911)
        cmd.add_argument("--count", type=int, choices=(10, 13, 16), default=13)
        cmd.add_argument("--strategy", choices=("a", "b"), default="b",
                         help="a=原方案一，b=方案四/策略B（默认）")
        cmd.add_argument("--force-fallback", action="store_true")
        cmd.add_argument("--output-dir", type=Path)
        cmd.set_defaults(func=_run_problem)
    cmd = subs.add_parser("selftest")
    cmd.add_argument("--output-dir", type=Path, default=ROOT / "outputs" / "offline" / "selftest")
    cmd.set_defaults(func=_selftest)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))
