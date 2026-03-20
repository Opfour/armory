---
name: test-standards
type: rule
description: >
  Defines testing standards including coverage thresholds (80% overall, 90% new code, 95% critical
  paths), test naming conventions, structural patterns (arrange-act-assert), test categorization
  (unit/integration/e2e), fixture management, mock boundaries, and CI gate requirements. Use this
  rule when writing tests, setting up test infrastructure, reviewing test quality, or defining
  coverage requirements. Triggers on "test coverage", "testing standards", "test requirements",
  "coverage thresholds", "unit test", "integration test", "test structure", "arrange act assert",
  "mock boundaries", "test naming".
metadata:
  version: 1.0.0
  scope: global
  applies_to:
    languages: ["*"]
---

# Test Standards

Standards for test coverage, structure, naming, and CI enforcement across all repositories.

## Coverage Thresholds

| Scope              | Minimum Coverage |
| ------------------ | ---------------- |
| Overall codebase   | 80%              |
| New/modified code  | 90%              |
| Critical paths     | 95%              |

### Critical Path Definition

Code is critical when it handles:

- Authentication and authorization
- Payment processing and financial calculations
- Public API endpoints
- Security-sensitive operations (encryption, token validation, input sanitization)
- Data migration and schema changes

Coverage gates run on every pull request. A PR that drops coverage below thresholds is blocked.

## Test Naming

### Convention

```
test_<unit>_<scenario>_<expected_outcome>
```

Examples:

```python
def test_login_valid_credentials_returns_token():
def test_login_expired_password_raises_auth_error():
def test_parse_config_missing_file_uses_defaults():
```

```typescript
it("returns 401 when token is expired")
it("creates user with valid email and hashed password")
it("rejects duplicate usernames with conflict error")
```

### Rules

- Name describes behavior, not implementation
- Include the expected outcome in the name
- Never use `test_1`, `test_function`, or generic names
- Group related tests under a describe/class named after the unit under test

## Test Structure: Arrange-Act-Assert

Every test follows three distinct phases:

```python
def test_transfer_sufficient_funds_debits_sender():
    # Arrange
    sender = Account(balance=1000)
    receiver = Account(balance=500)

    # Act
    transfer(sender, receiver, amount=200)

    # Assert
    assert sender.balance == 800
    assert receiver.balance == 700
```

- **Arrange**: Set up preconditions and inputs
- **Act**: Execute the single behavior under test
- **Assert**: Verify the expected outcome

One logical assertion per test. Multiple `assert` statements are acceptable when they verify a single behavior (e.g., checking both status code and body of an HTTP response).

## Test Categories

### Unit Tests

- Test a single function, method, or class in isolation
- No network, filesystem, or database access
- Execute in < 100ms per test
- Mock all external dependencies at the boundary
- Run on every commit

### Integration Tests

- Test interaction between two or more real components
- Use real database (test container or in-memory)
- Use real filesystem (temp directories)
- Execute in < 5s per test
- Run on every pull request

### End-to-End Tests

- Test complete user flows through the system
- Use real (or staging) infrastructure
- Execute in < 60s per test
- Run on merge to main or on a schedule

### When to Use Each

| Signal                           | Test Type   |
| -------------------------------- | ----------- |
| Pure function, no side effects   | Unit        |
| Database query correctness       | Integration |
| API contract between services    | Integration |
| User login through UI            | E2E         |
| Payment flow across services     | E2E         |
| Config parsing logic             | Unit        |
| File upload and storage          | Integration |

## Fixture Patterns

### Principles

- Fixtures are reusable test data factories, not copy-pasted literals
- Use factory functions or builder patterns over raw dictionaries
- Keep fixtures close to the tests that use them; shared fixtures go in `conftest.py` / `fixtures/`
- Never use production data in fixtures
- Name fixtures after the scenario they represent, not the data shape

```python
# correct
@pytest.fixture
def expired_jwt_token():
    return create_token(exp=datetime.now() - timedelta(hours=1))

# incorrect
@pytest.fixture
def token():
    return "eyJhbGciOiJIUzI1NiJ9..."
```

### Cleanup

- Every fixture that creates state must clean it up (use `yield` with teardown or `addCleanup`)
- Database fixtures use transactions that roll back after each test
- File fixtures use temporary directories that auto-delete

## Mock Boundaries

### What to Mock

- External HTTP APIs (third-party services, payment gateways)
- System clock (`datetime.now`, `time.time`)
- Random/UUID generation when determinism is required
- Environment variables
- File system operations in unit tests only

### What NOT to Mock

- The code under test
- Data structures and value objects
- Pure utility functions
- Database queries in integration tests (use a real test database)
- Internal module boundaries within the same service

### Mock Rules

- Mock at the boundary, not deep inside the call chain
- Verify mock interactions only when the interaction IS the behavior (e.g., "sends email on signup")
- Prefer fakes over mocks when the fake is simpler than the mock setup
- Never mock more than two dependencies per test — if you need more, the unit is too coupled

## What NOT to Test

- Framework internals (ORM save, HTTP router dispatch)
- Third-party library behavior (test your usage, not the library)
- Private methods directly — test through the public interface
- Trivial getters/setters with no logic
- Generated code (protobuf stubs, ORM models with no custom methods)
- Configuration constants

## CI Gate Requirements

- All tests pass (zero failures, zero skipped without annotation)
- Coverage thresholds met (see above)
- No flaky tests — a test that fails intermittently is a bug, not an inconvenience
- Test results report uploaded as CI artifact
- Tests run in parallel where possible; no test depends on execution order
- Maximum CI test suite runtime: 10 minutes for unit, 30 minutes for integration
- Flaky test quarantine: move to `@pytest.mark.flaky` or `it.skip` with a linked issue, fix within one sprint
