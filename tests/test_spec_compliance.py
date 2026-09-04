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
    """받아서 바로 돌지 않는다. 저쪽에서 무엇을 준비해야 하는지 알 방법이 이것뿐이다."""
    assert "TODO.md" in shipped
    assert any(p.startswith("todo/") for p in shipped), "TODO.md 가 가리키는 문서도 가야 한다"


def test_the_copy_reads_as_an_ordinary_program(shipped):
    """사본에 남는 문서는 이 프로그램을 돌리는 법뿐이다 (C9).

    README 와 규격 문서는 왜 이런 구조인지를 설명한다 — 그건 개발 저장소에만 남는다.
    저쪽에서 필요한 것(돌리기 전에 준비할 것)은 TODO.md 와 todo/ 가 맡는다.
    """
    assert "TODO.md" in shipped
    for path in ("README.md", "IMPLEMENTATION_SPEC.md"):
        assert path not in shipped, path


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
    """import 방향은 한쪽이다. 위치보다 이 규칙이 실제 사고를 막는다."""
    for path in (ROOT / "src").rglob("*.py"):
        text = path.read_text()
        assert "import tools" not in text and "from tools" not in text, path


# ── C9: 사본은 평범한 프로그램으로 보여야 한다 ──────────────────────────────

# 파일 단위 제외로는 코드 주석 안의 어휘를 못 뺀다 — 코드는 가야 하기 때문이다.
# 그래서 내용까지 본다. sync.sh 도 같은 것을 보지만 그건 태그를 낸 뒤다.
WORKFLOW_WORDS = (
    "개발 장비", "운영 장비", "운영 환경", "이식", "반입", "스캐폴드",
    "규격", "인사이트", "반출", "{AA}", "{BB}", "staging", "sync.sh", "§",
)


def test_copy_carries_no_workflow_vocabulary(shipped):
    """사본의 어느 파일에도 워크플로를 드러내는 낱말이 없어야 한다.

    HEAD 를 본다 — 커밋한 것이 곧 태그가 될 것이기 때문이다. 작업 트리의 변경은
    아직 안 잡히지만, 그건 sync.sh 가 태그 시점에 다시 본다.
    """
    out = subprocess.run(["git", "archive", "HEAD"], cwd=ROOT,
                         capture_output=True, check=True).stdout
    listing = subprocess.run(["tar", "-tf", "-"], input=out,
                             capture_output=True, check=True).stdout.decode()

    hits: list[str] = []
    for name in (n for n in listing.splitlines() if n and not n.endswith("/")):
        blob = subprocess.run(["git", "show", f"HEAD:{name}"], cwd=ROOT,
                              capture_output=True).stdout.decode("utf-8", "replace")
        for lineno, line in enumerate(blob.splitlines(), 1):
            for word in WORKFLOW_WORDS:
                if word in line:
                    hits.append(f"{name}:{lineno}: {line.strip()[:70]}")
                    break
    assert not hits, "사본에 워크플로 어휘가 남았다:\n" + "\n".join(hits)


def test_workflow_documents_do_not_ship(shipped):
    """워크플로를 설명하는 문서는 통째로 빠진다."""
    for path in ("README.md", "scripts/sync.sh", "tests/test_spec_compliance.py",
                 "SCAFFOLD.md", "IMPLEMENTATION_SPEC.md"):
        assert path not in shipped, path


def test_sync_sh_checks_the_vocabulary_itself():
    """태그를 낸 뒤에도 기계가 한 번 더 본다. 사람 눈에만 맡기지 않는다."""
    body = (ROOT / "scripts" / "sync.sh").read_text(encoding="utf-8")
    assert "C9" in body
    for word in ("개발 장비", "이식", "{AA}", "sync\\.sh"):
        assert word in body, word
