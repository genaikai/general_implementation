# 코드 구현 규격

**기능 개발은 본 머신에서, 검증은 사내 머신에서.** 이 분리를 코드 구조로 강제하기 위한 규격이다.

| 기호 | 의미 |
|---|---|
| **BB** | 본 머신의 저장소. 로직의 단일 진실 원본 |
| **AA** | 사내 머신의 작업 폴더. 사내 git으로 관리됨 |
| `<pkg>` | BB가 제공하는 패키지 이름 (프로젝트마다 고유하게) |

```
[본 머신] 구현 ──이식──▶ [사내] 실험 ──인사이트──▶ [본 머신] 개선 ──▶ …
```

## 제약

| ID | 제약 |
|---|---|
| C1 | 이식은 BB → AA 단방향. 사내에서 push 불가 |
| C2 | 따라서 사내에서 코드 수정 불가. 수정은 본 머신에서만 |
| C3 | 사내 실데이터는 밖으로 나올 수 없다 |
| C4 | 파일·문서 반출 불가. 결과 파일도 플롯도 로그도 못 가져온다 |
| C5 | 회수 가능한 것은 **입력 데이터의 포맷**과 **사람의 인사이트** 둘뿐 |
| C6 | AA는 사내 git 관리 대상. 가짜 데이터와 BB의 `.git`이 AA에 올라가면 안 된다 |
| C7 | 사내는 Python 3.14 + **기존 venv**(공용일 수 있음). PyPI 설치는 가능 |

아래 규칙은 전부 이 제약에서 따라나온 것이다. 규칙이 불편하면 제약이 아직 유효한지 먼저 확인하라.

---

## 1. 개발 쪽 — 데이터 없이 짠다

### 1.1 데이터 계약을 파일 하나에 둔다

C5에 의해 사내에서 회수되는 정보의 절반이 "입력 포맷"이다. 그 정보가 도착할 지점이
한 곳이어야 반영이 쉽다. `src/<pkg>/contracts.py`가 유일한 출처다.

```python
@dataclass(frozen=True)
class Field:
    name: str
    dtype: str                    # "int" | "float" | "str" | "datetime" | "category"
    nullable: bool
    allowed: tuple | None = None  # 카테고리 허용값
    rng: tuple | None = None      # (min, max)
    note: str = ""                # 사내에서 확인된 사실을 적는 자리

INPUT_SCHEMA = (
    Field("customer_id", "str",   False, note="영문+숫자 12자리"),
    Field("amount",      "float", True,  rng=(0, 1e12)),
    Field("grade",       "category", True, allowed=("A", "B", "C")),
)
```

구조만 적는다. 실제 값·분포·식별 가능한 코드값 목록은 적지 않는다 (C3).

### 1.2 가짜 데이터는 **파일이 아니라 코드**다

C6 때문이다. 가짜 데이터가 파일로 BB에 있으면 AA를 통해 사내 저장소로 흘러간다.
`.gitignore`는 `git add -f` 한 번에 뚫리지만, **없는 파일은 올라갈 수 없다.**

- `src/<pkg>/synth.py`의 `generate(n, seed=0)`이 계약을 읽어 런타임에 만든다
- 결정론적: 같은 seed는 같은 데이터
- 테스트 픽스처도 파일로 두지 않는다. 테스트는 `generate()`를 호출한다
  (계약이 바뀌면 테스트 데이터가 따라 바뀌는 이득도 있다)

가짜 데이터가 보증하는 것은 "코드가 끝까지 돈다"까지다. 실제 분포에서의 성능,
실규모에서의 메모리·시간, 계약이 실데이터를 맞게 기술하는지는 **사내에서만 알 수 있다.**

### 1.3 바뀔 만한 값은 전부 설정으로

C2 때문에 사내에서는 한 줄도 못 고친다. 아래는 코드에 박지 않는다.

- 파일·디렉터리 경로, 접속 정보
- 컬럼명·테이블명·도메인 코드값 → 계약으로
- 임계값·하이퍼파라미터·날짜 범위·샘플 수·워커 수

`configs/example.yaml`(커밋)에 모든 키가 등장하고, 사내 실값은 `AA/configs/local.yaml`에 둔다.
설정은 시작 즉시 검증하고 누락 시 **계산 전에** 죽는다 — 30분 뒤에 키 하나로 죽으면 사이클 하나를 버린다.

> **사내에서 "코드 한 줄만 고치면 되는데" 하는 순간이 오면, 그건 이 규칙이 이미 깨졌다는 신호다.**
> 고치지 말고 "이 값이 설정에 없었다"를 인사이트로 가지고 나온다.

---

## 2. 이식 — `.git`도 데이터도 넘기지 않는다

### 2.1 배치

```
BB/                       AA/
  pyproject.toml            BB/                  ← BB 소스 사본. .git 없음. 통째 교체
  requirements.txt          configs/local.yaml   ← 사내 실값
  configs/example.yaml      outputs/             ← 산출물
  scripts/sync.sh           notebooks/           ← 사내 탐색
  src/<pkg>/                .staging/BB/         ← 이식 중계 clone (AA에서 무시)
  tests/                    .staging/.gitignore  ← 내용은 `*` 한 줄
```

**사내 자산은 `AA/BB` 밖에 둔다.** `AA/BB`는 갱신 때마다 삭제·재생성되므로 안에 두면 사라진다.

### 2.2 절차

```bash
# 최초 1회
cd AA && git clone <BB-remote> .staging/BB && printf '*\n' > .staging/.gitignore

# 갱신 (= 사내에서의 "pull") — scripts/sync.sh 가 담고 있다
git -C .staging/BB fetch --tags && git -C .staging/BB checkout <tag>
rm -rf BB && mkdir BB
git -C .staging/BB archive <tag> | tar -x -C BB
git -C .staging/BB rev-parse --short HEAD > BB/VERSION
```

`git archive`를 쓰는 이유가 세 겹으로 맞물린다.

1. **`.git`이 결과물에 없다** — 외부 원격 주소도 히스토리도 AA로 넘어가지 않는다 (C6)
2. **추적된 파일만 나온다** — 데이터·산출물·로컬 설정이 넘어갈 경로가 원천적으로 없다
3. **`AA/BB`에 git이 없으니 사내에서 고칠 수 없다** — C2가 규칙이 아니라 물리적 상태가 된다

`AA/BB`가 사내 저장소에 커밋되는 것은 목적이다. 결과 파일이 반출 안 되는 상황에서
"어떤 코드로 돌렸는지"가 사내에 남는 유일한 형태다. 그래서 **태그 없이 실행하지 않는다.**

> AA를 zip이나 파일 복사로 외부에 전달하는 절차가 있다면, 중계 clone을 AA 밖(`~/src/BB`)으로 옮긴다.
> git은 중첩 저장소 내부를 추적하지 않지만 zip·백업 도구는 `.git`을 통째로 가져간다.

### 2.3 `.gitignore` (BB) — 부록이 아니라 조항이다

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
configs/local.yaml
.env
notebooks/local/
__pycache__/
*.py[cod]
.venv/
*.egg-info/
.pytest_cache/
```

커밋 전 점검 — 아무것도 출력되지 않아야 한다:

```bash
git ls-files | grep -E '\.(csv|tsv|parquet|xlsx|pkl|npy|npz|h5|feather|sqlite)$|^\.staging'
```

---

## 3. 검증 쪽 — 콘솔이 리포트다

### 3.1 실행

```bash
source <기존 venv>/bin/activate
pip install --dry-run -r BB/requirements.txt && pip check   # 충돌 먼저 확인
pip install -r BB/requirements.txt
PYTHONPATH=BB/src python -m <pkg> --config configs/local.yaml --dry-run   # 합성 데이터 스모크
PYTHONPATH=BB/src python -m <pkg> --config configs/local.yaml
```

- **BB 패키지를 venv에 설치하지 않는다.** `PYTHONPATH`로만 붙인다 — 공용 venv를 오염시키지 않고,
  `AA/BB` 통째 교체가 무연산이 된다
- **`--upgrade`·`--force-reinstall` 금지.** 남의 환경을 조용히 깨뜨리고 되돌릴 수 없다.
  충돌은 인사이트로 가지고 나와 본 머신에서 `requirements.txt`를 고친다
- 본 머신도 Python 3.14를 쓴다 — 3.14 wheel이 없는 패키지를 미리 거르기 위함

### 3.2 리포트

C4에 의해 화면이 유일한 출력이다. 성공·실패 무관하게 마지막에 이 블록을 찍는다.

```
================ RUN SUMMARY ================
version   : v0.4 (a1b2c3d)
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

- **계약 위반은 사람이 그대로 옮겨 적을 수 있게 적는다.** `validation failed` 같은 메시지는
  이 규격에서 결함이다 — 옮겨 적을 것이 없기 때문이다. 이 출력이 포맷 회수의 주 채널이다
- 한 줄에 한 항목, 80자 이내. 지표 이름은 사이클 사이에 바뀌지 않는다
- 실데이터의 개별 값·식별자는 찍지 않는다 (C3)
- 노트북 탐색은 자유롭되 `AA/notebooks/`에 두고, **로직은 노트북에 살지 않는다.**
  노트북은 반출되지 않으므로 그 사이클이 끝나면 사라진다

---

## 4. 되돌리기

사람 머릿속을 거치는 유일한 고리라 가장 잘 샌다. **실험 직후**,
`BB/docs/insights/YYYY-MM-DD-<tag>.md`에 적는다.

기록할 것 → 반영할 곳:

| 사내에서 본 것 | 본 머신에서 고칠 곳 |
|---|---|
| 계약 위반 메시지 (전문) | `contracts.py` — `note`에 확인된 사실도 남긴다 |
| 새로 터진 데이터 사고 유형 | `synth.py` — 그 유형을 생성 가능하게 |
| "코드 고치고 싶었던 순간" | `configs/example.yaml` — 그 값을 설정으로 승격 |
| 의존성 충돌 메시지 | `requirements.txt` |
| 지표·규모·런타임 | 다음 실험 설계 |

반영이 끝나면 새 태그를 내고 다시 이식한다.

---

## 하지 말 것

1. 사내에서 `AA/BB` 코드 수정
2. BB에 데이터 파일 커밋 (테스트 픽스처 포함)
3. `AA/BB`에 `.git` 두기 / `AA/BB` 안에 사내 설정·노트북 두기
4. 태그 없이 사내에서 실행
5. 사내에서 `pip --upgrade` / BB 패키지를 venv에 설치
6. 리포트에 실데이터 값 찍기
7. 사내 탐색을 인사이트 기록 없이 끝내기
