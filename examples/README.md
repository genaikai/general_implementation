# 예제 — 스캐폴드를 실제로 채우면 이렇게 된다

`orders/` 는 **주문 로그**를 다루는 프로젝트로 스캐폴드를 채운 것이다. 고친 파일은
둘뿐이고, 나머지는 손대지 않았다.

```
src/<pkg>/contracts.py   ← 표시된 블록만 orders/schema.py 로 갈아끼움
src/<pkg>/pipeline.py    ← orders/pipeline.py 로 통째 교체
```

> 이 폴더는 `{AA}` 로 넘어가지 않는다(`export-ignore`). 개발 장비에서 배우는 용도고,
> 운영 저장소에 남는 것은 제품 코드뿐이어야 한다 (§1.4).

---

## 1. 계약을 적는다 — `orders/schema.py`

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

## 2. 계산을 짠다 — `orders/pipeline.py`

```python
def compute_metrics(rows: list[dict]) -> dict:
    ...
    # 채널은 계약의 allowed 에서 가져온다 — 코드에 박으면 계약과 갈라진다
    declared = next((f.allowed for f in INPUT_SCHEMA if f.name == "channel"), ())
    for name in declared:
        metrics[f"share_{name}"] = f"{channels[name] / len(rows):.3f}"
```

채널 목록을 이 파일에 박지 않고 **계약에서 읽는다.** 채널이 하나 늘면 고칠 곳이
계약 한 줄뿐이다 — 운영 환경에서는 코드를 못 고치므로(C2), 고칠 곳이 하나여야
다음 사이클이 싸다.

## 3. 돌린다

계약만 채우면 **가짜 데이터가 저절로 따라온다.** 데이터 파일을 만들지 않았는데도
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
contract  : 6 ok / 0 MISMATCH
metrics   :
  orders           1,000
  revenue          511,006,300
  amount_mean      511,006
  qty_mean         490.08
  share_web        0.327
  share_app        0.317
  share_store      0.356
runtime   : 0.0s, peak 0.02GB
status    : OK
=============================================
```

종료 코드 `0`.

## 4. 계약이 깨지면 이렇게 보인다

`--adversarial` 은 운영 환경에서 실제로 터졌던 사고 유형을 섞는다.

```bash
python src/run.py --dry-run --rows 1000 --seed 7 --adversarial
```

```
contract  : 0 ok / 9 MISMATCH
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
있다는 걸 알 수 있다. 그러면 개발 장비로 돌아가 `contracts.py` 의 `note` 에 적거나,
`load.py` 에서 `strip()` 하도록 고친다.

## 5. 안 읽는 필드는 위반이 아니다

`coupon_code` 는 `used=False` 라서, 어긋나도 **노트로 내려가고 종료 코드는 `0`** 이다.

```
contract  : 5 ok / 0 MISMATCH
notes     : 1 (판정에 영향 없음)
  - coupon_code : column missing
status    : OK
```

이게 왜 중요한가 — 파이프라인이 읽지도 않는 필드 때문에 매 실행마다 `MISMATCH` 가
뜨면, 사람은 곧 `contract` 줄 자체를 안 보게 된다. 그러면 **포맷을 회수하는 유일한
채널이 죽는다.** `contract` 줄은 "판정이 틀렸을 수 있다"는 뜻이어야 한다.

---

## 직접 해보려면

```bash
cp examples/orders/pipeline.py src/mypkg/pipeline.py
# src/mypkg/contracts.py 의 "갈아끼운다" 표시 블록을 examples/orders/schema.py 로 교체
python src/run.py --dry-run --rows 1000 --seed 7
```

`tests/test_examples.py` 가 이걸 임시 폴더에서 자동으로 해본다. **예제는 설명하지
않고 돌린다** — 스캐폴드 API 가 바뀌면 문서가 아니라 테스트가 먼저 깨진다.
