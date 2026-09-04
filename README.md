## 개요

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

## 역할

- [운영 환경]
데이터 처리 로직, 입력에 필요한 데이터 전처리, 데이터 준비

- [개발 장비]
'운영 환경'에서 입력으로 받을 데이터 포맷을 기반으로 기능 개발
출력 데이터 생성
'운영 환경'에서 해당 기능 개발에 대한 코드 수정 금지

## 이식 방법 (운영 환경)

```bash
cd {AA}/{target_path}
git clone <원격> .staging/{BB}           # 최초 1회만
bash .staging/{BB}/scripts/sync.sh v{tag_version}  # 매번 (ex. v0.15)
```
위 실행 이후, {AA}/{target_path}/{BB} 위치로 해당 tag 버전에 해당하는 코드가 생성/업데이트 된다.



---

# 무엇을 가져가나

| 파일 | 용도 |
|---|---|
| `scripts/sync.sh` | 개발→운영 이식 스크립트. **반드시 `scripts/` 안에** (↓ 아래) |
| `.gitattributes` | 이식 제외 목록 |
| `.gitignore` | 저장소에 애초에 못 들어오게 (데이터·산출물·설정) |
| `src/run.py` | 진입점. venv 갈아타기 + 위임만 |
| `src/<pkg>/__main__.py` | CLI 인자, 실행 순서, 종료 코드 |
| `src/<pkg>/contracts.py` | **입력 계약.** 프로젝트마다 갈아끼운다 |
| `src/<pkg>/synth.py` | 계약에서 가짜 데이터 생성 (데이터 파일을 두지 않기 위해) |
| `src/<pkg>/report.py` | RUN SUMMARY. 화면이 유일한 출력이다 |
| **`src/<pkg>/pipeline.py`** | **← 기능 코드를 여기 짠다** |
| `src/<pkg>/load.py` | 입력 포맷을 아는 유일한 곳 |
| `requirements.txt` | 운영 의존성 (버전 고정) |
| `requirements-dev.txt` | 개발 전용 패키지 (이식 제외) |
| `configs/env.example.yaml` | 설정 예시. 실값은 `{AA}` 에만 |
| `TODO.md` · `todo/` | `{AA}` 에서 만들어야 할 것과 그 방법 |
| `SCAFFOLD.md` | `adopt.sh` 가 대상에 만든다. 사본을 받아든 쪽이 읽는 지도 |
| `IMPLEMENTATION_SPEC.md` | 규격 전문 — 왜 이런 규칙인지 (이식 제외) |
| `examples/` | 채운 예시 (이식 제외) |
| `scripts/adopt.sh` | 위 목록을 대상 저장소로 복사하는 스크립트 (이식 제외) |

# 가져가기

기존 저장소에 얹으려면 스크립트가 대신 해준다. **이미 있는 파일은 건드리지 않고**
끝에 무엇을 손으로 합쳐야 하는지 알려준다.

```bash
bash scripts/adopt.sh ~/work/rule-based-tagging          # 패키지 이름은 폴더에서
bash scripts/adopt.sh ~/work/rule-based-tagging tagging  # 직접 줄 수도
```

`mypkg` 를 새 이름으로 바꿔서 복사하고, 대상에 `SCAFFOLD.md`(이 표와 단계)를 만든다.
덮어쓰려면 `--force`.

# 다음 단계

손으로 한다면:

```
1. src/ 를 통째로 가져와 mypkg 를 프로젝트 이름으로 바꾼다
2. contracts.py 의 INPUT_SCHEMA 를 실제 입력 형태로
3. pipeline.py 에 기능 코드를 짠다            ← 작업은 대부분 여기
4. requirements.txt 에 실제 의존성 (버전 고정)
5. git tag v1.0.0
   bash scripts/sync.sh v1.0.0                 ← preflight. 통과해야 push
   git push origin main --tags
6. 운영 환경에서:
   bash .staging/<저장소이름>/scripts/sync.sh v1.0.0
```

```bash
python src/run.py --dry-run   # 2번까지 끝났으면 데이터 없이 끝까지 돈다
```

# 핵심

- **기능 코드는 `src/<pkg>/pipeline.py`.** 포맷을 읽는 코드는 `load.py`,
  그 외에는 손댈 일이 거의 없다
- **`sync.sh` 는 반드시 `scripts/sync.sh` 다.** 자기 위치에서 저장소 이름을 유도하기
  때문이다 — 스크립트의 부모의 부모가 저장소 루트고, 그 이름이 `{BB}` 다.
  운영 모드는 자기가 `{AA}/.staging/{BB}/scripts/sync.sh` 에 있는지로 판별한다.
  옮기면 이름을 잘못 잡고, 그래서 **`{AA}`·`{BB}` 를 어디에도 설정하지 않아도 된다**
- **태그를 먼저 내고 preflight 를 돌린다.** `sync.sh` 가 태그를 받으므로 순서가
  반대면 "태그가 없습니다" 하고 멈춘다
- **`configs/env.yaml` 은 항상 `{AA}` 루트에.** 사본(`{AA}/{BB}/configs/`) 안에 두면
  다음 sync 때 통째로 지워진다
- **LLM·외부 API 는 `src/` 밖에서.** 개발 도구는 `tools/` 에 두고 이식에서 뺀다 (C8)
- **`tools/` 말고 새로 만든 개발 전용 파일은 `.gitattributes` 에 한 줄 추가한다.**
  `sync.sh` 의 금지 목록은 고정이라 처음 보는 이름은 못 잡는다.
  줄 끝 주석은 쓰지 마라 — git 이 그 줄을 통째로, 조용히 무시한다

## `sync.sh` 가 기계적으로 막는 것

태그 낼 때 한 번, 운영 환경에서 또 한 번. 이 여섯은 잊어도 된다.

```
개발 전용 파일이 넘어가는 것    tools/  CLAUDE.md  .gitattributes  requirements-dev.txt
데이터 파일                    .csv  .parquet  .pkl …
src/ 안의 anthropic·openai import
requirements.txt 에 섞인 개발 전용 패키지
개인 머신 절대 경로            /Users/…  /home/…
이메일·커밋 트레일러
```

**못 막는 둘은 눈으로 본다** — 리포트에 실데이터 값 찍기(C3), 임계값·컬럼명을 코드에
박기(§1.3). 둘 다 기계가 못 가린다.

---

채운 예시는 [`examples/`](examples/) 에, **왜 이런 규칙인지**는
[`IMPLEMENTATION_SPEC.md`](IMPLEMENTATION_SPEC.md) 에 있다. 규칙이 불편하면 거기
적힌 제약(C1–C8)이 아직 유효한지 먼저 확인하라.
