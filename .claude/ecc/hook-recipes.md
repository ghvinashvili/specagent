# ECC hook recipes

The section "Common Hook Recipes" of ECC's `hooks/README.md`, lines 254-306 at commit
`25278e7d7b6cf6e6a4e7a6c8e10f14ff22f0eb5b`, is copied byte for byte from its heading to the end of this page. MIT,
"Copyright (c) 2026 Affaan Mustafa"; the license text is `agents/LICENSE`, and the pin, selection and re-pin are in
[ECC sources](sources.md). Reference only: no recipe below is installed in this repository.

## Read with three differences
Claude Code's hooks page (`https://code.claude.com/docs/en/hooks`) says Claude never sees the stderr of a hook that
exits 0; a hook speaks to Claude through `additionalContext` in its JSON output.
- The TODO and test-file recipes print to stderr and exit 0, so they warn nobody.
- The ruff recipe runs whatever `ruff` is on the PATH and throws its errors away.
- The test-file recipe points at `/tdd`, an ECC command this repository does not have.

## This repository's hooks
- `.claude/hooks/format-on-edit.py`, after Edit or Write of a Python file inside the project (`CLAUDE_PROJECT_DIR`,
  not the folder a `cd` moved the session to): runs this checkout's ruff, else the main checkout's
  (`.venv/bin/ruff`), as `ruff format --force-exclude <file>`, so `pyproject.toml`'s exclusions hold; with
  neither it does nothing (it never runs `uv`, which would create `.venv`). When ruff fails, Claude reads
  "format-on-edit: ruff could not format <file>: <ruff's first line>". Fix the file and save it again.
- `.claude/hooks/test-alongside.py`, before Write of a new source file (Python, C++ or TypeScript) under
  `packages/<package>/src/`, or of `ops/<name>.py`: when no file under `packages/<package>/tests/` or `ops/tests/`
  is named `test_<name>.*`, `<name>_test.*`, `<name>.test.*` or `<name>.spec.*`, or names `<name>` as a whole word,
  Claude reads "test-alongside: no test under <folder> names <name>". It never blocks the write; write the test
  (`AGENTS.md`, "Testing").

## Common Hook Recipes

### Warn about TODO comments

```json
{
  "matcher": "Edit",
  "hooks": [{
    "type": "command",
    "command": "node -e \"let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{const i=JSON.parse(d);const ns=i.tool_input?.new_string||'';if(/TODO|FIXME|HACK/.test(ns)){console.error('[Hook] New TODO/FIXME added - consider creating an issue')}})\""
  }],
  "description": "Warn when adding TODO/FIXME comments"
}
```

### Block large file creation

```json
{
  "matcher": "Write",
  "hooks": [{
    "type": "command",
    "command": "node -e \"let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{const i=JSON.parse(d);const c=i.tool_input?.content||'';const lines=c.split('\\n').length;if(lines>800){console.error('[Hook] BLOCKED: File exceeds 800 lines ('+lines+' lines)');console.error('[Hook] Split into smaller, focused modules');process.exit(2)}})\""
  }],
  "description": "Block creation of files larger than 800 lines"
}
```

### Auto-format Python files with ruff

```json
{
  "matcher": "Edit",
  "hooks": [{
    "type": "command",
    "command": "node -e \"let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{const i=JSON.parse(d);const p=i.tool_input?.file_path||'';if(/\\.py$/.test(p)){const{execFileSync}=require('child_process');try{execFileSync('ruff',['format',p],{stdio:'pipe'})}catch(e){}}})\""
  }],
  "description": "Auto-format Python files with ruff after edits"
}
```

### Require test files alongside new source files

```json
{
  "matcher": "Write",
  "hooks": [{
    "type": "command",
    "command": "node -e \"const fs=require('fs');let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{const i=JSON.parse(d);const p=i.tool_input?.file_path||'';if(/src\\/.*\\.(ts|js)$/.test(p)&&!/\\.test\\.|\\.spec\\./.test(p)){const testPath=p.replace(/\\.(ts|js)$/,'.test.$1');if(!fs.existsSync(testPath)){console.error('[Hook] No test file found for: '+p);console.error('[Hook] Expected: '+testPath);console.error('[Hook] Consider writing tests first (/tdd)')}}})\""
  }],
  "description": "Remind to create tests when adding new source files"
}
```
