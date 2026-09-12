"""기능 하나. 복사해서 쓰는 원본이다.

**기능은 판정만이 아니다.** 같은 입력을 읽어 지표를 내는 독립 단위면 무엇이든
기능이다 — 사고 검출도, 분포 집계도, 성능 계산도. 계약은 아래 둘뿐이다.

    cp -r src/<pkg>/features/template src/<pkg>/features/<기능>

그다음 `pipeline.py` 의 `FEATURES` 에 한 줄 더하면 리포트에 나온다. 스키마·적재·
리포트·진입점은 손대지 않는다 — 기능을 늘릴 때 만질 곳이 둘뿐인 것이 이 구조의 뜻이다.

**이 폴더 자체는 지우지 마라.** 일곱 번째 기능을 만드는 사람이 기존 기능 하나를
골라 베끼면 그 기능만의 사정까지 따라간다. 원본이 있어야 깨끗한 데서 시작한다.

**기능이 커지면 파일을 옆에 만든다.** 패턴 표든 헬퍼든 이 폴더 안에 두고 여기서
import 한다 (`from .patterns import PATTERNS`). 폴더 깊이가 처음부터 고정이라
그때 상대 import 를 고칠 일이 없다 — 기능마다 폴더를 주는 이유가 이것이다.

    features/<기능>/__init__.py    ← process_data 를 노출한다. 여기가 입구다
    features/<기능>/patterns.py    ← 그 기능만 쓰는 것들

둘 이상의 기능이 같은 기준을 쓰게 되면 그때 `features/_shared.py` 로 올린다.

지켜야 하는 것 둘:

- **`process_data(rows) -> dict` 로 노출한다.** `pipeline.py` 가 이 이름으로 부른다
- **지표 이름 앞에 `NAME` 을 붙인다.** 여럿의 결과가 한 리포트에 모이므로 접두어가
  없으면 같은 이름끼리 겹친다. `pipeline.py` 가 겹치면 죽이지만, 죽기 전에 붙여라
"""

from .._shared import tally

NAME = "template"  # 폴더 이름과 같게 둔다. 지표 접두어로 쓰인다


def process_data(rows: list[dict]) -> dict:
    """이 기능의 결과를 지표로 돌려준다.

    실데이터의 개별 값·식별자는 넣지 않는다. 세는 것까지다.
    """
    hits = sum(1 for row in rows if _hit(row))
    return {NAME: tally(hits, len(rows))}


def _hit(row: dict) -> bool:
    """이 행이 이 기능에 걸리는가.

    ⭐ TODO: 실제 내용을 여기에. 지금은 "빈 값이 하나라도 있나" 를 본다 —
    자리를 지키면서 전 구간이 도는 것까지만 보이는 최소 구현이다.

    타입을 해석해야 하면 `parse()`, 스키마가 필요하면 `INPUT_SCHEMA` 를 읽는다:

        from ...schema import INPUT_SCHEMA, is_null, parse
    """
    from ...schema import is_null

    return any(is_null(value) for value in row.values())
