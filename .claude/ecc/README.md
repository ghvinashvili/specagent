# ECC texts

Every text the template copies from ECC (everything-claude-code) at one pinned commit, in one place. The manager reads
this page before it writes a brief for a role with a domain, picks the lines that fit, and puts them in the brief: a
`Spec:` line with the copy and its line range (`.claude/ecc/agents/<name>.md:<a>-<b>`), a `Skills:` line with the skill.
The copies are byte for byte as pinned; the pin, the drop rules K1-K5 and M, and the re-pin steps are in
[ECC sources](sources.md) ([summary](sources.summary.md)); every copied file with its sha256 is in [ECC files](files.md);
ECC's hook recipes, for reference only, are in [ECC hook recipes](hook-recipes.md).

## Agent texts (`agents/`, 70)
Brief material, never `.claude/agents/`. Each line: the copy and what its `description:` says; the sha256 of each is in
[the folder's list](agents/README.md).

- [a11y-architect](agents/a11y-architect.md): Accessibility Architect specializing in WCAG 2.2 compliance for Web and Native platforms
- [agent-evaluator](agents/agent-evaluator.md): Evaluates agent output against 5-axis quality rubric (accuracy, completeness, clarity
- [architect](agents/architect.md): Software architecture specialist for system design, scalability, and technical decision-making
- [bengali-reviewer](agents/bengali-reviewer.md): Reviews code handling Bengali (Bangla) text for Unicode correctness, proper normalization
- [build-error-resolver](agents/build-error-resolver.md): Build and TypeScript error resolution specialist
- [chief-of-staff](agents/chief-of-staff.md): Personal communication chief of staff that triages email, Slack, LINE, and Messenger
- [code-architect](agents/code-architect.md): Designs feature architectures by analyzing existing codebase patterns and conventions
- [code-explorer](agents/code-explorer.md): Deeply analyzes existing codebase features by tracing execution paths, mapping architecture
- [code-reviewer](agents/code-reviewer.md): Expert code review specialist
- [code-simplifier](agents/code-simplifier.md): Simplifies and refines code for clarity, consistency, and maintainability while preserving
- [comment-analyzer](agents/comment-analyzer.md): Analyze code comments for accuracy, completeness, maintainability, and comment rot risk
- [commit-reviewer](agents/commit-reviewer.md): Reviews a staged diff and drafts a Conventional Commits-compliant message matching
- [conversation-analyzer](agents/conversation-analyzer.md): Use this agent when analyzing conversation transcripts to find behaviors worth preventing
- [cpp-build-resolver](agents/cpp-build-resolver.md): C++ build, CMake, and compilation error resolution specialist
- [cpp-reviewer](agents/cpp-reviewer.md): Expert C++ code reviewer specializing in memory safety, modern C++ idioms, concurrency
- [csharp-reviewer](agents/csharp-reviewer.md): Expert C# code reviewer specializing in .NET conventions, async patterns, security, nullable
- [dart-build-resolver](agents/dart-build-resolver.md): Dart/Flutter build, analysis, and dependency error resolution specialist
- [database-reviewer](agents/database-reviewer.md): PostgreSQL database specialist for query optimization, schema design, security, and performance
- [django-build-resolver](agents/django-build-resolver.md): Django/Python build, migration, and dependency error resolution specialist
- [django-reviewer](agents/django-reviewer.md): Expert Django code reviewer specializing in ORM correctness, DRF patterns, migration safety
- [doc-updater](agents/doc-updater.md): Documentation and codemap specialist
- [docs-lookup](agents/docs-lookup.md): When the user asks how to use a library, framework, or API or needs up-to-date code examples, use
- [e2e-runner](agents/e2e-runner.md): End-to-end testing specialist using Vercel Agent Browser (preferred) with Playwright fallback
- [fastapi-reviewer](agents/fastapi-reviewer.md): Reviews FastAPI applications for async correctness, dependency injection, Pydantic schemas
- [flutter-reviewer](agents/flutter-reviewer.md): Flutter and Dart code reviewer
- [fsharp-reviewer](agents/fsharp-reviewer.md): Expert F# code reviewer specializing in functional idioms, type safety, pattern matching
- [gan-evaluator](agents/gan-evaluator.md): GAN Harness — Evaluator agent
- [gan-generator](agents/gan-generator.md): GAN Harness — Generator agent
- [gan-planner](agents/gan-planner.md): GAN Harness — Planner agent
- [go-build-resolver](agents/go-build-resolver.md): Go build, vet, and compilation error resolution specialist
- [go-reviewer](agents/go-reviewer.md): Expert Go code reviewer specializing in idiomatic Go, concurrency patterns, error handling
- [harmonyos-app-resolver](agents/harmonyos-app-resolver.md): HarmonyOS application development expert specializing in ArkTS and ArkUI. Reviews code for V2
- [harness-optimizer](agents/harness-optimizer.md): Improve local agent-harness configuration reliability and cost using eval-driven grading
- [healthcare-reviewer](agents/healthcare-reviewer.md): Reviews healthcare application code for clinical safety, CDSS accuracy, PHI compliance
- [homelab-architect](agents/homelab-architect.md): Designs home and small-lab network plans from hardware inventory, goals, and operator experience
- [java-build-resolver](agents/java-build-resolver.md): Java/Maven/Gradle build, compilation, and dependency error resolution specialist
- [java-reviewer](agents/java-reviewer.md): Expert Java code reviewer for Spring Boot and Quarkus projects
- [kotlin-build-resolver](agents/kotlin-build-resolver.md): Kotlin/Gradle build, compilation, and dependency error resolution specialist
- [kotlin-reviewer](agents/kotlin-reviewer.md): Kotlin and Android/KMP code reviewer
- [loop-operator](agents/loop-operator.md): Operate autonomous agent loops, monitor progress, and intervene safely when loops stall
- [marketing-agent](agents/marketing-agent.md): Marketing strategist and copywriter for campaign planning, audience research, positioning, copy
- [mle-reviewer](agents/mle-reviewer.md): Production machine-learning engineering reviewer for data contracts, feature pipelines, training
- [network-architect](agents/network-architect.md): Designs enterprise or multi-site network architecture from requirements, using existing network
- [network-config-reviewer](agents/network-config-reviewer.md): Reviews router and switch configurations for security, correctness, stale references, risky
- [network-troubleshooter](agents/network-troubleshooter.md): Diagnoses network connectivity, routing, DNS, interface, and policy symptoms with a read-only
- [opensource-forker](agents/opensource-forker.md): Fork any project for open-sourcing
- [opensource-packager](agents/opensource-packager.md): Generate complete open-source packaging for a sanitized project
- [opensource-sanitizer](agents/opensource-sanitizer.md): Verify an open-source fork is fully sanitized before release
- [performance-optimizer](agents/performance-optimizer.md): Performance analysis and optimization specialist
- [planner](agents/planner.md): Expert planning specialist for complex features and refactoring
- [pr-test-analyzer](agents/pr-test-analyzer.md): Review pull request test coverage quality and completeness, with emphasis on behavioral coverage
- [python-reviewer](agents/python-reviewer.md): Expert Python code reviewer specializing in PEP 8 compliance, Pythonic idioms, type hints
- [pytorch-build-resolver](agents/pytorch-build-resolver.md): PyTorch runtime, CUDA, and training error resolution specialist
- [rag-pipeline-reviewer](agents/rag-pipeline-reviewer.md): Reviews RAG (Retrieval-Augmented Generation) pipelines for retrieval quality, chunking strategy
- [react-build-resolver](agents/react-build-resolver.md): Diagnose and fix React build failures across Vite, webpack, Next.js, CRA, Parcel, esbuild, and Bun
- [react-reviewer](agents/react-reviewer.md): Expert React/JSX code reviewer specializing in hook correctness, render performance
- [refactor-cleaner](agents/refactor-cleaner.md): Dead code cleanup and consolidation specialist
- [ruby-reviewer](agents/ruby-reviewer.md): Expert Ruby and Rails code reviewer specializing in idiomatic Ruby, Active Record query safety
- [rust-build-resolver](agents/rust-build-resolver.md): Rust build, compilation, and dependency error resolution specialist
- [rust-reviewer](agents/rust-reviewer.md): Expert Rust code reviewer specializing in ownership, lifetimes, error handling, unsafe usage
- [security-reviewer](agents/security-reviewer.md): Security vulnerability detection and remediation specialist
- [seo-specialist](agents/seo-specialist.md): SEO specialist for technical SEO audits, on-page optimization, structured data, Core Web Vitals
- [silent-failure-hunter](agents/silent-failure-hunter.md): Review code for silent failures, swallowed errors, bad fallbacks, and missing error propagation
- [spec-miner](agents/spec-miner.md): Extracts behavioral specs from existing codebases for OpenSpec
- [swift-build-resolver](agents/swift-build-resolver.md): Swift/Xcode build, compilation, and dependency error resolution specialist
- [swift-reviewer](agents/swift-reviewer.md): Expert Swift code reviewer specializing in protocol-oriented design, value semantics, ARC memory
- [tdd-guide](agents/tdd-guide.md): Test-Driven Development specialist enforcing write-tests-first methodology
- [type-design-analyzer](agents/type-design-analyzer.md): Analyze type design for encapsulation, invariant expression, usefulness, and enforcement
- [typescript-reviewer](agents/typescript-reviewer.md): Expert TypeScript/JavaScript code reviewer specializing in type safety, async correctness
- [vue-reviewer](agents/vue-reviewer.md): Expert Vue.js code reviewer specializing in Composition API correctness, reactivity pitfalls

## Skills (`../skills/`, 11)
Project skills, each in its own folder. Role types are those the text suits; a type's row in
`docs/roles/need-to-know.yaml` (`skills:`) or the brief's `Skills:` line makes the skill available to it.

- [python-patterns](../skills/python-patterns/SKILL.md): writer, test-verifier; Python code: structure, typing, PEP 8 style
- [python-testing](../skills/python-testing/SKILL.md): writer, test-verifier; pytest tests: TDD, fixtures, mocks, coverage
- [cpp-coding-standards](../skills/cpp-coding-standards/SKILL.md): writer; C++ code that follows the Core Guidelines
- [cpp-testing](../skills/cpp-testing/SKILL.md): writer, test-verifier; C++ tests: GoogleTest, CTest, flaky tests, sanitizers
- [postgres-patterns](../skills/postgres-patterns/SKILL.md): writer, planner; PostgreSQL queries, schemas, indexes, RLS, a slow query
- [docs-governance](../skills/docs-governance/SKILL.md): librarian; a read-only audit of the docs when no narrower docs skill fits
- [conventional-commit-review](../skills/conventional-commit-review/SKILL.md): writer; a Conventional Commits message for staged changes
- [agent-security-hardening](../skills/agent-security-hardening/SKILL.md): planner, critic; an agent runtime that takes untrusted content or holds credentials
- [eval-harness](../skills/eval-harness/SKILL.md): planner, analyst; capability and regression evals, graders, pass@k
- [agent-eval](../skills/agent-eval/SKILL.md): analyst, advisor; choosing between coding agents by pass rate, cost and time
- [agent-self-evaluation](../skills/agent-self-evaluation/SKILL.md): every role that writes; a 1-5 self-rating with evidence after a non-trivial task

## Rules (`../rules/ecc/`, 11)

- [ECC rules](files.md): the Python, C++ and TypeScript coding-style, patterns, security and testing rules; each loads by its `paths` when Claude touches a matching file, so a brief needs no line for them
