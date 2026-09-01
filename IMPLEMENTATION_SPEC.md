# 코드 구현 규격

**기능 개발은 개발 장비에서, 검증은 운영 장비에서.** 이 분리를 코드 구조로 강제하기 위한 규격이다.

| 기호 | 의미 |
|---|---|
| `{BB}` | 개발 장비의 저장소. 로직의 단일 진실 원본 |
| `{AA}` | 운영 장비의 작업 폴더. 운영 git으로 관리됨 |
| `<pkg>` | `{BB}`가 제공하는 패키지 이름 (프로젝트마다 고유하게) |

세 이름 모두 프로젝트마다 다른 실제 문자열이며, 경로로 등장할 때 `{AA}`·`{BB}`로 적는다.
`sync.sh`는 `{BB}`를 자기 위치(`{AA}/.staging/{BB}/scripts/sync.sh`)에서 유도하고 `{AA}`는
실행 위치이므로, **어느 쪽도 설정하거나 수정할 필요가 없다.**

```
[개발 장비] 구현 ──이식──▶ [운영 환경] 실험 ──인사이트──▶ [개발 장비] 개선 ──▶ …
```

**이 저장소 자체가 규격을 만족하는 스캐폴드다.** 복사한 뒤 패키지 이름(`mypkg`)을 바꾸고
`src/mypkg/contracts.py`의 `INPUT_SCHEMA`를 갈아끼우면 시작이다.

## 제약

| ID | 제약 |
|---|---|
| C1 | 이식은 BB → AA 단방향. 운영 환경에서 push 불가 |
| C2 | 따라서 운영 환경에서 코드 수정 불가. 수정은 개발 장비에서만 |
| C3 | 운영 실데이터는 밖으로 나올 수 없다 |
| C4 | 파일·문서 반출 불가. 결과 파일도 플롯도 로그도 못 가져온다 |
| C5 | 회수 가능한 것은 **입력 데이터의 포맷**과 **사람의 인사이트** 둘뿐 |
| C6 | AA는 운영 git 관리 대상. 가짜 데이터와 BB의 `.git`이 AA에 올라가면 안 된다 |
| C7 | 운영 환경는 Python 3.14 + **기존 venv**(공용일 수 있음). PyPI 설치는 가능 |
| C8 | 운영 환경에서는 Claude Code·LLM API를 쓸 수 없다. 개발 장비 개발 중에는 제한 없이 쓴다 |

아래 규칙은 전부 이 제약에서 따라나온 것이다. 규칙이 불편하면 제약이 아직 유효한지 먼저 확인하라.

---

## 1. 개발 쪽 — 데이터 없이 짠다

### 1.1 데이터 계약을 파일 하나에 둔다

C5에 의해 운영 환경에서 회수되는 정보의 절반이 "입력 포맷"이다. 그 정보가 도착할 지점이
한 곳이어야 반영이 쉽다. `src/<pkg>/contracts.py`가 유일한 출처다.

```python
@dataclass(frozen=True)
class Field:
    name: str
    dtype: str                    # "int" | "float" | "str" | "datetime" | "category"
    nullable: bool
    allowed: tuple | None = None  # 카테고리 허용값
    rng: tuple | None = None      # (min, max)
    note: str = ""                # 운영 환경에서 확인된 사실을 적는 자리

INPUT_SCHEMA = (
    Field("customer_id", "str",   False, note="영문+숫자 12자리"),
    Field("amount",      "float", True,  rng=(0, 1e12)),
    Field("grade",       "category", True, allowed=("A", "B", "C")),
)
```

구조만 적는다. 실제 값·분포·식별 가능한 코드값 목록은 적지 않는다 (C3).

### 1.2 가짜 데이터는 **파일이 아니라 코드**다

C6 때문이다. 가짜 데이터가 파일로 BB에 있으면 AA를 통해 운영 저장소로 흘러간다.
`.gitignore`는 `git add -f` 한 번에 뚫리지만, **없는 파일은 올라갈 수 없다.**

- `src/<pkg>/synth.py`의 `generate(n, seed=0)`이 계약을 읽어 런타임에 만든다
- 결정론적: 같은 seed는 같은 데이터
- 테스트 픽스처도 파일로 두지 않는다. 테스트는 `generate()`를 호출한다
  (계약이 바뀌면 테스트 데이터가 따라 바뀌는 이득도 있다)

가짜 데이터가 보증하는 것은 "코드가 끝까지 돈다"까지다. 실제 분포에서의 성능,
실규모에서의 메모리·시간, 계약이 실데이터를 맞게 기술하는지는 **운영 환경에서만 알 수 있다.**

### 1.3 바뀔 만한 값은 전부 코드 밖으로

C2 때문에 운영 환경에서는 한 줄도 못 고친다. 아래는 코드에 박지 않고 **CLI 인자로 받는다.**

- 파일·디렉터리 경로, 접속 정보
- 컬럼명·테이블명·도메인 코드값 → 계약으로
- 임계값·하이퍼파라미터·날짜 범위·샘플 수·워커 수

```bash
python {BB}/src/run.py --data /mnt/real/2026-08.parquet --threshold 0.5
```

`argparse`로 받고, 필수 인자가 빠지면 **어떤 계산도 하기 전에** 죽는다 — 30분 돌린 뒤
인자 하나 때문에 죽으면 사이클 하나를 통째로 버린다.

인자가 열 개를 넘어 명령줄이 길어지면 그때 설정 파일(`--config`)을 얹어도 늦지 않다.
미리 만들 이유는 없다.

> **운영 환경에서 "코드 한 줄만 고치면 되는데" 하는 순간이 오면, 그건 이 규칙이 이미 깨졌다는 신호다.**
> 고치지 말고 "이 값이 인자에 없었다"를 인사이트로 가지고 나온다.

### 1.4 개발 도구와 제품 코드를 가른다

C8. 개발 장비에서는 Claude Code·LLM API로 얼마든지 짜고 검증한다. 운영 환경에서는 그 호출이 전부 실패한다.
그리고 운영 저장소에 남는 것은 **제품 코드뿐이어야 한다** — 개발 환경 아티팩트가 섞이면
읽는 사람에게 잡음이고, 도구 설정·프롬프트에는 생각보다 많은 것이 묻어 있다.

**도구를 어디에 둘 것인가** — 기본은 같은 저장소에 두고 `export-ignore`로 이식에서 뺀다.
판단 기준은 하나다: **두 번 이상 쓸 것이면 커밋하고(도구도 자산이다), 한 번 쓰고 버릴 것이면
커밋하지 않는다.** 도구에 도메인 지식이 묻어 있거나 `{BB}`가 public이면 별도 저장소로 뺀다.

**어디에 두든 지켜야 하는 것**

- **import 방향은 한쪽이다.** `tools/`는 `src/`를 import해도 되지만,
  **`src/`는 `tools/`를 import하지 않는다.** 위치보다 이 규칙이 실제 사고를 막는다
- 의존성을 가른다 — `requirements.txt`(운영 실행용) / `requirements-dev.txt`(개발 장비 전용)
- **API 키 없이 테스트가 전부 통과해야 한다.** 운영 환경 실행 가능성을 개발 장비에서 기계적으로
  확인하는 유일한 방법이다. 키를 지운 채 통과하면 API 의존이 없다는 것이 증명된다:

  ```bash
  env -u ANTHROPIC_API_KEY -u OPENAI_API_KEY python -m pytest
  ```

- 로직 자체가 LLM을 필요로 한다면 그 기능은 운영 환경에서 돌지 않는다. 설계에서 배제하거나,
  규칙 기반 대체 경로를 `src/` 안에 두고 그쪽을 기본 경로로 삼는다

무엇이 실제로 운영 환경에 도착하는지는 §2.3이 정하고, `sync.sh`가 양쪽에서 검사한다(§2.2).

> 운영 환경에서 막힌 것이 LLM API만이 아니라 외부 네트워크 전반이라면, 이 조항의 대상을
> 네트워크를 타는 모든 호출로 넓혀 읽는다. 판단 기준은 같다 — *운영 환경에서 실패할 호출은 `src/`에 없다.*

---

## 2. 이식 — `.git`도 데이터도 넘기지 않는다

### 2.1 배치

```
{BB}/                      {AA}/
  requirements.txt           {BB}/                 ← 소스 사본. .git 없음. 통째 교체
  requirements-dev.txt ✗     outputs/              ← 산출물
  scripts/sync.sh            notebooks/            ← 운영 환경 탐색
  src/run.py                 .staging/{BB}/        ← 이식 중계 clone (무시됨)
  src/<pkg>/                 .staging/.gitignore   ← 내용은 `*` 한 줄
  tools/               ✗
  tests/

✗ = .gitattributes 의 export-ignore. 개발 장비 전용이며 archive 결과에 포함되지 않는다
```

**운영 자산은 `{AA}/{BB}` 밖에 둔다.** `{AA}/{BB}`는 갱신 때마다 삭제·재생성되므로 안에 두면 사라진다.

### 2.2 절차 — 한 스크립트, 두 모드

`sync.sh`는 실행 위치를 보고 스스로 모드를 정한다. 점검 로직은 한 벌이라 양쪽이 공유한다.

```bash
# ① 개발 장비 — 태그를 낸 뒤, push 하기 전에
cd {BB} && bash scripts/sync.sh v0.2
#   태그의 archive 를 임시로 풀어 §2.3 점검만 하고 지운다

# ② 운영 환경 — {AA} 루트에서. 최초든 갱신이든 같은 명령이고 멱등하다
cd {AA}
git clone <remote> .staging/{BB}           # 최초 1회만
bash .staging/{BB}/scripts/sync.sh v0.2    # 매번
```

**같은 점검이 두 번 도는 것이 설계다.** ①에서 걸리면 태그를 다시 내면 그만이고,
②에서 걸리면 이미 운영 환경까지 간 뒤라 사이클을 하나 버린다. ①을 잊어도 ②가 막아주지만,
비싸게 막는다.

이식 모드(②)가 하는 일 (전문은 **부록 A**):

1. `.staging/.gitignore`(`*`)와 `{AA}`의 `.gitignore`의 `.staging/` 항목을 보장한다
2. 태그를 fetch·checkout 한다. 태그가 없으면 목록을 보여주고 중단한다 — 태그 없이 실행하지 않는다
3. `{AA}/{BB}`를 `git archive`로 통째 교체하고 `{BB}/VERSION`을 기록한다
4. `outputs/`·`notebooks/`를 만든다
5. 설정 파일을 쓰는 프로젝트라면(`{BB}/configs/env.example.yaml` 존재) `{AA}/configs/env.yaml`을
   **없을 때만** 복사한다. 있으면 손대지 않고 **example 에만 있는 키를 경고**한다.
   CLI 인자만 쓰는 프로젝트에서는 이 단계를 건너뛴다.

   **설정은 언제나 `{AA}` 에 둔다.** `{AA}/{BB}` 는 갱신 때마다 삭제·재생성되므로
   거기 둔 설정은 다음 sync 에 조용히 사라진다 — 화면에는 `{AA}/configs` 쪽이
   "그대로 둡니다"로 찍혀서 자기 파일이 지켜진 줄 알게 된다. 그래서 경로를 전부
   절대 경로로 말하고, 사본 안에 설정이 남아 있으면 사라졌다고 알린다
6. §2.3 점검을 수행한다. 걸리면 **사본을 지우고** 실패로 끝낸다
7. 다음에 실행할 명령을 출력한다

**일부러 하지 않는 일** — `pip install`(공용 venv라 사람이 `--dry-run`을 보고 판단해야 한다),
`env.yaml` 덮어쓰기(운영 실값이 든 유일한 파일), venv 생성, git commit.

`git archive`를 쓰는 이유가 세 겹으로 맞물린다.

1. **`.git`이 결과물에 없다** — 외부 원격 주소도 히스토리도 AA로 넘어가지 않는다 (C6)
2. **추적된 파일만 나온다** — 데이터·산출물·로컬 설정이 넘어갈 경로가 원천적으로 없다
3. **`{AA}/{BB}`에 git이 없으니 운영 환경에서 고칠 수 없다** — C2가 규칙이 아니라 물리적 상태가 된다

`{AA}/{BB}`가 운영 저장소에 커밋되는 것은 목적이다. 결과 파일이 반출 안 되는 상황에서
"어떤 코드로 돌렸는지"가 운영 환경에 남는 유일한 형태다. 그래서 **태그 없이 실행하지 않는다.**

> AA를 zip이나 파일 복사로 외부에 전달하는 절차가 있다면, 중계 clone을 AA 밖(`~/src/{BB}`)으로 옮긴다.
> git은 중첩 저장소 내부를 추적하지 않지만 zip·백업 도구는 `.git`을 통째로 가져간다.

### 2.3 이식 표면 — 무엇이 운영 환경에 도착하는가

두 파일이 경계를 정한다.

- **`.gitignore`** — 저장소에 애초에 들어오지 못하게 한다 (데이터·산출물·로컬 설정)
- **`.gitattributes`의 `export-ignore`** — 저장소에는 두되 archive 결과에서 뺀다 (개발 전용)

`git archive`는 커밋 히스토리를 담지 않으므로 작성자·이메일·커밋 메시지는 애초에 넘어가지
않는다. 파일 단위 선별과 파일 내용만 관리하면 된다.

```gitattributes
tools/                export-ignore    # LLM·외부 API 를 쓰는 개발 보조 도구
requirements-dev.txt  export-ignore
docs/insights/        export-ignore    # 운영 환경에서 가져온 인사이트 기록
.claude/              export-ignore    # AI 도구 설정
CLAUDE.md             export-ignore
.github/              export-ignore
.gitattributes        export-ignore    # ← 자기 자신도 뺀다
```

마지막 줄이 요점이다. `.gitattributes`가 남으면 "무언가를 제외했다"는 사실이 목록째 드러난다.
자기 자신을 대상에 넣으면 `{AA}`에서는 그 파일이 보이지 않는다.

`sync.sh`가 양쪽 모드에서 확인하는 항목:

| 항목 | 잡는 것 |
|---|---|
| 금지 파일·디렉터리 | `tools/`, `.claude/`, `CLAUDE.md`, `requirements-dev.txt`, `.gitattributes`, `.git` 잔존 |
| API import | `anthropic`·`openai` — 운영 환경에서 죽을 의존 (C8) |
| `requirements.txt` | 개발 전용 패키지 혼입 |
| 개인 머신 절대 경로 | `/Users/…`, `/home/…` — §1.3 위반이기도 하다 |
| 이메일·커밋 트레일러 | 소스에 박힌 개인 이메일, `Co-Authored-By` |
| 데이터 확장자 | `.csv`, `.parquet` 등 |

#### `{BB}`의 `.gitignore`

```gitignore
*.csv
*.tsv
*.parquet
*.xlsx
*.pkl
*.npy
*.npz
*.h5
*.feather
*.sqlite*
data/
outputs/
logs/
configs/env.yaml
.env
notebooks/local/
__pycache__/
*.py[cod]
.venv/
*.egg-info/
.pytest_cache/
```

이 점검을 손으로 할 필요는 없다. `sync.sh`가 두 모드 모두에서 자동으로 한다.

---

## 3. 검증 쪽 — 콘솔이 리포트다

### 3.1 실행

```bash
source <기존 venv>/bin/activate
pip install --dry-run -r {BB}/requirements.txt && pip check   # 충돌 먼저 확인
pip install -r {BB}/requirements.txt

python {BB}/src/run.py --dry-run                        # ① 합성 데이터 스모크
python {BB}/src/run.py --data <실데이터> --limit 1000    # ② 계약 확인
python {BB}/src/run.py --data <실데이터>                 # ③ 전체
```

①에서 실패하면 환경 문제고, ②에서 나오는 계약 위반이 첫 사이클의 실제 수확이다.
계약이 깨끗해진 뒤에 ③으로 간다 — 틀린 계약 위에서 뽑은 성능 숫자는 믿을 수 없다.

- **`PYTHONPATH`도 설치도 필요 없다.** `python {BB}/src/run.py`는 `sys.path[0]`을 `{BB}/src`로
  잡으므로 `<pkg>`가 그대로 import된다. 공용 venv에 우리 패키지를 남기지 않고,
  `{AA}/{BB}` 통째 교체가 무연산이 된다
- 진입점만 `src/run.py`로 두고 나머지는 `src/<pkg>/` 안에 넣는다. `src/`를 평평하게 쓰면
  `contracts`·`report` 같은 흔한 이름이 최상위 모듈이 되어 서드파티를 가릴 수 있다
- 상대 경로는 전부 **cwd(`{AA}`) 기준**으로 해석된다 — `{BB}`가 어디 있든 `outputs/`가 맞아떨어진다
- **`--upgrade`·`--force-reinstall` 금지.** 남의 환경을 조용히 깨뜨리고 되돌릴 수 없다.
  충돌은 인사이트로 가지고 나와 개발 장비에서 `requirements.txt`를 고친다
- 개발 장비도 Python 3.14를 쓴다 — 3.14 wheel이 없는 패키지를 미리 거르기 위함

### 3.2 리포트

C4에 의해 화면이 유일한 출력이다. 성공·실패 무관하게 마지막에 이 블록을 찍는다.

```
================ RUN SUMMARY ================
version   : v0.4 (a1b2c3d)
args      : --data /mnt/real/2026-08.parquet --threshold 0.5 --limit 1000
input     : 1,204,331 rows x 27 cols
contract  : 24 ok / 3 MISMATCH
  - grade      : unexpected values {'Z', '?'}
  - amount     : dtype float expected, got str
  - joined_at  : 12,004 nulls but nullable=False
metrics   : auc 0.8123 / precision@100 0.4410
runtime   : 412s, peak 6.2GB
status    : OK
=============================================
```

- **실행 인자를 그대로 한 줄 찍는다.** 반출이 안 되므로 "그때 뭘로 돌렸는지"가 셸 히스토리에만
  남으면 사라진다. 이 한 줄만 옮겨 적으면 재현된다
- **계약 위반은 사람이 그대로 옮겨 적을 수 있게 적는다.** `validation failed` 같은 메시지는
  이 규격에서 결함이다 — 옮겨 적을 것이 없기 때문이다. 이 출력이 포맷 회수의 주 채널이다
- 한 줄에 한 항목, 80자 이내. 지표 이름은 사이클 사이에 바뀌지 않는다
- 실데이터의 개별 값·식별자는 찍지 않는다 (C3)
- 노트북 탐색은 자유롭되 `{AA}/notebooks/`에 두고, **로직은 노트북에 살지 않는다.**
  노트북은 반출되지 않으므로 그 사이클이 끝나면 사라진다

---

## 4. 되돌리기

사람 머릿속을 거치는 유일한 고리라 가장 잘 샌다. **실험 직후**,
`{BB}/docs/insights/YYYY-MM-DD-<tag>.md`에 적는다.

기록할 것 → 반영할 곳:

| 운영 환경에서 본 것 | 개발 장비에서 고칠 곳 |
|---|---|
| 계약 위반 메시지 (전문) | `contracts.py` — `note`에 확인된 사실도 남긴다 |
| 새로 터진 데이터 사고 유형 | `synth.py` — 그 유형을 생성 가능하게 |
| "코드 고치고 싶었던 순간" | `src/run.py` — 그 값을 CLI 인자로 승격 |
| 의존성 충돌 메시지 | `requirements.txt` |
| 지표·규모·런타임 | 다음 실험 설계 |

반영이 끝나면 새 태그를 내고 다시 이식한다.

---

## 하지 말 것

1. 운영 환경에서 `{AA}/{BB}` 코드 수정
2. BB에 데이터 파일 커밋 (테스트 픽스처 포함)
3. `{AA}/{BB}`에 `.git` 두기 / `{AA}/{BB}` 안에 운영 설정·노트북 두기
4. 태그 없이 운영 환경에서 실행
5. 운영 환경에서 `pip --upgrade` / BB 패키지를 venv에 설치
6. `{BB}/src/` 안에서 LLM·외부 API 호출 (C8)
7. 리포트에 실데이터 값 찍기
8. 운영 환경 탐색을 인사이트 기록 없이 끝내기

---

## 부록 A. `scripts/sync.sh`

아래는 `scripts/sync.sh` 전문이며 pre-commit 훅이 자동으로 동기화한다.
저장소를 clone 한 뒤 한 번만 `git config core.hooksPath scripts/hooks` 를 실행해두면 된다.

<!-- BEGIN sync.sh -->
```bash
#!/usr/bin/env bash
#
# {BB} → {AA} 이식 스크립트. 실행 위치에 따라 두 모드로 동작한다.
#
#   개발 ({BB} 저장소 루트에서)   bash scripts/sync.sh <tag>
#       → 태그의 archive 를 임시로 풀어 점검만 한다. push 전에 돌린다
#
#   운영 ({AA} 루트에서)           bash .staging/{BB}/scripts/sync.sh <tag>
#       → 이식(교체·VERSION·디렉터리)을 하고 같은 점검을 한 번 더 한다
#
# {AA}·{BB} 의 실제 이름은 프로젝트마다 다르다. {BB} 는 이 스크립트의 위치에서 유도하고
# ({AA}/.staging/{BB}/scripts/sync.sh), {AA} 는 실행 위치(cwd)라 이름이 필요 없다.
#
# 이 스크립트는 실행 도중 checkout 으로 자기 자신을 바꿀 수 있으므로, 본문 전체를
# main() 으로 감싸 파싱이 먼저 끝나게 한다. (bash 는 스크립트를 조금씩 읽어가며 실행한다)

set -euo pipefail

SELF_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
REPO_DIR=$(dirname "$SELF_DIR")
NAME=$(basename "$REPO_DIR")
STAGING=".staging/$NAME"
DEST="$NAME"

DATA_EXT='csv|tsv|parquet|xlsx|xls|pkl|pickle|npy|npz|h5|feather|sqlite'
# 이식 표면에 남아서는 안 되는 것들 — .gitattributes 의 export-ignore 로 빼야 한다
FORBIDDEN=(.git .gitattributes .github .claude .cursor .mcp.json CLAUDE.md AGENTS.md
           tools requirements-dev.txt docs/insights)

log()  { printf '[sync] %s\n' "$*"; }
warn() { printf '[sync] ⚠ %s\n' "$*" >&2; }
die()  { printf '[sync] ✗ %s\n' "$*" >&2; exit 1; }

# YAML 의 키를 점 경로로 뽑는다. 2칸 들여쓰기 매핑을 가정하며, 새 키 알림 용도의 근사치다.
yaml_keys() {
  awk '
    /^[[:space:]]*#/ { next }
    /^[[:space:]]*$/ { next }
    /^[[:space:]]*-/ { next }
    {
      line = $0
      match(line, /^[[:space:]]*/); indent = RLENGTH
      sub(/^[[:space:]]*/, "", line)
      if (line ~ /^[A-Za-z0-9_.-]+[[:space:]]*:/) {
        key = line; sub(/[[:space:]]*:.*/, "", key)
        lvl = int(indent / 2)
        path[lvl] = key
        out = path[0]
        for (i = 1; i <= lvl; i++) out = out "." path[i]
        print out
      }
    }
  ' "$1" | sort -u
}

# 트리 안을 훑되 자기 자신(scripts/sync.sh)은 제외하고, 경로를 트리 기준 상대 경로로 줄인다.
scan() {  # scan <dir> <regex>
  grep -rInE "$2" "$1" 2>/dev/null | grep -v "^$1/scripts/sync\.sh:" | sed "s|^$1/||" || true
}

# 이식 표면 점검. 인자로 받은 디렉터리는 "실제로 운영 환경에 도착할 것"이어야 한다.
# 두 모드가 이 함수를 공유하므로 검사 기준이 한 벌뿐이다.
inspect_tree() {
  local d="$1" bad=0 hits f

  for f in "${FORBIDDEN[@]}"; do
    if [[ -e "$d/$f" ]]; then
      warn "이식 표면에 남아있음: $f   → .gitattributes 에 '$f export-ignore' 추가"
      bad=1
    fi
  done

  hits=$(find "$d" -type f | grep -Ei "\.($DATA_EXT)\$" | sed "s|^$d/||" || true)
  if [[ -n "$hits" ]]; then
    warn "데이터 파일:"; printf '%s\n' "$hits" >&2; bad=1
  fi

  hits=$(scan "$d" '^[[:space:]]*(import|from)[[:space:]]+(anthropic|openai)')
  if [[ -n "$hits" ]]; then
    warn "운영 환경에서 쓸 수 없는 API import (C8):"; printf '%s\n' "$hits" >&2; bad=1
  fi

  if [[ -f "$d/requirements.txt" ]]; then
    hits=$(grep -inE '^[[:space:]]*(anthropic|openai|claude)' "$d/requirements.txt" || true)
    if [[ -n "$hits" ]]; then
      warn "requirements.txt 에 개발 전용 패키지:"; printf '%s\n' "$hits" >&2; bad=1
    fi
  fi

  hits=$(scan "$d" '/(Users|home)/[A-Za-z0-9._-]+')
  if [[ -n "$hits" ]]; then
    warn "개인 머신 절대 경로 (§1.3 위반이기도 하다 — 인자로 빼라):"; printf '%s\n' "$hits" >&2; bad=1
  fi

  hits=$(scan "$d" 'Co-Authored-By|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
  if [[ -n "$hits" ]]; then
    warn "이메일·커밋 트레일러:"; printf '%s\n' "$hits" >&2; bad=1
  fi

  return $bad
}

require_tag() {
  local repo="$1" tag="$2"
  if ! git -C "$repo" rev-parse -q --verify "refs/tags/$tag^{}" >/dev/null; then
    warn "태그 '$tag' 가 없습니다. 사용 가능한 태그:"
    git -C "$repo" tag -l >&2
    exit 1
  fi
}

# 개발 장비 — archive 결과를 임시로 풀어 점검만 한다
preflight() {
  local tag="$1"
  require_tag "$REPO_DIR" "$tag"
  local sha; sha=$(git -C "$REPO_DIR" rev-parse --short "$tag^{}")
  local tmp; tmp=$(mktemp -d)
  # 값을 지금 확정해 둔다 — 함수를 벗어난 뒤 트랩이 돌 때 $tmp 는 이미 사라지고 없다
  trap "rm -rf '$tmp'" EXIT

  git -C "$REPO_DIR" archive "$tag" | tar -x -C "$tmp"
  log "preflight: $tag ($sha) — $(find "$tmp" -type f | wc -l | tr -d ' ') files"

  if ! inspect_tree "$tmp"; then
    die "preflight FAILED — 위 항목을 고치고 태그를 다시 내세요"
  fi
  log "preflight: OK"
  cat <<EOF

next:
  git push origin $tag
EOF
}

# 운영 환경 — 이식하고 같은 점검을 한 번 더 한다
sync_into_aa() {
  local tag="$1"

  [[ -f .staging/.gitignore ]] || printf '*\n' > .staging/.gitignore
  if [[ ! -f .gitignore ]] || ! grep -qx '\.staging/' .gitignore; then
    printf '.staging/\n' >> .gitignore
    log "$(basename "$(pwd -P)")/.gitignore 에 .staging/ 추가"
  fi

  git -C "$STAGING" fetch --tags --quiet
  require_tag "$STAGING" "$tag"
  git -C "$STAGING" -c advice.detachedHead=false checkout --quiet "$tag"
  local sha; sha=$(git -C "$STAGING" rev-parse --short HEAD)

  [[ ! -e "$DEST/.git" ]] || die "$DEST 에 .git 이 있습니다. clone 인지 확인하고 직접 정리하세요 (자동 삭제하지 않습니다)"
  rm -rf "$DEST"; mkdir -p "$DEST"
  git -C "$STAGING" archive "$tag" | tar -x -C "$DEST"
  printf '%s %s\n' "$tag" "$sha" > "$DEST/VERSION"
  log "tag $tag ($sha)"
  log "$DEST/ replaced ($(find "$DEST" -type f | wc -l | tr -d ' ') files)"

  mkdir -p outputs notebooks

  # 설정은 **언제나 {AA} 에 둔다.** $DEST 안에 두면 다음 교체 때 통째로 지워진다.
  # 경로를 상대로 찍으면 어느 configs 인지 알 수 없어서 - 사본에도 configs/ 가
  # 있다 - 전부 절대 경로로 말한다.
  local ex="$DEST/configs/env.example.yaml" here; here=$(pwd -P)
  if [[ -f "$ex" ]]; then
    mkdir -p configs
    if [[ ! -f configs/env.yaml ]]; then
      # 옛 이름을 쓰던 작업 폴더가 있다. 그대로 두면 채워둔 실값이 무시된 채
      # 빈 env.yaml 로 돌아서, 설정을 고쳤는데 안 먹는 상태가 된다.
      # 자동으로 옮기지 않는다 - 실값이 든 유일한 파일이라 사람이 확인해야 한다.
      if [[ -f configs/local.yaml ]]; then
        warn "$here/configs/local.yaml 이 있습니다. 이름이 env.yaml 로 바뀌었습니다:"
        warn "    mv $here/configs/local.yaml $here/configs/env.yaml"
      fi
      cp "$ex" configs/env.yaml
      log "생성 — 운영 실값을 채우세요: $here/configs/env.yaml"
    else
      log "그대로 둡니다 (실값이 든 파일): $here/configs/env.yaml"
      local missing
      missing=$(comm -23 <(yaml_keys "$ex") <(yaml_keys configs/env.yaml) | tr '\n' ' ')
      missing="${missing%"${missing##*[! ]}"}"
      [[ -z "$missing" ]] || warn "env.example.yaml 에만 있는 키: $missing"
    fi
    # 사본 안에 설정을 만들어 둔 경우. 방금 지워졌다는 사실을 알려야 한다 -
    # 안 그러면 다음 실행에서 "설정을 고쳤는데 안 먹는" 상태가 된다.
    if [[ -f "$DEST/configs/env.yaml" ]]; then
      warn "$DEST/configs/env.yaml 은 방금 교체로 사라졌습니다."
      warn "    설정은 $here/configs/env.yaml 에 둡니다."
    fi
  fi

  if ! inspect_tree "$DEST"; then
    rm -rf "$DEST"   # 실수로 커밋되는 것을 막기 위해 사본을 남기지 않는다
    die "점검 FAILED — $DEST 를 제거했습니다. 개발 장비에서 고치고 새 태그를 내세요"
  fi
  log "점검: OK"

  local entry="$DEST/src/run.py"
  if [[ ! -f "$entry" ]]; then
    local pys=("$DEST"/src/*.py)
    if [[ ${#pys[@]} -eq 1 && -f "${pys[0]}" ]]; then entry="${pys[0]}"; else entry="$DEST/src/<entry>.py"; fi
  fi

  cat <<EOF

next:  (전부 $here 에서 — 설정도 실행도 여기가 기준이다)
  source <venv>/bin/activate
  pip install --dry-run -r $DEST/requirements.txt && pip check
  python $entry --dry-run
EOF
}

main() {
  local tag="${1:-}" cwd; cwd=$(pwd -P)
  [[ -n "$tag" ]] || die "태그를 지정하세요:  bash <이 스크립트> <tag>"

  if [[ "$REPO_DIR" == "$cwd" ]]; then
    preflight "$tag"
  elif [[ "$REPO_DIR" == "$cwd/.staging/$NAME" ]]; then
    [[ -d "$STAGING/.git" ]] || die "$STAGING 이 clone 이 아닙니다 (.git 없음)"
    sync_into_aa "$tag"
  else
    die "실행 위치가 맞지 않습니다. 둘 중 하나여야 합니다:
       개발: cd <{BB} 저장소> && bash scripts/sync.sh <tag>
       운영: cd <{AA}>        && bash .staging/$NAME/scripts/sync.sh <tag>
     현재 cwd: $cwd"
  fi
}

main "$@"
```
<!-- END sync.sh -->
