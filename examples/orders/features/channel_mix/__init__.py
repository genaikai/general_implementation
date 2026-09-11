"""주문이 채널별로 어떻게 갈리는가."""

from collections import Counter

from ...schema import INPUT_SCHEMA, is_null
from .._shared import tally

NAME = "channel"


def process_data(rows: list[dict]) -> dict:
    counts: Counter = Counter()
    for row in rows:
        value = row.get("channel")
        if not is_null(value):
            counts[value] += 1

    # 채널 목록을 여기 박지 않고 스키마에서 읽는다. 박으면 채널이 하나 늘 때
    # 고칠 곳이 둘이 되고, 그러면 언젠가 한쪽만 고쳐진다.
    declared = next((f.allowed for f in INPUT_SCHEMA if f.name == "channel"), ()) or ()
    return {f"{NAME}_{name}": tally(counts[name], len(rows)) for name in declared}
