# 예제 — 스캐폴드를 실제로 채우면 이렇게 된다

`orders/` 는 **주문 로그**를 다루는 프로젝트로 스캐폴드를 채운 것이다. 손댄 곳은
셋뿐이고, 나머지는 그대로다.

```
src/<pkg>/schema.py          ← 표시된 블록만 orders/schema.py 로
src/<pkg>/features/<기능>/   ← orders/features/ 의 둘을 얹음
src/<pkg>/pipeline.py        ← 그 둘을 목록에 적음
```

> 이 폴더는 `{AA}` 로 넘어가지 않는다(`export-ignore`). 개발 장비에서 배우는 용도고,
> 운영 저장소에 남는 것은 제품 코드뿐이어야 한다 (§1.4).

---

## 1. 스키마를 적는다 — `orders/schema.py`

입력이 어떻게 생겼는지를 **구조로만** 적는다.

```python
INPUT_SCHEMA: tuple[Field, ...] = (
    Field("order_id", "str", False,
          note="2026-08 확인: ORD- 접두어 + 숫자 10자리"),
    Field("ordered_at", "datetime", False),
    Field("channel", "category", False, allowed=("web", "app", "store")),
    Field("amount", "float", False, rng=(0.0, 1e9),
          note="원 단위 정수로 들어온다. 소수점 없음"),
    Field("quantity", "int", False, rng=(1, 999)),
    Field("coupon_code", "str", True, used=False),
)
```

세 가지가 보인다.

- **`note` 는 운영 환경에서 확인한 사실**을 적는 자리다. 날짜와 함께 남기면 나중에
  "언제 본 것인가"를 알 수 있다. 실험에서 배운 것이 코드로 돌아오는 통로다
- **`allowed=("web","app","store")` 는 구조다.** 실제 채널 코드 40개를 나열하면 그건
  데이터고 밖으로 나올 수 없다 (C3)
- **`coupon_code` 는 `used=False`** — 로그에는 있지만 이 파이프라인이 읽지 않는다

## 2. 기능을 만든다 — `orders/features/`

**기능 하나가 폴더 하나다.** `template` 을 복사해서 시작한다.

```bash
cp -r src/<pkg>/features/template src/<pkg>/features/channel_mix
```

```python
# features/channel_mix/__init__.py
NAME = "channel"

def process_data(rows: list[dict]) -> dict:
    ...
    # 채널 목록을 여기 박지 않고 스키마에서 읽는다. 박으면 채널이 하나 늘 때
    # 고칠 곳이 둘이 되고, 그러면 언젠가 한쪽만 고쳐진다.
    declared = next((f.allowed for f in INPUT_SCHEMA if f.name == "channel"), ())
    return {f"{NAME}_{name}": tally(counts[name], len(rows)) for name in declared}
```

**지표 이름 앞에 `NAME` 을 붙이는 것이 규칙이다.** 여럿의 결과가 한 리포트에 모이므로
접두어가 없으면 겹친다.

`tally()` 처럼 **둘 이상의 기능이 같이 쓰는 것**은 `features/_shared.py` 에 둔다.
한 기능만 쓰는 것은 그 기능 폴더 안에 둔다 — `_shared` 에 올려두면 고칠 때 누가
영향받는지 알 수 없다.

## 3. 목록에 적는다 — `orders/pipeline.py`

```python
from .features import big_order, channel_mix

FEATURES = (
    channel_mix,
    big_order,
)
```

**기능을 늘려도 만질 곳은 둘뿐이다** — 폴더 하나, 목록 한 줄. 스키마·적재·리포트·
진입점은 그대로다.

이름이 겹치면 **죽는다.** 조용히 덮어쓰면 화면에는 마지막 기능의 숫자만 남고,
덮였다는 사실이 어디에도 안 뜬다 — 사람은 틀린 숫자를 옳은 줄 알고 옮겨 적는다.

```python
raise KeyError(f"{feature.NAME} 의 지표 이름이 겹친다: {sorted(collided)}")
```

## 4. 돌린다

스키마만 채우면 **가짜 데이터가 저절로 따라온다.** 데이터 파일을 만들지 않았는데도
전 구간이 돈다.

```bash
python src/run.py --dry-run --rows 1000 --seed 7
```

```
=============================================
                 RUN SUMMARY
=============================================
version   : unversioned
args      : --dry-run --rows 1000 --seed 7
input     : synthetic(n=1000, seed=7, mode=normal)
shape     : 1,000 rows x 6 cols
schema    : 6 ok / 0 MISMATCH
metrics   :
  rows             1,000
  channel_web      327 (32.70%)
  channel_app      317 (31.70%)
  channel_store    356 (35.60%)
  big_order        529 (52.90%)
runtime   : 0.0s, peak 0.02GB
status    : OK
=============================================
```

종료 코드 `0`. 지표에 `channel_`·`big_order` 접두어가 붙은 것이 보인다 — 기능이 열
개로 늘어도 이 규칙 때문에 겹치지 않는다.

## 5. 스키마가 깨지면 이렇게 보인다

`--adversarial` 은 운영 환경에서 실제로 터졌던 사고 유형을 섞는다.

```bash
python src/run.py --dry-run --rows 1000 --seed 7 --adversarial
```

```
schema    : 0 ok / 9 MISMATCH
  - ordered_at  : dtype datetime expected, 1 rows failed to parse
  - channel     : 2 nulls but nullable=False
  - channel     : unexpected values {' app', '?'}
  - amount      : 1 nulls but nullable=False
  - amount      : dtype float expected, 2 rows failed to parse
  - amount      : 2 rows outside (0.0, 1000000000.0)
  - quantity    : 4 nulls but nullable=False
  - quantity    : dtype int expected, 4 rows failed to parse
  - quantity    : 2 rows outside (1, 999)
...
status    : CONTRACT MISMATCH
```

종료 코드 `1` — **돌긴 돌았지만 온전치 않다.**

**이 줄들이 이 구조의 결과물이다.** 결과 파일도 로그도 못 가져오는 환경에서, 사람이
화면을 보고 손으로 베껴 나오는 것이 이 아홉 줄이다. 그래서 `validation failed` 같은
요약은 이 규격에서 결함이다 — 베낄 것이 없기 때문이다.

`channel : unexpected values {' app', '?'}` 를 보면 **앞에 공백이 붙은 `' app'`** 이
있다는 걸 알 수 있다. 그러면 개발 장비로 돌아가 `schema.py` 의 `note` 에 적거나,
`load.py` 에서 `strip()` 하도록 고친다.

## 6. 안 읽는 필드는 위반이 아니다

`coupon_code` 는 `used=False` 라서, 어긋나도 **노트로 내려가고 종료 코드는 `0`** 이다.

```
schema    : 5 ok / 0 MISMATCH
notes     : 1 (판정에 영향 없음)
  - coupon_code : column missing
status    : OK
```

이게 왜 중요한가 — 파이프라인이 읽지도 않는 필드 때문에 매 실행마다 `MISMATCH` 가
뜨면, 사람은 곧 `schema` 줄 자체를 안 보게 된다. 그러면 **포맷을 회수하는 유일한
채널이 죽는다.** `schema` 줄은 "판정이 틀렸을 수 있다"는 뜻이어야 한다.

---

## 직접 해보려면

```bash
cp -r examples/orders/features/channel_mix src/core/features/
cp -r examples/orders/features/big_order   src/core/features/
cp    examples/orders/pipeline.py          src/core/pipeline.py
# src/core/schema.py 의 "갈아끼운다" 표시 블록을 examples/orders/schema.py 로 교체
python src/run.py --dry-run --rows 1000 --seed 7
```

`tests/test_examples.py` 가 이걸 임시 폴더에서 자동으로 해본다. **예제는 설명하지
않고 돌린다** — 스캐폴드 API 가 바뀌면 문서가 아니라 테스트가 먼저 깨진다.
