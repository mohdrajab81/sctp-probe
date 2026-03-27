# Architecture and Design Rules

- Start from the requested outcome, acceptance criteria, and current architecture.
- Perform cross-impact analysis before editing: callers, downstream consumers, config, docs, tests, dashboards, alerts, and rollout implications.
- Preserve backward compatibility by default for APIs, method signatures, data contracts, events, and persisted formats.
- If backward compatibility must be broken, document the migration path, rollout sequence, deprecation window, and rollback plan before making any change.
- Keep business logic out of controllers, transport adapters, and views.
- Prefer the repository's established patterns over new frameworks or abstractions.
- Prefer the simplest design that solves today's problem. Avoid solving for anticipated future requirements that have not been confirmed.
- Extract shared logic only when there is clear reuse or a clear boundary benefit. Do not extract an abstraction until the shared concept is stable and has at least two proven, concrete uses.
- Keep functions focused. If a function becomes hard to explain quickly, split it.
- Keep classes cohesive. If a class owns unrelated responsibilities, separate them.
- Treat design docs and feature specs as part of the implementation surface. Update them when behavior changes.

## Distributed systems and service decomposition

- Do not introduce microservices or distributed processing unless there is a clear, specific value case that justifies the cost. Every service boundary adds network latency, serialization overhead, an additional failure point, and operational complexity. A well-structured modular monolith is often faster, cheaper to operate, and easier to reason about than a distributed equivalent.
- Before drawing a service boundary, estimate the data volume, call frequency, and latency budget for the communication that will cross that boundary. Data that moved in-process now consumes real network bandwidth and adds measurable round-trip time. Model these costs against your SLA before committing.
- Use observable signals — not instinct or fashion — as the trigger for decomposition. Growing state machine complexity that spans unrelated concerns, persistent ownership confusion between teams, independent scaling requirements that cannot be met in a single process, and accumulating compensating logic are legitimate decomposition signals. Fashionable architecture patterns are not.
- Keep the number of states in a service's state machine at a level where every state can be named and every transition explained without hesitation. When that becomes difficult, the state machine is signalling that the service boundary may be wrong. Treat this as a prompt to re-examine ownership, not as a mandate to immediately split.
- When crossing process or network boundaries, choose the wire format deliberately based on the specific tradeoffs for your context: latency and parse cost, bandwidth, human readability and debuggability, schema evolution needs, and available tooling. Text formats such as JSON are self-describing and easy to inspect but verbose and slow to parse at high throughput. Binary formats such as Protocol Buffers or Avro are compact and fast but require schema management discipline and tooling to inspect.
- Treat wire format and schema evolution strategy as first-class design decisions at the interface level, not incidental implementation details. Once chosen, changing the wire format is a migration, not a refactor. If a binary format is chosen, establish explicit schema versioning discipline before the first message is sent — a schema registry is one valid implementation of this, but the non-negotiable is the versioning discipline itself, not the tooling. Never mix wire formats on the same interface without explicit versioning — a consumer expecting one format receiving another fails in confusing, hard-to-diagnose ways.
