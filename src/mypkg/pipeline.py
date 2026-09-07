"""도메인 로직을 붙이는 자리 .

⭐ TODO: 아래의 process_data() 함수를 실제 로직으로 구현하세요!

입력: contracts.py의 INPUT_SCHEMA를 만족하는 rows (list[dict])
출력: dict (key: 지표명, value: 숫자 또는 문자열)

📋 규칙:
  - 지표 이름은 사이클 사이에 바꾸지 않는다 — 바뀌면 과거 수치와 대조 불가
  - 예: metric_v2 라고 이름 바꾸면 안 되고, 개선 후에도 metric 이름은 유지
  - is_null(), parse() 는 contracts.py 에서 쓸 수 있음
  - input_value = row.get("column_name") 로 접근

💡 예시:
  def process_data(rows):
      result = {"rows": len(rows)}
      # 실제 기능 코드를 여기에
      return result
"""

from .contracts import INPUT_SCHEMA, is_null, parse


def process_data(rows: list[dict]) -> dict:
    """입력 데이터를 처리하고 결과 지표를 반환합니다.

    이 함수가 이 파일의 핵심 — 실제 도메인 로직을 여기에 구현하세요.
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
