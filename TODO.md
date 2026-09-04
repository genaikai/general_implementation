# 처음 돌리기 전에 준비할 것

이 저장소에 없는 것들이다 — 실값이라 커밋할 수 없거나(설정), 돌리는 환경마다
다른 것(경로·스케줄)이다.

```
[ ] 1. configs/env.yaml 채우기   실값                    이 환경에만
[ ] 2. 작업 폴더 .gitignore      ⚠ 실데이터가 git 에      어느 환경이나
[ ] 3. 실행 스크립트             todo/scripting.md       어느 환경이나
[ ] 4. 순서대로 점검             아래 4단계              어느 환경이나
```

**항목마다 "이 환경만의 사정인가, 어디서나 해당하는가"를 갈라 적어라.** 구분이 없으면
다음 사람이 안 해도 될 일을 하거나, 반대로 이 환경만의 것을 빠뜨린다.

만드는 방법은 `todo/` 에 있다. 이 파일은 **무엇이 남았나**만 센다.

---

## 1. `configs/env.yaml` 채우기

`configs/env.example.yaml` 을 복사해서 만든다.

```yaml
paths:
  venv: /opt/shared/venv   # 이 파이썬으로 갈아타서 실행한다. activate 불필요
```

비워두면 지금 켜져 있는 파이썬으로 그냥 돈다. venv 가 여럿이면 채우는 쪽이 안전하다
— activate 를 잊고 돌면 실패가 아니라 **다른 결과**가 나온다.

## 2. 작업 폴더의 `.gitignore`

**여기가 제일 위험하다.** 1번에서 채운 `configs/env.yaml` 에는 실값이 들어간다.
작업 폴더의 `.gitignore` 에 넣지 않으면 그대로 커밋된다.

```gitignore
configs/env.yaml   # ⚠ 실값. 1번에서 방금 채운 그 파일이다
outputs/           # 산출물
*.csv              # 실데이터. 확장자를 실제로 쓰는 것에 맞춰 늘린다
*.parquet
__pycache__/
```

한 번 새면 되돌릴 수 없다.

## 3. 실행 스크립트

**정하는 것: [`todo/scripting.md`](todo/scripting.md)**

①②는 손으로 쳐도 된다. **반복되는 실행은 스크립트로 감싼다** — 인자를 하나 빠뜨려도
프로그램은 기본값으로 돌아버리고, 그건 실패가 아니라 **다른 결과**로 나타난다.

## 4. 순서대로 점검

```bash
source <venv>/bin/activate
pip install --dry-run -r requirements.txt && pip check   # ⓪ 충돌 먼저
pip install -r requirements.txt

python src/run.py --dry-run --config configs/env.yaml     # ① 환경 확인
python src/run.py --data <실데이터> --limit 1000           # ② 계약 확인
./run_daily.sh <실데이터>                                  # ③ 전체 — 3번의 스크립트로
```

- **①에서 실패하면 환경 문제다.** 코드가 아니라 venv·파이썬 버전을 본다
- **②가 실제 수확이다.** 여기서 나오는 `contract : n MISMATCH` 줄을 **그대로
  옮겨 적어라.** 그게 입력 형식을 정확히 아는 유일한 경로다
- ②가 깨끗해진 뒤에 ③으로 간다 — 틀린 계약 위에서 뽑은 숫자는 믿을 수 없다

**`--upgrade`·`--force-reinstall` 금지.** 공용 venv 라면 남의 환경을 조용히 깨뜨리고
되돌릴 수 없다. 충돌은 고치지 말고 메시지를 적어 둔다.

---

## 돌린 뒤

콘솔이 유일한 출력이다. 화면을 보고 손으로 옮겨 적는 것이 전제다.

| 옮겨 적을 것 | 왜 |
|---|---|
| `contract` 의 MISMATCH 줄 전문 | 계약을 고치는 근거 |
| `args` 줄 | 그때 뭘로 돌렸는지. 셸 히스토리는 사라진다 |
| 새로 터진 데이터 사고 유형 | 합성 데이터에 그 유형을 넣기 위해 |
| "코드 한 줄만 고치면 되는데" 했던 순간 | 그 값이 CLI 인자에 없었다는 뜻 |
| 의존성 충돌 메시지 | `requirements.txt` 를 고치는 근거 |
