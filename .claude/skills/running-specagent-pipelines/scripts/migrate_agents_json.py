#!/usr/bin/env python3
"""Migrate a live run folder to watch_agents.py version 2: write `<run-dir>/_agents-v2.json` from the folder's config
and its watcher copy, and print how the copy's behaviour differs from v2's defaults.

  python3 migrate_agents_json.py <run-dir> [--out <file>]    (default <run-dir>/_agents-v2.json)

The config is `_agents-active.json`, else `_agents.json`; its run_dir, common, blocked_files, pack, extra_prompt and
agents are copied as they are. The copy, `<run-dir>/_watch_agents.py`, is parsed with ast and never imported (a copy
starts watching at import). Its module-level assignments are evaluated when they are made of str and int constants,
f-strings on RUN (which becomes `{run}`, filled in by the watcher), + and *, `.format(<name>=<value>)`, dicts and the
`{role: text + LANG for role, text in FRESH.items()}` comprehension; `if`, `for` and `def` bodies are skipped (an
earlier run's startup-pack texts sit in an `if`). Its loop gives three numbers: nudges from `revived[...] > N`,
permission_wait from `... - first < N` (null when the copy has no `blocked_since` and ends a blocked or failed session
at once, as an earlier run's does), interval from `time.sleep(N)`. lang is the copy's LANG when FRESH, NUDGE and
HANDOFF_ORDER all end with it (it is stripped from them), else ''.

The new config holds the copied fields and every value that differs from watch_agents.DEFAULTS; fresh holds the copy's
texts that differ from v2's, a role no agent of the config uses included (and named). Printed: `config: <file>`,
`<field>: <default> -> <value>` for numbers, a word diff for texts, `<NAME>: not a literal` for a value the parser
cannot read and `<NAME>: not in this copy` (v2's default stays), `fresh.<role>: no text in this copy` for a role of the
config that the copy lacks, the copy's wording of blocked and failed sessions where it differs, pack, extra_prompt and
what v2 adds. Exit codes: 0 written; 2 an input is missing or unreadable (nothing is written). The new config is the
only file it writes; `--out` keeps it out of a live run folder until the main session puts it there.
"""

import argparse
import ast
import difflib
import json
import pathlib
import sys

sys.dont_write_bytecode = True  # `python3 -I` ignores PYTHONDONTWRITEBYTECODE; the skill folder stays clean
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import watch_agents as wa

CONFIGS = ("_agents-active.json", "_agents.json")
COPIED = ("run_dir", "common", "blocked_files", "pack", "extra_prompt", "agents")
ORDER = (
    "run_dir",
    "common",
    "blocked_files",
    "cap",
    "handoff_wait",
    "nudges",
    "permission_wait",
    "interval",
    "lang",
    "nudge",
    "handoff_order",
    "unblock",
    "fresh",
    "pack",
    "extra_prompt",
    "agents",
)
NUMBERS = (("CAP", "cap"), ("HANDOFF_WAIT", "handoff_wait"))
TEXTS = (("NUDGE", "nudge"), ("HANDOFF_ORDER", "handoff_order"), ("UNBLOCK", "unblock"))
UNREAD = object()  # the value of a name whose assignment is not a literal, and of a field left at v2's default


class NotLiteral(Exception):
    pass


def literal(node, env):
    """The value of an expression made of constants and names already read; NotLiteral for anything else."""
    try:
        if isinstance(node, ast.Constant) and type(node.value) in (str, int, float):
            return node.value
        if isinstance(node, ast.Name) and env.get(node.id, UNREAD) is not UNREAD:
            return env[node.id]
        if isinstance(node, ast.JoinedStr):  # an f-string: `{RUN}` gives `{run}`
            return "".join(literal(part, env) for part in node.values)
        if isinstance(node, ast.FormattedValue) and node.conversion == -1 and node.format_spec is None:
            return str(literal(node.value, env))
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mult)):
            left, right = literal(node.left, env), literal(node.right, env)
            return left + right if isinstance(node.op, ast.Add) else left * right
        if isinstance(node, ast.Dict) and None not in node.keys:  # a None key is a `**` unpacking
            return {literal(k, env): literal(v, env) for k, v in zip(node.keys, node.values)}
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "format"
            and not node.args
            and all(k.arg for k in node.keywords)
        ):
            return literal(node.func.value, env).format(**{k.arg: literal(k.value, env) for k in node.keywords})
        if isinstance(node, ast.DictComp) and len(node.generators) == 1:  # {role: text + LANG for role, text in …}
            gen, target = node.generators[0], node.generators[0].target
            if (
                isinstance(target, ast.Tuple)
                and len(target.elts) == 2
                and all(isinstance(t, ast.Name) for t in target.elts)
                and not gen.ifs
                and isinstance(gen.iter, ast.Call)
                and isinstance(gen.iter.func, ast.Attribute)
                and gen.iter.func.attr == "items"
                and not gen.iter.args
            ):
                items, out = literal(gen.iter.func.value, env), {}
                for key, value in items.items():
                    inner = {**env, target.elts[0].id: key, target.elts[1].id: value}
                    out[literal(node.key, inner)] = literal(node.value, inner)
                return out
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):  # what the copy itself would fail on
        raise NotLiteral() from None
    raise NotLiteral()


def assign(env, target, node):
    if isinstance(target, ast.Name):
        if target.id != "RUN":  # the run folder stays the placeholder the watcher fills in
            try:
                env[target.id] = literal(node, env)
            except NotLiteral:
                env[target.id] = UNREAD
    elif (
        isinstance(target, ast.Subscript)
        and isinstance(target.value, ast.Name)
        and isinstance(env.get(target.value.id), dict)
    ):  # FRESH['x'] = …
        try:
            env[target.value.id][literal(target.slice, env)] = literal(node, env)
        except (NotLiteral, TypeError):
            env[target.value.id] = UNREAD
    else:  # a tuple, an attribute: the names it binds are not read
        for name in ast.walk(target):
            if isinstance(name, ast.Name) and isinstance(name.ctx, ast.Store) and name.id != "RUN":
                env[name.id] = UNREAD


def module_names(tree):
    """The copy's module-level names in source order: {name: value}, UNREAD when an assignment is not a literal."""
    env = {"RUN": "{run}"}
    for stmt in tree.body:  # the bodies of `if`, `for` and `def` are skipped
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                assign(env, target, stmt.value)
        elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
            assign(env, stmt.target, stmt.value)
        elif isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name):  # NUDGE += LANG
            assign(env, stmt.target, ast.BinOp(ast.Name(stmt.target.id, ast.Load()), stmt.op, stmt.value))
    return env


def named(node, name):
    return isinstance(node, ast.Name) and node.id == name


def loop_parts(tree):
    """The expressions of the copy's loop numbers ({field: [nodes]}), whether it ends a session in state blocked or
    failed at once (`state in ('blocked', 'failed')`, an earlier run), and whether it has a `blocked_since` wait."""
    found, at_once = {"nudges": [], "permission_wait": [], "interval": []}, False
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            left, op, right = node.left, node.ops[0], node.comparators[0]
            if isinstance(op, ast.Gt) and isinstance(left, ast.Subscript) and named(left.value, "revived"):
                found["nudges"].append(right)
            elif (
                isinstance(op, ast.Lt)
                and isinstance(left, ast.BinOp)
                and isinstance(left.op, ast.Sub)
                and named(left.right, "first")
            ):
                found["permission_wait"].append(right)
            elif isinstance(op, ast.In) and {"blocked", "failed"} <= {
                e.value for e in getattr(right, "elts", ()) if isinstance(e, ast.Constant)
            }:
                at_once = True
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "sleep"
            and named(node.func.value, "time")
            and len(node.args) == 1
        ):
            found["interval"].append(node.args[0])
    waits = any(named(node, "blocked_since") for node in ast.walk(tree))
    return found, at_once, waits


def name_value(env, name, kind, lines):
    """A module-level name's value, or UNREAD after the line that says why v2's default stays."""
    value = env.get(name, UNREAD)
    if name not in env:
        lines.append(f"{name}: not in this copy")
    elif (
        value is UNREAD
        or not isinstance(value, kind)
        or isinstance(value, bool)
        or (kind is dict and not all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()))
    ):
        lines.append(f"{name}: not a literal")
        value = UNREAD
    return value


def loop_value(field, nodes, env, lines):
    """The one value of a loop number's expressions, or UNREAD after the line that says why v2's default stays."""
    if not nodes:
        lines.append(f"{field}: not in this copy")
        return UNREAD
    try:
        values = sorted({literal(node, env) for node in nodes})
    except (NotLiteral, TypeError):
        values = None
    if values is None or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
        lines.append(f"{field}: not a literal")
        return UNREAD
    if len(values) > 1:
        lines.append(f"{field}: several values ({', '.join(map(str, values))})")
        return UNREAD
    return values[0]


def short(text, width=60):
    text = " ".join(text.split())
    return text if len(text) <= width else text[: width - 1] + "…"


def word_diff(old, new, chunks=3):
    """The changed runs of words, `-"old words" +"new words"`, at most `chunks` of them."""
    if not new:
        return f"'' (v2's default: \"{short(old)}\")"
    a, b = old.split(), new.split()
    parts = [
        " ".join(f'{sign}"{short(" ".join(words))}"' for sign, words in (("-", a[i1:i2]), ("+", b[j1:j2])) if words)
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
        if op != "equal"
    ]
    if not parts:
        return "whitespace only"
    return "; ".join(parts[:chunks]) + (f"; and {len(parts) - chunks} more" if len(parts) > chunks else "")


def migrate(config_path, config, tree):
    """The v2 config and the lines that say how the copy differs from v2's defaults."""
    lines, same, defaults = [f"config: {config_path.name}"], [], wa.DEFAULTS
    v2 = {k: config[k] for k in COPIED if k in config}
    env = module_names(tree)
    values = {field: name_value(env, name, (int, float), lines) for name, field in NUMBERS}
    found, at_once, waits = loop_parts(tree)
    for field, nodes in found.items():
        if field == "permission_wait" and not waits and at_once:
            values[field] = None  # every block is an exit event, as the copy has it
        else:
            values[field] = loop_value(field, nodes, env, lines)
    texts = {field: name_value(env, name, str, lines) for name, field in TEXTS}
    fresh = name_value(env, "FRESH", dict, lines)
    lang = name_value(env, "LANG", str, lines) if "LANG" in env else ""
    with_lang = [t for t in (texts["nudge"], texts["handoff_order"]) if t is not UNREAD]
    with_lang += list(fresh.values()) if fresh is not UNREAD else []
    if lang is UNREAD or not lang or not with_lang or not all(t.endswith(lang) for t in with_lang):
        lang = ""
    else:
        for field in ("nudge", "handoff_order"):
            if texts[field] is not UNREAD:
                texts[field] = texts[field][: -len(lang)]
        if fresh is not UNREAD:
            fresh = {role: text[: -len(lang)] for role, text in fresh.items()}
    for field, value in values.items():
        if value is UNREAD:
            continue
        if value == defaults[field]:
            same.append(field)
        else:
            v2[field] = value
            lines.append(f"{field}: {json.dumps(defaults[field])} -> {json.dumps(value)}")
    for field, value in (("lang", lang), *texts.items()):
        if value is UNREAD:
            continue
        if value == defaults[field]:
            same.append(field)
        else:
            v2[field] = value
            lines.append(f"{field}: {word_diff(defaults[field], value)}")
    if at_once:
        lines.append(
            'events: the copy says "<name> is blocked" and "<name> is failed"; v2 says "<name> is blocked '
            '(<waitingFor>)" and "<name> failed"'
        )
    roles = sorted({name.split("/")[-1] for name in config["agents"]})
    if fresh is not UNREAD:
        changed = {role: text for role, text in fresh.items() if text != wa.FRESH.get(role)}
        same += [f"fresh.{role}" for role in fresh if role not in changed]
        for role, text in changed.items():
            unused = "" if role in roles else f" (no agent of {config_path.name} uses it; kept)"
            lines.append(
                f"fresh.{role}: {word_diff(wa.FRESH[role], text) if role in wa.FRESH else 'a new role'}{unused}"
            )
        if changed:
            v2["fresh"] = changed
        for role in roles:
            if role not in fresh:
                default = "v2's default applies" if role in wa.FRESH else "no default either: v2 refuses the config"
                lines.append(f"fresh.{role}: no text in this copy; {default}")
    if "pack" in config or "USE_PACK" in env:
        lines.append(
            f"pack: {json.dumps(config.get('pack', False))} (startup packs (`scripts/make_pack.py`): v2 "
            "does not build them; pack: true is a config error, a resume of a session that started with "
            "a pack an exit event)"
        )
    if "extra_prompt" in config:
        uses = any(isinstance(node, ast.Constant) and node.value == "extra_prompt" for node in ast.walk(tree))
        lines.append(
            f"extra_prompt: copied, {short(json.dumps(config['extra_prompt'], ensure_ascii=False), 100)}"
            + ("" if uses else "; this copy ignores it, v2 uses it")
        )
    lines.append(
        f"new in v2: budget {json.dumps(defaults['budget'])} per session (an event line, exit 3); control "
        "files checked before each launch (exit 4); a note acted on only in its session's transcript window"
    )
    if same:
        lines.append(f"same as v2's defaults: {', '.join(same)}")
    return {k: v2[k] for k in ORDER if k in v2}, lines


def main(argv=None):
    parser = argparse.ArgumentParser(description="Write <run-dir>/_agents-v2.json from a live config and watcher copy.")
    parser.add_argument("run_dir")
    parser.add_argument("--out", help="the file to write instead of <run-dir>/_agents-v2.json")
    args = parser.parse_args(argv)
    run = pathlib.Path(args.run_dir)
    config_path = next((run / name for name in CONFIGS if (run / name).is_file()), None)
    if config_path is None:
        print(f"no _agents-active.json or _agents.json in {run}")
        return 2
    copy_path = run / "_watch_agents.py"
    if not copy_path.is_file():
        print(f"no _watch_agents.py in {run}")
        return 2
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        tree = ast.parse(copy_path.read_text(encoding="utf-8"), str(copy_path))
    except (OSError, ValueError, SyntaxError) as e:
        print(f"cannot read {e}")
        return 2
    if not isinstance(config, dict) or not isinstance(config.get("agents"), dict):
        print(f"{config_path.name}: no agents")
        return 2
    v2, lines = migrate(config_path, config, tree)
    out = pathlib.Path(args.out) if args.out else run / "_agents-v2.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(v2, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\n".join(lines + [f"wrote: {out}"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
