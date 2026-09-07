"""태거 베이스 클래스."""

from abc import ABC, abstractmethod


class Tagger(ABC):
    """모든 태거가 상속해야 하는 베이스 클래스."""

    name: str

    @abstractmethod
    def tag(self, rows: list[dict]) -> dict:
        """행 데이터를 태깅하고 결과를 반환한다."""
        pass
