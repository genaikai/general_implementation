"""기능들을 불러 한 장으로 합친다.

기능 하나하나는 `features/<기능>/` 안에 있고, 이 파일은 그것들을 부르는 일만 한다.
**목록이 여기 있는 것이 요점이다** — 기능이 늘어도 스키마·적재·리포트·진입점은
손대지 않는다.

기능을 하나 만들려면 둘이면 된다:

    cp -r src/core/features/template src/core/features/<기능>
    # 아래 FEATURES 에 한 줄 더한다

기능이 하나뿐이어도 이 모양을 쓴다. 나중에 옮기는 것보다 처음부터 자리를 잡아두는
편이 싸다 — 옮기는 순간에는 import 도 테스트도 지표 이름도 함께 흔들린다.
"""

from .features import template

# 화면에 뜨는 순서다. 사람이 사이클 사이에 눈으로 대조하므로 순서를 바꾸지 않는다.
FEATURES = (
    template,
)


def process_data(rows: list[dict]) -> dict:
    """기능 전부를 돌리고 지표를 합친다."""
    metrics = {"rows": f"{len(rows):,}"}
    for feature in FEATURES:
        result = feature.process_data(rows)
        collided = metrics.keys() & result.keys()
        if collided:
            # 조용히 덮어쓰면 화면의 숫자가 거짓이 된다 — 마지막 기능의 값만 남고
            # 덮였다는 사실은 어디에도 안 뜬다. 시끄럽게 죽는 쪽이 낫다.
            raise KeyError(
                f"{feature.NAME} 의 지표 이름이 겹친다: {sorted(collided)}. "
                f"지표 이름 앞에 NAME 을 붙여라"
            )
        metrics.update(result)
    return metrics
