"""scripts/adopt.sh 가 실제로 쓸 수 있는 저장소를 만드는지 확인한다.

복사 스크립트는 조용히 낡는다 — 스캐폴드에 파일이 하나 늘어도 목록에 안 넣으면
아무도 모른다. 그래서 설명하지 말고 **돌려서 결과를 검사한다.**
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ADOPT = ROOT / "scripts" / "adopt.sh"

pytestmark = pytest.mark.skipif(not ADOPT.exists(), reason="이식된 사본이다 (adopt.sh 없음)")


@pytest.fixture(scope="module")
def adopted(tmp_path_factory) -> Path:
    dest = tmp_path_factory.mktemp("adopt") / "rule-based-tagging"
    got = subprocess.run(["bash", str(ADOPT), str(dest)],
                         capture_output=True, text=True)
    assert got.returncode == 0, got.stdout + got.stderr
    return dest


def test_package_is_renamed(adopted):
    """대상 폴더 이름에서 패키지 이름을 만들고, import 까지 함께 바꾼다."""
    assert (adopted / "src" / "rule_based_tagging" / "contracts.py").exists()
    assert not (adopted / "src" / "mypkg").exists()
    assert "mypkg" not in (adopted / "src" / "run.py").read_text(encoding="utf-8")


def test_adopted_project_runs(adopted):
    """계약을 안 고쳐도 데이터 파일 없이 전 구간이 돈다."""
    got = subprocess.run([sys.executable, "src/run.py", "--dry-run", "--rows", "200"],
                         cwd=adopted, capture_output=True, text=True)
    assert got.returncode == 0, got.stdout + got.stderr
    assert "RUN SUMMARY" in got.stdout


def test_adopted_project_keeps_exit_code_contract(adopted):
    """0 / 1 / 2 가 그대로 살아 있어야 실행 스크립트가 분기할 수 있다."""
    def code(args):
        return subprocess.run([sys.executable, "src/run.py", *args],
                              cwd=adopted, capture_output=True, text=True).returncode

    assert code(["--dry-run", "--rows", "200"]) == 0
    assert code(["--dry-run", "--rows", "1000", "--adversarial"]) == 1
    assert code(["--data", "없는파일.csv"]) == 2


def test_transport_boundary_comes_along(adopted):
    """경계 두 파일이 빠지면 데이터가 조용히 운영 환경으로 넘어간다 (규격 §2.3)."""
    assert (adopted / ".gitattributes").exists()
    assert (adopted / ".gitignore").exists()
    assert "export-ignore" in (adopted / ".gitattributes").read_text(encoding="utf-8")


def test_guide_is_written_with_the_real_package_name(adopted):
    """사본을 받아든 쪽이 읽을 지도. <pkg> 자리표시자가 남아 있으면 안 된다."""
    guide = (adopted / "SCAFFOLD.md").read_text(encoding="utf-8")
    assert "src/rule_based_tagging/pipeline.py" in guide
    assert "<pkg>" not in guide
    assert ".staging/rule-based-tagging/scripts/sync.sh" in guide


def test_existing_files_are_not_clobbered(tmp_path):
    """기존 저장소에 얹는 것이 목적이다. 남의 파일을 덮으면 안 된다."""
    dest = tmp_path / "existing"
    dest.mkdir()
    (dest / "requirements.txt").write_text("numpy==2.0\n", encoding="utf-8")

    got = subprocess.run(["bash", str(ADOPT), str(dest), "tagging"],
                         capture_output=True, text=True)
    assert got.returncode == 0, got.stdout + got.stderr
    assert (dest / "requirements.txt").read_text(encoding="utf-8") == "numpy==2.0\n"
    assert "requirements.txt" in got.stderr, "건너뛴 것을 알려줘야 한다"


def test_force_overwrites(tmp_path):
    dest = tmp_path / "existing"
    dest.mkdir()
    (dest / "requirements.txt").write_text("numpy==2.0\n", encoding="utf-8")

    subprocess.run(["bash", str(ADOPT), str(dest), "tagging", "--force"],
                   capture_output=True, text=True, check=True)
    assert (dest / "requirements.txt").read_text(encoding="utf-8") != "numpy==2.0\n"


def test_refuses_to_copy_onto_itself():
    got = subprocess.run(["bash", str(ADOPT), str(ROOT)], capture_output=True, text=True)
    assert got.returncode != 0
    assert "대상이 이 저장소다" in got.stderr
