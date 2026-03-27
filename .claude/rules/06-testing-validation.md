# Testing and Validation Rules

- Define the validation plan before coding.
- Translate acceptance criteria into explicit test cases.
- Cover happy path, boundary conditions, error handling, malformed input, and critical regressions.
- Add a regression test for every bug fix when practical. The test should fail before the fix is applied and pass after.
- Add integration tests when behavior crosses module or service boundaries.
- Add contract tests when the change touches a published API, event schema, or shared data contract. Verify that producers and consumers remain compatible.
- For event-driven or stateful session systems, add replay-and-recovery tests covering: duplicate event delivery, out-of-order event arrival, late events arriving after session termination, and restart-after-partial-commit sequences. These scenarios do not occur in happy-path tests but are exactly the conditions that cause ghost sessions, corrupted state, and data loss in production.
- When using a new function, method, SDK call, or API, review relevant overloads, optional parameters, and defaults. Record why the chosen option set was used and why other relevant options were not.
- Tests must be deterministic and hermetic. Unit tests must not depend on timing, network access, external services, or shared mutable state between runs. Mock external dependencies, fix random seeds, and use controlled clocks where the code under test depends on time.
- Do not modify or delete tests to make them pass unless the tested behavior intentionally changed. If tests are removed, document why in the commit message.
- Prefer file-scoped or targeted checks first for fast feedback, then run broader checks before finishing.
- Never claim success from compilation alone. Run the relevant tests and inspect the results.
- Report exactly what was validated manually and automatically.
