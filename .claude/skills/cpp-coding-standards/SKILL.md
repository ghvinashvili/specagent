---
name: cpp-coding-standards
description: C++ Core Guidelines coding standards. Use when writing, reviewing or refactoring C++ code for modern, safe, idiomatic practice.
metadata:
  origin: ECC
---

# C++ Coding Standards (C++ Core Guidelines)

Comprehensive coding standards for modern C++ (C++17/20/23) derived from the [C++ Core Guidelines](https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines). Enforces type safety, resource safety, immutability, and clarity.

## When to Use

- Writing new C++ code (classes, functions, templates)
- Reviewing or refactoring existing C++ code
- Making architectural decisions in C++ projects
- Enforcing consistent style across a C++ codebase
- Choosing between language features (e.g., `enum` vs `enum class`, raw pointer vs smart pointer)

### When NOT to Use

- Non-C++ projects
- Legacy C codebases that cannot adopt modern C++ features
- Embedded/bare-metal contexts where specific guidelines conflict with hardware constraints (adapt selectively)

## Additional resources

Each further section of this skill is a file of its own under `references/`; read the one the task needs:

- [Cross-Cutting Principles](references/cross-cutting-principles.md)
- [Philosophy & Interfaces (P.*, I.*)](references/philosophy-interfaces-p-i.md)
- [Functions (F.*)](references/functions-f.md)
- [Classes & Class Hierarchies (C.*)](references/classes-class-hierarchies-c.md)
- [Resource Management (R.*)](references/resource-management-r.md)
- [Expressions & Statements (ES.*)](references/expressions-statements-es.md)
- [Error Handling (E.*)](references/error-handling-e.md)
- [Constants & Immutability (Con.*)](references/constants-immutability-con.md)
- [Concurrency & Parallelism (CP.*)](references/concurrency-parallelism-cp.md)
- [Templates & Generic Programming (T.*)](references/templates-generic-programming-t.md)
- [Standard Library (SL.*)](references/standard-library-sl.md)
- [Enumerations (Enum.*)](references/enumerations-enum.md)
- [Source Files & Naming (SF.*, NL.*)](references/source-files-naming-sf-nl.md)
- [Performance (Per.*)](references/performance-per.md)
- [Quick Reference Checklist](references/quick-reference-checklist.md)
