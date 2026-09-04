# 코드 구현 규격 — 참조 스캐폴드

**기능 개발은 개발 장비에서, 검증은 운영 장비에서.** 두 곳을 오갈 수 없는 환경에서
그 분리를 사람의 규율이 아니라 코드 구조로 강제하기 위한 스캐폴드다.

```
[개발 장비] 구현 ──이식──▶ [운영 환경] 실험 ──인사이트──▶ [개발 장비] 개선 ──▶ …
```

풀려는 문제는 이렇다. 운영 데이터는 밖으로 못 나오고, 결과 파일도 못 가져오고,
저쪽에서는 코드를 고칠 수도 LLM을 쓸 수도 없다. 그래서 **데이터 없이 짜고, 통째로
보내고, 화면만 보고, 사람이 배운 것만 들고 나온다.**

| | |
|---|---|
| `{BB}` | 개발 장비의 저장소 — **이 저장소** |
| `{AA}` | 운영 장비의 작업 폴더 |

---

## 시작하기 (개발 장비)

```bash
git clone <이 저장소> my-project && cd my-project
rm -rf .git && git init          # 히스토리는 가져가지 않는다

git grep -l mypkg                # 패키지 이름을 바꾼다
git mv src/mypkg src/<이름>       #   src/run.py, tests/ 안의 import 도 함께

$EDITOR src/<이름>/contracts.py   # INPUT_SCHEMA 를 실제 입력 형태로 갈아끼운다
```

`INPUT_SCHEMA` 하나만 고치면 합성 데이터·검증·리포트가 전부 따라온다. 그게 이 구조의
요점이다 — **입력 형태에 대해 아는 것이 코드 안 한 곳에만 있다.**

```bash
python -m pip install -r requirements-dev.txt
python src/run.py --dry-run                    # 합성 데이터로 전 구간 스모크
python src/run.py --dry-run --adversarial      # 계약 위반을 일부러 섞어서
env -u ANTHROPIC_API_KEY -u OPENAI_API_KEY python -m pytest
```

마지막 줄이 중요하다. **API 키를 지운 채 테스트가 전부 통과해야** 운영 환경에서 돌 수
있다는 것이 기계적으로 증명된다.

## 무엇이 어디 있나

| | | 이식 |
|---|---|:--:|
| `src/run.py` | 진입점. CLI 인자, 종료 코드 | ✔ |
| `src/<pkg>/contracts.py` | **입력 계약.** 이 프로젝트에서 제일 먼저 고칠 파일 | ✔ |
| `src/<pkg>/synth.py` | 합성 데이터. 계약을 읽어 런타임에 만든다 (파일이 아니다) | ✔ |
| `src/<pkg>/report.py` | RUN SUMMARY 블록. 화면이 유일한 출력이다 | ✔ |
| `tests/` | 규격 규칙을 못박은 테스트도 여기 있다 | ✔ |
| `scripts/sync.sh` | 이식 스크립트. 개발/운영 두 모드 | ✔ |
| `requirements.txt` | 운영 실행용. 스캐폴드는 표준 라이브러리만 쓴다 | ✔ |
| `tools/` | 개발 보조 도구 (LLM·외부 API 를 쓴다) | ✗ |
| `requirements-dev.txt` | 개발 장비 전용 의존성 | ✗ |
| `docs/insights/` | 운영 환경에서 가져온 기록 | ✗ |
| `IMPLEMENTATION_SPEC.md` | **규격 전문.** 아래 모든 규칙의 근거와 이유 | ✗ |

✗ 는 `.gitattributes` 의 `export-ignore` — 저장소에는 있지만 `{AA}` 로 넘어가지 않는다.
**규격 문서 자체도 넘어가지 않는다.** 그래서 저쪽에서 필요한 것은 이 README 와
`TODO.md` 에 있어야 한다.

## 이식하기

```bash
git tag v0.2
bash scripts/sync.sh v0.2        # ① push 전 점검 — 넘어가면 안 되는 것이 없는지
git push origin main --tags
```

`sync.sh` 가 태그의 `git archive` 를 임시로 풀어서 확인한다 — 금지 파일, 운영 환경에서
죽을 `anthropic`·`openai` import, 개인 머신 절대 경로, 이메일, 데이터 확장자.
**걸리면 태그를 다시 낸다.** 여기서 막는 것이 저쪽에서 막는 것보다 훨씬 싸다.

`{AA}` 쪽에서는:

```bash
cd {AA}
git clone <원격> .staging/{BB}           # 최초 1회만
bash .staging/{BB}/scripts/sync.sh v0.2  # 매번. 멱등하다
```

`git archive` 라서 **`.git` 이 결과물에 없다.** 히스토리도 원격 주소도 넘어가지 않고,
저쪽에 git 이 없으니 코드를 고칠 수 없는 것이 규칙이 아니라 물리적 상태가 된다.

## 운영 환경에서 실행

```bash
source <기존 venv>/bin/activate
pip install --dry-run -r {BB}/requirements.txt && pip check    # 충돌 먼저
pip install -r {BB}/requirements.txt

python {BB}/src/run.py --dry-run                     # ① 환경 확인
python {BB}/src/run.py --data <실데이터> --limit 1000 # ② 계약 확인 ← 첫 사이클의 수확
python {BB}/src/run.py --data <실데이터>              # ③ 전체
```

①에서 실패하면 환경 문제다. **②에서 나오는 계약 위반이 실제로 가져갈 것이다** —
틀린 계약 위에서 뽑은 성능 숫자는 믿을 수 없으니 ②가 깨끗해진 뒤에 ③으로 간다.

`PYTHONPATH` 도 설치도 필요 없다. `--upgrade`·`--force-reinstall` 은 **금지** — 공용
venv 라 남의 환경을 조용히 깨뜨리고 되돌릴 수 없다.

### 화면이 리포트다

```
================ RUN SUMMARY ================
version   : v0.2 (c9bd85a)
args      : --data /mnt/real/2026-08.csv --limit 1000
input     : 1,204,331 rows x 27 cols
contract  : 24 ok / 3 MISMATCH
  - grade      : unexpected values {'Z', '?'}
  - amount     : dtype float expected, got str
metrics   : auc 0.8123 / precision@100 0.4410
runtime   : 412s, peak 6.2GB
status    : OK
=============================================
```

파일을 못 가져오므로 **이 블록을 사람이 손으로 옮겨 적는 것이 전제**다. 그래서
`args` 를 그대로 한 줄 찍고, 계약 위반을 옮겨 적을 수 있게 적는다. RUN SUMMARY 는
stdout, 진행 상황은 stderr 로 간다.

종료 코드는 실행 스크립트가 분기할 수 있게 세 등급이다.

| | | |
|---|---|---|
| `0` | 정상 | 다음으로 |
| `1` | 돌았지만 온전치 않다 | 재시도해도 같다. 사람이 본다 |
| `2` | 시작도 못 했다 | 고치고 다시 돌린다 |

## 되돌리기 — 사이클을 닫는다

가져올 수 있는 것은 **입력 데이터의 포맷**과 **사람이 배운 것** 둘뿐이다.
실험 **직후** `docs/insights/YYYY-MM-DD-<tag>.md` 에 적는다. 이 고리가 가장 잘 샌다.

| 운영 환경에서 본 것 | 개발 장비에서 고칠 곳 |
|---|---|
| 계약 위반 메시지 (전문) | `contracts.py` — `note` 에 확인된 사실도 |
| 새로 터진 데이터 사고 유형 | `synth.py` — 그 유형을 생성 가능하게 |
| "코드 고치고 싶었던 순간" | `src/run.py` — 그 값을 CLI 인자로 승격 |
| 의존성 충돌 메시지 | `requirements.txt` |

**반영의 종착점은 문서가 아니라 테스트다.** 규칙으로 굳은 것은 테스트로 옮긴다 —
마크다운은 썩어도 조용하지만 테스트는 썩으면 빨간다. 반영이 끝나면 새 태그를 낸다.

## 하지 말 것

1. 운영 환경에서 `{AA}/{BB}` 코드 수정
2. 저장소에 데이터 파일 커밋 (테스트 픽스처 포함)
3. 태그 없이 운영 환경에서 실행
4. 운영 환경에서 `pip --upgrade`
5. `src/` 안에서 LLM·외부 API 호출
6. 리포트에 실데이터 값 찍기
7. 운영 환경 탐색을 인사이트 기록 없이 끝내기

---

**규칙의 근거와 나머지 전부는 [`IMPLEMENTATION_SPEC.md`](IMPLEMENTATION_SPEC.md) 에 있다.**
위의 규칙이 불편하게 느껴지면, 거기 적힌 제약(C1–C8)이 아직 유효한지 먼저 확인하라 —
규칙은 전부 그 제약에서 따라나온 것이라, 제약이 바뀌면 규칙도 바뀌어야 한다.
