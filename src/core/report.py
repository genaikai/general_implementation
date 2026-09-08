"""RUN SUMMARY 블록.

콘솔이 유일한 출력이고, 이 함수가 곧 리포트다.
한 줄에 한 항목, 80칸 이내 — 사람이 손으로 옮겨 적는 것이 전제다.
실데이터의 개별 값·식별자는 절대 찍지 않는다.
"""

import resource
import sys
import unicodedata

WIDTH = 45


def peak_gb() -> float:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / 1024**3 if sys.platform == "darwin" else rss / 1024**2


def _w(text: str) -> int:
    """표시 폭. 한글·한자는 터미널에서 두 칸을 쓰므로 len() 으로는 정렬이 깨진다."""
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def _pad(text: str, width: int) -> str:
    return text + " " * max(0, width - _w(text))


def render(
    *,
    version: str,
    args: str,
    source: str,
    n_rows: int,
    n_cols: int,
    violations: list[str],
    notes: list[str],
    metrics: dict,
    runtime_s: float,
    status: str,
) -> str:
    n_ok = max(0, n_cols - len(violations))
    # 빈칸이면 옮겨 적을 때 통째로 빠진다. 모르면 모른다고 적는다.
    version = version.strip() or "unversioned"
    lines = [
        "=" * WIDTH,
        "RUN SUMMARY".center(WIDTH),
        "=" * WIDTH,
        f"version   : {version}",
        f"args      : {args}",
        f"input     : {source}",
        f"shape     : {n_rows:,} rows x {n_cols} cols",
        f"schema    : {n_ok} ok / {len(violations)} MISMATCH",
    ]
    lines += [f"  - {v}" for v in violations]
    # 노트는 "어긋났지만 처리 로직이 안 읽는다" — 위반과 섞으면 매 실행마다 뜨는
    # 줄이 생기고, 사람은 곧 schema 줄 자체를 안 보게 된다
    if notes:
        lines.append(f"notes     : {len(notes)} (판정에 영향 없음)")
        lines += [f"  - {n}" for n in notes]
    lines.append("metrics   :")
    lines += [f"  {_pad(k, 16)} {v}" for k, v in metrics.items()]
    lines.append(f"runtime   : {runtime_s:.1f}s, peak {peak_gb():.2f}GB")
    lines.append(f"status    : {status}")
    lines.append("=" * WIDTH)
    return "\n".join(lines)
