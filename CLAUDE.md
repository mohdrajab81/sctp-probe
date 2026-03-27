# AI Engineering Operating Rules — sctp-probe

## Purpose

- Make the smallest safe change that solves the problem.
- Preserve code health, safety, readability.
- Prefer verifiable work over impressive work.

## Source of truth

The authoritative design document is `DESIGN.md`. It defines:
- Module responsibilities and boundaries
- Data model (Message, Rule)
- Full REST API surface
- Reply templates
- Rule engine matching logic
- Web UI layout and behaviors

If this CLAUDE.md conflicts with DESIGN.md on any technical matter, DESIGN.md takes
precedence. Update this file to reflect the resolution.

## Non-negotiable rules

- Never invent Python library names, function signatures, or pycrate API calls without
  verifying them against installed package source or official documentation.
- Never claim a test passed without actually running it and showing the output.
- Never hardcode ports, file paths, or hostnames in business logic — use environment
  variables as defined in DESIGN.md section 10.
- Every SCTP socket operation must have an explicit timeout.
- Never log raw binary payloads at INFO level — log hex summary only.
- Never expose the web UI or REST API on a non-loopback interface without explicit
  user instruction. Default bind is `127.0.0.1`.
- Do not modify DESIGN.md as part of a feature task. Design changes are a separate
  activity with their own plan and review.

## Required working pattern

1. Restate the task in implementation terms.
2. List affected modules, callers, and risks.
3. For any non-trivial change, propose a short plan before editing.
4. Define validation before coding: which test file, which test case, what command.
5. Implement in small reviewable steps.
6. Report exactly what changed, what was tested, and what remains unverified.

## Architecture rules specific to this project

- `decoder.py` must never raise — all exceptions caught, fallback to raw hex.
- `encoder.py` returns `None` on failure — rule engine must handle None gracefully.
- `store.py` uses `asyncio.to_thread` for all SQLite calls — never block the event loop.
- `sctp_server.py` and `sctp_client.py` must not import from each other.
- `rules.py` depends on `store.py`, `encoder.py`, and the transport modules — nothing
  else depends on `rules.py` except `sctp_server.py` and `sctp_client.py`.
- `ws.py` has no dependencies on transport or storage — it is a pure fan-out hub.
- `main.py` is the only file that wires all modules together.
- Adding a new protocol (CBSP, NR-CBC) means adding new `decoder_cbsp.py` and
  `encoder_cbsp.py` modules — do not modify the existing SBc-AP decoder/encoder.

## pysctp and pycrate rules

- Before using any pysctp or pycrate API, verify the call exists in the installed
  version by reading the installed package source (`pip show -f pysctp`).
- pycrate's SBc-AP module path must be verified against the installed version before
  use. Do not assume the import path from documentation — check the actual file tree.
- If pysctp cannot be imported (non-Linux or module not loaded), all SCTP functionality
  must degrade gracefully — the FastAPI app still starts, endpoints return 503 with a
  clear message, the web UI shows a "SCTP unavailable" banner.

## Test rules

- Run `pytest tests/ -v` to validate. Never claim tests pass without running this.
- SCTP-dependent tests are marked `@pytest.mark.sctp` and skipped automatically when
  pysctp is unavailable. All other tests must pass on Windows and macOS too.
- Never delete or modify existing tests to make them pass unless the tested behavior
  intentionally changed.

## Commit and change management

- Do not push to remote without explicit user instruction.
- Keep changes small — one logical change per commit.
- Commit message format: `type(scope): description`
  Examples: `feat(encoder): add WRR_PARTIAL reply template`
            `fix(store): handle concurrent reset correctly`
            `test(decoder): validate against sentinel-cbc fixtures`
