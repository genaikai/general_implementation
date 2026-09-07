"""계약에서 파생된 합성 데이터 생성기.

가짜 데이터는 **파일이 아니라 코드로** 존재한다. 저장소에 데이터 파일이 없으면
실수로 커밋될 파일 자체가 없다.
테스트도 픽스처 파일 대신 이 함수를 호출한다.
"""

import random
import string
from datetime import datetime, timedelta

from .contracts import INPUT_SCHEMA, Field

_EPOCH = datetime(2020, 1, 1)


def _value(field: Field, rng: random.Random) -> str:
    if field.dtype == "category":
        return rng.choice(field.allowed or ("A",))
    if field.dtype == "float":
        lo, hi = field.rng or (0.0, 1000.0)
        return f"{rng.uniform(lo, min(hi, lo + 1e6)):.2f}"
    if field.dtype == "int":
        lo, hi = field.rng or (0, 1000)
        return str(rng.randint(int(lo), int(hi)))
    if field.dtype == "datetime":
        return (_EPOCH + timedelta(days=rng.randint(0, 2000))).isoformat()
    return "".join(rng.choices(string.ascii_uppercase + string.digits, k=12))


def _corrupt(row: dict, rng: random.Random) -> dict:
    """실제 데이터에서 나타나는 사고 유형을 주입한다 (적대적 모드).

    새 유형을 만나면 여기에 추가한다. 그러면 다음부터는 합성 데이터에서 미리 터진다.
    """
    field = rng.choice(INPUT_SCHEMA)
    kind = rng.randrange(5)
    if kind == 0:                                    # 숫자 컬럼이 문자열로 읽힘
        row[field.name] = "1,234" if field.dtype in ("int", "float") else " " + str(row[field.name])
    elif kind == 1:                                  # 계약에 없는 카테고리 값
        row[field.name] = "?" if field.allowed else "UNKNOWN"
    elif kind == 2:                                  # 결측 (nullable=False 여도)
        row[field.name] = ""
    elif kind == 3:                                  # 대소문자·공백 흔들림
        row[field.name] = f" {str(row[field.name]).lower()} "
    else:                                            # 범위 밖
        row[field.name] = "-1" if field.rng else str(row[field.name])
    return row


def generate(n: int = 1000, seed: int = 0, mode: str = "normal") -> list[dict]:
    """계약을 읽어 합성 데이터를 만든다. 같은 seed 는 같은 데이터를 준다.

    mode="normal"      계약을 온전히 만족하는 데이터
    mode="adversarial" 위 사고 유형을 섞은 데이터
    """
    rng = random.Random(seed)
    rows: list[dict] = []
    for _ in range(n):
        row = {f.name: _value(f, rng) for f in INPUT_SCHEMA}
        for f in INPUT_SCHEMA:
            if f.nullable and rng.random() < 0.02:
                row[f.name] = ""
        if mode == "adversarial" and rng.random() < 0.05:
            row = _corrupt(row, rng)
        rows.append(row)
    return rows
