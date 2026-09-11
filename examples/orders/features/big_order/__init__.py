"""금액이 큰 주문이 얼마나 되는가."""

from ...schema import is_null, parse
from .._shared import tally

NAME = "big_order"

# ⚠ 이런 값은 원래 CLI 인자여야 한다. 예시라 박아두었을 뿐이다 —
# 운영 환경에서는 한 줄도 못 고치므로 임계값이 코드에 있으면 사이클을 버린다.
THRESHOLD = 500_000.0


def process_data(rows: list[dict]) -> dict:
    hits = sum(1 for row in rows if _hit(row))
    return {NAME: tally(hits, len(rows))}


def _hit(row: dict) -> bool:
    raw = row.get("amount")
    if is_null(raw):
        return False
    try:
        return parse(raw, "float") >= THRESHOLD
    except (TypeError, ValueError):
        return False        # 스키마 위반은 validate 가 이미 세었다
