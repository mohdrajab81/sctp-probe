# Resilience and Networking Rules

- Put an explicit timeout on every external dependency call: HTTP, database, cache, queue, filesystem, RPC, telnet, websocket handshake, or third-party SDK.
- For multi-step or chained external calls, define an end-to-end deadline budget. Per-call timeouts alone do not prevent total latency overruns when calls are composed.
- Classify failure mode before adding retry logic.
- Retry only transient failures such as timeout, connection reset, temporary unavailability, or rate limiting.
- Use exponential backoff with a bounded retry count. Add jitter for distributed callers when appropriate.
- Do not retry validation failures, auth failures, programmer errors, or business-rule failures.
- When multiple distributed clients may retry the same dependency simultaneously, cap the total retry pressure to prevent retry storms under sustained failure.
- Implement a circuit breaker for dependencies that experience sustained failures. When a dependency is unresponsive or error-rate exceeds a defined threshold, stop sending requests rather than continuing to retry. Allow periodic probe requests to detect recovery. A circuit breaker protects both the caller and the struggling dependency.
- Isolate thread pools or execution slots per downstream dependency. Without bulkhead isolation, a single slow or failing dependency can exhaust all available threads in a high-concurrency process — cascading the failure to every other dependency that shares the same pool, even healthy ones. Assign each critical external dependency its own bounded thread pool or semaphore so that one dependency's failure cannot propagate to the others.
- When a downstream dependency signals overload across a network boundary, propagate that signal upstream — do not absorb it silently into an unbounded buffer and continue. An HTTP 429 response must cause the caller to slow intake or apply backpressure to its own callers, not just retry after a delay. A Kafka consumer receiving sustained lag pressure should pause partition consumption rather than accumulate a growing backlog. A gRPC client receiving flow-control signals must respect them rather than queue requests against a stalled stream. Absorbing overload signals silently converts a recoverable downstream overload into an upstream OOM or thread-exhaustion cascade.
- Prefer idempotent operations for retried flows. If the operation is not idempotent, design a guard.
- Reuse connections and clients through pooling or persistent sessions when supported by the platform.
- Think about bandwidth and payload size. Prefer batching, compression, pagination, delta updates, and streaming when appropriate.
- Record retry attempts, timeout events, fallback activation, and circuit-breaker-style decisions in logs and telemetry.
