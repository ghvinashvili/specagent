#!/usr/bin/env python3
"""Create .claude/agents/<name>.md from templates/role-type.md and validate the frontmatter."""

import json
import os
import re
import sys
from pathlib import Path

import jsonschema
import yaml


def main() -> int:
    name = sys.argv[1]
    if not re.fullmatch(r"[a-z][a-z0-9-]*", name):
        sys.exit(f"invalid type name: {name}")
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
    target = root / ".claude" / "agents" / f"{name}.md"
    if target.exists():
        sys.exit(f"already exists: {target}")
    text = (root / "templates" / "role-type.md").read_text(encoding="utf-8").replace("<type-name>", name, 1)
    frontmatter = yaml.safe_load(text.split("---", 2)[1])
    frontmatter["description"] = "placeholder " * 4  # replaced by the human in step 2
    schema = json.loads((root / "schemas" / "role-type.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(frontmatter, schema)
    target.write_text(text, encoding="utf-8")
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
