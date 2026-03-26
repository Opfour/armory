---
name: security-scan
type: command
description: 'Security audit workflow that scans a codebase path or scope for vulnerabilities
  across six categories: hardcoded secrets, input validation, authentication and authorization
  logic, dependency vulnerabilities, HTTP security headers, and misconfiguration.
  Produces severity-ranked findings with remediation guidance. Triggers on: "/security-scan",
  "scan for vulnerabilities", "security audit this code", "check for hardcoded secrets",
  "find security issues", "vulnerability scan". Use this command when auditing code
  for security issues before deployment or during review.

  '
metadata:
  version: 1.0.0
  category: review
  tags: [security, scanning, vulnerabilities, audit]
  difficulty: intermediate
command:
  syntax: /security-scan [path-or-scope]
  handler: inline
  dependencies: []
---
# Security Scan — Vulnerability Audit Workflow

When the user invokes `/security-scan [path-or-scope]`, execute this workflow exactly.

## Step 0: Scope Resolution

1. If a path is provided, validate it exists. Scan that subtree.
2. If no path is provided, scan the entire project root.
3. If a scope keyword is provided (e.g., "auth", "api", "config"), resolve to matching
   directories and files.
4. Identify the project language(s) and framework(s) from file extensions, package files,
   and import patterns.

## Step 1: Hardcoded Secrets

Scan for:
- API keys, tokens, passwords in source files (string literals matching key patterns).
- Private keys, certificates, or PEM blocks in the repository.
- `.env` files tracked in git (check `.gitignore` coverage).
- Connection strings with embedded credentials.
- Base64-encoded secrets in config files.

Search patterns:
- `password\s*=\s*["'][^"']+["']`
- `(api[_-]?key|secret|token|auth)\s*[:=]\s*["'][^"']+["']`
- `-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----`
- Database URIs with credentials: `(mysql|postgres|mongodb)://\w+:\w+@`

Flag severity: **CRITICAL** for any match.

## Step 2: Input Validation Boundaries

Scan for:
- User input passed directly to SQL queries (SQL injection).
- User input rendered in HTML without escaping (XSS).
- User input used in file paths without sanitization (path traversal).
- User input in shell commands without escaping (command injection).
- User input in regex without escaping (ReDoS).
- Deserialization of untrusted data (pickle, yaml.load, eval, JSON.parse of user input
  passed to eval).

For each finding:
- Identify the input source (request parameter, form field, URL path, header).
- Trace the data flow to the dangerous sink.
- Classify: CRITICAL (RCE, SQLi), HIGH (XSS, path traversal), MEDIUM (ReDoS).

## Step 3: Authentication & Authorization

Scan for:
- Endpoints without authentication middleware/decorators.
- Authorization checks missing after authentication (authn without authz).
- Role/permission checks using client-supplied values without server validation.
- Session management issues: missing expiration, predictable tokens, no rotation.
- Password handling: plaintext comparison, weak hashing (MD5, SHA1 without salt).
- JWT issues: algorithm confusion (none/HS256 when RS256 expected), missing expiry,
  secret in source.
- OAuth/OIDC: missing state parameter, open redirects in callback.

Classify: CRITICAL (auth bypass, privilege escalation), HIGH (session fixation, weak hashing).

## Step 4: Dependency Vulnerabilities

1. Identify dependency files: `requirements.txt`, `pyproject.toml`, `package.json`,
   `Cargo.toml`, `go.mod`, `Gemfile`.
2. Check for:
   - Unpinned dependencies (wildcard or range specifiers without upper bounds).
   - Known-vulnerable packages (cross-reference with common CVE databases if version
     is identifiable).
   - Deprecated packages still in use.
   - Dev dependencies in production bundles.
3. Flag packages with known critical CVEs as CRITICAL, unpinned as MEDIUM.

## Step 5: HTTP Security Headers

If the project serves HTTP responses, check for:
- `Strict-Transport-Security` (HSTS) — missing or max-age < 31536000.
- `Content-Security-Policy` — missing or overly permissive (`unsafe-inline`, `unsafe-eval`).
- `X-Content-Type-Options: nosniff` — missing.
- `X-Frame-Options` or CSP `frame-ancestors` — missing (clickjacking).
- `Cache-Control` for sensitive endpoints — missing `no-store`.
- CORS configuration — overly permissive (`Access-Control-Allow-Origin: *` with credentials).

Classify: HIGH (missing HSTS, permissive CORS with credentials), MEDIUM (missing other headers).

## Step 6: Configuration & Misconfiguration

Scan for:
- Debug mode enabled in production config.
- Verbose error messages exposing internals (stack traces, SQL errors).
- Default credentials in config files.
- Overly permissive file permissions in deployment scripts.
- TLS/SSL: disabled certificate verification, outdated protocols.
- Logging sensitive data (passwords, tokens, PII in log statements).

Classify: HIGH (debug mode, verbose errors), MEDIUM (logging PII).

## Output Format

```
## Security Scan Results

**Scope:** `{path_or_scope}`
**Files scanned:** {count}
**Findings:** {total_count}

### CRITICAL ({count})

| # | Category | File:Line | Finding | Remediation |
|---|----------|-----------|---------|-------------|
| 1 | Secrets  | config.py:42 | Hardcoded API key | Move to environment variable |

### HIGH ({count})

| # | Category | File:Line | Finding | Remediation |
|---|----------|-----------|---------|-------------|

### MEDIUM ({count})

| # | Category | File:Line | Finding | Remediation |
|---|----------|-----------|---------|-------------|

### Summary

- **Immediate action required:** {CRITICAL count} findings
- **Address before deployment:** {HIGH count} findings
- **Track for remediation:** {MEDIUM count} findings
- **Clean categories:** {list of categories with 0 findings}
```

## Rules

- Scan source files only. Do not execute code, install packages, or make network requests.
- Report exact file paths and line numbers for every finding.
- Do not report findings in test files unless they contain real credentials.
- Do not flag environment variable references as secrets (only hardcoded values).
- Each finding must include a specific remediation, not generic advice.
- If zero findings in a category, explicitly state it as clean — do not skip the category.
- False positive rate matters: when uncertain, note confidence level in the finding.
