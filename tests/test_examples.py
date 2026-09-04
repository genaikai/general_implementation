"""examples/ 가 실제로 도는지 확인한다.

예제는 썩기 쉽다 — 스캐폴드 API 가 바뀌어도 문서 안의 코드는 조용히 남는다.
그래서 예제를 설명하지 말고 **돌린다.** 여기서 깨지면 예제가 낡은 것이다.

방식은 사람이 하는 것과 같다: `src/` 를 임시 폴더로 복사하고, `contracts.py` 의
표시된 블록을 예제 스키마로 바꾸고, `pipeline.py` 를 통째로 갈아끼운 뒤 돌린다.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
BEGIN = "# ── 프로젝트를 시작할 때 이 부분을 갈아끼운다"
END = "# ────"


def _example_dirs() -> list[Path]:
    return sorted(p for p in EXAMPLES.iterdir() if p.is_dir()) if EXAMPLES.exists() else []


def _splice_schema(contracts: str, schema_src: str) -> str:
    """contracts.py 의 표시된 블록만 예제 스키마로 갈아끼운다."""
    head, _, rest = contracts.partition(BEGIN)
    _, _, tail = rest.partition(END)
    tail = tail.split("\n", 1)[1] if "\n" in tail else ""

    body = schema_src.partition(BEGIN)[2]
    body = body.split("\n", 1)[1].rpartition(END)[0]
    return f"{head}{BEGIN}\n{body}{END}\n{tail}"


def build(example: Path, dest: Path) -> Path:
    """예제를 적용한 src/ 사본을 만든다. 사람이 손으로 하는 것과 같은 조작이다."""
    src = dest / "src"
    shutil.copytree(ROOT / "src", src, ignore=shutil.ignore_patterns("__pycache__"))
    pkg = src / "mypkg"

    contracts = pkg / "contracts.py"
    contracts.write_text(
        _splice_schema(contracts.read_text(encoding="utf-8"),
                       (example / "schema.py").read_text(encoding="utf-8")),
        encoding="utf-8")

    shutil.copyfile(example / "pipeline.py", pkg / "pipeline.py")
    return src


def run(src: Path, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(src / "run.py"), *args],
                          capture_output=True, text=True, cwd=src.parent)


@pytest.mark.parametrize("example", _example_dirs(), ids=lambda p: p.name)
def test_example_runs_end_to_end(example, tmp_path):
    """예제 계약 + 예제 파이프라인으로 전 구간이 돈다."""
    src = build(example, tmp_path)
    got = run(src, ["--dry-run", "--rows", "500"])
    assert got.returncode == 0, got.stdout + got.stderr
    assert "RUN SUMMARY" in got.stdout
    assert "0 MISMATCH" in got.stdout, "합성 데이터는 제 계약을 만족해야 한다"


@pytest.mark.parametrize("example", _example_dirs(), ids=lambda p: p.name)
def test_example_catches_contract_violations(example, tmp_path):
    """적대적 모드에서 위반이 잡히고 종료 코드가 1 이다."""
    src = build(example, tmp_path)
    got = run(src, ["--dry-run", "--rows", "1000", "--adversarial"])
    assert got.returncode == 1, got.stdout + got.stderr
    assert "MISMATCH" in got.stdout


@pytest.mark.parametrize("example", _example_dirs(), ids=lambda p: p.name)
def test_example_pipeline_ignores_unused_fields(example, tmp_path):
    """used=False 필드가 통째로 빠져도 판정은 멀쩡하다 (규격 §3.2)."""
    src = build(example, tmp_path)
    sys.path.insert(0, str(src))
    try:
        for mod in [m for m in sys.modules if m.startswith("mypkg")]:
            del sys.modules[mod]
        from mypkg.contracts import INPUT_SCHEMA, validate
        from mypkg.synth import generate

        unused = [f for f in INPUT_SCHEMA if not f.used]
        if not unused:
            pytest.skip("이 예제에는 used=False 필드가 없다")

        rows = generate(200, seed=0)
        for row in rows:
            del row[unused[0].name]

        report = validate(rows)
        assert report.ok, report.violations
        assert any(unused[0].name in n for n in report.notes)
    finally:
        sys.path.remove(str(src))
        for mod in [m for m in sys.modules if m.startswith("mypkg")]:
            del sys.modules[mod]
