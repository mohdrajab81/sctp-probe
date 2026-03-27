# Readability and Maintainability Rules

## Naming

- Use intention-revealing names. A name should communicate what the variable, function, or type represents without requiring the reader to trace its usage.
- Avoid misleading names. A name that implies a different type, scope, or behavior than the actual one is worse than a generic name.
- Avoid abbreviations that are not universally known in the codebase's domain. Prefer `connectionTimeout` over `connT`.
- Name boolean variables and functions as assertions: `isReady`, `hasExpired`, `canRetry`.
- Linters enforce casing and prefix conventions. This rule file governs semantic clarity, which linters cannot check.

## Comments

- Comments should explain why, not what. Code should be clear enough that describing what it does is unnecessary. Comments earn their place by explaining intent, constraints, assumptions, and non-obvious decisions.
- Do not leave misleading or stale comments. A comment that no longer matches the code is worse than no comment.
- Document preconditions, postconditions, and invariants for non-trivial functions, especially when callers must satisfy constraints.
- TODO comments must include the reason and a reference (ticket, issue, or owner). A bare TODO is not actionable.

## Cognitive load and structure

- Prefer early returns and guard clauses over deeply nested conditionals.
- Limit function length to what a reader can hold in working memory at once. If explaining a function requires more than a few sentences, consider splitting it.
- Avoid clever code. Explicit and predictable is almost always better than concise and surprising.
- Avoid deeply chained method calls when intermediate results have meaning that a named variable would communicate.

## Abstractions

- Do not introduce abstractions speculatively. Duplication is preferable to a premature or wrong abstraction.
- An abstraction that is harder to understand than the two concrete cases it replaces is not an improvement.
- Avoid abstraction layers that exist only to satisfy a pattern name (Factory, Manager, Handler) without a real boundary benefit.

## Dead code and hygiene

- Remove dead code rather than commenting it out. Version control preserves history.
- Remove stale feature flags and their branches once the rollout is complete and stable.
- Remove unused imports, variables, parameters, and dependencies. They create noise and confuse future readers.
