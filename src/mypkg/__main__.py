"""실행 흐름.

진입점은 `src/run.py` 지만 본체는 여기다 — 저쪽은 venv 를 갈아타고 이리로 넘긴다.

바뀔 만한 값은 전부 CLI 인자로 받는다. 실행할 때 코드를 고칠 수 없다고 보므로,
"코드 한 줄만 고치면 되는데" 하는 순간이 오면 그건 이 규칙이 이미 깨졌다는 신호다.

종료 코드 — 실행 스크립트가 여기에 분기한다:
    0  정상
    1  돌았지만 온전치 않다 (스키마 위반). 재시도해도 같다
    2  시작도 못 했다 (인자 누락·입력 없음). 고치고 다시 돌린다
"""

import argparse
import sys
import time
from pathlib import Path

from .schema import validate
from .load import load_csv
from .pipeline import process_data
from .report import render
from .synth import generate


def read_version() -> str:
    """배포할 때 저장소 루트의 VERSION 에 적힌 값을 읽는다. 없으면 unversioned."""
    path = Path(__file__).resolve().parent.parent.parent / "VERSION"
    return path.read_text().strip() if path.exists() else "unversioned"


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="run.py", description=__doc__.splitlines()[0])
    ap.add_argument("--data", help="입력 CSV 경로. --dry-run 이 아니면 필수")
    ap.add_argument("--dry-run", action="store_true", help="합성 데이터로 전 구간 스모크")
    ap.add_argument("--limit", type=int, default=0, help="앞 N행만 처리 (0=전체)")
    ap.add_argument("--rows", type=int, default=1000, help="--dry-run 이 생성할 행 수")
    ap.add_argument("--seed", type=int, default=0, help="--dry-run 생성 시드")
    ap.add_argument("--adversarial", action="store_true", help="--dry-run 에 사고 유형 주입")
    ap.add_argument("--config", help="설정 파일. paths.venv 를 여기서 읽는다")
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)

    # 조기 실패 — 어떤 계산도 하기 전에 죽는다. 30분 돌린 뒤 인자 하나 때문에
    # 죽으면 사이클 하나를 통째로 버린다
    if not args.dry_run and not args.data:
        ap.error("--data is required unless --dry-run")

    started = time.perf_counter()
    if args.dry_run:
        mode = "adversarial" if args.adversarial else "normal"
        rows = generate(args.rows, seed=args.seed, mode=mode)
        source = f"synthetic(n={args.rows}, seed={args.seed}, mode={mode})"
    else:
        try:
            rows = load_csv(args.data, args.limit)
        except OSError as exc:
            print(f"입력을 열 수 없습니다: {exc}", file=sys.stderr)
            return 2
        source = args.data

    # 진행 상황은 stderr. RUN SUMMARY 가 stdout 이라야 `> log.txt` 가 비지 않는다
    print(f"실행 조건: {source} / {len(rows):,} rows", file=sys.stderr)

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
        runtime_s=time.perf_counter() - started,
        status="OK" if report.ok else "CONTRACT MISMATCH",
    ))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
