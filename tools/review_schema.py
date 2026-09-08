"""개발 보조 도구 — 개발 장비 전용 (규격 §1.4).

스키마 파일을 LLM 에게 보여 빠진 필드나 모순을 짚게 한다.
운영 환경에서는 이 API 를 쓸 수 없으므로(C8) 이 디렉터리는 .gitattributes 의
export-ignore 로 이식에서 제외된다.

import 방향은 한쪽이다: tools/ 는 src/ 를 읽어도 되지만, src/ 는 tools/ 를 import하지 않는다.
"""

import sys
from pathlib import Path

import anthropic

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mypkg.schema import INPUT_SCHEMA  # noqa: E402

PROMPT = """다음은 데이터 스키마다. 빠졌을 법한 필드, 서로 모순되는 제약,
실데이터에서 흔히 깨질 지점을 짚어라.

{schema}
"""


def main() -> int:
    schema = "\n".join(repr(f) for f in INPUT_SCHEMA)
    client = anthropic.Anthropic()
    reply = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": PROMPT.format(schema=schema)}],
    )
    print(reply.content[0].text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
