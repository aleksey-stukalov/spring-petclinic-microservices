# Default review rubric

Use this rubric unless a higher-precedence `review-requirements.md` or explicit user instruction overrides it. Review every applicable dimension, but report only evidence-backed findings. “Not applicable” is better than forced commentary.

## Evidence threshold

A reportable finding needs all of the following:

- A specific changed line or hunk that introduces, removes, or exposes the behavior.
- A concrete mechanism: violated invariant, reachable failure path, incompatible contract, measurable resource risk, or material maintenance burden.
- An affected surface and credible blast radius.
- A proportionate proposal that addresses the cause rather than merely the symptom.
- Confidence of at least medium after checking nearby guards, tests, callers, configuration, and relevant platform behavior.

Anchor the primary claim to the changed diff. Add supporting anchors when multiple locations are needed to demonstrate the causal chain. A missing test, migration, rollback path, or license proof can be a finding, but anchor it to the change that creates the obligation and state precisely what is absent.

Do not report:

- Style preferences already enforced by formatters or linters.
- Generic “add tests,” “improve error handling,” or “consider performance” advice without a named behavior and scenario.
- Pre-existing defects the change neither worsens nor makes reachable; note them outside the findings only when they materially constrain the review.
- Vulnerability, performance, or license claims based only on package reputation, memory, or an unverified version assumption.
- Multiple symptoms of one root cause as separate findings.
- Pure praise or a green item added only to make the report look balanced.

## Prioritization and finding budget

Group every manifestation of the same root cause into one finding. Sort findings
by severity, then credible blast radius, then confidence. Include every red
finding even when that exceeds the normal budget. Otherwise cap combined red
and yellow findings at 15 and green findings at 5. Keep the highest-value items
and state how many lower-severity candidates were omitted and the selection
rule used. A budget is a noise control, never a reason to hide a release blocker.

When essential context is unavailable, either omit the claim or frame a specific verification request as yellow if the uncertainty itself creates material release risk. Never present an assumption as an observed fact.

## Severity and confidence

Severity measures impact if the evidenced scenario occurs, combined with its credible reach. Confidence measures how strongly the repository and tool evidence establish that scenario. Do not lower severity merely because confidence is medium; explain what remains to verify.

### 🔴 Red — release or merge blocker

Use red when the change has a credible path to severe harm or cannot safely ship as proposed, for example:

- Exploitable authorization bypass, injection, secret exposure, or material privacy breach.
- Data loss, corruption, irreversible migration failure, cross-tenant exposure, or a deterministic outage/deadlock on a supported path.
- An unversioned breaking public API, wire, schema, storage, or deployment contract with affected consumers.
- A build/runtime failure on a required target or a violated project invariant explicitly defined as blocking.
- A demonstrated license incompatibility for the project's actual use and distribution model.

Red requires a clear causal chain and concrete affected surface. Mere possibility, an unverified advisory, or uncertainty about a license is not red.

### 🟡 Yellow — material concern

Use yellow for a credible issue worth fixing or explicitly accepting before release, such as:

- Incorrect behavior on a realistic edge case with contained or recoverable impact.
- Missing rollback, migration, timeout, cancellation, idempotency, observability, or targeted test coverage on a risky path.
- Plausible performance/resource regression on a relevant workload.
- Compatibility or supply-chain uncertainty supported by evidence but needing one bounded verification step.
- Maintainability debt that makes a likely near-term change unsafe, not merely less elegant.

### 🟢 Green — non-blocking, actionable note

Use green sparingly for a concrete low-impact improvement whose omission does not threaten correctness, security, compatibility, reliability, or operability. A green item still needs evidence and a useful proposal. If there are no actionable findings, one green “No actionable findings” summary row is required; do not create a detailed pseudo-finding for it.

Confidence is `High` when the behavior is directly demonstrated by code, tests, or a reproducible command, and `Medium` when the causal path is solid but one environmental or consumer fact remains. Do not publish low-confidence speculation as a finding.

## Review dimensions

### Architecture cleanliness

Check boundary direction, ownership, cohesion, coupling, dependency inversion, layering, lifecycle placement, and whether the change duplicates or bypasses an established abstraction. Look for cross-cutting state or policies placed in a leaf component and for domain logic leaking into transport, persistence, or UI layers. Prefer repository conventions over an abstract ideal.

### Correctness and data integrity

Trace nominal and boundary behavior, null/empty states, numeric and time semantics, encoding, ordering, partial failure, error propagation, and state transitions. Check validation at trust boundaries and transactional behavior across writes. Verify that tests assert observable behavior rather than only implementation details.

### Implementation quality

Look for a simpler correct mechanism, inconsistent invariants, misleading naming, unreachable or duplicated logic, accidental complexity, unsafe type escapes, and error handling that loses context. Avoid aesthetic comments that do not affect comprehension or change safety.

### Security and privacy

Evaluate authentication and authorization separately; input validation and output encoding; injection and request forgery; path/archive handling; unsafe deserialization; secrets and cryptography; tenant isolation; sensitive logging; collection, retention, and deletion of personal data; and least privilege. Identify attacker capability, entry point, and protected asset. Never call a theoretical primitive exploitable without a reachable path.

### Performance and resource use

Inspect algorithmic growth, repeated I/O or network calls, query shape, allocation/copying, cache semantics, batching, pagination, backpressure, startup cost, and unbounded memory/disk/queue growth. Tie findings to a relevant workload or hot path. Do not demand micro-optimizations without evidence.

### Concurrency and state

Check races, lock ordering and scope, atomicity, thread/async safety, lost updates, reentrancy, cancellation, shared mutable state, ordering guarantees, duplicate delivery, and lifecycle cleanup. Account for multiple processes or replicas where the system supports them.

### Reliability and observability

Check timeout and retry interaction, idempotency, circuit breaking, failure isolation, cleanup, fallback behavior, crash recovery, and degraded modes. Ensure operators can detect and diagnose important failures through useful logs, metrics, traces, health signals, or audit events without leaking sensitive data.

### Maintainability and testability

Assess readability of invariants, modularity, extension points, ownership boundaries, determinism, test seams, fixtures, and focused regression coverage. Flag debt only when it creates a concrete cost or risk. Check whether comments and documentation explain non-obvious constraints and stay aligned with behavior.

### API, data, and schema compatibility

Consider source, binary, wire, behavioral, serialization, storage, configuration, and CLI compatibility. Trace known consumers and versioning promises. For schema or data migrations, examine expand/migrate/contract ordering, old/new version coexistence, defaults, backfill, validation, reversibility, and rolling deployment. A type-checking build is not proof of runtime or consumer compatibility.

### Dependencies, supply chain, and licenses

Ask whether a new dependency is necessary and appropriately scoped. Inspect the manifest and lockfile together for pinning, integrity data, source/provenance, transitive changes, install scripts, vendoring, duplicate versions, runtime footprint, and supported platform effects. Use existing scanner results, or scanners explicitly authorized for execution, and authoritative package metadata when available; do not invent vulnerabilities.

License compatibility depends on the exact version/artifact, direct and transitive licenses, linking or aggregation model, modification, distribution channel, and the project's own license and obligations. Record the evidence source. Treat missing or ambiguous license evidence as a bounded verification need, not as an established violation. Escalate to red only when incompatibility is demonstrated for the actual distribution model.

### UX, accessibility, and internationalization

When user-facing behavior changes, check task clarity, feedback, error recovery, destructive-action safeguards, keyboard and assistive-technology semantics, focus, contrast, motion, responsive behavior, localization of text and formats, pluralization, text expansion, bidirectionality, and time-zone/locale assumptions. Do not apply web-only expectations to non-visual changes.

### Operations and deployment

Review configuration defaults and validation, secrets handling, feature flags, migrations, rollout order, backward coexistence, health checks, resource limits, platform compatibility, rollback/roll-forward plans, and runbook or alert changes. Consider CI/CD and packaging effects and whether partial deployment is safe.

### Risk and blast radius

Apply this across every dimension. Identify affected callers, users, tenants, services, persisted data, platforms, and operators; whether failure is contained or cascading; whether detection is prompt; and whether recovery is automatic, manual, or impossible. Call out irreversible effects, central/shared components, privilege boundaries, and changes that amplify load or failure across replicas.

## Overall verdict

Use one verdict:

- `Changes requested` when any red finding exists.
- `Ready with concerns` when yellow findings exist but no red finding does.
- `Ready with follow-ups` when only green findings exist.
- `Ready` when there are no actionable findings.
- `Blocked — review incomplete` only when missing access or evidence prevents a responsible review of material scope.

The verdict summarizes findings; it is not an independent score.
