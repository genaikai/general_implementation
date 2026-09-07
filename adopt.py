#!/usr/bin/env python3
"""새로운 프로젝트 스캐폴드를 다른 저장소로 복사한다.

다중 프로젝트 구조:
  src/
    framework/     (공유)
    template/      (복사 용도)
    A/, B/, C/     (각 프로젝트)
    taggers/       (공유 태거들)

사용법:
  python adopt.py <대상 폴더>
"""

import shutil
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        print("사용법: python adopt.py <대상 폴더>", file=sys.stderr)
        sys.exit(1)

    dest = Path(sys.argv[1]).resolve()
    src = Path(__file__).parent

    if dest == src:
        print("✗ 대상이 이 저장소다", file=sys.stderr)
        sys.exit(1)

    dest.mkdir(parents=True, exist_ok=True)

    # 필수 파일·폴더
    essentials = [
        "scripts/sync.sh",
        ".gitattributes",
        ".gitignore",
        "requirements.txt",
        "requirements-dev.txt",
        "configs/env.example.yaml",
        "TODO.md",
        "IMPLEMENTATION_SPEC.md",
        "src/framework",
        "src/template",
        "src/taggers",
        "todo",
        "tests",
    ]

    print(f"복사 중: {src} → {dest}")

    for item in essentials:
        src_path = src / item
        if not src_path.exists():
            print(f"  ⊘ {item} (없음)", file=sys.stderr)
            continue

        dest_path = dest / item

        if src_path.is_dir():
            if dest_path.exists():
                print(f"  ⊘ {item} (이미 있음)", file=sys.stderr)
            else:
                shutil.copytree(src_path, dest_path)
                print(f"  + {item}/")
        else:
            if dest_path.exists():
                print(f"  ⊘ {item} (이미 있음)", file=sys.stderr)
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dest_path)
                print(f"  + {item}")

    # run.py 복사
    run_py = src / "run.py"
    if run_py.exists():
        shutil.copy2(run_py, dest / "run.py")
        print(f"  + run.py")

    # 프로젝트 개수 입력
    print("\n몇 개 프로젝트를 만들까요? (1~10)", end=" ")
    try:
        num_projects = int(input().strip())
        if not 1 <= num_projects <= 10:
            print("1~10 사이의 숫자를 입력하세요")
            sys.exit(1)
    except ValueError:
        print("숫자를 입력하세요")
        sys.exit(1)

    # 각 프로젝트 이름 입력 및 생성
    print()
    projects = []
    for i in range(num_projects):
        print(f"프로젝트 {i + 1} 이름? ", end="")
        name = input().strip()
        if not name or not name.replace("_", "").isalnum():
            print("유효한 이름을 입력하세요 (알파벳, 숫자, 언더스코어)")
            sys.exit(1)
        projects.append(name)

    # 프로젝트 생성
    print("\n생성 중...")
    template_dir = dest / "src" / "template"
    for proj in projects:
        proj_dir = dest / "src" / proj
        if proj_dir.exists():
            print(f"  ⊘ src/{proj}/ (이미 있음)")
        else:
            shutil.copytree(template_dir, proj_dir)
            # __init__.py 수정: 주석 제거
            init_file = proj_dir / "__init__.py"
            if init_file.exists():
                init_file.write_text(f'"""프로젝트 {proj}의 로직."""\n')
            print(f"  + src/{proj}/")

    # SCAFFOLD.md 생성
    scaffold_md = dest / "SCAFFOLD.md"
    if not scaffold_md.exists():
        scaffold_md.write_text(f"""# 이 저장소의 구조

다중 프로젝트 개발 구조.

## 구조

```
src/
  framework/           (공유 - 수정 금지)
    contracts.py       입력 스키마
    load.py            데이터 로드
    base.py, report.py, synth.py

  template/            (복사 용도)
    main.py, pipeline.py

""")

        for proj in projects:
            scaffold_md.write_text(scaffold_md.read_text() + f"  {proj}/               (프로젝트 {proj})\n")
            scaffold_md.write_text(
                scaffold_md.read_text() + f"    main.py, pipeline.py\n\n"
            )

        scaffold_md.write_text(
            scaffold_md.read_text()
            + """  taggers/             (공유 태거들)
    language_mixing/, error_keyword/, ...
```

## 개발 흐름

1. **src/framework/contracts.py** - INPUT_SCHEMA 정의 (한 번)
2. **src/{프로젝트}/pipeline.py** - 각 프로젝트의 로직 구현
3. **필요하면 새 태거 추가** - src/{tagger}/ 생성

## 다음 단계

```bash
# 각 프로젝트 준비
$EDITOR src/framework/contracts.py
$EDITOR src/{프로젝트1}/pipeline.py
$EDITOR src/{프로젝트2}/pipeline.py

# 테스트 (프로젝트별로 run.py를 수정해야 할 수도 있음)
python run.py --dry-run
```

자세한 규격: IMPLEMENTATION_SPEC.md
""")
        print(f"  + SCAFFOLD.md")

    print(f"\n✓ 완료! {len(projects)}개 프로젝트 생성됨:")
    for proj in projects:
        print(f"  - src/{proj}/")

    print("\n다음:")
    print("  $EDITOR src/framework/contracts.py    # INPUT_SCHEMA 정의")
    print("  $EDITOR src/{프로젝트}/pipeline.py      # 로직 구현")
    print("  python run.py --dry-run")


if __name__ == "__main__":
    main()
