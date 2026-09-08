"""스키마 ↔ 생성기 왕복. 픽스처 파일 없이 generate() 로 데이터를 만든다."""

from core.schema import INPUT_SCHEMA, validate
from core.synth import generate


def test_generated_data_satisfies_schema():
    assert validate(generate(500, seed=0)).ok


def test_generation_is_deterministic():
    assert generate(100, seed=7) == generate(100, seed=7)
    assert generate(100, seed=7) != generate(100, seed=8)


def test_adversarial_mode_produces_violations():
    assert not validate(generate(500, seed=0, mode="adversarial")).ok


def test_missing_column_is_reported_by_name():
    rows = generate(10, seed=0)
    dropped = INPUT_SCHEMA[0].name
    for row in rows:
        del row[dropped]
    messages = validate(rows).violations
    assert any(dropped in m and "column missing" in m for m in messages)


def test_violation_messages_name_the_field():
    """'validation failed' 같은 요약은 결함이다 — 사람이 옮겨 적을 것이 있어야 한다."""
    rows = generate(50, seed=0)
    for row in rows:
        row["grade"] = "Z"
    messages = validate(rows).violations
    assert messages and all("grade" in m for m in messages)
    assert any("Z" in m for m in messages)


def test_empty_input_is_reported():
    assert validate([]).violations == ["input       : 0 rows"]


def test_unused_fields_do_not_count_as_schema_violations():
    """안 쓰는 필드의 어긋남은 노트로 내려가고, 쓰는 필드는 그대로 위반이다.

    스키마 위반 줄은 "판정이 틀렸을 수 있다"는 뜻이어야 한다 — 거기 잡음이 섞이면
    사람이 그 줄 자체를 안 보게 된다.
    """
    unused = [f for f in INPUT_SCHEMA if not f.used]
    assert unused, "used=False 인 필드가 하나는 있어야 이 규칙을 보여준다"

    rows = generate(50, seed=0)
    for row in rows:
        del row[unused[0].name]

    report = validate(rows)
    assert report.ok, f"안 쓰는 필드 때문에 위반이 떴다: {report.violations}"
    assert any(unused[0].name in n for n in report.notes)


def test_undeclared_columns_are_notes_not_violations():
    """선언되지 않은 컬럼은 처리 로직이 읽을 리 없다 — 알리되 판정은 막지 않는다."""
    rows = generate(50, seed=0)
    for row in rows:
        row["surprise"] = "x"

    report = validate(rows)
    assert report.ok
    assert any("surprise" in n for n in report.notes)
