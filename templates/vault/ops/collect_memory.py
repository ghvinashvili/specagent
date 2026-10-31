#!/usr/bin/env python3
"""Copy Claude Code memory files into the vault's context/memory/<name>/ with a secret filter.

Usage: collect_memory.py <name>=<memory-dir> [<name>=<memory-dir> ...]\n       collect_memory.py --recheck      (rescan existing copies with the current patterns; remove hits)

Policy (vault rules.md, "Never here"): a file that shows any sign of a credential, key, token, password,
e-mail address, non-loopback IP address or ssh login is skipped whole; only its name and the pattern label are
written to context/memory/<name>/_skipped.md. Nothing is printed from file contents. Files already collected
(same source path in an existing header) are left alone. Deterministic; no model.
"""
import re
import sys
from datetime import date
from pathlib import Path

VAULT = Path(__file__).resolve().parents[1]
HEADER = "<!-- collected {day} from {src} -->\n"
PATTERNS = {
    "anthropic-key": re.compile(r"sk-ant-[A-Za-z0-9_-]{8,}"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{10,}|github_pat_"),
    "aws-key": re.compile(r"\bAKIA[0-9A-Z]{12,}"),
    "slack-token": re.compile(r"\bxox[abprs]-"),
    "private-key": re.compile(r"BEGIN (RSA|OPENSSH|EC|DSA|PGP)? ?PRIVATE KEY"),
    "ssh-pubkey": re.compile(r"ssh-(rsa|ed25519|dss) AAAA"),
    "bearer": re.compile(r"Bearer [A-Za-z0-9._\-]{16,}"),
    "key-value": re.compile(r"(?i)\b(api[_ -]?key|secret|token|password|passwd|client[_ -]?secret|access[_ -]?key)\b[\"']?\s*[:=]\s*[\"']?\S{6,}"),
    "key-nearby": re.compile(r"(?i)\b(api[_ -]?key|secret|token|password|passwd|client[_ -]?secret)\b\W{0,4}[A-Za-z0-9_\-]{16,}"),
    "sk-key": re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}"),
    "url-userinfo": re.compile(r"://[^/\s:@]+:[^@\s]+@"),
    "ipv6": re.compile(r"(?i)\b(?:[0-9a-f]{1,4}:){4,7}[0-9a-f]{1,4}\b"),
    # a run of 40+ key-like characters with upper case, lower case and digits, not part of a path, slug or hex id
    "high-entropy": re.compile(r"(?<![A-Za-z0-9+=/_.-])(?=[A-Za-z0-9+=]*[A-Z])(?=[A-Za-z0-9+=]*[a-z])(?=[A-Za-z0-9+=]*\d)[A-Za-z0-9+=]{40,}(?![A-Za-z0-9+=/_.-])"),
    "email": re.compile(r"[A-Za-z0-9._%+-]+@(?!example\.(com|org|net)\b|anthropic\.com\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "ipv4": re.compile(r"(?<![\d.])(?!127\.0\.0\.1|0\.0\.0\.0)(\d{1,3}\.){3}\d{1,3}(?![\d.])"),
    "ssh-login": re.compile(r"\bssh\s+(-\w+\s+)*[A-Za-z0-9_.-]+@[A-Za-z0-9_.-]+"),
    "hex-secret": re.compile(r"(?i)\b(key|token|secret)\b\W{0,4}[0-9a-f]{32,}"),
}


def existing_sources(root: Path) -> set[str]:
    found = set()
    for f in root.rglob("*.md"):
        try:
            first = f.open(encoding="utf-8").readline()
        except OSError:
            continue
        m = re.match(r"<!-- collected \S+ from (\S+) -->", first)
        if m:
            found.add(tail(Path(m.group(1))))
    return found


def tail(p: Path) -> str:
    """<project-dir>/memory/<file>: the part of a memory path that is stable across machines and header styles."""
    return "/".join(p.parts[-3:])


def recheck(root: Path, day: str) -> int:
    """Rescan copies already under context/memory with the current patterns; remove hits (names to _skipped.md)."""
    removed = 0
    for f in sorted(root.glob("*/*.md")):
        if f.name == "_skipped.md":
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        hits = [label for label, rx in PATTERNS.items() if rx.search(text)]
        if hits:
            f.unlink()
            sk = f.parent / "_skipped.md"
            prev = sk.read_text(encoding="utf-8") if sk.exists() else "# Skipped (secret filter)\n\nName and pattern label only; contents never copied.\n"
            sk.write_text(prev + f"- `{f.name}`: {', '.join(hits)} (recheck {day})\n", encoding="utf-8")
            print(f"removed {f.parent.name}/{f.name}: {', '.join(hits)}")
            removed += 1
    print(f"recheck: removed {removed}")
    return 0


def main(argv: list[str]) -> int:
    if argv == ["--recheck"]:
        return recheck(VAULT / "context" / "memory", date.today().isoformat())
    if not argv:
        print(__doc__)
        return 2
    day = date.today().isoformat()
    root = VAULT / "context" / "memory"
    done = existing_sources(root)
    for arg in argv:
        name, _, src_dir = arg.partition("=")
        src = Path(src_dir).expanduser()
        dst = root / name
        dst.mkdir(parents=True, exist_ok=True)
        copied = skipped = already = words = 0
        skipped_lines = []
        for f in sorted(src.glob("*.md")):
            if f.name == "MEMORY.md":
                continue
            if tail(f) in done:
                already += 1
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            hits = [label for label, rx in PATTERNS.items() if rx.search(text)]
            if hits:
                skipped += 1
                skipped_lines.append(f"- `{f.name}`: {', '.join(hits)}")
                continue
            (dst / f.name).write_text(HEADER.format(day=day, src=f) + text, encoding="utf-8")
            copied += 1
            words += len(text.split())
        if skipped_lines:
            sk = dst / "_skipped.md"
            prev = sk.read_text(encoding="utf-8") if sk.exists() else "# Skipped (secret filter)\n\nName and pattern label only; contents never copied.\n"
            sk.write_text(prev + f"\n## {day}\n" + "\n".join(skipped_lines) + "\n", encoding="utf-8")
        print(f"{name}: copied {copied}, skipped {skipped}, already {already}, words {words}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
