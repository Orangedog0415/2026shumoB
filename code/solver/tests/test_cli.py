from pathlib import Path

import pytest

from bsolver.cli import ROOT, _resolve_run_output, build_parser


def test_offline_run_uses_partitioned_default_output():
    args = build_parser().parse_args(["q3"])
    assert _resolve_run_output(args) == ROOT / "outputs" / "offline" / "q3"


def test_official_run_requires_unique_output_directory():
    args = build_parser().parse_args(["q4", "--mode", "official", "--robot-id", "test"])
    with pytest.raises(SystemExit, match="unique --output-dir"):
        _resolve_run_output(args)


def test_explicit_official_output_is_preserved():
    output = Path("outputs/official/q3-drill-02")
    args = build_parser().parse_args([
        "q3", "--mode", "official", "--robot-id", "test", "--output-dir", str(output),
    ])
    assert _resolve_run_output(args) == output
