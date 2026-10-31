#!/usr/bin/env python3
"""Deterministic grader: exit 0 when the file has no opinion words in the reader's own voice."""

import re
import sys
from pathlib import Path

WORDS = re.compile(r"\b(probably|seems|I think|likely)\b", re.IGNORECASE)


def main() -> int:
    text = Path(sys.argv[1]).read_text(encoding="utf-8")
    hits = [m.group(0) for m in WORDS.finditer(text)]
    print(f"opinion words: {hits}")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
