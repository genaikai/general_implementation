"""기능 등록부. 기능이 늘어도 여기만 손대면 되는지, 겹치면 죽는지 본다."""

import pytest

from core import pipeline
from core.synth import generate


def test_features_are_merged_into_one_report():
    rows = generate(200, seed=0)
    metrics = pipeline.process_data(rows)

    assert metrics["rows"] == "200"
    for feature in pipeline.FEATURES:
        assert any(k.startswith(feature.NAME) for k in metrics), feature.NAME


def test_colliding_metric_names_raise_instead_of_overwriting():
    """조용히 덮어쓰면 화면의 숫자가 거짓이 된다 — 마지막 기능의 값만 남는다.

    덮였다는 사실이 어디에도 안 뜨므로, 사람은 틀린 숫자를 옳은 줄 알고 옮겨 적는다.
    시끄럽게 죽는 쪽이 낫다.
    """

    class Twin:
        NAME = "twin"

        @staticmethod
        def process_data(rows):
            return {"rows": "겹친다"}       # pipeline 이 먼저 넣는 이름

    original = pipeline.FEATURES
    pipeline.FEATURES = (*original, Twin)
    try:
        with pytest.raises(KeyError, match="twin"):
            pipeline.process_data(generate(10, seed=0))
    finally:
        pipeline.FEATURES = original


def test_feature_exposes_the_agreed_shape():
    """pipeline 이 이 이름들로 부른다. 하나라도 없으면 등록해도 안 돈다."""
    for feature in pipeline.FEATURES:
        assert isinstance(feature.NAME, str) and feature.NAME
        assert callable(feature.process_data)


def test_metric_names_carry_the_feature_prefix():
    """접두어가 없으면 기능이 늘 때 겹친다. 겹치기 전에 규칙으로 막는다."""
    rows = generate(50, seed=0)
    for feature in pipeline.FEATURES:
        for name in feature.process_data(rows):
            assert name.startswith(feature.NAME), f"{feature.NAME}: {name}"
