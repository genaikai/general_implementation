"""입력 데이터 계약 — 이 파일이 유일한 출처다 (규격 §1.1).

운영 환경에서 확인한 포맷은 여기에만 반영한다. 적는 것은 구조뿐이다:
이름 / 타입 / 널 허용 / 허용값 / 범위. 실제 값·분포·식별 가능한 코드값은 적지 않는다.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Field:
    name: str
    dtype: str                      # "int" | "float" | "str" | "datetime" | "category"
    nullable: bool
    allowed: tuple | None = None    # 카테고리 허용값
    rng: tuple | None = None        # (min, max)
    note: str = ""                  # 운영 환경에서 확인된 사실을 적는 자리
    used: bool = True               # 처리 로직이 이 필드를 읽나 (규격 §3.2)


# ── 프로젝트를 시작할 때 이 부분을 갈아끼운다 ────────────────────────────────
INPUT_SCHEMA: tuple[Field, ...] = (
    Field("customer_id", "str", False, note="영문+숫자 12자리"),
    Field("amount", "float", True, rng=(0.0, 1e12)),
    Field("grade", "category", True, allowed=("A", "B", "C")),
    # 로그에 있지만 처리 로직이 읽지 않는 필드. 어긋나도 판정은 멀쩡하므로
    # 위반이 아니라 노트로 내려간다 — 매 실행마다 뜨는 줄이 있으면 사람은
    # 곧 contract 줄 자체를 안 보게 된다.
    Field("legacy_memo", "str", True, used=False),
)
# ─────────────────────────────────────────────────────────────────────────────

NULL_TOKENS = frozenset({"", "NA", "N/A", "null", "NULL", "None", "-"})


def parse(value: str, dtype: str):
    """문자열을 dtype 으로 해석한다. 실패하면 ValueError."""
    if dtype == "int":
        return int(value)
    if dtype == "float":
        return float(value)
    if dtype == "datetime":
        return datetime.fromisoformat(value)
    return str(value)


def is_null(value) -> bool:
    return value is None or (isinstance(value, str) and value.strip() in NULL_TOKENS)


@dataclass(frozen=True)
class Report:
    """계약 대조 결과. 위반과 노트를 가른다 (규격 §3.2).

    위반(violations) 은 "판정이 틀렸을 수 있다"는 뜻이고, 노트(notes) 는 "어긋났지만
    처리 로직이 안 읽는다"는 뜻이다. 둘을 섞으면 매 실행마다 뜨는 줄이 생기고,
    사람은 곧 contract 줄 자체를 안 보게 된다 — 그러면 포맷 회수 채널이 죽는다.
    """

    violations: list[str]
    notes: list[str]

    @property
    def ok(self) -> bool:
        return not self.violations


def _field_messages(f: Field, rows: list[dict]) -> list[str]:
    """한 필드의 어긋남을 사람이 그대로 옮겨 적을 수 있는 한 줄씩으로."""
    nulls = bad_type = out_of_range = 0
    unexpected: set = set()

    for row in rows:
        raw = row.get(f.name)
        if is_null(raw):
            nulls += 1
            continue
        try:
            value = parse(raw, f.dtype)
        except (TypeError, ValueError):
            bad_type += 1
            continue
        if f.allowed is not None and value not in f.allowed:
            unexpected.add(value)
        if f.rng is not None and not (f.rng[0] <= value <= f.rng[1]):
            out_of_range += 1

    out: list[str] = []
    if nulls and not f.nullable:
        out.append(f"{f.name:<12}: {nulls:,} nulls but nullable=False")
    if bad_type:
        out.append(f"{f.name:<12}: dtype {f.dtype} expected, {bad_type:,} rows failed to parse")
    if unexpected:
        shown = sorted(unexpected)[:5]
        more = "" if len(unexpected) <= 5 else f" (+{len(unexpected) - 5} more)"
        out.append(f"{f.name:<12}: unexpected values {set(shown)}{more}")
    if out_of_range:
        out.append(f"{f.name:<12}: {out_of_range:,} rows outside {f.rng}")
    return out


def validate(rows: list[dict]) -> Report:
    """계약을 대조한다 (규격 §3.2).

    파일 반출이 안 되는 환경에서 이 출력이 입력 포맷을 회수하는 주 채널이다.
    따라서 "validation failed" 같은 요약 메시지는 이 규격에서 결함이다 —
    옮겨 적을 것이 없기 때문이다.
    """
    if not rows:
        return Report(["input       : 0 rows"], [])

    present = set(rows[0])
    violations: list[str] = []
    notes: list[str] = []

    for f in INPUT_SCHEMA:
        sink = violations if f.used else notes
        if f.name not in present:
            sink.append(f"{f.name:<12}: column missing")
            continue
        sink.extend(_field_messages(f, rows))

    extra = present - {f.name for f in INPUT_SCHEMA}
    if extra:
        # 선언되지 않은 컬럼은 처리 로직이 읽을 리 없다 — 알려는 주되 위반은 아니다
        notes.append(f"{'(schema)':<12}: undeclared columns {sorted(extra)}")
    return Report(violations, notes)
