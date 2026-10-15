# Plugin architecture, code quality and tests

The generated project's `AGENTS.md` is the authoritative rule set and is kept current by the
template. Read it completely. This file adds the skill's quality bar and condenses the pitfalls
that `AGENTS.md` and the docs describe, so you know what to look for. If a point here conflicts with
`AGENTS.md` or the docs, those win; verify before relying on any detail.

## Shape of a Macro Deck 3 plugin

Plugins are out-of-process .NET programs (a headless ASP.NET Core host) that talk to Macro Deck
over the plugin protocol. Roughly (verify names in the generated project and SDK):

- `Program.cs`: a short builder chain from the hosting package, then `RunAsync`. Leave its shape
  alone; extra DI registrations go on `builder.Services` before `Build()`.
- One integration class implementing the SDK's plugin integration interface. Capabilities are opted
  into by implementing that capability's interface on the integration (actions, config flow,
  variables, events, issues, music player, weather, profiles, UI providers and others, see
  `/features/`). Implement only what the idea needs.
- Actions are definition classes plus executors. Variables, events and catalogs are declared by
  providers.
- `manifest.json` is the plugin identity. The integration carries no id, name or version.
- User-facing text comes from `Localization/Strings.resx` through the generated `Strings` class.
- Writable data goes only to the plugin data directory the host provides (environment variable
  documented in the plugin hosting reference), never next to the executable.

Prefer an SDK-native feature over custom code every time: config flows for credentials and OAuth
(never your own redirect server), `IHttpClientFactory` for HTTP, Serilog through the Macro Deck
logging bridge for logs, host-provided localization strings, integration issues for user-visible
problems, catalog-changed notifications when catalogs go stale. Use the docs page of the capability
before writing a line, and the sample plugin for the closest capability as a shape reference.

## Pitfalls that AGENTS.md and the docs call out

Check each against the generated `AGENTS.md`; the list is a reminder, not a replacement.

- Action results must be truthful: failures return an explicit failed result with the closest error
  code, never success for a no-op that did nothing; legitimate no-ops are success.
- Forward the invocation cancellation token into everything awaited.
- No blocking calls (`.Result`, `.Wait()`, `Thread.Sleep`) anywhere in types the dispatcher runs.
  No `async void` on SDK contract types.
- Invocations run concurrently, each in its own DI scope; shared state needs synchronization.
- Constructors of integrations and handlers must be cheap and side-effect free.
- `InitializeAsync` runs after the connection is established, can run again after reconnects and on
  config change: make it idempotent.
- Never set a listener URL. Never map routes under the reserved prefix.
- Parameter visibility rules are presentation only; validate parameter combinations in the executor.
- Credentials are secrets in the config flow's secret type, never plain fields or logs.
- Catalog-shaped members are served from a cached description; notify the catalog change when
  something outside a host call changes them.
- Event ids and variable definition ids are persisted in user data: renaming breaks users.
- Host callbacks can throw on rate limiting or timeouts; handle them like network calls.
- Logging is rate limited; use the failure-episode helper for repeating failures instead of logging
  every poll tick.
- Every user-facing string is a resource key; log and exception messages stay English literals.

## Clean code expectations

- **Clear responsibilities.** Integration (lifecycle and opt-ins), actions, config flow and
  provider-specific code stay separate. Do not leak a provider's types into SDK-facing surfaces. Do
  not add layers (repository, mediator, manager, factory) that nothing needs; add an abstraction when
  a second implementation, a test seam or a real boundary exists.
- **DRY, pragmatically.** Extract after a real duplication pattern appears (the second or third
  occurrence with the same reason to change), not on the first similar line. Do not merge code that
  only looks alike.
- **Dependency injection done properly.** Constructor injection of small dependencies, registered
  on `builder.Services`; no `new`-ing of services inside actions, no static state, no service
  locator, no `GetService` in business code. Use `IHttpClientFactory` (typed clients), `IOptions<T>`
  and `TimeProvider` rather than `DateTime.UtcNow`, `new HttpClient()` or global singletons. Pay
  attention to lifetimes: singletons must not capture scoped services (the invocation context only
  exists per invocation).
- **Maintainable and testable.** Put decision logic in plain classes that take their inputs and
  collaborators explicitly, and keep SDK glue thin. Pure logic (parsing, mapping, state machines,
  rate limiting, validation) is separate from I/O so it is testable without a network or host.
- **Resources and lifetimes.** Dispose what owns unmanaged or long-lived resources (sockets,
  timers, subscriptions, cancellation registrations). Event subscriptions must not outlive their
  subscriber.
- **External APIs.** Typed clients, timeouts, cancellation, retry only where idempotent and with
  backoff, honor rate-limit headers, map failures to actionable user-facing results or integration
  issues, never swallow exceptions silently (log with context or surface a result).
- **Naming and style.** Self-explanatory names beat comments. Match the surrounding code,
  indentation (the template uses tabs in C#) and idioms. Keep nullable annotations honest.
- **Complexity budget.** Prefer the smallest design that satisfies the plan. If a class needs a
  paragraph to explain it, split or simplify it.

## Tests

Write tests that protect behavior and allow refactoring, not tests that raise a coverage number.

- Test **observable behavior at meaningful seams**: an action given parameters returns the right
  result and side effect; a parser maps real sample payloads; a config flow step validates and
  advances; a variable provider reports the right values and unavailable states; rate limiting and
  retries behave; failure paths produce the right error code or issue. Derive expected values from the
  requirement, not from copying the implementation's output.
- Use the SDK's test package (test harness and fakes; see `/features/testing/`) to run actions,
  providers and flows the way the host would. Use fakes or a fake `HttpMessageHandler` for external
  services; never call a real service from automated tests.
- Do **not** test private methods, DI wiring trivia, getters/setters, framework behavior, or
  mirror each production method with a test that restates it. Do not assert on incidental details
  (exact log text, call counts of internal collaborators) unless that is the contract. Avoid
  heavy mocking of your own classes; a test that breaks on every refactor without catching a bug is
  a defect.
- One reason to fail per test, descriptive names (`Failed_result_when_api_returns_401`), small
  arrange sections, shared builders only when they reduce noise. Deterministic: no sleeps, no clock
  or randomness dependency (inject `TimeProvider`), no ordering between tests.
- Cover the edges that matter: invalid input, cancellation, timeouts, empty and huge responses,
  reconnect/re-initialization, localization completeness for shipped languages.
- Keep the suite fast and runnable on every supported OS. Report coverage only if the project already
  measures it; never write tests merely to move it.
- Run the plugin conformance suite (`macrodeck-plugin test`) in addition to unit tests; it checks
  protocol-level behavior unit tests cannot.

Every change that adds behavior ships with the tests that would catch its regression. A bug fix
starts with a test that fails for the right reason.

## Platforms

Most plugins are pure .NET and run unchanged on Windows, Linux and macOS: build, test (CI matrix)
and declare all three. Platform-specific code (P/Invoke, registry, osascript, Windows-only
APIs, native libraries, OS paths, shelling out to platform tools) changes that. In that case
**ask the user** whether the plugin should target only the current platform, so it can actually be
tested, or provide implementations per platform. Do not silently ship an untested platform. Put
OS-specific code behind a small interface with one implementation per OS, selected at registration
time, and declare only the supported platforms in `entrypoints` and `macrodeck-build.json`.
See [release-workflow.md](release-workflow.md#platforms).

## Comments and documentation

- English only. Short, one line where possible, explaining a non-obvious *why*: a race, a protocol
  rule, a workaround. Prefer no comment over a comment that restates the code.
- No emojis, no em dashes, no decorative comments, banners, ASCII art or section separators, no
  multi-paragraph comments where a sentence works. No "this section does X" comments.
- Public API gets concise XML documentation; internal code usually none.
- Good: `// Retry once because the previous request may still be processing.`
  Bad: a banner block titled "RETRY LOGIC".
- The same rules apply to YAML, scripts, project files and the README.

## README

A useful English `README.md`, written for a user and a developer, replacing all template text:
what the plugin does, main features, how to use it in Macro Deck (setup flow, actions, variables,
widgets, with concrete examples), prerequisites and external services (accounts, API keys, rate
limits, what data is sent where), limitations, and when useful: local development, building,
debugging against a local Macro Deck, external API configuration, license and third-party notices
pointer. Disclose network communication and data handling (Creator Guidelines). No placeholders,
no marketing fluff, no claims the code does not fulfill.
