# 코드 구현 규격

**기능 개발은 개발 장비에서, 검증은 운영 장비에서.** 이 분리를 코드 구조로 강제하기 위한 규격이다.

| 기호 | 의미 |
|---|---|
| `{BB}` | 개발 장비의 저장소. 로직의 단일 진실 원본 |
| `{AA}` | 운영 장비의 작업 폴더. 운영 git으로 관리됨 |
| `<pkg>` | `{BB}`가 제공하는 패키지 이름. **기본은 `core`** 이고, 바꾸려면 `adopt.sh` 의 둘째 인자로 준다 |

세 이름 모두 프로젝트마다 다른 실제 문자열이며, 경로로 등장할 때 `{AA}`·`{BB}`로 적는다.
`sync.sh`는 `{BB}`를 자기 위치(`{AA}/.staging/{BB}/scripts/sync.sh`)에서 유도하고 `{AA}`는
실행 위치이므로, **어느 쪽도 설정하거나 수정할 필요가 없다.**

```
[개발 장비] 구현 ──이식──▶ [운영 환경] 실험 ──인사이트──▶ [개발 장비] 개선 ──▶ …
```

**이 저장소 자체가 규격을 만족하는 스캐폴드다.** 복사한 뒤
`src/core/schema.py`의 `INPUT_SCHEMA`를 갈아끼우면 시작이다.

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
| C9 | **사본은 평범한 프로그램으로 보여야 한다.** 밖에서 개발해 이식했다는 사실이 `{AA}`를 보는 사람에게 드러나지 않는다 |

아래 규칙은 전부 이 제약에서 따라나온 것이다. 규칙이 불편하면 제약이 아직 유효한지 먼저 확인하라.

---

## 1. 개발 쪽 — 데이터 없이 짠다

### 1.1 데이터 스키마를 파일 하나에 둔다

C5에 의해 운영 환경에서 회수되는 정보의 절반이 "입력 포맷"이다. 그 정보가 도착할 지점이
한 곳이어야 반영이 쉽다. `src/<pkg>/schema.py`가 유일한 출처다.

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

- `src/<pkg>/synth.py`의 `generate(n, seed=0)`이 스키마를 읽어 런타임에 만든다
- 결정론적: 같은 seed는 같은 데이터
- 테스트 픽스처도 파일로 두지 않는다. 테스트는 `generate()`를 호출한다
  (스키마가 바뀌면 테스트 데이터가 따라 바뀌는 이득도 있다)

가짜 데이터가 보증하는 것은 "코드가 끝까지 돈다"까지다. 실제 분포에서의 성능,
실규모에서의 메모리·시간, 스키마가 실데이터를 맞게 기술하는지는 **운영 환경에서만 알 수 있다.**

### 1.3 바뀔 만한 값은 전부 코드 밖으로

C2 때문에 운영 환경에서는 한 줄도 못 고친다. 아래는 코드에 박지 않고 **CLI 인자로 받는다.**

- 파일·디렉터리 경로, 접속 정보
- 컬럼명·테이블명·도메인 코드값 → 스키마로
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

### 1.5 기능이 여럿일 때

여기까지는 `pipeline.py` 하나를 가정했다. 판정 규칙이 열 개인 프로젝트처럼 **서로 독립인
기능이 여럿**이면 그 가정이 깨진다 — 한 파일에 다 넣으면 어느 규칙이 깨졌는지 분리되지 않고,
규칙 하나를 고치는 동안 나머지 아홉이 같이 흔들린다.

**기능이 하나면 `pipeline.py` 그대로 둔다.** 아래 배치는 둘째 기능이 생기는 순간에 옮긴다.

```
src/<pkg>/
  schema.py  load.py  report.py  synth.py   ← 공유. 기능이 늘어도 하나뿐이다
  __main__.py                                   ← 진입점도 하나뿐이다
  pipeline.py                                   ← 기능들을 불러 합치는 자리가 된다
  features/
    template/__init__.py   ← 복사 원본. 저장소에 둔다
    <기능>/__init__.py     ← 기능마다 폴더 하나. process_data 를 노출한다
    <기능>/patterns.py     ← 그 기능만 쓰는 것들은 그 폴더 안에
```

**단순한 기능도 폴더를 준다.** 파일 하나로 시작해 커질 때 폴더로 올리는 쪽이 덜 번거로워
보이지만, 그 승격에 **조용하지 않은 대신 매번 걸리는 함정**이 하나 붙는다 — 파일이 폴더로
들어가면서 깊이가 한 칸 깊어지므로 상대 import 의 점을 하나 더 붙여야 한다
(`from ..schema` → `from ...schema`). 안 고치면 `ModuleNotFoundError` 로 죽는다.
**처음부터 폴더면 깊이가 고정이라 그 순간이 없다.** 기능 열 개짜리 프로젝트에서는 그 순간이
열 번 온다.

모양이 하나뿐이라는 것 자체도 값이다 — 어떤 기능은 파일이고 어떤 기능은 폴더면, 새 기능을
만드는 사람이 **먼저 어느 쪽인지 정해야 한다.** 정할 것이 없으면 틀릴 것도 없다.

**기능 폴더에는 판정 로직만 둔다.** 인자 파싱·적재·리포트를 기능마다 복사하면 기능별로 따로
실행하게 되고, 그러면 §3.2의 "리포트 한 장"이 깨진다. 진입점은 끝까지 하나다.

**`pipeline.py` 는 조율자가 된다.** 기능 파일들을 import 해서 결과를 합치는 일만 한다.
기능 목록이 여기 있는 것이 요점이다 — `pipeline.py` 는 프로젝트가 고치는 파일이고,
공유 코드(`schema` · `load` · `report` · `synth`)와 진입점은 기능이 늘어도 손대지 않는다.

```python
from .features import aa, bb

def process_data(rows: list[dict]) -> dict:
    metrics = {"rows": f"{len(rows):,}"}
    for feature in (aa, bb):
        metrics.update(feature.process_data(rows))
    return metrics
```

**지표 이름에는 기능 이름을 접두어로 붙인다.** 결과가 한 리포트에 모이므로(§3.2), 두 기능이
같은 지표 이름을 쓰면 `update()` 에서 **조용히 덮어쓴다** — 화면에는 마지막 기능의 숫자만
남고 덮였다는 사실은 어디에도 뜨지 않는다. 그러면 §3.2가 지키려는 회수 채널이 거짓을 준다.

**복사 원본을 저장소에 둔다** (`features/template/`). 시작할 때 기능이 몇 개가 될지 모르기
때문이다 — 둘인 줄 알고 시작해 여섯이 되는 일이 실제로 있었다. 원본이 없으면 일곱 번째를
만드는 사람이 기존 기능 하나를 골라 베끼는데, 그 하나에 묻은 그 기능만의 사정까지 따라간다.

> `adopt.sh`는 `src/core/` 아래를 통째로 훑으므로 하위 폴더가 늘어도 그대로 동작한다.
> 새 기능은 폴더를 하나 만드는 일이지 스캐폴드를 고치는 일이 아니다.

---

## 2. 이식 — `.git`도 데이터도 넘기지 않는다

### 2.1 배치

```
{BB}/                      {AA}/
  README.md                  {BB}/                 ← 소스 사본. .git 없음. 통째 교체
  TODO.md                    configs/env.yaml      ← 운영 실값
  todo/                      outputs/              ← 산출물
  docs/                      notebooks/            ← 운영 환경 탐색
  docs/insights/       ✗     run_*.sh              ← 실행 스크립트 (§3.0)
  configs/env.example.yaml   .staging/{BB}/        ← 이식 중계 clone (무시됨)
  requirements.txt           .staging/.gitignore   ← 내용은 `*` 한 줄
  requirements-dev.txt ✗
  scripts/sync.sh
  src/run.py
  src/<pkg>/
  tools/               ✗
  tests/

✗ = .gitattributes 의 export-ignore. 개발 장비 전용이며 archive 결과에 포함되지 않는다
```

문서는 **성격으로 나눈다.** 둘 다 반입된다 — 저쪽에서 봐야 하는 것들이다.

| | 무엇 |
|---|---|
| `TODO.md` | 첫 실행 전에 `{AA}` 에서 **만들어야 하는 것**의 목록 (§3.0) |
| `todo/` | 그것들의 규격. 만드는 쪽이 읽는다 |
| `docs/` | 이 프로그램이 **어떻게 도는지**. 결과를 읽는 쪽이 읽는다 |
| `docs/insights/` ✗ | 저쪽에서 **가져온** 기록 (§4). 되돌아가지 않는다 |

**운영 자산은 `{AA}/{BB}` 밖에 둔다.** `{AA}/{BB}`는 갱신 때마다 삭제·재생성되므로 안에 두면 사라진다.

### 2.2 절차 — 한 스크립트, 두 모드

`sync.sh`는 실행 위치를 보고 스스로 모드를 정한다. 점검 로직은 한 벌이라 양쪽이 공유한다.

```bash
# ① 개발 장비 — 태그를 낸 뒤, push 하기 전에
cd {BB} && bash scripts/sync.sh v0.2
#   태그의 archive 를 임시로 풀어 §2.3 점검만 하고 지운다

# ② 운영 환경 — {AA} 루트에서. 최초든 갱신이든 같은 명령이고 멱등하다
cd {AA}
git clone <remote> .staging/app            # 최초 1회만
bash .staging/app/scripts/sync.sh v0.2     # 매번
```

**clone 할 디렉터리 이름이 사본 폴더 이름을 정한다.** `sync.sh` 는 자기 위치
(`{AA}/.staging/<이름>/scripts/sync.sh`)에서 그 이름을 유도해 `{AA}/<이름>` 에 푼다.
`{BB}` 의 실제 저장소 이름과 같을 필요가 없다.

> **작업 폴더와 같은 이름을 쓰지 마라.** `{AA}` 가 `.../DD` 인데 `.staging/DD` 로
> clone 하면 사본이 `{AA}/DD/DD` 가 된다. 동작은 정상이지만 `cd` 를 두 번 해야 하고,
> 상대 경로를 어느 `DD` 에서 푸는지 사람이 헷갈린다 — 사본 안에서 실행하면
> `outputs/` 가 사본 안에 생기고 다음 교체 때 사라진다.

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

   **안내 문구에서 `{AA}` 는 실행 위치로 잡는다. 사본의 부모가 아니다.**
   `sync.sh` 는 `{AA}/{BB}` 로 놓지만(§2.4), 사본을 손으로 옮겨 `{AA}/tools/vendor/{BB}`
   처럼 둘 수 있다. 그러면 부모는 `{AA}` 가 아니라 중간 폴더라, "거기에 설정을
   만들고 거기서 실행하라"는 있지도 않은 자리를 가리키는 안내가 된다.
   프로그램이 아는 것은 사본의 위치뿐이므로(`VERSION` 표식) 부모를 `{AA}` 로
   추측하지 말고, cwd 와 사본의 **상대 경로**로 명령을 만든다(`os.path.relpath`)
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
# 개발 장비 전용 도구 (LLM·외부 API 를 쓴다)
tools/                export-ignore
requirements-dev.txt  export-ignore

# 운영 환경에서 가져온 인사이트 기록
docs/insights/        export-ignore

# AI 도구 설정
.claude/              export-ignore
CLAUDE.md             export-ignore
.github/              export-ignore

# 자기 자신도 뺀다
.gitattributes        export-ignore
```

마지막 줄이 요점이다. `.gitattributes`가 남으면 "무언가를 제외했다"는 사실이 목록째 드러난다.
자기 자신을 대상에 넣으면 `{AA}`에서는 그 파일이 보이지 않는다.

#### C9 — 어휘도 이식 표면이다

**파일 단위 제외만으로는 부족하다.** 코드는 가야 하는데 주석과 독스트링에 워크플로가
박혀 있으면 그대로 넘어간다. 독스트링 한 줄에 `(규격 §1.1)` 이 붙어 있으면 충분히 드러난다.

두 겹으로 막는다.

- **통째로 빼는 것** — 워크플로를 설명하는 문서와 스크립트. `README.md`,
  `scripts/sync.sh`(사본에서 한 번도 불리지 않는다 — 운영 모드는 `.staging` 쪽에서
  실행하고, 사본 위치에서 돌리면 오히려 거부한다), 이식 표면을 검사하는 테스트
- **어휘를 바꾸는 것** — 남는 파일에서 *개발 장비·운영 환경·이식·규격 §·`{AA}`·`{BB}`* 를
  걷어낸다. 근거는 이 문서에 남고, 사본에는 규율의 **결과**만 남는다

| 사본에서 | 대신 |
|---|---|
| 운영 환경에서 확인된 사실 | 실제 데이터에서 확인된 사실 |
| 파일 반출이 안 되는 환경이라 | 콘솔이 유일한 출력이라 |
| `(규격 §3.2)` | (지운다) |

`sync.sh` 가 이 어휘를 기계적으로 검사한다. 사람 눈에만 맡기면 다시 샌다 — 이 문서의
다른 규칙들과 같은 이유다.

##### 도메인 어휘가 겹칠 때 — `scripts/sync-allow.txt`

**낱말 검사는 워크플로 어휘와 도메인 어휘를 구별하지 못한다.** 사내 문서 반출 심사를
판정하는 프로그램에서 "외부 반출은 보안심의를 거친다" 는 합성 데이터의 본문이고, 그
프로그램이 **판정하는 대상**이지 워크플로가 아니다. 그런 프로젝트에서 이 검사는 영원히
빨간불이고, 그러면 태그를 낼 수 없다 — 지키라고 만든 규칙이 이식 자체를 막는다.

프로젝트가 `scripts/sync-allow.txt` 에 문구를 적으면 그 문구가 든 줄만 넘어간다.
가드가 조용히 넓어지지 않도록 세 가지를 건다.

| | 왜 |
|---|---|
| **고정 문구다. 정규식이 아니다** | `.*` 한 줄로 검사를 통째로 끌 수 없다 |
| **여덟 바이트 미만은 거부한다** | 짧은 조각은 뜻하지 않은 줄까지 연다. 한글 세 글자·영문 여덟 글자쯤이다. 글자가 아니라 바이트로 재는 것은, 글자로 재려면 UTF-8 로케일이 있어야 하고 그게 없는 환경에서는 조용히 바이트로 떨어져 **가드가 약해지는 쪽으로** 틀리기 때문이다 |
| **넘긴 줄 수를 매번 화면에 찍는다** | 조용히 넘기면 목록이 자라도 아무도 모르고, 그때부터 이 검사는 통과 도장일 뿐이다 |

파일이 없는 것이 기본이다. **예외를 적기 전에 문장을 고칠 수 없는지 먼저 본다** — 코드
주석과 독스트링은 거의 언제나 다시 쓸 수 있고, 예외가 맞는 경우는 판정 대상인 **데이터**
쪽이다. 이 파일은 `export-ignore` 로 빠진다.


> **줄 끝 주석을 쓰지 마라.** git 은 `.gitattributes` 에서 그걸 지원하지 않는다. 패턴 뒤의 모든
> 토큰을 속성 이름으로 읽으므로 `tools/ export-ignore  # 설명` 은 `# 은 올바른 속성 이름이
> 아니다` 경고 한 줄만 내고 **그 줄이 통째로 무시된다.** 설명은 위처럼 앞 줄에 단다.

**아직 없는 파일도 미리 적어둔다.** 나중에 하나 생겼을 때 이 줄이 없으면 조용히 운영 환경으로
넘어가고, 그건 사본을 지우고 태그를 다시 내야 하는 사고다.

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
configs/*.yaml
!configs/env.example.yaml
.env
notebooks/local/
__pycache__/
*.py[cod]
.venv/
*.egg-info/
.pytest_cache/
```

**막을 것을 이름으로 나열하지 말고, 통째로 막고 예외를 적는다.** 위의 `configs/` 두 줄이
그 형태다. 이름을 하나씩 적으면 오타 한 번에 무시가 풀리고, 그때 **조용히 커밋된다** —
실제로 그렇게 `configs/local.example.yaml` 이 저장소에 들어간 적이 있다. 예외를 명시하는
쪽은 새 파일이 생겨도 기본이 "막힘"이라 사고가 나지 않는다.

이 점검을 손으로 할 필요는 없다. `sync.sh`가 두 모드 모두에서 자동으로 한다.

---

## 3. 검증 쪽 — 콘솔이 리포트다

### 3.0 먼저 만들어야 하는 것 — `{BB}/TODO.md`

**이식만으로 돌지 않는다.** C1·C2 때문에 `{AA}` 쪽에서 만들어야 하는 것이 남고,
그게 무엇인지는 저쪽에서 알 방법이 없다 — 물어볼 곳도 인터넷도 없다. 그래서
`{BB}/TODO.md` 에 목록을 두고 함께 이식한다.

이 규격으로 도는 프로젝트라면 **최소한 이 셋**이 남는다.

| | 왜 남나 |
|---|---|
| `configs/env.yaml` 채우기 | 운영 실값은 `{BB}` 에 둘 수 없다 (C3) |
| 실행 스크립트 | 인자를 하나 빠뜨려도 프로그램은 기본값으로 돈다. 종료 코드를 사람이 눈으로 보면 등급 차이가 묻힌다 |
| `{AA}/.gitignore` | `sync.sh` 는 `.staging/` 만 넣는다. 나머지(캐시·데이터)는 그대로 두면 운영 git 에 커밋된다 |

**항목마다 "이 프로젝트의 사정인가, 어느 프로젝트나 해당하는가"를 갈라 적는다.**
이 목록은 다음 프로젝트에서 본보기가 되는데, 구분이 없으면 안 해도 될 일을 하거나
반대로 프로젝트 고유의 것을 빠뜨린다.

**`TODO.md` 는 방법을 베끼지 않는다.** 만드는 법은 `todo/` 의 규격에 두고 가리키기만
한다 — 베끼면 둘이 갈라지고, 갈라진 쪽을 보고 만들면 어긋난 것이 나온다.

목록이 비면 그건 그것대로 정보다. 다 채운 뒤에 §3.1 로 간다.

### 3.1 실행

```bash
source <기존 venv>/bin/activate
pip install --dry-run -r {BB}/requirements.txt && pip check   # 충돌 먼저 확인
pip install -r {BB}/requirements.txt

python {BB}/src/run.py --dry-run                        # ① 합성 데이터 스모크
python {BB}/src/run.py --data <실데이터> --limit 1000    # ② 스키마 확인
./run_daily.sh <실데이터>                                # ③ 전체 — 스크립트로
```

①에서 실패하면 환경 문제고, ②에서 나오는 스키마 위반이 첫 사이클의 실제 수확이다.
스키마가 깨끗해진 뒤에 ③으로 간다 — 틀린 스키마 위에서 뽑은 성능 숫자는 믿을 수 없다.

①②는 손으로 친다. 한 번씩만 돌리고 화면을 보는 것이 목적이라 그렇다. **③부터는
§3.0 의 실행 스크립트로 한다** — 반복되는 실행에서 인자를 빠뜨리면 프로그램은
기본값으로 돌아버리고, 그건 실패가 아니라 다른 결과로 나타난다.

- **`PYTHONPATH`도 설치도 필요 없다.** `python {BB}/src/run.py`는 `sys.path[0]`을 `{BB}/src`로
  잡으므로 `<pkg>`가 그대로 import된다. 공용 venv에 우리 패키지를 남기지 않고,
  `{AA}/{BB}` 통째 교체가 무연산이 된다
- 진입점만 `src/run.py`로 두고 나머지는 `src/<pkg>/` 안에 넣는다. `src/`를 평평하게 쓰면
  `schema`·`report` 같은 흔한 이름이 최상위 모듈이 되어 서드파티를 가릴 수 있다
- 상대 경로는 전부 **cwd(`{AA}`) 기준**으로 해석된다 — `{BB}`가 어디 있든 `outputs/`가 맞아떨어진다.
  화면에 찍는 안내 문구도 같은 규칙을 따른다 (§2.2 ⑤)
- **`--upgrade`·`--force-reinstall` 금지.** 남의 환경을 조용히 깨뜨리고 되돌릴 수 없다.
  충돌은 인사이트로 가지고 나와 개발 장비에서 `requirements.txt`를 고친다
- 개발 장비도 Python 3.14를 쓴다 — 3.14 wheel이 없는 패키지를 미리 거르기 위함

**venv 를 설정에 적었으면 프로그램이 갈아탄다.** 공용 venv 가 여럿인 환경에서는 activate 를
잊거나 다른 것을 켠 채로 도는 일이 흔하고, 그건 실패가 아니라 **다른 결과**로 나타난다.
`configs/env.yaml` 의 `paths.venv` 에 경로가 있으면 진입점이 그 파이썬으로 `os.execv` 해서
같은 명령을 다시 시작한다 — 인자와 cwd 가 보존되고, 아직 아무 계산도 하지 않았으므로 잃을
것이 없다. 경로에 파이썬이 없으면 **어떤 계산도 하기 전에** 종료 코드 `2` 로 죽는다.

> 적어만 두고 쓰지 않으면 "설정했는데 무시된다"가 된다. **설정 파일의 값이 아무것도 바꾸지
> 않는 것은 그 자체로 결함이다.**

### 3.2 리포트

C4에 의해 화면이 유일한 출력이다. 성공·실패 무관하게 마지막에 이 블록을 찍는다.

```
================ RUN SUMMARY ================
version   : v0.4 (a1b2c3d)
args      : --data /mnt/real/2026-08.parquet --threshold 0.5 --limit 1000
input     : 1,204,331 rows x 27 cols
schema    : 24 ok / 3 MISMATCH
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
- **스키마 위반은 사람이 그대로 옮겨 적을 수 있게 적는다.** `validation failed` 같은 메시지는
  이 규격에서 결함이다 — 옮겨 적을 것이 없기 때문이다. 이 출력이 포맷 회수의 주 채널이다
- **`version` 은 절대 빈칸이 아니다.** 모르면 `unversioned` 라고 적는다. 빈칸은 옮겨 적을 때
  통째로 빠지고, 빠진 줄은 없었던 것이 된다
- 한 줄에 한 항목, **80칸** 이내. 글자 수가 아니라 **표시 폭**이다 — 한글·한자는 터미널에서
  두 칸을 쓰므로 `len()` 으로 자르면 정렬이 깨지고 글자가 중간에서 끊긴다
  (`unicodedata.east_asian_width(ch) in "WF"` 면 2)
- 지표 이름은 사이클 사이에 바뀌지 않는다
- 실데이터의 개별 값·식별자는 찍지 않는다 (C3)
- 노트북 탐색은 자유롭되 `{AA}/notebooks/`에 두고, **로직은 노트북에 살지 않는다.**
  노트북은 반출되지 않으므로 그 사이클이 끝나면 사라진다

**안 쓰는 필드의 어긋남은 위반이 아니라 노트다.** 파이프라인이 읽지 않는 필드가 스키마와
달라도 판정은 멀쩡하다. 그걸 `MISMATCH` 로 올리면 매 실행마다 같은 줄이 뜨고, **사람은
곧 그 줄 자체를 안 보게 된다.** `schema` 줄은 "판정이 틀렸을 수 있다"는 뜻이어야 한다 —
회수 채널을 지키는 규칙이지 편의가 아니다.

#### 기능이 여럿이어도 리포트는 한 장

§1.5의 배치로 기능이 여럿이 되어도 **한 번 실행에 RUN SUMMARY 는 하나**고, 그 안에 전 기능의
결과가 들어온다.

```
schema    : 24 ok / 3 MISMATCH
features  :
  language_mixing        1,204 / 1,204,331
  sensitive_info            37 / 1,204,331
  answer_truncated       9,881 / 1,204,331
```

기능마다 진입점을 두어 열 번 실행하면 블록이 열 장 나온다. C4 때문에 그 열 장을 합칠 방법이
없다 — 파일로 못 꺼내므로 **합치는 일이 사람 머릿속에서 일어난다.** 그리고 열 번은 각각 다른
실행이라 `--limit` 이나 seed 가 하나만 달라도 나란히 놓을 수 없는 숫자가 되는데, **그 사실이
화면에 드러나지도 않는다.** 한 장이면 `args` 한 줄이 열 기능 전부를 덮는다.

행 단위 산출물이 목적일 때 — 한 행에 판정 열 개를 붙이는 식 — 이유가 하나 더 붙는다.
따로 뽑으면 조인할 대상이 파일인데, 그 파일을 반출할 수 없다.

> 개발 중 한 기능만 보려는 `--only <feature>` 같은 인자는 둬도 된다. 그건 보조 진입점이고,
> **기본 실행은 전부 한 번에 도는 것**이어야 한다.

#### 종료 코드와 출력 스트림

리포트를 사람만 읽는 것이 아니다. §3.0 의 실행 스크립트가 분기하려면 계약이 필요하다.

| 코드 | 뜻 | 스크립트가 할 일 |
|---|---|---|
| `0` | 정상 | 다음으로 |
| `1` | **돌았지만 온전치 않다** (스키마 위반, 볼 것이 없음) | 재시도해도 같다. 사람이 본다 |
| `2` | **시작도 못 했다** (인자 누락, 파일 없음, 설정 오류) | 고치고 다시 돌린다 |

`1` 과 `2` 를 가르는 기준은 **"계산을 시작했나"** 다. 종료 코드를 사람이 눈으로만 보면
이 등급 차이가 묻히고, 스크립트는 둘을 같게 취급하게 된다.

**RUN SUMMARY 는 stdout, 진행 상황은 stderr.** 요약이 stderr 로 새면 `> log.txt` 로 남긴
파일이 비어 있다. 로그로 남길 것과 사람이 보며 판단할 것을 가르는 선이다.

---

## 4. 되돌리기

사람 머릿속을 거치는 유일한 고리라 가장 잘 샌다. **실험 직후**,
`{BB}/docs/insights/YYYY-MM-DD-<tag>.md`에 적는다.

기록할 것 → 반영할 곳:

| 운영 환경에서 본 것 | 개발 장비에서 고칠 곳 |
|---|---|
| 스키마 위반 메시지 (전문) | `schema.py` — `note`에 확인된 사실도 남긴다 |
| 새로 터진 데이터 사고 유형 | `synth.py` — 그 유형을 생성 가능하게 |
| "코드 고치고 싶었던 순간" | `src/run.py` — 그 값을 CLI 인자로 승격 |
| 의존성 충돌 메시지 | `requirements.txt` |
| 지표·규모·런타임 | 다음 실험 설계 |

**반영의 종착점은 문서가 아니라 테스트다.** 인사이트 파일은 *포착* 장치다 — 실험 직후,
아직 무엇이 중요한지 모르는 상태로 본 것을 다 적는 자리라 문서가 맞다. 하지만 거기 남겨두면
다음 사이클에 아무도 다시 읽지 않는다. **규칙으로 굳은 것은 테스트로 옮긴다.**

```python
def test_prev_question_accepts_the_shape_the_real_log_uses():
    """운영 환경 로그의 prev_question 은 list 다 (2026-09-01, 16,141건)."""
```

관찰 날짜와 규모를 독스트링에 남기면, 그 테스트가 **깨질 때** 무엇을 근거로 만든 규칙이었는지가
같이 나온다. 마크다운은 썩어도 조용하지만 테스트는 썩으면 빨간다 — §4가 "사람 머릿속을 거치는
유일한 고리라 가장 잘 샌다"고 한 문제를 실제로 막는 것은 이쪽이다.

반영이 끝나면 새 태그를 내고 다시 이식한다.

---

## 5. 스캐폴드로 되돌리기 — 도메인 어휘를 넣지 않는다

고리가 한 겹 더 있다. §4가 *운영 환경 → 프로젝트*라면, 이번엔 *프로젝트 → 이 스캐폴드*다.
프로젝트를 하나 짜보면 규격이 가정하지 않았던 것이 드러나고(§1.5가 그렇게 생겼다), 그것은
여기로 돌아와야 한다.

**돌아오는 것은 규칙이지 코드가 아니다.** 판단 기준은 하나다 — *다음 프로젝트가 쓸 수 있나.*

한 번 샜다. 판정 규칙 열 개짜리 프로젝트를 짜면서 그 프로젝트의 `Tagger` 기반 클래스를
스캐폴드의 공유 코드에 넣었고, 공유 `report()` 가 `tags` 인자를 받게 만들었다. 판정 태그라는
개념이 없는 다음 프로젝트에게 그 둘은 **의미 없는 클래스와 늘 비어 있는 인자**다. 같은 커밋에서
`src/core/` 를 그 프로젝트에 맞는 이름으로 갈아엎는 바람에 `adopt.sh` 가 찾을 디렉터리가
사라져 채택 절차 자체가 죽었다 — 한 프로젝트의 사정을 범용 쪽에 옮기면 이렇게 번진다.

| 프로젝트가 부르는 이름 | 스캐폴드가 아는 것 |
|---|---|
| 태거 · 판정 규칙 · 검출기 | 기능 (`features/<feature>/pipeline.py`) |
| `Tagger.tag()` | `pipeline.py` 가 노출하는 함수. 이름은 프로젝트가 정한다 |
| 태그 개수 | 기능 개수 |

**C9와 같은 모양의 규칙이다.** C9는 사본에서 워크플로 어휘를 걷어냈고, 이건 스캐폴드에서
도메인 어휘를 걷어낸다. 방향만 반대다.

**도메인이 필요한 설명은 `examples/` 에 둔다.** 거기서는 주문이든 태그든 마음껏 구체적이어도
된다 — 예제는 하나의 완결된 프로젝트를 보여주는 자리다. 다만 스캐폴드 본문이 특정 프로젝트를
**유일한** 예제로 가리키지는 않는다. 그 프로젝트가 사라지면 설명이 통째로 비고, 그 프로젝트의
도메인을 모르는 사람에게는 처음부터 읽히지 않는다.

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
9. `TODO.md` 없이 이식하기 — 저쪽에서 무엇이 남았는지 알 방법이 없다 (§3.0)
10. `.gitattributes` 에 줄 끝 주석 달기 — 그 줄이 통째로 무시되고, **조용히** 무시된다 (§2.3)
11. 막을 것을 `.gitignore` 에 이름으로 나열하기 — 오타 한 번에 무시가 풀린다. allowlist 로 쓴다 (§2.3)
12. 기능마다 진입점 두기 — 리포트가 여러 장으로 갈라지고, C4 때문에 합칠 수 없다 (§3.2)
13. 스캐폴드의 공유 코드에 한 프로젝트의 도메인 개념 넣기 — 다음 프로젝트에겐 죽은 코드다 (§5)

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

# 자기 본문의 지문. checkout 이 자신을 갈아치웠는지 보는 데 쓴다.
sum_self() { cksum < "${BASH_SOURCE[0]}"; }

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

# C9 예외. scripts/sync-allow.txt 의 문구를 담고 있는 줄을 걸러낸다.
#
#   - **고정 문구다. 정규식이 아니다** (grep -F). `.*` 로 전부 열 수 없다
#   - 여덟 바이트 미만은 거부한다. 짧은 조각은 뜻하지 않은 줄까지 열어버린다.
#     글자가 아니라 바이트로 세는 것은 awk 의 length() 가 로케일 없이는 바이트를
#     세기 때문이다. 글자로 재려면 UTF-8 로케일이 있어야 하는데, 없는 환경에서
#     조용히 바이트로 떨어지면 가드가 **약해지는** 쪽으로 틀린다. 바이트 수는
#     언제나 글자 수 이상이라 이쪽으로 세면 틀려도 엄격해지는 쪽이다
#     (여덟 바이트 = 한글 세 글자 · 영문 여덟 글자)
#   - 파일이 없으면 아무것도 안 거른다. 예외를 쓰지 않는 프로젝트가 기본이다
#
# 이 파일은 프로젝트가 만든다. 스캐폴드는 자리만 안다.
c9_allowed() {
  local f="$REPO_DIR/scripts/sync-allow.txt" pat
  if [[ ! -f "$f" ]]; then cat; return; fi
  pat=$(grep -vE '^[[:space:]]*(#|$)' "$f" || true)
  local short
  short=$(printf '%s\n' "$pat" | awk 'length($0) > 0 && length($0) < 8')
  if [[ -n "$short" ]]; then
    warn "sync-allow.txt 에 너무 짧은 문구가 있어 무시한다 (8바이트 이상만):"
    printf '      %s\n' "$short" >&2
  fi
  pat=$(printf '%s\n' "$pat" | awk 'length($0) >= 8')
  if [[ -z "$pat" ]]; then cat; return; fi
  grep -vF -f <(printf '%s\n' "$pat") || true
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

  # RFC 2606 이 실제로 존재할 수 없게 예약해 둔 도메인은 뺀다. 민감정보를 찾는
  # 프로그램이라면 이메일 꼴의 표본이 있어야 자기 규칙을 시험할 수 있는데, 전부
  # 막으면 그 표본을 둘 자리가 없어져 규칙이 죽었는지 알 수 없게 된다.
  # 줄이 아니라 주소 단위로 지운 뒤 다시 본다 — 줄로 거르면 예약 주소와 실제
  # 주소가 한 줄에 있을 때 둘 다 놓친다.
  hits=$(scan "$d" 'Co-Authored-By|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' | awk '
    {
      line = $0
      gsub(/[A-Za-z0-9._%+-]+@(example\.(com|net|org)|[A-Za-z0-9.-]*\.(example|invalid|test))/, "", line)
      if (line ~ /Co-Authored-By/ || line ~ /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z][A-Za-z]/) print
    }')
  if [[ -n "$hits" ]]; then
    warn "이메일·커밋 트레일러:"; printf '%s\n' "$hits" >&2; bad=1
  fi

  # 사본은 평범한 프로그램으로 보여야 한다 (C9). 코드 주석·독스트링에 워크플로
  # 어휘가 남으면 파일 단위 제외로는 못 뺀다 — 코드는 가야 하기 때문이다.
  #
  # 도메인 어휘가 이 목록과 겹치는 프로젝트가 있다. 문서 반출 심사를 다루는
  # 프로그램의 합성 데이터에는 "외부 반출은 보안심의를 거친다" 가 들어가고,
  # 그건 워크플로가 아니라 그 프로그램이 판정하는 대상이다. 그런 프로젝트는
  # scripts/sync-allow.txt 에 문구를 적어 그 줄만 뺀다 (형식은 아래 c9_allowed).
  local raw exempt
  raw=$(scan "$d" '개발 장비|운영 장비|운영 환경|이식|반입|스캐폴드|규격|인사이트|반출|\{AA\}|\{BB\}|규격 §|sync\.sh|\.staging')
  hits=$(printf '%s' "$raw" | c9_allowed)
  exempt=$(( $(printf '%s' "$raw" | grep -c . || true) - $(printf '%s' "$hits" | grep -c . || true) ))
  # 예외로 넘긴 줄은 **반드시 화면에 센다.** 조용히 넘기면 목록이 자라도 아무도
  # 모르고, 그때부터 이 점검은 통과 도장일 뿐이다.
  [[ $exempt -gt 0 ]] && log "C9: $exempt 줄을 예외로 넘김 (scripts/sync-allow.txt)"
  if [[ -n "$hits" ]]; then
    warn "사본에 워크플로 어휘가 남아있음 (C9):"; printf '%s\n' "$hits" >&2; bad=1
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

  # 이 스크립트가 만드는 것은 이 스크립트가 막는다. env.yaml 은 실값을 채우라고
  # 만들어 놓고 무시 목록에 안 넣으면, 채운 순간 그대로 커밋된다 - 사람이 잊으면
  # 끝인 자리를 사람에게 맡기지 않는다.
  #
  # env.example.yaml 은 일부러 뺀다. 실값이 없고, 어떤 키가 있는지 남는 편이 낫다.
  local ig
  # venv 는 여기서 만들지 않지만, 작업 폴더에 만드는 사람이 많고 한 번 커밋되면
  # 수천 파일이 히스토리에 박힌다. 되돌리기 가장 비싼 사고라 미리 막는다.
  for ig in '.staging/' 'configs/env.yaml' 'outputs/' 'notebooks/' \
            '.venv/' 'venv/' '__pycache__/'; do
    if [[ ! -f .gitignore ]] || ! grep -qxF "$ig" .gitignore; then
      printf '%s\n' "$ig" >> .gitignore
      log "$(basename "$(pwd -P)")/.gitignore 에 $ig 추가"
    fi
  done

  git -C "$STAGING" fetch --tags --quiet
  require_tag "$STAGING" "$tag"

  # checkout 은 이 스크립트 자신도 갈아치운다. bash 는 이미 읽어들인 옛 본문으로
  # 계속 돌기 때문에, 그대로 두면 "한 번 더 실행해야 새 동작이 나오는" 상태가 된다.
  # 바뀌었으면 새 본문으로 다시 시작한다 - exec 라 이 프로세스가 대체되고 인자와
  # cwd 가 보존된다. 아직 아무것도 바꾸지 않았으므로 잃을 것이 없다.
  local before; before=$(sum_self)
  git -C "$STAGING" -c advice.detachedHead=false checkout --quiet "$tag"
  if [[ -z "${SYNC_RESTARTED:-}" && "$(sum_self)" != "$before" ]]; then
    log "스크립트가 $tag 의 것으로 바뀌었습니다. 새 본문으로 다시 시작합니다"
    SYNC_RESTARTED=1 exec bash "${BASH_SOURCE[0]}" "$tag"
  fi

  local sha; sha=$(git -C "$STAGING" rev-parse --short HEAD)

  [[ ! -e "$DEST/.git" ]] || die "$DEST 에 .git 이 있습니다. clone 인지 확인하고 직접 정리하세요 (자동 삭제하지 않습니다)"

  # 교체 전에 봐 둔다. rm -rf 뒤에 물으면 언제나 없다고 나온다.
  local had_config=0
  [[ -f "$DEST/configs/env.yaml" ]] && had_config=1

  rm -rf "$DEST"; mkdir -p "$DEST"
  git -C "$STAGING" archive "$tag" | tar -x -C "$DEST"
  printf '%s %s\n' "$tag" "$sha" > "$DEST/VERSION"
  log "tag $tag ($sha)"
  log "$DEST/ replaced ($(find "$DEST" -type f | wc -l | tr -d ' ') files)"

  mkdir -p outputs notebooks

  # 설정은 **언제나 {AA} 에 둔다.** $DEST 안에 두면 다음 교체 때 통째로 지워진다.
  # 경로를 상대로 찍으면 어느 configs 인지 알 수 없어서 - 사본에도 configs/ 가
  # 있다 - 전부 절대 경로로 말한다.
  # 예시는 중계 clone 에서 읽는다. 사본에는 configs/ 가 아예 없다 — 런타임에
  # 아무도 안 읽는 폴더라, 두면 "여기 채우면 되나" 하는 오해만 만든다.
  # clone 은 방금 이 태그로 checkout 했으므로 버전도 맞다.
  local ex="$STAGING/configs/env.example.yaml" here; here=$(pwd -P)
  if [[ -f "$ex" ]]; then
    mkdir -p configs

    # 예시를 실값 파일 옆에 둔다. 키 설명이 이 파일 주석에 있어서, 채우는 사람이
    # 사본 안까지 들어가지 않아도 된다.
    #
    # **매번 덮어쓴다.** 실값이 없는 파일이라 잃을 것이 없고, 안 덮으면 저장소에
    # 키가 늘어도 여기 것은 낡은 채 남아 "예시에 없는 키" 를 찾게 만든다.
    cp "$ex" configs/env.example.yaml

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
      log "  키 설명은 옆의 env.example.yaml 에 있습니다"
    else
      log "그대로 둡니다 (실값이 든 파일): $here/configs/env.yaml"
      local missing
      missing=$(comm -23 <(yaml_keys "$ex") <(yaml_keys configs/env.yaml) | tr '\n' ' ')
      missing="${missing%"${missing##*[! ]}"}"
      [[ -z "$missing" ]] || warn "env.example.yaml 에만 있는 키: $missing"
    fi
    # 사본 안에 설정을 만들어 둔 경우. 방금 지워졌다는 사실을 알려야 한다 -
    # 안 그러면 다음 실행에서 "설정을 고쳤는데 안 먹는" 상태가 된다.
    if [[ "$had_config" == 1 ]]; then
      warn "$DEST/configs/env.yaml 이 있었는데 방금 교체로 사라졌습니다."
      warn "    설정은 언제나 $here/configs/env.yaml 에 둡니다."
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
