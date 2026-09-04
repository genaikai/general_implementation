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

## 이식 (운영 환경)

```bash
cd {AA}
git clone <원격> .staging/{BB}           # 최초 1회만
bash .staging/{BB}/scripts/sync.sh v{tag_version}  # 매번 (ex. v0.15)
```
