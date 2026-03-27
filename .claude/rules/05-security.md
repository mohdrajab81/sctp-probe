# Security Rules

- Treat all external input as untrusted. Validate format, type, range, and length at boundaries.
- Use parameterized queries and safe encoders; never build SQL, shell commands, or markup unsafely from raw input.
- Encode output for the target context before writing: HTML encoding for HTML output, JSON encoding for JSON, shell escaping for shell, URL encoding for URLs. Input validation and output encoding are complementary controls, not interchangeable.
- Enforce authorization at every protected operation. Do not assume a caller is authorized because they are authenticated or because an earlier check passed elsewhere in the call chain.
- Follow least privilege for runtime identities, service accounts, file permissions, and data access.
- Use secure defaults: TLS where applicable, modern algorithms, and no insecure fallback modes in production.
- Never commit secrets. Use environment variables, secret managers, or approved configuration stores.
- Prefer trusted, actively maintained libraries and official package managers.
- Avoid obscure or hallucinated dependencies. If adding a dependency, justify why the standard library or existing repo dependencies are insufficient.
- Pin dependency versions. Review changelogs before upgrading. Do not accept automatic major-version upgrades without explicit review.
- Run the repository's security checks when available and call out unresolved findings.

## CSRF defense

- For any server-rendered or cookie-authenticated endpoint, require CSRF token validation on all state-changing operations (POST, PUT, PATCH, DELETE). Do not rely on SameSite cookies alone as the only control — browser support and deployment context vary. AI-generated web endpoint code must include a CSRF defense by default, not as an optional hardening step.
- Validate CSRF tokens server-side on every state-changing request. Token presence in the request does not imply validity; check origin and token value together.

## Rate limiting and abuse control

- Every public or partner-facing endpoint must have a rate limit. Define the limit before the endpoint is deployed, not after abuse is observed. Absence of a rate limit is a design defect, not a performance concern.
- Apply rate limits at the authenticated identity layer when available, not only at IP address. IP-based limits alone are trivially bypassed and penalize legitimate users behind shared NAT.

## Supply chain integrity

- For any build artifact published to a package registry or deployed to production, generate and retain a build provenance record capturing: source commit, build environment, build inputs, and the identity of the build system. This is the minimum SLSA Level 1 requirement and establishes a baseline for supply-chain incident investigation.
- SLSA Level 1 (provenance record exists) is the appropriate baseline for internal services and private registries. Teams publishing artifacts to public registries, operating in regulated industries, or integrating with third-party supply chain verification should target Level 2 (build service generates and signs the attestation) and evaluate Level 3 (hermetic, verifiable build environment) against their specific threat model. Moving between levels is a deliberate security investment decision, not an automatic upgrade.
- Do not consume a third-party dependency that has no verifiable release provenance — signed release, reproducible build, or known-good hash in lockfile. If provenance cannot be verified, treat the dependency as untrusted and escalate before adopting it.
