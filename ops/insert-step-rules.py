"""Give every numbered step of every type's Working method its rule `<!-- check: ... -->` (specs/001-chat-depth,
part 2). The manager runs it once, outside any run, on the agent files a role session may not open:

    uv run python ops/insert-step-rules.py specs/001-chat-depth/step-rules.json .claude/agents

The rules file maps a type to {step number: rule}. Every type of the file must have its agent file, every step of
the file must exist in the type's method and every step of the method must get a rule; every rule must parse. Only
then is anything written, all files at once. A step that already carries a rule keeps it, so a second run changes
nothing. Prints one JSON object: the types and how many rules each received, or the problems; exit 1 on a problem.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from harness.gates import steps


def plan(rules: dict[str, dict[str, str]], agents: Path) -> tuple[dict[str, str], list[str]]:
    """The new text of every agent file the rules name, and the problems that stop the insertion."""
    texts, problems = {}, []
    for role_type, own in sorted(rules.items()):
        path = agents / f"{role_type}.md"
        if not path.is_file():
            problems.append(f"{role_type}: no agent file {path}")
            continue
        try:
            for rule in own.values():
                steps.parse(rule)
            text = steps.insert_rules(path.read_text(encoding="utf-8"), {int(n): r for n, r in own.items()})
        except ValueError as exc:
            problems.append(f"{role_type}: {exc}")
            continue
        bare = [s["n"] for s in steps.method_steps(text) if len(s["rules"]) != 1]
        if bare:
            problems.append(f"{role_type}: steps {bare} do not carry exactly one rule")
        texts[role_type] = text
    return texts, problems


def main(argv: list[str]) -> int:
    rules = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    agents = Path(argv[1])
    texts, problems = plan(rules, agents)
    if problems:
        print(json.dumps({"ok": False, "problems": problems}, indent=2))
        return 1
    changed = {}
    for role_type, text in texts.items():
        path = agents / f"{role_type}.md"
        if path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8")
            changed[role_type] = len(steps.method_steps(text))
    print(json.dumps({"ok": True, "types": len(texts), "changed": changed}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
