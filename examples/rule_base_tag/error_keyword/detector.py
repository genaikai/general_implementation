"""$comment 검출 태거."""

from src.base import Tagger


class $class_name(Tagger):
    """$comment 판정 태거."""

    name = "$tagger_dir"

    def tag(self, rows: list[dict]) -> dict:
        """각 행을 검사한다."""
        flagged = []
        for i, row in enumerate(rows):
            if self._detect(row):
                flagged.append(i)
        return {
            "count": len(flagged),
            "rows": flagged,
            "note": f"{len(flagged)}/{len(rows)} 행에서 감지됨",
        }

    def _detect(self, row: dict) -> bool:
        """한 행에서 조건을 감지한다. TODO: 실제 로직 구현"""
        return False
