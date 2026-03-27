# Performance and Resource Rules

- Think in terms of memory, CPU, threads, handles, sockets, queue pressure, and I/O.
- Do not open and close expensive clients per request when pooling or reuse is available.
- Release resources in reverse order of acquisition.
- Avoid unbounded in-memory growth; prefer streaming, chunking, backpressure, or bounded queues.
- Profile before major optimization, but design obvious hot paths responsibly from the start.
- Prefer batch operations for supported database and API workloads.
- For background or asynchronous execution, define ownership, lifecycle, cancellation, timeout, and shutdown behavior.
- Design processes to be stateless where possible. Session state, user context, and in-flight data that must survive a process restart belong in an external store — database, cache, or broker — not in local memory. A stateless process can be stopped, restarted, or scaled horizontally without data loss or session disruption. Local memory that holds authoritative state creates invisible dependencies on process continuity.
- Optimize for fast startup and graceful shutdown. A process that takes minutes to start cannot be replaced quickly during an incident. A process that does not drain in-flight work before exit corrupts state. Target startup times measured in seconds, not minutes, and implement shutdown hooks that finish in-progress requests before exiting.
- Maintain dev/prod parity in dependencies. The database, broker, cache, and external services used in development should be the same technology and version as production — not substitutes or stubs. Differences between dev and prod environments are a primary source of bugs that only appear after deployment.
- For changes to performance-critical paths, validate against a defined baseline. Record the benchmark method, environment, and result in the change summary.
- Monitor long-running services for resource leak indicators: sustained memory growth, connection pool exhaustion, file handle accumulation, and queue depth increase. Add health checks or alarms where practical.

## Database access patterns

- Minimize database round trips on hot paths. A call-per-record or call-per-event pattern that could be a single bulk operation is a design defect, not a minor inefficiency. Buffer writes within a session or time window and execute as a single batch where semantics allow.
- For session-owned or aggregate-owned state, consider storing it as a single document or JSON column when doing so reduces round trips and simplifies ownership. A single READ, single UPDATE, and single DELETE is cleaner than scattered column-level operations across the session lifecycle. This is a useful tactic in the right context, not a universal rule — evaluate against normalized tables, append-only events, or key-value storage for your specific access patterns.
- Reuse prepared statements for repeated query shapes where the database client supports it. Preparing once and executing many times avoids repeated parse-and-plan cost, which is measurable at high call rates. Be aware that some databases cache a generic query plan for prepared statements that may be suboptimal for skewed data distributions — monitor slow queries on prepared statements, not just ad-hoc queries.
- Validate connection pool sizing under realistic concurrency before going to production. An undersized pool under concurrent session load serializes database access silently — threads queue for a connection rather than failing visibly, making the bottleneck hard to diagnose.
- When multiple application instances share a database or cache, do not rely on local in-process memory for state that must be consistent across instances. Instance A's local buffer is invisible to Instance B. Use a shared distributed state mechanism — such as a distributed cache or database — when correctness depends on cross-instance visibility. The choice of specific technology is an implementation decision; the principle is that shared correctness requires shared state.

## Load and soak testing

- Perform load testing whenever a change touches a hot path, changes resource allocation, introduces a new external call, or modifies concurrency behaviour. Functional tests confirm correctness; load tests confirm stability under real traffic volume.
- Use a dataset that is as close to production traffic as possible in volume, distribution, and variety. A synthetic uniform dataset will not reveal pathological behaviour triggered by skewed keys, large payloads, rare data shapes, or the access patterns of real users.
- Do not treat a single-process load test result as the full picture. In production, multiple instances compete for the same shared resources: database connection pools, cache capacity, broker throughput, and external API rate limits. The bottleneck under multi-instance contention is frequently different from the bottleneck under single-instance load.
- Record load test results with enough context to be reproducible and comparable: instance count, dataset characteristics, hardware and configuration, and the specific metric targets. A result without a baseline is just a number.
- For long-running services, supplement spike load tests with soak tests — sustained load over hours rather than minutes. Memory leaks, handle accumulation, connection pool drift, and GC pressure often only appear over time and are invisible in short tests.
- Perform fault injection under load: introduce artificial latency or failure in one downstream dependency while the system is under full traffic load. This reveals thread starvation, queue backup, timeout cascade failures, and retry storms that are invisible when all dependencies are healthy.

## Backpressure propagation

- In multi-stage processing pipelines, backpressure signals from a saturated downstream stage must propagate upstream — they must not be absorbed silently by an unbounded buffer at the stage boundary. An unbounded intermediate buffer between a fast producer and a slow consumer hides the overload condition, delays the signal that something is wrong, and eventually causes an OOM failure or processing collapse instead of graceful flow control.
- Design each stage boundary explicitly: what is the maximum buffer depth, what happens when it is reached (block, drop with metric, reject with error, apply backpressure upstream), and what is the alert condition. These are not defaults to accept from the framework — they are design decisions that determine how the system behaves under load.

## Cache cold-start and thundering herd

- After a cache flush, process restart, or cold deployment, do not allow all concurrent callers to simultaneously miss the cache and stampede the backing store. This thundering herd failure mode is deterministic under load — it will occur every time the cache is cold if no guard exists.
- Use one or more of the following mitigations: probabilistic early recomputation (recompute before expiry, not after), mutex-per-key (only one caller recomputes; others wait or receive a stale value), request coalescing (collapse concurrent misses for the same key into one backing-store call), or staggered TTL jitter (spread expiration times to prevent simultaneous mass expiry). The choice is a design decision; the non-negotiable is that the thundering herd case is explicitly handled.

## Idempotency key design

- When a retried operation must not produce duplicate side effects — payment, message send, record creation, external API call — design an idempotency key that is: stable across retries for the same logical operation, unique across logically distinct operations, and scoped to a time window after which the guarantee expires and the key can be safely recycled.
- Do not use auto-incremented IDs or server-generated UUIDs as idempotency keys — they change on each attempt. Use a key derived from the input that uniquely identifies the operation: a hash of the stable input fields, a client-generated UUID committed before the first attempt, or a composite of entity ID plus operation type plus request timestamp rounded to a window.
- Store idempotency key state in the same durable store as the operation result, not in a separate cache with a shorter TTL. A key that expires before the retry window closes defeats the purpose.
- When concurrent duplicate requests are possible — two callers arriving with the same key before either has written the result — use an atomic check-and-set operation to ensure exactly one caller proceeds: `INSERT ... ON CONFLICT DO NOTHING`, `Redis SET NX`, or equivalent. Without this, both callers may execute the operation simultaneously, producing a duplicate side effect the idempotency key was designed to prevent.
