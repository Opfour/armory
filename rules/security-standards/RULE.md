---
name: security-standards
type: rule
description:
  'Defines security standards for application development including secret
  management (environment variables, vault integration, never hardcode), input validation
  at system boundaries, authentication and session handling (JWT, refresh tokens,
  session expiry), HTTP security headers, file upload restrictions, SQL parameterization,
  dependency scanning, and CORS policy. Use this rule when handling secrets, implementing
  authentication, validating user input, configuring HTTP security, processing file
  uploads, or writing database queries. Triggers on "security rules", "secret management",
  "input validation", "security standards", "JWT handling", "CORS policy", "SQL injection",
  "file upload security", "dependency scanning", "HTTP headers".

  '
metadata:
  version: 1.0.0
  scope: global
  applies_to:
    languages: ["*"]
  category: security
  tags: [security, secrets, input-validation, authentication]
  difficulty: beginner
---

# Security Standards

Standards for secure application development across all repositories and languages.

## Secret Management

### Rules

- Never hardcode secrets, API keys, tokens, passwords, or connection strings in source code
- Store secrets in environment variables for local development
- Use a secrets manager (Vault, AWS Secrets Manager, GCP Secret Manager) in production
- Never commit `.env` files — add to `.gitignore` at project creation
- Rotate secrets on a defined schedule (90 days maximum for API keys)
- Use distinct secrets per environment (dev, staging, production)

### Detection

- Pre-commit hooks scan for high-entropy strings and known secret patterns
- CI pipeline runs secret scanning on every push
- Block merges that introduce patterns matching: API keys, private keys, connection strings, tokens

```python
# blocked — hardcoded secret
API_KEY = "sk-proj-abc123def456"

# required — environment variable
API_KEY = os.environ["API_KEY"]
```

### Configuration Files

- Application config uses `.env` (local) or environment variables (deployed)
- Schema validation for config at startup — fail fast on missing required values
- Separate config for connection strings, feature flags, and operational parameters
- Never log secret values, even at debug level

## Input Validation

### Boundary Rule

Validate all input at the system boundary — the first point where external data enters your code:

- HTTP request bodies, query parameters, headers
- CLI arguments
- File contents (uploaded or read from disk)
- Database query results from untrusted sources
- Message queue payloads
- WebSocket messages

### Validation Requirements

- Validate type, length, format, and range
- Use allowlists over denylists — define what IS valid, not what is invalid
- Reject invalid input immediately with a descriptive error — never silently coerce
- Sanitize output (HTML encoding, SQL parameterization) separately from input validation

```python
# validate at the boundary
def create_user(request: CreateUserRequest) -> User:
    if len(request.username) < 3 or len(request.username) > 64:
        raise ValidationError("username must be 3-64 characters")
    if not USERNAME_PATTERN.match(request.username):
        raise ValidationError("username must be alphanumeric with hyphens")
    # internal code trusts validated data from here
```

### Numeric Input

- Validate ranges explicitly — never accept unbounded integers
- Check for integer overflow on multiplication and exponentiation
- Reject NaN and Infinity for floating-point inputs

## Authentication and Session Handling

### JWT Requirements

- Use RS256 or ES256 — never HS256 with a weak or shared secret
- Set `exp` claim on every token (maximum 15 minutes for access tokens)
- Use refresh tokens for session extension (maximum 7 days, rotated on use)
- Validate `iss`, `aud`, and `exp` claims on every request
- Store refresh tokens server-side with ability to revoke
- Never store JWTs in localStorage — use httpOnly, secure, sameSite cookies

### Session Rules

- Generate session IDs with cryptographically secure random generators (minimum 128 bits)
- Invalidate sessions on logout, password change, and privilege escalation
- Set absolute session timeout (8 hours) and idle timeout (30 minutes)
- Bind sessions to user agent and IP range to detect hijacking

### Password Requirements

- Minimum 12 characters, no maximum length (up to 128 chars for DoS prevention)
- Use bcrypt, scrypt, or argon2id for hashing — never MD5, SHA-1, or SHA-256 alone
- Enforce breached password checking (HaveIBeenPwned API or local k-anonymity check)
- Rate-limit login attempts: 5 per minute per account, 20 per minute per IP

## HTTP Security Headers

Every HTTP response includes these headers:

```
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
Cache-Control: no-store (for authenticated responses)
```

- Adjust CSP directives per application needs, but never use `unsafe-eval`
- HSTS `max-age` must be at least 1 year (31536000 seconds)
- Remove `X-Powered-By` and server version headers

## File Upload Security

### Restrictions

- Validate file type by content (magic bytes), not extension or MIME type
- Maximum file size: enforce at reverse proxy and application level
- Store uploaded files outside the web root — never serve directly from the upload directory
- Generate random filenames — never use user-supplied filenames for storage
- Scan uploads with antivirus/malware detection before processing
- Strip EXIF metadata from images before storage

### Blocked Operations

- Never execute uploaded files
- Never include uploaded file paths in server-side includes or templates
- Never decompress archives without size limits (zip bomb protection)

## SQL and Database Security

### Parameterization

- Use parameterized queries or ORM query builders for every database operation
- Never concatenate user input into SQL strings

```python
# blocked — SQL injection
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# required — parameterized
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

### Access Control

- Use least-privilege database accounts — application users never have DDL permissions
- Separate read and write database credentials where possible
- Audit log all schema changes and privilege grants

## Dependency Scanning

### Requirements

- Run dependency vulnerability scanning on every CI build
- Block merges that introduce dependencies with known critical or high CVEs
- Pin all dependency versions — no floating ranges in production
- Review dependency licenses for compatibility before adding
- Maximum 7-day SLA to patch critical vulnerabilities, 30-day for high

### Tools

- Use `dependabot`, `renovate`, or equivalent for automated dependency updates
- Run `npm audit`, `pip-audit`, `cargo audit`, or language-equivalent in CI
- Generate and maintain SBOM (Software Bill of Materials) for production deployments

## CORS Policy

### Rules

- Never use `Access-Control-Allow-Origin: *` on authenticated endpoints
- Allowlist specific origins — derive from configuration, not hardcoded strings
- Restrict `Access-Control-Allow-Methods` to the methods the endpoint supports
- Set `Access-Control-Max-Age` to cache preflight responses (600 seconds default)
- Include `Vary: Origin` when the response depends on the request origin
- Credentials mode (`Access-Control-Allow-Credentials: true`) requires explicit origin (not wildcard)

```python
# correct — explicit origin from config
ALLOWED_ORIGINS = os.environ["CORS_ORIGINS"].split(",")

# blocked — wildcard with credentials
Access-Control-Allow-Origin: *
Access-Control-Allow-Credentials: true
```
