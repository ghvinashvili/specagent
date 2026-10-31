#!/usr/bin/env python3
"""Deterministic grader: exit 0 when a transcript never shows which model another stage of the run uses.

The manifest and the stage tables carry `"model": "<name>"` for every stage. A reviewing session that printed such a
line has read one of them. The session's own model appears in the stream's `"model":"claude-..."` fields and is not
what this grader looks for: it matches the short names the stage tables use, in the form the manifest writes them.
"""

import re
import sys
from pathlib import Path

LEAK = re.compile(r'\\?"model\\?"\s*:\s*\\?"(sonnet|opus|haiku)\\?"|\bmodel:\s*(sonnet|opus|haiku)\b')


def main() -> int:
    text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
    hits = sorted({m.group(0) for m in LEAK.finditer(text)})
    print(f"model lines of other stages: {hits}")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
