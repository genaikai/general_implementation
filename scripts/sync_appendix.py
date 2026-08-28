#!/usr/bin/env python3
"""IMPLEMENTATION_SPEC.md 의 부록 A 를 scripts/sync.sh 원본과 동기화한다.

  python3 scripts/sync_appendix.py           # 부록을 원본에 맞춰 갱신
  python3 scripts/sync_appendix.py --check    # 어긋나 있으면 exit 1 (아무것도 고치지 않음)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "IMPLEMENTATION_SPEC.md"
SCRIPT = ROOT / "scripts" / "sync.sh"
BEGIN, END = "<!-- BEGIN sync.sh -->", "<!-- END sync.sh -->"


def render() -> str:
    spec = SPEC.read_text()
    i, j = spec.find(BEGIN), spec.find(END)
    if i < 0 or j < 0:
        sys.exit(f"marker not found in {SPEC.name}: {BEGIN} / {END}")
    body = "```bash\n" + SCRIPT.read_text().rstrip("\n") + "\n```\n"
    return spec[: i + len(BEGIN)] + "\n" + body + spec[j:]


def main() -> int:
    new, old = render(), SPEC.read_text()
    if new == old:
        print("appendix in sync")
        return 0
    if "--check" in sys.argv:
        print(f"OUT OF SYNC: {SPEC.name} 부록 A != {SCRIPT}", file=sys.stderr)
        print("  고치려면: python3 scripts/sync_appendix.py", file=sys.stderr)
        return 1
    SPEC.write_text(new)
    print(f"updated {SPEC.name} 부록 A from {SCRIPT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
