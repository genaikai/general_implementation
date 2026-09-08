"""기능 하나의 판정. 복사해서 쓰는 원본이다.

    cp -r src/<pkg>/features/template src/<pkg>/features/<기능>

기능이 하나뿐인 동안은 이 폴더를 쓰지 않는다 — `pipeline.py` 에 그대로 짠다.
둘째 기능이 생기는 순간 첫 기능도 여기로 옮기고, `pipeline.py` 는 기능들을 불러
합치는 자리가 된다.

**이 폴더 자체는 아무도 부르지 않는다.** `pipeline.py` 가 import 하는 것은 복사해서
만든 것들이다. 원본을 지우지 마라 — 일곱 번째 기능을 만드는 사람이 기존 기능
하나를 골라 베끼면 그 기능만의 사정까지 따라간다.

**기능이 커지면 파일을 옆에 만든다.** 패턴 표든 헬퍼든 이 폴더 안에 두고 여기서
import 한다 (`from .patterns import PATTERNS`). 폴더 깊이가 처음부터 고정이라
그때 상대 import 를 고칠 일이 없다 — 기능마다 폴더를 주는 이유가 이것이다.

    features/<기능>/__init__.py    ← process_data 를 노출한다. 여기가 입구다
    features/<기능>/patterns.py    ← 그 기능만 쓰는 것들

지켜야 하는 것 둘:

- **`process_data(rows) -> dict` 로 노출한다.** `pipeline.py` 가 이 이름으로 부른다
- **지표 이름 앞에 `NAME` 을 붙인다.** 기능 여럿의 결과가 한 리포트에 모이므로
  접두어가 없으면 같은 이름끼리 **조용히 덮어쓴다** — 화면에는 마지막 기능의 숫자만
  남고, 덮였다는 사실은 어디에도 안 뜬다
"""

from ...schema import is_null

NAME = "template"  # 폴더 이름과 같게 둔다. 지표 접두어로 쓰인다


def process_data(rows: list[dict]) -> dict:
    """이 기능의 판정 결과를 지표로 돌려준다.

    실데이터의 개별 값·식별자는 넣지 않는다 (C3). 세는 것까지다.
    """
    hits = sum(1 for row in rows if _hit(row))
    return {
        f"{NAME}_hits": f"{hits:,}",
        f"{NAME}_rate": f"{hits / len(rows):.4f}" if rows else "n/a",
    }


def _hit(row: dict) -> bool:
    """이 행이 이 기능에 걸리는가.

    ⭐ TODO: 실제 판정을 여기에. 지금은 "빈 값이 하나라도 있나" 를 본다 —
    자리를 지키면서 전 구간이 도는 것까지만 보이는 최소 구현이다.

    `parse()` 로 타입을 해석할 수 있고, 스키마가 필요하면 `INPUT_SCHEMA` 를 읽는다:

        from ...schema import INPUT_SCHEMA, is_null, parse
    """
    return any(is_null(value) for value in row.values())
