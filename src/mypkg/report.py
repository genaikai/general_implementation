"""RUN SUMMARY 블록 (규격 §3.2).

파일 반출이 불가능하므로 화면이 유일한 출력이고, 이 함수가 곧 리포트다.
한 줄에 한 항목, 80자 이내 — 사람이 손으로 옮겨 적는 것이 전제다.
실데이터의 개별 값·식별자는 절대 찍지 않는다.
"""

import resource
import sys

WIDTH = 45


def peak_gb() -> float:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / 1024**3 if sys.platform == "darwin" else rss / 1024**2


def render(
    *,
    version: str,
    args: str,
    source: str,
    n_rows: int,
    n_cols: int,
    violations: list[str],
    metrics: dict,
    runtime_s: float,
    status: str,
) -> str:
    n_ok = max(0, n_cols - len(violations))
    lines = [
        "=" * WIDTH,
        "RUN SUMMARY".center(WIDTH),
        "=" * WIDTH,
        f"version   : {version}",
        f"args      : {args}",
        f"input     : {source}",
        f"shape     : {n_rows:,} rows x {n_cols} cols",
        f"contract  : {n_ok} ok / {len(violations)} MISMATCH",
    ]
    lines += [f"  - {v}" for v in violations]
    lines.append("metrics   :")
    lines += [f"  {k:<16} {v}" for k, v in metrics.items()]
    lines.append(f"runtime   : {runtime_s:.1f}s, peak {peak_gb():.2f}GB")
    lines.append(f"status    : {status}")
    lines.append("=" * WIDTH)
    return "\n".join(lines)
