from __future__ import annotations

import csv
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .models import Point, RunResult


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _pyplot():
    os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "bsolver-mpl-cache"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def plot_region(path: Path, pure: list[Point], online: list[Point], observations: list[tuple[Point, float]]) -> None:
    plt = _pyplot()
    fig, ax = plt.subplots(figsize=(7, 7))
    for poly, label, color in ((pure, "pure half-plane intersection", "tab:red"),
                               (online, "online conservative envelope", "tab:blue")):
        if poly:
            xs = [p[0] for p in poly] + [poly[0][0]]
            ys = [p[1] for p in poly] + [poly[0][1]]
            ax.plot(xs, ys, color=color, label=label)
    for station, bearing in observations:
        ax.scatter(*station, marker="x", color="black")
        ax.arrow(station[0], station[1], 200 * __import__("math").cos(__import__("math").radians(bearing)),
                 200 * __import__("math").sin(__import__("math").radians(bearing)), width=1.5)
    ax.set_aspect("equal"); ax.grid(True, alpha=.3); ax.legend(); ax.set_title("Problem 1 localization regions")
    fig.tight_layout(); fig.savefig(path, dpi=180); plt.close(fig)


def plot_second_station(path: Path, rows: list[dict[str, float]], circles: list[dict[str, Any]], nominal: Point | None) -> None:
    plt = _pyplot()
    fig, ax = plt.subplots(figsize=(8, 6))
    if rows:
        sc = ax.scatter([r["x"] for r in rows], [r["y"] for r in rows], c=[r["score"] for r in rows], s=18)
        fig.colorbar(sc, ax=ax, label="finite-sample score")
    for circle in circles:
        ax.add_patch(plt.Circle(circle["center"], circle["radius_m"],
                                fill=False, color="tab:green", alpha=.12))
    if nominal is not None:
        ax.scatter(*nominal, marker="*", s=160, color="red", label="nominal station")
    ax.set_aspect("equal"); ax.grid(True, alpha=.3); ax.legend(loc="best")
    ax.set_title("Problem 2 finite-sample score and safe candidate circles")
    fig.tight_layout(); fig.savefig(path, dpi=180); plt.close(fig)


def plot_trajectory(path: Path, actions: list[dict[str, Any]], title: str) -> None:
    plt = _pyplot()
    points = []
    for event in actions:
        p = event.get("position") or event.get("request", {}).get("position")
        if isinstance(p, dict):
            points.append((p["x"], p["y"]))
        elif isinstance(p, (list, tuple)) and len(p) == 2:
            points.append(tuple(p))
    fig, ax = plt.subplots(figsize=(7, 7))
    if points:
        ax.plot([p[0] for p in points], [p[1] for p in points], linewidth=.8)
        ax.scatter([points[0][0]], [points[0][1]], color="green", label="first action")
        ax.scatter([points[-1][0]], [points[-1][1]], color="red", label="last action")
    ax.set_aspect("equal"); ax.grid(True, alpha=.3); ax.legend(loc="best"); ax.set_title(title)
    fig.tight_layout(); fig.savefig(path, dpi=180); plt.close(fig)


def plot_time_breakdown(path: Path, breakdown: dict[str, float]) -> None:
    plt = _pyplot()
    rows = [(k, v) for k, v in breakdown.items() if v > 0 and not k.endswith("latency_s")]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar([k for k, _ in rows], [v for _, v in rows])
    ax.set_ylabel("seconds"); ax.set_title("Local simulation virtual-time breakdown")
    ax.tick_params(axis="x", rotation=25); fig.tight_layout(); fig.savefig(path, dpi=180); plt.close(fig)


def write_formal_template(path: Path, problem: int) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow([f"问题{problem}正式测试结果（待官方测试填写）"])
        writer.writerow(["测试案例编码", "清除干扰源个数", "平均定位清除时间/s", "程序运行时间/s", "官方原名日志"])
        for _ in range(3):
            writer.writerow(["待测试", "—", "—", "—", "—"])


def write_run_outputs(output: Path, result: RunResult, actions: list[dict[str, Any]], problem: int,
                      config: dict[str, Any], truth_summary: dict[str, Any] | None = None,
                      transport_log: list[dict[str, Any]] | None = None) -> None:
    output.mkdir(parents=True, exist_ok=True)
    summary = result.to_dict()
    summary["artifact_label"] = "本地仿真" if truth_summary is not None else "官方客户端本地记录"
    if truth_summary is not None:
        summary["simulation_truth_summary"] = truth_summary
        summary["clear_ratio"] = result.cleared_count / truth_summary["source_count"] if truth_summary["source_count"] else None
        summary["average_localization_clear_time_s"] = result.virtual_time_s / result.cleared_count if result.cleared_count else None
    write_json(output / "summary.json", summary)
    write_json(output / "config_snapshot.json", config)
    write_jsonl(output / "actions.jsonl", actions)
    if transport_log is not None:
        write_jsonl(output / "transport_attempts.jsonl", transport_log)
    write_json(output / "channel_states.json", [r.public_dict() for r in result.channels])
    plot_trajectory(output / "trajectory.png", actions, f"Problem {problem} - local simulation trajectory")
    plot_time_breakdown(output / "time_breakdown.png", result.time_breakdown)
    write_formal_template(output / "formal_results_template.csv", problem)
