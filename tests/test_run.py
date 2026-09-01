"""전 구간 스모크. 진입점이 끝까지 돌고 RUN SUMMARY 를 찍는지 본다 (규격 §3.2)."""

import csv

import pytest

import run
from mypkg.synth import generate

REQUIRED_LABELS = ["version", "args", "input", "shape", "contract", "metrics", "runtime", "status"]


def test_dry_run_succeeds_and_prints_summary(capsys):
    assert run.main(["--dry-run", "--rows", "200"]) == 0
    out = capsys.readouterr().out
    assert "RUN SUMMARY" in out
    for label in REQUIRED_LABELS:
        assert f"{label:<10}:" in out


def test_adversarial_dry_run_reports_mismatch(capsys):
    assert run.main(["--dry-run", "--rows", "500", "--adversarial"]) == 1
    assert "MISMATCH" in capsys.readouterr().out


def test_data_is_required_without_dry_run():
    with pytest.raises(SystemExit) as exc:
        run.main([])
    assert exc.value.code == 2


def test_reads_csv_and_honors_limit(tmp_path, capsys):
    path = tmp_path / "input.csv"
    rows = generate(50, seed=0)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    assert run.main(["--data", str(path), "--limit", "10"]) == 0
    assert "10 rows" in capsys.readouterr().out


def test_summary_is_printed_even_on_mismatch(tmp_path, capsys):
    path = tmp_path / "bad.csv"
    path.write_text("customer_id,amount,grade\n,not-a-number,Z\n", encoding="utf-8")
    assert run.main(["--data", str(path)]) == 1
    out = capsys.readouterr().out
    assert "RUN SUMMARY" in out and "status    : CONTRACT MISMATCH" in out
