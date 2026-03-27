# Change Management Rules

- Keep changes small, coherent, and reviewable.
- Maintain runbooks or operational playbooks for critical system operations: deployments, rollbacks, failovers, data migrations, and incident response. Update them as part of every major release. A runbook that does not reflect the current system is worse than no runbook — it creates false confidence during incidents.
- Write a short plan for multi-file or high-risk work before editing.
- Commit only logically complete, validated changes.
- Do not mix refactoring with behavior changes in the same commit unless they are trivially inseparable. Separating them makes review faster and rollback cleaner.
- Keep docs, config examples, diagrams, and migration notes in sync with code.
- Use branch and PR discipline appropriate to the repository.
- In the PR description or summary, explain the problem, the approach, risks, rollback considerations, and validation performed.
- For breaking schema, API, or event changes, use the expand-migrate-contract pattern: add the new form first, migrate all consumers, then remove the old form as a separate step.
- For high-risk production changes, prefer a feature flag or staged rollout. Define the flag's owner, default value, purpose, and planned removal timeline before merging.
- Human review is mandatory for AI-generated code before merge.
