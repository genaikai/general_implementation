"""도메인 로직을 붙이는 자리.

지표 이름은 사이클 사이에 바꾸지 않는다 (규격 §3.2) — 이름이 바뀌면 지난 사이클의
숫자와 대조할 수 없고, 반출이 안 되는 환경에서 그건 되돌릴 수 없는 손실이다.
"""

from .contracts import INPUT_SCHEMA, is_null, parse


def compute_metrics(rows: list[dict]) -> dict:
    """자리표시자. 계약의 수치 필드에 대해 평균과 널 비율을 낸다."""
    numeric = [f.name for f in INPUT_SCHEMA if f.dtype in ("int", "float")]
    metrics = {"rows": f"{len(rows):,}"}
    for name in numeric:
        values = []
        for row in rows:
            raw = row.get(name)
            if is_null(raw):
                continue
            try:
                values.append(parse(raw, "float"))
            except (TypeError, ValueError):
                continue
        metrics[f"{name}_mean"] = f"{sum(values) / len(values):.4f}" if values else "n/a"
        metrics[f"{name}_nullrate"] = f"{1 - len(values) / len(rows):.4f}" if rows else "n/a"
    return metrics
