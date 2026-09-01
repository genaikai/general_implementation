#!/usr/bin/env python3
"""진입점 (규격 §3.1).

    python {BB}/src/run.py --data <csv> [--limit N]
    python {BB}/src/run.py --dry-run [--adversarial]

파일을 직접 실행하면 sys.path[0] 이 {BB}/src 가 되므로 mypkg 가 그대로 import 된다.
PYTHONPATH 도, 공용 venv 에 대한 설치도 필요 없다.
바뀔 만한 값은 전부 CLI 인자로 받는다 (규격 §1.3) — 사내에서는 코드를 고칠 수 없다.
"""

import argparse
import csv
import sys
import time
from pathlib import Path

from mypkg.contracts import INPUT_SCHEMA, is_null, parse, validate
from mypkg.report import render
from mypkg.synth import generate


def read_version() -> str:
    path = Path(__file__).resolve().parent.parent / "VERSION"
    return path.read_text().strip() if path.exists() else "unversioned"


def load_csv(path: str, limit: int) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = []
        for i, row in enumerate(csv.DictReader(fh)):
            if limit and i >= limit:
                break
            rows.append(row)
    return rows


def compute_metrics(rows: list[dict]) -> dict:
    """도메인 지표로 갈아끼울 자리. 지표 이름은 사이클 사이에 바꾸지 않는다."""
    numeric = [f.name for f in INPUT_SCHEMA if f.dtype in ("int", "float")]
    metrics = {"rows": f"{len(rows):,}"}
    for name in numeric:
        values = []
        for row in rows:
            raw = row.get(name)
            if is_null(raw):
                continue
            try:
                values.append(parse(raw, "float"))
            except (TypeError, ValueError):
                continue
        metrics[f"{name}_mean"] = f"{sum(values) / len(values):.4f}" if values else "n/a"
        metrics[f"{name}_nullrate"] = f"{1 - len(values) / len(rows):.4f}" if rows else "n/a"
    return metrics


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="run.py", description=__doc__.splitlines()[0])
    ap.add_argument("--data", help="입력 CSV 경로. --dry-run 이 아니면 필수")
    ap.add_argument("--dry-run", action="store_true", help="합성 데이터로 전 구간 스모크")
    ap.add_argument("--limit", type=int, default=0, help="앞 N행만 처리 (0=전체)")
    ap.add_argument("--rows", type=int, default=1000, help="--dry-run 이 생성할 행 수")
    ap.add_argument("--seed", type=int, default=0, help="--dry-run 생성 시드")
    ap.add_argument("--adversarial", action="store_true", help="--dry-run 에 사고 유형 주입")
    args = ap.parse_args(argv)

    # 조기 실패 — 어떤 계산도 하기 전에 죽는다
    if not args.dry_run and not args.data:
        ap.error("--data is required unless --dry-run")

    started = time.perf_counter()
    if args.dry_run:
        mode = "adversarial" if args.adversarial else "normal"
        rows = generate(args.rows, seed=args.seed, mode=mode)
        source = f"synthetic(n={args.rows}, seed={args.seed}, mode={mode})"
    else:
        rows = load_csv(args.data, args.limit)
        source = args.data

    violations = validate(rows)

    # ── 도메인 로직을 붙이는 자리 ─────────────────────────────────────────
    metrics = compute_metrics(rows)
    # ─────────────────────────────────────────────────────────────────────

    print(render(
        version=read_version(),
        args=" ".join(argv if argv is not None else sys.argv[1:]) or "(none)",
        source=source,
        n_rows=len(rows),
        n_cols=len(rows[0]) if rows else 0,
        violations=violations,
        metrics=metrics,
        runtime_s=time.perf_counter() - started,
        status="OK" if not violations else "CONTRACT MISMATCH",
    ))
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
