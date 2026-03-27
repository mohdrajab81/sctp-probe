# Concurrency and Thread Safety Rules

- Assume shared mutable state is dangerous until proven otherwise.
- Use explicit concurrency-safe primitives and collections, such as `ConcurrentHashMap`, `CopyOnWriteArrayList`, `BlockingQueue`, `threading.Lock`, `asyncio.Lock`, channels, or language-equivalent constructs.
- Document the synchronization model when state is shared across threads, tasks, workers, or callbacks. Make ownership and lifetime of shared state explicit.
- Acquire multiple locks only in a documented global order.
- Prefer bounded acquisition (`tryLock`, timeout-based acquire, or equivalent) where blocking indefinitely could stall the system.
- Never perform network I/O, disk I/O, waits, or CPU-heavy work while holding a lock.
- Prefer immutable handoff, message passing, or snapshot copies over long-lived shared mutation.
- Background tasks and async operations must define explicit cancellation behavior. Respect cancellation signals promptly; do not silently discard them.
- Do not mix concurrency models (for example, raw threads with asyncio, or executor futures with coroutines) without explicit justification and clearly documented ownership boundaries.
- Add concurrency-focused tests when the change introduces shared state, async flows, retries, timers, or callbacks.

## Session state machines and event sequencing

These rules apply to any system where related events for the same logical session, entity, or workflow can arrive across multiple threads, streams, connections, or brokers. Out-of-order delivery is normal, not exceptional, in these environments.

- Never assume that related events arrive in the order they were generated. Multiple network streams, worker threads, or broker partitions can deliver events for the same session in any order. Design for this explicitly.
- For stateful sessions, either serialize all events for a given session key through a single thread or processing slot, or make the state machine explicitly tolerant of reordering with documented handling for each out-of-order case.
- A session may only be created by a valid, recognized initiation event for that protocol or workflow. If a non-initiation message arrives and no session exists, reject or hold it — do not silently create a session in an undefined state using a mid-flow or termination message as the trigger.
- Termination of a session does not always mean immediate hard deletion of session state. When late-arriving messages are expected (due to network reordering or multi-stream delivery), retain a bounded tombstone or grace-period state after termination to absorb them safely. Define the grace period explicitly; do not leave it open-ended.
- Duplicate or replayed events must be handled idempotently at the state machine level. Receiving the same event twice must not create a duplicate session, corrupt state, or trigger duplicate side effects.
- Illegal state transitions must be rejected explicitly with a logged error. Do not silently coerce the state machine into an adjacent valid state. A suppressed illegal transition hides protocol violations and makes post-mortem diagnosis impossible.
- Log each state transition at an operationally retained severity level — or emit it as a structured event to an equivalent stream — including session key, previous state, triggering event, and new state. This produces a complete, reconstructible audit trail without requiring a debugger or replay. In high-volume systems where INFO-level logging per transition would saturate the pipeline, use a dedicated structured event sink or reduce to sampled or DEBUG logging with a periodic summary.

## Atomic state and messaging

- Never send a message, emit an event, or trigger a downstream action before the state change that caused it is durably committed. If the commit fails, the message must not have been sent. The reverse — committing first and then failing to send — is recoverable; the forward case (message sent, commit fails) creates ghost state that is extremely difficult to diagnose and clean up.
- For operations that must update a database and publish an event atomically, use a transactional outbox pattern or equivalent: write the event to a durable outbox table within the same transaction as the state change, then deliver it asynchronously after commit. Do not rely on best-effort dual writes.
- When designing multi-step operations that span a database and a message broker, explicitly define what happens on partial failure at each step. Document the failure modes and recovery path before implementation, not after.
