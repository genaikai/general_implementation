"""처리 로직 - 여기서 실제 구현하세요."""

from ..framework.contracts import INPUT_SCHEMA, is_null, parse


def process_data(rows: list[dict]) -> dict:
    """입력 데이터를 처리하고 지표를 반환합니다.

    TODO: 실제 도메인 로직 구현
    """
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
