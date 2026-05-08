# AGENTS.md

## 0. Purpose

This repository is maintained with help from LLM coding agents.

LLM agents are useful for fast implementation, but they tend to produce code that merely works locally while weakening robustness, readability, maintainability, security, performance, and operational safety.

This document is the mandatory operating contract for all coding agents working in this repository.

The goal is not to maximize generated code volume. The goal is to produce small, reviewable, tested, observable, secure, and maintainable changes that can survive production operation.

---

## 1. Core Principles

### 1.1 Treat every change as production-bound

Do not write "prototype-quality" code unless the task explicitly says it is a throwaway prototype.

Default assumption:

- The code will be read by another engineer.
- The code will be modified later.
- The code may run in production.
- The code may fail under unexpected input.
- The code may become a security boundary.
- The code may be debugged at 3 a.m. by someone who did not write it.

Therefore, every implementation must prioritize correctness, clarity, testability, observability, and safe failure.

### 1.2 Prefer boring, explicit code

Do not use clever abstractions, metaprogramming, hidden global state, dynamic imports, implicit side effects, or framework magic unless there is a clear architectural reason.

Good code is usually:

- Explicit.
- Small.
- Typed.
- Testable.
- Easy to delete.
- Easy to debug.
- Boring enough that future maintainers can trust it.

### 1.3 Optimize for future change, not just current success

Passing the current test is not enough.

Before finishing, verify that the implementation does not:

- Create a god function.
- Hide errors.
- Add unnecessary coupling.
- Bypass existing architecture.
- Introduce unbounded retries or loops.
- Add dependencies without justification.
- Make future refactoring harder.
- Depend on undocumented behavior.
- Make observability worse.

### 1.4 Small diffs are mandatory

Prefer small, focused changes.

Do not perform broad rewrites, mass formatting, file moves, architectural migrations, or dependency upgrades unless explicitly requested.

If a task appears to require a large change, first narrow it into the smallest safe implementation.

---

## 2. Agent Operating Rules

### 2.1 Read before editing

Before modifying code, inspect the relevant existing files and identify:

- Existing architectural pattern.
- Existing naming conventions.
- Existing error handling style.
- Existing test style.
- Existing dependency boundaries.
- Existing logging / observability conventions.
- Existing CI or build constraints.

Do not introduce a new style simply because it is familiar.

### 2.2 State the intended change before large edits

For non-trivial changes, prepare a short implementation plan before editing.

The plan must include:

- Files to change.
- Public interfaces affected.
- Tests to add or update.
- Possible risks.
- Rollback or failure behavior if relevant.

### 2.3 Do not edit unrelated files

Only modify files directly required for the task.

Forbidden unless explicitly requested:

- Large formatting-only diffs.
- Renaming unrelated symbols.
- Reorganizing folders.
- Upgrading unrelated dependencies.
- Changing lockfiles unnecessarily.
- Touching generated files manually.
- Changing CI/CD configuration as a side effect.

### 2.4 Preserve existing behavior unless explicitly changing it

If behavior changes, make it visible through:

- A test.
- A changelog entry if the repository uses one.
- A migration note if data or config is affected.
- Updated documentation if public usage changes.

---

## 3. Permission and Safety Boundaries

### 3.1 Default to least privilege

Agents must assume read-only intent unless a task clearly requires modification.

High-risk actions require explicit human approval:

- Deleting files.
- Rewriting history.
- Running destructive shell commands.
- Changing production configuration.
- Modifying secrets.
- Changing authentication or authorization logic.
- Disabling tests, linters, type checks, or security checks.
- Adding network calls to new external services.
- Adding new dependencies.
- Modifying deployment scripts.
- Changing database schemas.
- Running migrations.
- Pushing branches or tags.
- Creating releases.

### 3.2 Dangerous commands are forbidden by default

Do not run commands like:

```bash
rm -rf
git reset --hard
git clean -fd
git push --force
chmod -R 777
chown -R
curl ... | sh
wget ... | sh
npm audit fix --force
pip install --upgrade ...
docker system prune
kubectl delete
terraform apply
```

Only run such commands if the user explicitly asks and the risk is clearly explained.

### 3.3 Never expose secrets

Never print, copy, summarize, or commit:

- API keys.
- OAuth tokens.
- Session cookies.
- Private keys.
- Database URLs.
- `.env` contents.
- Production credentials.
- User personal data.
- Proprietary datasets.

If a secret appears in code, logs, screenshots, or test output, stop and report it as a security issue.

### 3.4 Do not silently weaken safeguards

Never remove or loosen the following just to make tests pass:

- Authentication checks.
- Authorization checks.
- Input validation.
- Rate limits.
- CSRF protection.
- CORS restrictions.
- SQL parameterization.
- Output escaping.
- Type checking.
- Security scanning.
- Test assertions.
- Error handling.
- Audit logging.

If a safeguard blocks the implementation, the correct response is to fix the implementation, not the safeguard.

---

## 4. Code Quality Requirements

### 4.1 Functions must be small and single-purpose

Avoid god functions.

A function should usually do one of these:

- Validate input.
- Transform data.
- Execute one business operation.
- Call one external dependency.
- Format output.
- Coordinate a workflow.

It should not do all of them at once.

Guidelines:

- Prefer functions under 50 lines.
- Avoid nesting deeper than 3 levels.
- Extract pure logic from I/O.
- Keep validation separate from persistence.
- Keep domain logic separate from UI and transport code.

### 4.2 Use meaningful names

Forbidden low-signal names unless their scope is tiny and obvious:

- `data`
- `result`
- `result2`
- `tmp`
- `obj`
- `thing`
- `stuff`
- `handle`
- `process`
- `doStuff`
- `manager`
- `helper`

Names should describe domain meaning, not implementation convenience.

Bad:

```ts
const data = await getData();
```

Better:

```ts
const activeSubscriptions = await fetchActiveSubscriptions();
```

### 4.3 Comments must explain why, not what

Do not add comments that merely restate the code.

Bad:

```ts
// Increment count
count++;
```

Good:

```ts
// Stripe may retry this webhook, so the operation must be idempotent.
await markInvoicePaidOnce(invoiceId);
```

Public APIs, non-obvious business rules, security-sensitive logic, and operational tradeoffs should be documented.

### 4.4 Avoid premature abstraction

Do not create abstractions before there are at least two clear use cases or a strong architectural reason.

Avoid:

- Generic managers.
- Overly flexible config objects.
- Plugin systems.
- Deep inheritance.
- Abstract base classes without a real need.
- Reusable helpers that obscure domain logic.

Duplication is sometimes cheaper than the wrong abstraction.

### 4.5 Do not introduce hidden global state

Avoid mutable module-level state unless necessary.

Risky patterns:

- Global caches without invalidation.
- Global clients with hidden configuration.
- Singleton managers.
- Shared mutable lists or dictionaries.
- Runtime monkey patching.
- Environment reads scattered throughout business logic.

Prefer explicit dependency injection for clocks, random generators, HTTP clients, repositories, and external services.

---

## 5. Type and Schema Discipline

### 5.1 Types are mandatory for new public interfaces

All new public functions, exported functions, API handlers, service methods, and domain objects must have explicit types.

For TypeScript:

- `strict` must remain enabled.
- `any` is forbidden unless justified.
- `unknown` is preferred over `any` at external boundaries.
- Use discriminated unions for state machines and error variants.
- Do not suppress errors with `as any`.

For Python:

- Add type hints to new or modified functions.
- Use `TypedDict`, `dataclass`, `pydantic`, or equivalent schema objects when handling structured data.
- Avoid untyped dictionaries for domain objects.
- Do not silence type checkers with broad ignores.

### 5.2 Validate external input at boundaries

Every external input must be validated before use.

External input includes:

- HTTP request bodies.
- Query parameters.
- Headers.
- Webhook payloads.
- CLI arguments.
- Environment variables.
- Database records if schema drift is possible.
- LLM output.
- User-uploaded files.
- Third-party API responses.

Validation must check:

- Type.
- Required fields.
- String length.
- Numeric range.
- Enum membership.
- Date/time format.
- Identifier format.
- File size and MIME type where relevant.

### 5.3 Do not trust LLM output

LLM output is untrusted input.

If code consumes LLM output, it must:

- Parse against a schema.
- Reject invalid shape.
- Avoid direct execution.
- Avoid direct database writes without validation.
- Avoid direct shell command use.
- Handle missing, malformed, or adversarial content.
- Log validation failures without leaking sensitive content.

---

## 6. Error Handling

### 6.1 Never swallow errors silently

Forbidden:

```python
try:
    do_work()
except Exception:
    pass
```

Forbidden:

```ts
try {
  await doWork();
} catch {
  return null;
}
```

If an error is intentionally ignored, explain why and limit the catch to a specific exception type.

### 6.2 Classify errors

Distinguish at least:

- Validation errors.
- Authentication errors.
- Authorization errors.
- Not found errors.
- Conflict errors.
- Rate limit errors.
- Timeout errors.
- Upstream service errors.
- Internal bugs.

Do not collapse all failures into `500`, `null`, `{}`, or `false`.

### 6.3 Preserve original error context

When wrapping errors, preserve the cause.

Python:

```python
raise UpstreamTimeout("Payment provider timed out") from exc
```

TypeScript:

```ts
throw new PaymentProviderError("Payment provider timed out", { cause: error });
```

### 6.4 Retry only transient failures

Retries are allowed only for transient failures such as:

- Timeouts.
- 429 rate limits.
- Temporary network failures.
- 5xx upstream errors where retry is safe.

Retries must have:

- Maximum attempt count.
- Exponential backoff or jitter.
- Timeout.
- Idempotency protection.
- Logging or metrics.

Forbidden:

- Infinite retries.
- Retrying validation errors.
- Retrying authorization failures.
- Retrying non-idempotent writes without idempotency keys.

---

## 7. Security Requirements

### 7.1 Parameterize queries

Never build SQL using string concatenation or template interpolation with untrusted input.

Bad:

```python
sql = f"SELECT * FROM users WHERE name = '{name}'"
```

Good:

```python
cursor.execute("SELECT * FROM users WHERE name = ?", (name,))
```

If dynamic sorting or column selection is needed, use an allowlist.

### 7.2 Escape output

Any user-controlled content rendered into HTML, Markdown, shell, SQL, CSV, logs, or URLs must be escaped or encoded for that context.

Do not assume framework defaults are sufficient without checking.

### 7.3 Normalize paths

For file operations:

- Normalize paths.
- Prevent path traversal.
- Use allowlisted directories.
- Reject absolute paths unless explicitly intended.
- Do not trust file names from uploads.

### 7.4 Avoid dangerous execution

Forbidden unless explicitly required and sandboxed:

- `eval`
- `exec`
- shell execution with untrusted input
- dynamic code loading
- unsafe deserialization
- arbitrary template execution

### 7.5 Secrets must come from secure configuration

Do not hard-code secrets.

Do not commit `.env` files.

Do not log secrets.

Do not include secrets in error messages.

Do not pass secrets to LLM prompts.

### 7.6 Authentication and authorization changes require tests

Any change touching auth must include tests for:

- Allowed user.
- Disallowed user.
- Unauthenticated user.
- Expired credential.
- Wrong tenant / wrong organization.
- Privilege escalation attempt.

---

## 8. Dependency Management

### 8.1 Do not add dependencies casually

Before adding a dependency, verify:

- It is actively maintained.
- It has a compatible license.
- It has no known critical vulnerabilities.
- It is necessary.
- The functionality is not already available in the repository.
- The dependency does not introduce excessive transitive dependencies.

Prefer standard library or existing dependencies for small tasks.

### 8.2 Lockfiles must be respected

Do not manually edit lockfiles unless that is the intended task.

If dependencies change, update the lockfile through the package manager.

### 8.3 Pin versions where appropriate

Avoid floating versions for production dependencies.

Bad:

```txt
requests>=2
```

Better:

```txt
requests==2.32.3
```

Use the repository's existing dependency policy if present.

### 8.4 Supply-chain checks must remain enabled

Do not disable:

- Dependency review.
- Vulnerability scanning.
- Secret scanning.
- License scanning.
- SBOM generation.
- Artifact attestation.
- Signature verification.

---

## 9. Testing Requirements

### 9.1 Every behavior change needs a test

If the code behavior changes, add or update tests.

Do not rely only on manual testing.

At minimum, cover:

- Normal case.
- Invalid input.
- Boundary values.
- Failure path.
- Permission-relevant path where applicable.

### 9.2 Prefer testing behavior, not implementation

Do not write brittle tests that only mirror internal implementation.

Test observable behavior:

- Return values.
- State changes.
- Emitted events.
- HTTP responses.
- Database records.
- Logs or metrics where operationally important.

### 9.3 Separate pure logic from I/O

Pure logic should be unit tested without network, database, file system, real time, or randomness.

External systems should be tested through integration tests or contract tests.

### 9.4 Avoid flaky tests

Forbidden in tests unless there is a strong reason:

- Fixed sleeps.
- Live external network calls.
- Real current time.
- Randomness without seed control.
- Order dependency.
- Shared mutable global state.
- Depending on local machine state.

Bad:

```ts
await page.waitForTimeout(2000);
```

Better:

```ts
await expect(page.getByTestId("status")).toHaveText("Submitted");
```

### 9.5 Coverage is not enough

Do not generate shallow tests merely to increase line coverage.

Good tests catch bugs. Bad tests execute lines.

Critical code should consider:

- Branch coverage.
- Property-based tests.
- Mutation testing.
- Fuzzing.
- Contract tests.
- End-to-end tests.

Critical code includes:

- Authentication.
- Authorization.
- Billing.
- Payments.
- Data deletion.
- Data migration.
- Input validation.
- Security filters.
- Financial calculations.
- User-generated content rendering.
- LLM output handling.

---

## 10. Performance Requirements

### 10.1 Avoid obvious inefficient patterns

Do not introduce:

- N+1 queries.
- Unbounded loops over user-controlled data.
- Loading large files fully into memory.
- Repeated API calls inside loops.
- Unbounded recursion.
- Unbounded concurrency.
- Unbounded retries.
- Full table scans without justification.
- Recomputing expensive values repeatedly.

### 10.2 State complexity when relevant

For data-processing code, document or make clear:

- Expected input size.
- Time complexity.
- Memory behavior.
- Pagination or streaming strategy.
- Backpressure strategy where relevant.

### 10.3 Add performance tests for performance-sensitive changes

If a change affects hot paths, large data paths, rendering performance, database queries, or API latency, add a benchmark or regression test where practical.

Track at least:

- P95 latency.
- P99 latency if user-facing.
- Query count.
- Memory growth.
- Payload size.
- Bundle size for frontend changes.

---

## 11. Observability and Operations

### 11.1 Structured logs are required for operational paths

Operationally important code should emit structured logs.

Include:

- Event name.
- Request ID or trace ID.
- User ID or tenant ID only when safe.
- Error code.
- Operation name.
- Duration where useful.
- Outcome.

Do not log:

- Secrets.
- Raw tokens.
- Full request bodies with personal data.
- Payment details.
- Sensitive LLM prompts.
- Private user content unless explicitly safe.

### 11.2 Errors need stable error codes

User-facing and operationally important failures should have stable error codes.

Bad:

```json
{ "error": "Something went wrong" }
```

Better:

```json
{
  "error": {
    "code": "PAYMENT_PROVIDER_TIMEOUT",
    "message": "Payment processing is temporarily unavailable."
  }
}
```

### 11.3 New features need rollback thinking

Any risky feature should include at least one:

- Feature flag.
- Kill switch.
- Config toggle.
- Canary deployment.
- Safe fallback.
- Rollback instruction.

### 11.4 Background jobs must be idempotent

Jobs, queues, webhooks, and scheduled tasks must handle retries safely.

Require:

- Idempotency key.
- Deduplication where needed.
- Safe retry policy.
- Dead-letter handling or failure visibility.
- Timeout.
- Observability.

---

## 12. Architecture Boundaries

### 12.1 Respect existing layers

Do not bypass established boundaries.

Typical boundaries:

- UI layer.
- API / transport layer.
- Application service layer.
- Domain layer.
- Repository / persistence layer.
- Infrastructure adapter layer.
- External API client layer.

Bad:

- UI directly querying the database.
- Domain logic reading environment variables.
- API handler containing complex business rules.
- Repository calling third-party APIs.
- Test utilities imported into production code.

### 12.2 Keep domain logic independent

Domain logic should not depend on:

- HTTP request objects.
- Framework-specific response objects.
- Database clients.
- UI components.
- Environment variables.
- Wall-clock time.
- Randomness.
- Network calls.

Inject these dependencies.

### 12.3 Use adapters for external systems

External APIs, databases, queues, storage, and LLM providers should be accessed through adapters or clients.

Benefits:

- Easier testing.
- Easier provider replacement.
- Centralized retry and timeout logic.
- Centralized logging and metrics.
- Clear failure semantics.

---

## 13. Frontend Requirements

### 13.1 Accessibility is required

Frontend changes must preserve:

- Semantic HTML.
- Keyboard navigation.
- Visible focus states.
- Proper labels.
- Sufficient contrast.
- Screen-reader-friendly structure.
- No reliance on color alone.
- Correct ARIA usage only when necessary.

Run accessibility checks when UI changes are meaningful.

### 13.2 Avoid fragile selectors in tests

Prefer role-based or stable test IDs.

Good:

```ts
page.getByRole("button", { name: "Submit" })
page.getByTestId("payment-status")
```

Bad:

```ts
page.locator("div > div:nth-child(3) > button")
```

### 13.3 Keep UI state explicit

Avoid inconsistent duplicated state.

Be careful with:

- Derived state stored separately.
- Race conditions in async effects.
- Missing loading states.
- Missing error states.
- Missing empty states.
- Updates after component unmount.
- Optimistic updates without rollback.

### 13.4 Do not hard-code user-facing strings if i18n exists

If the project has localization infrastructure, all new user-facing strings must use it.

Dates, numbers, currency, pluralization, and relative time must be locale-aware.

---

## 14. API Requirements

### 14.1 API endpoints must define contracts

Every new or modified endpoint should have:

- Request schema.
- Response schema.
- Error schema.
- Authentication requirement.
- Authorization rule.
- Rate-limit consideration.
- Idempotency rule for writes where relevant.

### 14.2 Use correct HTTP semantics

Use appropriate status codes:

- `400` invalid request.
- `401` unauthenticated.
- `403` authenticated but not allowed.
- `404` not found.
- `409` conflict.
- `422` semantic validation failure if used by the framework.
- `429` rate limited.
- `500` internal bug.
- `502/503/504` upstream or availability failure.

### 14.3 Writes should be idempotent where possible

For payment, webhook, job, and retry-sensitive writes, use idempotency keys or deduplication.

---

## 15. Database Requirements

### 15.1 Migrations require care

Database schema changes must include:

- Migration file.
- Rollback or forward-fix strategy.
- Backfill strategy if needed.
- Compatibility with existing deployed code.
- Test or local verification.
- Index impact consideration.
- Locking or downtime risk consideration.

### 15.2 Avoid destructive migrations by default

Do not drop columns, drop tables, rewrite large tables, or add non-null columns without defaults unless explicitly approved.

Prefer expand-contract migration:

1. Add nullable field or new table.
2. Deploy code that writes both old and new paths.
3. Backfill.
4. Read from new path.
5. Remove old path later.

### 15.3 Query performance matters

For new queries, consider:

- Index availability.
- Query count.
- Pagination.
- Sorting cost.
- Tenant filtering.
- Data volume.
- Transaction scope.

---

## 16. LLM-Specific Implementation Rules

### 16.1 Do not invent APIs

Before using a library API, verify it exists in the repository's installed version.

Use:

- Existing code examples.
- Lockfile.
- Official docs if available.
- Type definitions.
- Tests or import checks.

Do not rely on memory of a library's API.

### 16.2 Do not create fake tests

Tests must verify real behavior.

Forbidden:

- Tests that only assert mocks were called without validating outcome.
- Tests that duplicate implementation logic.
- Tests that always pass.
- Tests with weak assertions like `expect(result).toBeTruthy()` when exact behavior is known.
- Snapshot tests for large unstable output without a reason.

### 16.3 Do not use broad fallback behavior to hide uncertainty

Bad patterns:

```ts
return value || defaultValue;
```

```python
return payload.get("field", "")
```

These are acceptable only when the default is part of the explicit business rule.

Otherwise, validate and fail clearly.

### 16.4 Do not overfit to the visible failing test

When fixing a bug:

- Identify root cause.
- Add a regression test.
- Check adjacent cases.
- Avoid hard-coded special cases.
- Avoid changing the test to match broken behavior.

### 16.5 Do not generate large speculative systems

Do not create:

- Plugin frameworks.
- Generic workflow engines.
- Abstract repositories.
- Custom ORMs.
- Custom validation frameworks.
- Custom logging frameworks.
- Custom state machines.

Unless the task explicitly requires them.

---

## 17. Documentation Requirements

### 17.1 Update docs when behavior changes

Update relevant documentation when changing:

- Public API.
- CLI usage.
- Environment variables.
- Setup steps.
- Deployment process.
- Database schema.
- Authentication behavior.
- Error codes.
- Operational runbooks.

### 17.2 Document operational decisions

For non-obvious decisions, document:

- Why this approach was chosen.
- What alternatives were rejected.
- What risk remains.
- How to roll back.
- What metric indicates failure.

---

## 18. Required Validation Before Completion

Before claiming a task is complete, run the smallest relevant validation set.

Prefer this order:

1. Format.
2. Lint.
3. Typecheck.
4. Unit tests.
5. Integration tests.
6. Security scan.
7. Build.
8. E2E tests.
9. Performance or accessibility checks if relevant.

If a command cannot be run, say so explicitly and explain why.

Do not say "should work" when validation was not performed.

### 18.1 Completion report format

At the end of a non-trivial task, report:

```md
## Summary
- What changed.

## Validation
- Commands run and results.

## Risks / Notes
- Remaining risks, skipped checks, or assumptions.
```

If validation failed, do not hide it.

---

## 19. Review Checklist

Before submitting a change, verify:

### Correctness

- [ ] Does the code implement the requested behavior?
- [ ] Are edge cases handled?
- [ ] Are invalid inputs rejected?
- [ ] Are errors classified correctly?
- [ ] Are retries safe and bounded?

### Maintainability

- [ ] Is the diff focused?
- [ ] Are functions small?
- [ ] Are names meaningful?
- [ ] Is business logic separated from I/O?
- [ ] Is the code easy to delete or replace?

### Security

- [ ] Are inputs validated?
- [ ] Are queries parameterized?
- [ ] Is output escaped?
- [ ] Are secrets protected?
- [ ] Are permissions preserved?
- [ ] Are dependencies justified?

### Testing

- [ ] Are behavior changes tested?
- [ ] Are failure paths tested?
- [ ] Are auth paths tested if relevant?
- [ ] Are tests deterministic?
- [ ] Are assertions meaningful?

### Operations

- [ ] Are logs structured where needed?
- [ ] Are error codes stable?
- [ ] Are metrics/traces added where needed?
- [ ] Is rollback possible?
- [ ] Is the change safe to deploy incrementally?

---

## 20. Forbidden Shortcuts

The following are not acceptable unless explicitly requested and justified:

- "Temporary" code without a removal plan.
- `TODO` instead of implementation for required behavior.
- Broad `catch` / `except` without handling.
- Disabling lint/type/test/security rules.
- Adding `any` to silence TypeScript.
- Adding `# type: ignore` or equivalent without reason.
- Returning `{}` / `null` / `false` for unknown failures.
- Hard-coding environment-specific values.
- Adding a dependency for trivial functionality.
- Writing tests that do not test behavior.
- Using sleep-based timing in tests.
- Ignoring failed validation commands.
- Modifying generated files manually.
- Making unrelated refactors.
- Pushing destructive migrations.
- Logging sensitive data.
- Trusting LLM output as valid input.

---

## 21. Task-Specific Strict Mode

Use strict mode for high-risk areas.

High-risk areas include:

- Authentication.
- Authorization.
- Payment.
- Billing.
- Personal data.
- File upload.
- LLM output execution or parsing.
- Admin functionality.
- Database migration.
- Infrastructure.
- CI/CD.
- Secrets.
- Production configuration.
- Security-sensitive parsing.
- Multi-tenant data access.

In strict mode:

- No broad exceptions.
- No untyped public functions.
- No new dependency without approval.
- No behavior change without tests.
- No skipped validation.
- No silent fallback.
- No direct shell execution with user-controlled input.
- No merge unless CI passes.

---

## 22. Preferred Implementation Pattern

When adding a feature, prefer this sequence:

1. Define the contract.
2. Add validation.
3. Implement pure domain logic.
4. Add unit tests for pure logic.
5. Add infrastructure adapter.
6. Add integration tests.
7. Add API/UI layer.
8. Add observability.
9. Add failure handling.
10. Run validation.
11. Summarize the change.

Do not start by wiring UI directly to persistence or external services.

---

## 23. Minimal Quality Gates

The repository should eventually enforce these gates in CI.

For Python projects:

```bash
ruff format --check .
ruff check .
mypy .
pytest
coverage run -m pytest
coverage report --fail-under=80
bandit -r .
pip-audit
```

For TypeScript projects:

```bash
npm run format:check
npm run lint
npm run typecheck
npm test
npm run build
npm audit
```

For web UI projects:

```bash
npm run test:e2e
npm run test:a11y
```

For supply-chain hardening:

```bash
# Generate SBOM using the repository's chosen tool.
# Verify dependency review.
# Verify artifact attestation if releases are produced.
```

Do not add these commands blindly. Adapt to the repository's existing toolchain.

---

## 24. Agent Self-Check Before Final Response

Before responding, the agent must ask itself:

1. Did I change only what the task required?
2. Did I preserve existing architecture?
3. Did I avoid broad, hidden, or speculative changes?
4. Did I validate inputs at boundaries?
5. Did I preserve error context?
6. Did I add or update meaningful tests?
7. Did I avoid weakening security?
8. Did I avoid unnecessary dependencies?
9. Did I run the relevant validation commands?
10. Did I clearly report what was not validated?

If the answer to any item is no, report it honestly.

---

## 25. Final Rule

Speed is not the objective.

The objective is a change that is:

- Correct.
- Small.
- Typed.
- Tested.
- Secure.
- Observable.
- Reversible.
- Maintainable.

An LLM agent that produces more code than the reviewer can safely understand is not helping. It is creating operational debt.
