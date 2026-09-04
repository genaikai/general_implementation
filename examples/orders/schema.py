"""주문 로그 계약 — src/<pkg>/contracts.py 의 표시된 블록에 그대로 넣는 예시.

계약에 적는 것은 **구조**뿐이다. 실제 채널 코드 40개를 나열하거나 금액 분포를 적으면
그건 구조가 아니라 데이터고, 밖으로 나올 수 없다 (C3).
"""

# ── 프로젝트를 시작할 때 이 부분을 갈아끼운다 ────────────────────────────────
INPUT_SCHEMA: tuple[Field, ...] = (
    Field("order_id", "str", False,
          note="2026-08 확인: ORD- 접두어 + 숫자 10자리"),
    Field("ordered_at", "datetime", False),
    Field("channel", "category", False, allowed=("web", "app", "store")),
    Field("amount", "float", False, rng=(0.0, 1e9),
          note="원 단위 정수로 들어온다. 소수점 없음"),
    Field("quantity", "int", False, rng=(1, 999)),
    # 로그에는 있지만 이 파이프라인은 읽지 않는다. 어긋나도 판정은 멀쩡하므로
    # 위반이 아니라 노트로 내려간다 — 매 실행마다 뜨는 줄이 있으면 사람은 곧
    # contract 줄 자체를 안 보게 된다.
    Field("coupon_code", "str", True, used=False),
)
# ─────────────────────────────────────────────────────────────────────────────
