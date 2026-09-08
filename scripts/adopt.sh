#!/usr/bin/env bash
# 이 스캐폴드의 필수 부분만 다른 저장소로 복사한다.
#
#   bash scripts/adopt.sh <대상 폴더> [패키지 이름]   (기본: core)
#
# 예)  bash scripts/adopt.sh ~/work/rule-based-tagging           → src/core
#      bash scripts/adopt.sh ~/work/rule-based-tagging tagging   → src/tagging
#
# 패키지 이름을 안 주면 src/core 그대로 간다. 주면 복사하면서 core 를 그 이름으로
# 바꾼다 - 디렉터리도, 안의 import 도.
#
# **이미 있는 파일은 건드리지 않는다.** 기존 저장소에 얹는 것이 목적이라
# 남의 .gitignore 나 requirements.txt 를 덮어쓰면 안 된다. 건너뛴 것은 끝에
# 모아서 알려주고, 무엇을 손으로 합쳐야 하는지 말해준다. --force 로 덮어쓴다.
#
# 이 스크립트 자체는 이식되지 않는다 (.gitattributes 의 export-ignore).
set -euo pipefail

SELF_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
SRC=$(dirname "$SELF_DIR")

log()  { printf '[adopt] %s\n' "$*"; }
warn() { printf '[adopt] ⚠ %s\n' "$*" >&2; }
die()  { printf '[adopt] ✗ %s\n' "$*" >&2; exit 1; }

FORCE=0
ARGS=()
for a in "$@"; do
  case "$a" in
    --force) FORCE=1 ;;
    -*)      die "모르는 옵션: $a" ;;
    *)       ARGS+=("$a") ;;
  esac
done

[[ ${#ARGS[@]} -ge 1 ]] || die "사용법: bash scripts/adopt.sh <대상 폴더> [패키지 이름] [--force]"
DEST=${ARGS[0]}
PKG=${ARGS[1]:-}

mkdir -p "$DEST"
DEST=$(cd "$DEST" && pwd -P)
[[ "$DEST" != "$SRC" ]] || die "대상이 이 저장소다"

# 안 주면 core 그대로 둔다. 폴더 이름에서 유도하지 않는다 - 폴더 이름은 바뀌기
# 쉽고(사본 위치·작업 폴더 사정), 그때마다 패키지 이름이 따라 바뀌면 import 가
# 전부 흔들린다. 이름은 사람이 정할 때만 바꾼다.
PKG=${PKG:-core}
[[ "$PKG" =~ ^[a-z_][a-z0-9_]*$ ]] || die "패키지 이름으로 쓸 수 없다: $PKG (소문자·숫자·밑줄)"

log "$SRC"
log "  → $DEST   (패키지: $PKG)"

# ── 무엇을 가져가나 ─────────────────────────────────────────────────────────
# 규격이 요구하는 최소 집합이다. 하나라도 빠지면 규격을 만족하지 못한다:
#   src/          스키마·합성데이터·리포트 = §1.1·§1.2·§3.2 그 자체
#   scripts/      이식과 점검 (§2.2·§2.3)
#   .gitattributes/.gitignore   이식 표면의 경계 두 겹 (§2.3)
#   TODO.md·todo/ 저쪽에서 만들어야 할 것 (§3.0)
#   tests/        규칙을 잠그는 자리 (§4)
FILES=(
  scripts/sync.sh
  .gitattributes
  .gitignore
  requirements.txt
  requirements-dev.txt
  configs/env.example.yaml
  TODO.md
  IMPLEMENTATION_SPEC.md
)
DIRS=(todo tests)

skipped=()

copy_file() {                    # copy_file <상대경로> [대상 상대경로]
  # 한 local 문 안에서 방금 만든 변수를 다시 쓰지 않는다 — bash 가 못 본다
  local rel="$1"
  local to="${2:-$1}"
  local dst="$DEST/$to"
  if [[ -e "$dst" && $FORCE -eq 0 ]]; then
    skipped+=("$to"); return
  fi
  mkdir -p "$(dirname "$dst")"
  cp "$SRC/$rel" "$dst"
  # core 를 새 이름으로. 디렉터리 이름과 import 가 함께 바뀌어야 돈다
  [[ "$PKG" == core ]] || perl -pi -e "s/\bcore\b/$PKG/g" "$dst"
  printf '  + %s\n' "$to"
}

for f in "${FILES[@]}"; do
  [[ -e "$SRC/$f" ]] && copy_file "$f"
done

# src/ — 패키지 디렉터리 이름을 바꿔서 옮긴다
copy_file src/run.py
while IFS= read -r f; do
  copy_file "$f" "src/$PKG/${f#src/core/}"
done < <(cd "$SRC" && find src/core -type f -name '*.py' | sort)

for d in "${DIRS[@]}"; do
  [[ -d "$SRC/$d" ]] || continue
  while IFS= read -r f; do
    # 예제 테스트는 examples/ 를 보는데 그건 안 가져간다
    [[ "$f" == tests/test_examples.py ]] && continue
    copy_file "$f"
  done < <(cd "$SRC" && find "$d" -type f ! -name '*.pyc' | sort)
done

# ── 대상 저장소에서 볼 안내문 ────────────────────────────────────────────────
# 대상의 README.md 는 그쪽 것이므로 건드리지 않고 SCAFFOLD.md 로 따로 쓴다.
# 워크플로를 설명하므로 대상의 .gitattributes 에 export-ignore 로 넣는다 (C9) —
# 개발 저장소에서는 보이고 사본에서는 안 보인다.
REPO=$(basename "$DEST")
if [[ -e "$DEST/SCAFFOLD.md" && $FORCE -eq 0 ]]; then
  skipped+=("SCAFFOLD.md")
else
cat > "$DEST/SCAFFOLD.md" <<EOF
# 이 저장소의 구조

개발 장비에서 짜고 운영 환경에서 검증한다. 두 곳을 오갈 수 없으므로 그 분리를
사람의 규율이 아니라 코드 구조로 강제한다.

## 무엇이 어디 있나

| 파일 | 용도 |
|---|---|
| \`scripts/sync.sh\` | 개발→운영 이식 스크립트. **반드시 \`scripts/\` 안에** |
| \`.gitattributes\` | 이식 제외 목록 |
| \`.gitignore\` | 저장소에 애초에 못 들어오게 (데이터·산출물·설정) |
| \`src/run.py\` | 진입점. venv 갈아타기 + 위임만 |
| \`src/$PKG/__main__.py\` | CLI 인자, 실행 순서, 종료 코드 |
| \`src/$PKG/schema.py\` | **입력 스키마.** 프로젝트마다 갈아끼운다 |
| \`src/$PKG/synth.py\` | 스키마에서 가짜 데이터 생성 (데이터 파일을 두지 않기 위해) |
| \`src/$PKG/report.py\` | RUN SUMMARY. 화면이 유일한 출력이다 |
| **\`src/$PKG/pipeline.py\`** | **← 기능 코드를 여기 짠다** |
| \`src/$PKG/load.py\` | 입력 포맷을 아는 유일한 곳 |
| \`requirements.txt\` | 운영 의존성 (버전 고정) |
| \`requirements-dev.txt\` | 개발 전용 패키지 (이식 제외) |
| \`configs/env.example.yaml\` | 설정 예시. 실값은 운영 폴더에만 |
| \`TODO.md\` · \`todo/\` | 운영 환경에서 만들어야 할 것과 그 방법 |
| \`SCAFFOLD.md\` | 이 문서. 사본을 받아든 쪽이 읽는 지도 |
| \`IMPLEMENTATION_SPEC.md\` | 규격 전문 — 왜 이런 규칙인지 (**이식 제외**) |

**규격 문서는 운영 환경으로 넘어가지 않는다.** 그래서 이 \`SCAFFOLD.md\` 가 사본
쪽에서 그 자리를 맡는다 — 지도는 가고, 근거는 개발 저장소에 남는다.

**\`sync.sh\` 는 반드시 \`scripts/sync.sh\` 다.** 자기 위치에서 저장소 이름을 유도하기
때문이다 — 옮기면 이름을 잘못 잡는다. 그래서 경로를 어디에도 설정할 필요가 없다.

## 다음 단계

\`\`\`
1. schema.py 의 INPUT_SCHEMA 를 실제 입력 형태로
2. pipeline.py 에 기능 코드를 짠다            ← 작업은 대부분 여기
3. requirements.txt 에 실제 의존성 (버전 고정)
4. git tag v1.0.0
   bash scripts/sync.sh v1.0.0                 ← preflight. 통과해야 push
   git push origin main --tags
5. 운영 환경에서 (작업 폴더와 겹치지 않는 이름으로 clone 한다):
   git clone <원격> .staging/app
   bash .staging/app/scripts/sync.sh v1.0.0
\`\`\`

\`\`\`bash
python src/run.py --dry-run   # 1번까지 끝났으면 데이터 없이 끝까지 돈다
\`\`\`

## 핵심

- **기능 코드는 \`src/$PKG/pipeline.py\`.** 포맷을 읽는 코드는 \`load.py\`,
  그 외에는 손댈 일이 거의 없다
- **기능이 둘 이상이 되면** \`src/$PKG/features/<기능>/\` 로 가른다
  (\`cp -r features/template features/<기능>\`). 단순한 기능도 폴더를 준다 —
  깊이가 고정이라야 나중에 파일을 옆에 만들 때 상대 import 를 안 고친다.
  \`pipeline.py\` 는 그것들을 불러 합치는 자리가 되고, 공유 코드와 진입점은 그대로
  하나다 — 기능마다 진입점을 두면 리포트가 여러 장으로 갈라지고, 결과 파일을 못
  가져오는 환경에서는 그걸 합칠 방법이 없다.
  지표 이름에는 기능 이름을 접두어로 붙인다. 안 그러면 합칠 때 조용히 덮어쓴다
- **태그를 먼저 내고 preflight 를 돌린다.** \`sync.sh\` 가 태그를 받으므로 순서가
  반대면 "태그가 없습니다" 하고 멈춘다
- **\`configs/env.yaml\` 은 항상 운영 폴더 루트에.** 사본 안에 두면 다음 sync 때
  통째로 지워진다. 그리고 **운영 폴더의 \`.gitignore\` 에 반드시 넣어라** —
  \`sync.sh\` 가 보장하는 것은 \`.staging/\` 한 줄뿐이라, 안 넣으면 거기 채운 운영
  실값이 그대로 운영 git 에 커밋된다. 자세한 것은 \`TODO.md\` 의 2번
- **LLM·외부 API 는 \`src/\` 밖에서.** 개발 도구는 \`tools/\` 에 두고 이식에서 뺀다
- **새로 만든 개발 전용 파일은 \`.gitattributes\` 에 한 줄 추가한다.** \`sync.sh\` 의
  금지 목록은 고정이라 처음 보는 이름은 못 잡는다.
  줄 끝 주석은 쓰지 마라 — git 이 그 줄을 통째로, 조용히 무시한다

### \`sync.sh\` 가 기계적으로 막는 것

태그 낼 때 한 번, 운영 환경에서 또 한 번. 이 여섯은 잊어도 된다.

\`\`\`
개발 전용 파일이 넘어가는 것    tools/  CLAUDE.md  .gitattributes  requirements-dev.txt
데이터 파일                    .csv  .parquet  .pkl …
src/ 안의 anthropic·openai import
requirements.txt 에 섞인 개발 전용 패키지
개인 머신 절대 경로            /Users/…  /home/…
이메일·커밋 트레일러
\`\`\`

**못 막는 둘은 눈으로 본다** — 리포트에 실데이터 값 찍기, 임계값·컬럼명을 코드에
박기. 둘 다 기계가 못 가린다.

자세한 근거는 [\`IMPLEMENTATION_SPEC.md\`](IMPLEMENTATION_SPEC.md) 에 있다.
EOF
  printf '  + %s\n' "SCAFFOLD.md"
fi

# SCAFFOLD.md 는 워크플로를 설명한다. 사본은 평범한 프로그램으로 보여야 하므로
# 대상의 .gitattributes 에 한 줄 보장한다 (C9).
if [[ -f "$DEST/.gitattributes" ]] && ! grep -q '^SCAFFOLD.md' "$DEST/.gitattributes"; then
  printf 'SCAFFOLD.md              export-ignore\n' >> "$DEST/.gitattributes"
  printf '  ~ %s\n' ".gitattributes  (SCAFFOLD.md export-ignore 추가)"
fi

echo
if [[ ${#skipped[@]} -gt 0 ]]; then
  warn "이미 있어서 건너뛴 파일 ${#skipped[@]}개 — 손으로 합쳐야 한다:"
  printf '      %s\n' "${skipped[@]}" >&2
  echo >&2
  warn ".gitignore·.gitattributes 는 특히 중요하다. 빠진 줄이 있으면 데이터나"
  warn "  개발 전용 파일이 조용히 운영 환경으로 넘어간다 (규격 §2.3)."
  echo >&2
fi

cat <<EOF
다음:
  cd $DEST
  \$EDITOR src/$PKG/schema.py     # INPUT_SCHEMA 를 실제 입력 형태로
  \$EDITOR src/$PKG/pipeline.py      # 기능 코드는 여기
  python src/run.py --dry-run       # 데이터 파일 없이 끝까지 도는지

  git tag v0.1
  bash scripts/sync.sh v0.1         # preflight. 통과해야 push
EOF
