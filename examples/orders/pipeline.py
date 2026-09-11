"""주문 로그 판정 등록부 — src/<pkg>/pipeline.py 를 갈아끼운 예시.

기능이 둘이다. 여기서 보여주려는 것:

1. **기능을 늘려도 만질 곳이 둘뿐이다** — features/ 에 폴더 하나, 아래 목록에 한 줄.
   스키마·적재·리포트·진입점은 그대로다.
2. **지표 이름 앞에 NAME 이 붙는다.** 둘의 결과가 한 리포트에 모이므로, 접두어가
   없으면 겹친다. 겹치면 아래에서 죽는다 — 조용히 덮어쓰지 않는다.
3. **안 읽는 필드는 건드리지 않는다.** coupon_code 는 used=False 라 어느 기능도
   읽지 않고, 그래서 그게 어긋나도 판정은 멀쩡하다.
"""

from .features import big_order, channel_mix

# 화면에 뜨는 순서다. 사람이 사이클 사이에 눈으로 대조하므로 순서를 바꾸지 않는다.
FEATURES = (
    channel_mix,
    big_order,
)


def process_data(rows: list[dict]) -> dict:
    metrics = {"rows": f"{len(rows):,}"}
    for feature in FEATURES:
        result = feature.process_data(rows)
        collided = metrics.keys() & result.keys()
        if collided:
            raise KeyError(
                f"{feature.NAME} 의 지표 이름이 겹친다: {sorted(collided)}. "
                f"지표 이름 앞에 NAME 을 붙여라"
            )
        metrics.update(result)
    return metrics
