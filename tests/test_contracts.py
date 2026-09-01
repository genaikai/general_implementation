"""계약 ↔ 생성기 왕복. 픽스처 파일 없이 generate() 로 데이터를 만든다 (규격 §1.2)."""

from mypkg.contracts import INPUT_SCHEMA, validate
from mypkg.synth import generate


def test_generated_data_satisfies_contract():
    assert validate(generate(500, seed=0)) == []


def test_generation_is_deterministic():
    assert generate(100, seed=7) == generate(100, seed=7)
    assert generate(100, seed=7) != generate(100, seed=8)


def test_adversarial_mode_produces_violations():
    assert validate(generate(500, seed=0, mode="adversarial"))


def test_missing_column_is_reported_by_name():
    rows = generate(10, seed=0)
    dropped = INPUT_SCHEMA[0].name
    for row in rows:
        del row[dropped]
    messages = validate(rows)
    assert any(dropped in m and "column missing" in m for m in messages)


def test_violation_messages_name_the_field():
    """'validation failed' 같은 요약은 결함이다 — 사람이 옮겨 적을 것이 있어야 한다."""
    rows = generate(50, seed=0)
    for row in rows:
        row["grade"] = "Z"
    messages = validate(rows)
    assert messages and all("grade" in m for m in messages)
    assert any("Z" in m for m in messages)


def test_empty_input_is_reported():
    assert validate([]) == ["input       : 0 rows"]
