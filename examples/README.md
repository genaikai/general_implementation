# 예제 — 스캐폴드를 실제로 채우면 이렇게 된다

## rule_base_tag 예제

완전하고 실행 가능한 multi-package 구조 예제는 
[rule-base-tag 프로젝트](https://github.com/genaikai/rule-base-tag)를 참고하세요.

**구조:**
```
run.py
src/
  framework/           (수정 금지)
  project/             (수정 필요)
  error_keyword/
  sensitive_info/
  ... (10개 태거 패키지)
```

**시작:**
```bash
git clone https://github.com/genaikai/rule-base-tag.git
cd rule-base-tag
python run.py --dry-run
```

---

## 주요 파일

`framework/contracts.py` — 입력 스키마 정의  
`project/pipeline.py` — 실제 처리 로직  
`{tagger_name}/detector.py` — 각 태거의 구현

> 이 폴더는 {AA} 로 넘어가지 않는다 (export-ignore). 개발 장비 전용.
