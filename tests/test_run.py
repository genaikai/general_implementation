"""전 구간 스모크. 진입점이 끝까지 돌고 RUN SUMMARY 를 찍는지 본다."""

import csv

import pytest

from core import __main__ as run
from core.synth import generate

REQUIRED_LABELS = ["version", "args", "input", "shape", "schema", "metrics", "runtime", "status"]


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


# ── 리포트가 지켜야 하는 것들 ─────────────────────────────────────────────────

def test_exit_codes_match_the_scripting_contract(tmp_path, capsys):
    """0=정상 / 1=돌았지만 온전치 않다 / 2=시작도 못 했다.

    1 과 2 를 가르는 기준은 "계산을 시작했나"다. 2 는 고치고 다시 돌리면 되고,
    1 은 이미 돈 것이라 재시도해도 같다 — 실행 스크립트의 분기가 여기 걸린다.
    """
    assert run.main(["--dry-run", "--rows", "200"]) == 0
    assert run.main(["--data", str(tmp_path / "없다.csv")]) == 2

    bad = tmp_path / "bad.csv"
    bad.write_text("customer_id,amount,grade\n,not-a-number,Z\n", encoding="utf-8")
    assert run.main(["--data", str(bad)]) == 1


def test_summary_goes_to_stdout_and_progress_to_stderr(capsys):
    """RUN SUMMARY 가 stderr 로 새면 `> log.txt` 로 남긴 파일이 비어 있다."""
    run.main(["--dry-run", "--rows", "200"])
    captured = capsys.readouterr()
    assert "RUN SUMMARY" in captured.out
    assert "RUN SUMMARY" not in captured.err
    assert "실행 조건" in captured.err
    assert "실행 조건" not in captured.out


def test_summary_lines_fit_eighty_columns(capsys):
    """글자 수가 아니라 표시 폭이다. 한글은 두 칸이라 len() 으로 자르면 끊긴다."""
    from core.report import _w

    run.main(["--dry-run", "--rows", "500", "--adversarial"])
    for line in capsys.readouterr().out.splitlines():
        assert _w(line) <= 80, line


def test_version_is_never_blank():
    """빈칸이면 옮겨 적을 때 통째로 빠지고, 빠진 줄은 없었던 것이 된다."""
    from core.report import render

    out = render(version="  ", args="--x", source="s", n_rows=1, n_cols=1,
                 violations=[], notes=[], metrics={}, runtime_s=0.1, status="OK")
    assert "version   : unversioned" in out


def test_metric_names_align_regardless_of_script(capsys):
    """한글 지표명이 섞여도 값의 시작 칸이 같아야 옮겨 적을 때 안 헷갈린다."""
    from core.report import _w, render

    out = render(version="v1", args="--x", source="s", n_rows=1, n_cols=1,
                 violations=[], notes=[], metrics={"평균금액": "1.0", "rows": "1"},
                 runtime_s=0.1, status="OK")
    lines = out.splitlines()
    metrics = lines[lines.index("metrics   :") + 1:lines.index("metrics   :") + 3]
    starts = {_w(line[: line.rindex(" ") + 1]) for line in metrics}
    assert len(starts) == 1, out


def test_venv_switch_reads_paths_venv(tmp_path):
    """설정에 적은 값이 아무것도 바꾸지 않으면 그건 그 자체로 결함이다."""
    import run

    config = tmp_path / "env.yaml"
    config.write_text("paths:\n  venv: /opt/shared/venv   # 주석\n", encoding="utf-8")
    assert run._peek_venv(str(config)) == "/opt/shared/venv"

    config.write_text("paths:\n  venv:\n", encoding="utf-8")
    assert run._peek_venv(str(config)) == "", "비어 있으면 갈아타지 않는다"


def test_missing_venv_dies_before_computing(tmp_path):
    """시작도 못 한 것이므로 2 다. 어떤 계산도 하기 전에 죽는다."""
    import run

    config = tmp_path / "env.yaml"
    config.write_text(f"paths:\n  venv: {tmp_path / 'nope'}\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        run.switch_venv(["--config", str(config)])
    assert exc.value.code == 2


def test_entry_point_only_delegates():
    """진입점만 src/run.py 에 두고 나머지는 src/<pkg>/ 안에 넣는다."""
    import run

    for name in ("load_csv", "process_data", "main"):
        assert not hasattr(run, name), f"run.py 에 {name} 이 남아 있다 — 패키지로 옮겨라"
