"""규격 자체를 검사한다. 규칙으로 굳은 것은 테스트로 옮긴다 (규격 §4).

이식 표면은 `sync.sh` 가 태그 시점에 검사하지만, 그건 태그를 낸 뒤다. 여기서 깨지면
태그를 내기 전에 안다.
"""

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _archive_paths() -> set[str]:
    """HEAD 의 archive 에 실제로 들어가는 경로. export-ignore 가 적용된 결과다."""
    out = subprocess.run(
        ["git", "archive", "HEAD"], cwd=ROOT, capture_output=True, check=True
    ).stdout
    listing = subprocess.run(
        ["tar", "-t"], input=out, capture_output=True, check=True
    ).stdout.decode()
    return {line.rstrip("/") for line in listing.splitlines() if line.strip()}


@pytest.fixture(scope="module")
def shipped() -> set[str]:
    if not (ROOT / ".git").exists():
        pytest.skip("git 저장소가 아니다")
    return _archive_paths()


def test_todo_ships_with_the_copy(shipped):
    """이식만으로 돌지 않는다. 저쪽에서 무엇이 남았는지 알 방법이 이것뿐이다 (규격 §3.0)."""
    assert "TODO.md" in shipped
    assert any(p.startswith("todo/") for p in shipped), "TODO.md 가 가리키는 규격도 가야 한다"


def test_readme_ships_because_the_spec_does_not(shipped):
    """IMPLEMENTATION_SPEC.md 는 export-ignore 다. 저쪽이 읽을 것은 README 뿐이다."""
    assert "README.md" in shipped
    assert "IMPLEMENTATION_SPEC.md" not in shipped


def test_development_only_things_do_not_ship(shipped):
    """운영 저장소에 남는 것은 제품 코드뿐이어야 한다 (규격 §1.4·§2.3)."""
    for path in ("requirements-dev.txt", ".gitattributes", "CLAUDE.md"):
        assert path not in shipped, path
    assert not any(p.startswith("tools/") for p in shipped), "tools/ 는 LLM 을 쓴다 (C8)"
    assert not any(p.startswith("docs/insights") for p in shipped), "가져온 기록은 되돌아가지 않는다"


def test_gitattributes_has_no_trailing_comments():
    """git 은 .gitattributes 에서 줄 끝 주석을 지원하지 않는다 — 그 줄이 통째로 무시된다.

    조용히 무시되므로 archive 를 풀어보기 전에는 알 수 없다. 그게 사고가 되는 방식이다.
    """
    path = ROOT / ".gitattributes"
    if not path.exists():
        # 자기 자신도 export-ignore 라 이식된 사본에는 없다. 검사할 대상이 없는 것이지
        # 실패가 아니다 — 이 검사는 개발 장비에서만 뜻이 있다.
        pytest.skip("이식된 사본이다 (.gitattributes 없음)")

    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        body = line.strip()
        if not body or body.startswith("#"):
            continue
        assert "#" not in body, f".gitattributes:{lineno} 줄 끝 주석 — 이 줄은 무시된다"


def test_ignore_rule_is_an_allowlist_not_a_namelist():
    """이름을 하나씩 적으면 오타 한 번에 무시가 풀리고, 그때 조용히 커밋된다 (규격 §2.3)."""
    text = (ROOT / ".gitignore").read_text()
    assert "configs/*.yaml" in text
    assert "!configs/env.example.yaml" in text


def test_src_does_not_import_dev_tools():
    """import 방향은 한쪽이다. 위치보다 이 규칙이 실제 사고를 막는다 (규격 §1.4)."""
    for path in (ROOT / "src").rglob("*.py"):
        text = path.read_text()
        assert "import tools" not in text and "from tools" not in text, path
