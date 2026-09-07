"""Project entry point - modify as needed."""

import argparse
import sys
import time
from pathlib import Path

from ..framework.contracts import validate
from ..framework.load import load_csv
from .pipeline import process_data
from ..framework.report import render
from ..framework.synth import generate


def read_version() -> str:
    """VERSION 파일에서 버전을 읽는다."""
    path = Path(__file__).resolve().parent.parent.parent / "VERSION"
    return path.read_text().strip() if path.exists() else "unversioned"


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="run.py")
    ap.add_argument("--data", help="입력 CSV 경로")
    ap.add_argument("--dry-run", action="store_true", help="합성 데이터 스모크")
    ap.add_argument("--limit", type=int, default=0, help="앞 N행만 (0=전체)")
    ap.add_argument("--rows", type=int, default=1000, help="생성 행 수")
    ap.add_argument("--seed", type=int, default=0, help="생성 시드")
    ap.add_argument("--adversarial", action="store_true", help="사고 주입")
    ap.add_argument("--config", help="설정 파일")
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)

    if not args.dry_run and not args.data:
        ap.error("--data is required unless --dry-run")

    started = time.perf_counter()
    if args.dry_run:
        rows = generate(args.rows, seed=args.seed)
        source = f"synthetic(n={args.rows}, seed={args.seed})"
    else:
        try:
            rows = load_csv(args.data, args.limit)
        except OSError as exc:
            print(f"입력 오류: {exc}", file=sys.stderr)
            return 2
        source = args.data

    print(f"조건: {source} / {len(rows):,} rows", file=sys.stderr)

    report = validate(rows)
    metrics = process_data(rows)

    print(render(
        version=read_version(),
        args=" ".join(argv if argv is not None else sys.argv[1:]) or "(none)",
        source=source,
        n_rows=len(rows),
        n_cols=len(rows[0]) if rows else 0,
        violations=report.violations,
        notes=report.notes,
        metrics=metrics,
        tags={},
        runtime_s=time.perf_counter() - started,
        status="OK" if report.ok else "CONTRACT MISMATCH",
    ))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
