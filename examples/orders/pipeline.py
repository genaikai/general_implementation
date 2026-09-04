"""주문 로그 지표 — src/<pkg>/pipeline.py 를 통째로 갈아끼운 예시.

여기서 보여주려는 것 셋:

1. **계약에 있는 필드만 읽는다.** coupon_code 는 used=False 라 이 함수가 건드리지
   않는다. 안 읽는 필드가 어긋나도 판정은 멀쩡하다는 것이 그래서 성립한다.
2. **바뀔 만한 값이 코드에 없다.** 임계값·기간·채널 목록을 박지 않는다 — 운영
   환경에서는 한 줄도 못 고치므로 그런 값은 전부 CLI 인자여야 한다 (§1.3).
3. **지표 이름은 사이클 사이에 바뀌지 않는다.** 이름이 바뀌면 지난 실험 숫자와
   대조할 수 없고, 결과 파일을 못 가져오는 환경에서 그건 되돌릴 수 없다.
"""

from collections import Counter

from .contracts import INPUT_SCHEMA, is_null, parse


def process_data(rows: list[dict]) -> dict:
    """채널별 주문 분포와 금액 요약. 실데이터의 개별 값은 절대 찍지 않는다 (C3)."""
    amounts: list[float] = []
    quantities: list[int] = []
    channels: Counter = Counter()

    for row in rows:
        if not is_null(row.get("amount")):
            try:
                amounts.append(parse(row["amount"], "float"))
            except (TypeError, ValueError):
                pass                      # 계약 위반은 validate 가 이미 세었다
        if not is_null(row.get("quantity")):
            try:
                quantities.append(parse(row["quantity"], "int"))
            except (TypeError, ValueError):
                pass
        if not is_null(row.get("channel")):
            channels[row["channel"]] += 1

    metrics = {
        "orders": f"{len(rows):,}",
        "revenue": f"{sum(amounts):,.0f}",
        "amount_mean": f"{sum(amounts) / len(amounts):,.0f}" if amounts else "n/a",
        "qty_mean": f"{sum(quantities) / len(quantities):.2f}" if quantities else "n/a",
    }
    # 채널은 계약의 allowed 에서 가져온다 — 코드에 박으면 계약과 갈라진다
    declared = next((f.allowed for f in INPUT_SCHEMA if f.name == "channel"), ()) or ()
    for name in declared:
        share = channels[name] / len(rows) if rows else 0
        metrics[f"share_{name}"] = f"{share:.3f}"
    return metrics
