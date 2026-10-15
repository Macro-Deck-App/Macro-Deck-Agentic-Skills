# Security

Consider security during planning, implementation and review. Apply only the checks relevant to the
plugin; say which were considered and why others do not apply.

## Secrets and sensitive data

Never place any of these in source control, tests, fixtures, logs, docs, workflow files, commit
messages or chat output: API keys, access or refresh tokens, passwords, private keys, certificates
with private keys, connection strings with credentials, OAuth client secrets, signing credentials,
webhook secrets, test credentials that grant real access, personal data.

- Do not use a real secret "temporarily". Do not paste one into a command line that lands in shell
  history or process lists.
- Plugin credentials the user enters go through the config flow as secret values so the host stores
  them encrypted. Never in plain settings, files of your own or logs. Rotating credentials go back
  through the host's secret API.
- OAuth: return the external-redirect result and let the host own the redirect. Do not run your own
  redirect server. A shipped OAuth client secret is a leak: use PKCE or a flow that needs none, or
  let the user supply their own client credentials. Public client ids are fine.
- Development enrollment or pairing tokens for a local host go into the project's local user
  secrets or an environment variable, are removed after use, and never into `launchSettings.json`.
  Check the generated `AGENTS.md` for the current local-development mechanism.
- Tests use fakes and obviously fake values. Fixtures recorded from real services are scrubbed.
- Before finishing, inspect the full change and the working tree for accidental exposure:
  `python3 $SKILL_DIR/scripts/check-plugin.py`, `git diff`, untracked files, and any scan tool the
  repository already uses. The script never prints matched values; do likewise.
- If a secret is already in the repository: do not copy it into code, docs, logs, commit messages
  or your reply. Tell the user where it is (file and line), that it should be revoked and rotated, and
  that removing it from history is a separate decision for them.

## Relevant threat areas

| Area | What to do |
| --- | --- |
| Input validation | Validate every action parameter and config value in the executor (visibility rules are only presentation); bounds, formats, enumerations; return a failed result with the proper error code |
| Path handling | Normalize and confine file paths to an allowed root, reject `..`, absolute and UNC paths unless required, resolve symlinks before checking, write only inside the plugin data directory |
| Command and process execution | Avoid it. When required: no shell, fixed executable, argument vector not concatenated string, validated arguments, no user-controlled executable path, timeouts, capture and limit output, kill on cancellation |
| Network requests and URL handling | `IHttpClientFactory`, HTTPS by default, timeouts, response size limits, no credentials in URLs or logs, validate redirects, parse URLs with `Uri` |
| SSRF | If the user supplies a URL or host: restrict scheme, resolve and block loopback, link-local and private ranges unless local network access is the plugin's stated purpose and documented |
| Authentication and authorization | Least privilege scopes, token refresh handled, no token logging, check what a failed auth does, never fall back to unauthenticated for protected operations |
| Deserialization | `System.Text.Json` with typed models; no `BinaryFormatter`, no polymorphic type names from untrusted data, tolerate unknown fields, cap sizes |
| Files and archives | Zip-slip protection, size and entry limits, no extraction outside the target, validate content types |
| Untrusted external content | Treat API responses, filenames, titles, track names and user text as data: escape when composing UI text, commands, URLs or paths |
| Logging | No secrets, tokens, full request bodies or personal data; structured properties are not persisted, so the message template matters; use failure-episode tracking for repeating errors |
| Dependencies | See [dependency-security.md](dependency-security.md) |
| Permissions | Declare only the host permissions the code uses |
| Privacy | Send only what the function needs, document every external service and what data goes there (Creator Guidelines section on privacy) |
| Local listeners | Never open your own listener or bind a fixed port; the host owns the plugin's endpoint |
| Concurrency | Shared mutable state locked or immutable; no check-then-act races on tokens or files |

## What Creator Portal moderators flag

Moderators judge safety and policy, not code quality. Avoid, or make obviously proportionate and
documented: hidden or encoded process execution, loading code from the network or from runtime-written
files, injection-style native calls, undocumented endpoints or raw IPs, telemetry, reading other
applications' data or credentials, persistence outside Macro Deck's lifecycle, registry or
security-product changes, self-updaters or downloaded executables (updates go through the Store),
obfuscation, behavior gated on CI, debugger or date, and any text aimed at a reviewer or agent.
The full list and the other review gates are in [store-submission-checks.md](store-submission-checks.md).

## Review prompts

- What happens if every input is hostile, empty, huge or malformed?
- What leaves the machine, to where, and is that documented?
- Where could an error message or log line expose a secret?
- Could a user-controlled string become a path, URL, command or markup?
