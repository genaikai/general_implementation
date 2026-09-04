"""입력 적재 (규격 §1.3).

포맷을 아는 코드는 여기에만 둔다. 처리 로직은 dict 의 리스트만 본다 —
운영 환경에서 포맷이 어긋나면 고칠 수 있는 것은 이 파일 한 곳뿐이기 때문이다.
"""

import csv


def load_csv(path: str, limit: int = 0) -> list[dict]:
    """앞 limit 행만 읽는다 (0 = 전체). BOM 이 붙은 파일도 그대로 연다."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = []
        for i, row in enumerate(csv.DictReader(fh)):
            if limit and i >= limit:
                break
            rows.append(row)
    return rows
