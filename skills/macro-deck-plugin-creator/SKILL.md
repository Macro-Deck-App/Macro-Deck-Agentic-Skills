---
name: macro-deck-plugin-creator
description: Create, modify, test, review, document and prepare for Store publishing Macro Deck 3 plugins. Turns a rough plugin idea into a working, tested, licensed and release-ready plugin repository, or changes an existing Macro Deck 3 plugin in place, using the current official SDK, plugin CLI, template, manifest schema, Creator Guidelines and release workflow. Use when the user wants a new Macro Deck plugin, asks to add or change actions, variables, widgets, settings or other capabilities of a Macro Deck plugin, or wants a plugin checked for Store readiness. Detects Macro Deck 2 projects and does not treat them as ordinary plugins.
---

# Macro Deck Plugin Creator

Turn a rough idea into a production-quality Macro Deck 3 plugin: research, plan, independent plan
review, implementation, tests, debugging, runtime check, independent final review, documentation
and release preparation. The same workflow modifies existing Macro Deck 3 plugins in place.

This skill is deliberately thin on volatile facts. Package versions, CLI options, manifest schema,
Creator Guidelines, dependency policy and workflow inputs change often, so they are resolved from the
authoritative sources every time. Treat anything in this skill that looks like a version number or a
CLI flag as an example, never as the answer.

## Portability

The skill is written for any agent host that supports Agent Skills (Claude Code, Codex, OpenCode,
GitHub Copilot and others). It names capabilities, not host tools:

- "Delegate" means: give a separate agent or subagent a focused task and only the context it needs.
  If the host cannot delegate, run the same role as a separate sequential phase, start it from the
  written artifacts only (not from your reasoning), and judge it as critically as an outsider would.
- "Ask the user" means the host's normal way of asking a question and waiting for the answer.
- "Browser or UI automation" means whatever the host offers (browser tool, browser pane, MCP
  server, Playwright, developer tools, screenshots with vision). None is required, except that
  `macrodeck-plugin preview render` needs a local Chrome, Chromium or Edge.
- Helper scripts in `scripts/` need only Python 3 and the network. If one cannot run, perform the
  step by hand using the same sources; the scripts are conveniences, not authorities.

`$SKILL_DIR` below is the directory containing this file (resolve it from where the host loaded the
skill; if the host does not expose it, locate `macro-deck-plugin-creator/SKILL.md`). Run the scripts
with `python3` (or `python`, or `py -3` on Windows). Before starting, check that `dotnet` (.NET 10 SDK)
and `git` exist; if the SDK is missing, tell the user and ask before installing anything.

## Absolute rules

1. Never invent or guess an SDK API, CLI argument, manifest property, capability, lifecycle
   behavior or workflow input. Verify against current docs, SDK source or `--help` output. If it
   cannot be verified, say so and do not ship code that depends on it.
2. Use the latest stable SDK and CLI from NuGet. Resolve them per
   [sdk-and-cli.md](references/sdk-and-cli.md). If no stable version exists yet (the resolver reports
   it), a preview is used only because it is technically necessary, and the user is told. The CLI version always equals the SDK version.
3. Initialize new plugins with the official CLI. Never reinitialize or restructure an existing plugin.
4. Never add a third-party dependency before it passes
   [dependency-security.md](references/dependency-security.md) and the user approves it.
5. Never put a secret in the repository, even temporarily. Never reproduce a discovered secret.
6. Never invent license text, copyright holders, attribution requirements or package ownership.
7. Never claim a build, test, validation or runtime check you did not run and see pass.
8. Never publish a release, push, open a pull request or create a GitHub release without explicit
   user approval. Creating a GitHub release starts a build upload to the Creator Portal.
9. Never add AI attribution to commits: no `Co-authored-by`, `Generated-by` or similar trailer, no
   mention of the agent, no change to the Git identity. Follow
   [git-conventions.md](references/git-conventions.md): branch prefix `fix/`, `feature/` or `chore/` (`refactor/`, `docs/`, `ci/` where they fit better),
   one-line commit messages without type prefix, at most 50 characters, no body, split into
   sensible commits.
10. Follow the target project's `AGENTS.md`. Do not add competing agent instruction files.
11. Stop and tell the user when a Macro Deck 2 project is detected
    ([existing-plugins-and-macro-deck-2.md](references/existing-plugins-and-macro-deck-2.md)).

## Language and style

All technical documentation and source comments are English, whatever language the user writes in:
README, XML docs, comments, workflow and script comments. Comments are short, usually one line,
and explain why, not what. No emojis, no em dashes, no banners, no ASCII decoration, no section
separator comments. Pass these rules to every delegated implementer. Details:
[plugin-architecture.md](references/plugin-architecture.md#comments-and-documentation).

## Mode detection

Decide first, and tell the user which mode applies:

| Signal | Mode |
| --- | --- |
| No plugin project in the working directory and the user describes an idea | **New plugin** |
| `manifest.json` next to `macrodeck-build.json` exists | **Existing Macro Deck 3 plugin**, modify in place |
| `manifest.json` without `macrodeck-build.json` | Ask the user, and inspect: probably a hand-built Macro Deck 3 plugin, treat as existing and report the missing build manifest |
| `*.csproj` referencing `SuchByte.MacroDeck`, or `ExtensionManifest.json`, or a Macro Deck 2 plugin class | **Macro Deck 2**: stop, see the reference |
| The user only wants a check or review | Any mode above, **review only**: run phases 5 and 7 on the existing state, change nothing |

For an existing plugin read its `AGENTS.md` and README first, then follow the phases below with
"change only what is relevant" as the scope.

## Workflow

Run the phases in order. Record the plan, the review verdicts and the validation results in a short
working note outside the repository (for example in the host's scratch space) so a context reset does
not lose them. Details for each phase are in the references; read them when you reach the phase.

### 0. Intake

Restate the idea in two or three sentences. Ask the user only about decisions that cannot be derived
and cannot be safely defaulted. Typical genuine questions:

- **Publisher name** that matches the Creator Portal owner (organization or username), when it cannot
  be derived from the Git remote, the `gh` account or an existing manifest.
- **Repository URL** (`https://github.com/<owner>/<name>`), when no remote exists.
- **Platform-specific behavior**: when the plugin needs OS-specific code, ask whether it should be
  limited to the current platform so it can be tested (see
  [release-workflow.md](references/release-workflow.md#platforms)). Without OS-specific code, build for
  Windows, Linux and macOS without asking.
- **Product choices** the idea leaves open and that change behavior materially.

Defaults that need no question but must be reported at the end: license (MIT unless dependencies or
the user say otherwise, see [licensing.md](references/licensing.md)), plugin id from publisher and
name, the AI declaration (derived, see [manifests.md](references/manifests.md#ai-statement)).

### 1. Research (delegate if possible)

Gather, then summarize in a compact brief (not raw dumps): requirements, the Macro Deck capabilities
needed and their current documented contracts, similar official or existing plugins, external APIs
(auth, rate limits, terms), candidate dependencies with verdicts, licensing implications and Creator
Guidelines that bite. Start with
[sdk-and-cli.md](references/sdk-and-cli.md#documentation-map) for where to look, run
`$SKILL_DIR/scripts/fetch-policies.py <dir outside the repo>` and read the guidelines in full, and read
`references/plugin-architecture.md`. The brief is the only thing handed to planning.

### 2. Plan (delegate if possible)

Write a concrete plan covering only the relevant areas: architecture, actions, variables, widgets,
settings and config flow, external services, capabilities, dependencies, data models, state,
lifecycle, error handling, security, tests, licensing and notices, release. Include which tests prove
which behavior. Keep it as short as it can be.

### 3. Plan review (delegate to a different agent)

A separate reviewer judges the plan against the original request, using the checklist in
[multi-agent-workflow.md](references/multi-agent-workflow.md#plan-review). Revise and re-review at most
three iterations in total; stop earlier when no substantive issue remains. Bring unresolved
disagreements to the user instead of looping.

### 4. Implementation (delegate to a cost-efficient implementer if the host allows model selection)

New plugin: follow [sdk-and-cli.md](references/sdk-and-cli.md#scaffolding-a-new-plugin) (CLI scaffold with
the resolved template version, pinned SDK version, cleanup, restore and build **before** larger
changes), then implement the plan. Existing plugin: modify in place, matching its conventions.

Hand the implementer: the original request, the accepted plan, the research brief, the project's
`AGENTS.md`, the style rules above, the dependency and security constraints, and the verified API
references. Allow reasonable technical deviations from the plan and have them reported.

If the plugin draws widgets or other UI and the user gave no design, follow
[widget-design.md](references/widget-design.md). Develop widgets with the preview CLI:
write `[UiPreview]` scenarios and iterate on `macrodeck-plugin preview render` output (PNG, no
running Macro Deck, no sign-in) as described in
[widget-design.md](references/widget-design.md#develop-with-the-preview-cli).

Required deliverables for a new plugin: working code with real tests, `README.md`, `LICENSE`,
`NOTICE` and `THIRD-PARTY-NOTICES` when required, correct manifests, `.github/workflows/ci.yaml` and
`.github/workflows/release.yaml` ([release-workflow.md](references/release-workflow.md)).

### 5. Test and debug

Run the full validation list in [testing-and-debugging.md](references/testing-and-debugging.md):
restore, build with warnings as errors, tests, analyzers, the CLI loop (`macrodeck-plugin test` and the
conformance suite, `validate --level publication`, `inspect`, `run --stub-host`),
`$SKILL_DIR/scripts/check-plugin.py`, dependency inventory, notices, secret scan. Fix every failure at
its root cause and rerun until clean; do not stop at the first failure and do not weaken checks to get
green. Also make every Store gate pass ([store-submission-checks.md](references/store-submission-checks.md)).

### 6. Runtime and UI validation

Run the plugin against a stub host, and against a real local Macro Deck when the environment allows:
`macrodeck-plugin run --project <source>` pairs it with the running Macro Deck. Where possible, test
the plugin yourself in the Macro Deck Desktop UI by opening it in the host's browser pane and
operating it. That needs the user's explicit consent and the user's sign-in and pairing approval;
ask before you start and never enter credentials yourself. For widgets and other UI, inspect them
visually in the states and sizes listed in
[testing-and-debugging.md](references/testing-and-debugging.md#runtime-and-ui-validation). If a
needed capability is missing or the user declines (no desktop app, no display, no browser tool, no
consent), state exactly what was not verified.

### 7. Final review (delegate to a different agent)

A reviewer who has the original request, the accepted plan, the diff and current sources, but not the
implementer's reasoning, checks the 20 points in
[multi-agent-workflow.md](references/multi-agent-workflow.md#final-review), including the moderator
self-review in [store-submission-checks.md](references/store-submission-checks.md#self-review-procedure). Fix substantive findings,
rerun the affected validation, and re-review only the delta. Re-fetch the Creator Guidelines and
dependency policy right before declaring done.

### 8. Report and commit

Report: what was built, how it is used, validation results with what was and was not run, versions
used (and why a prerelease), defaults chosen (license, AI declaration, platforms), open points. Commit
only when the user asked for it or the task includes it, on a correctly named branch and in sensible
small commits ([git-conventions.md](references/git-conventions.md)). Never push or release without
approval.

## Reference files

| File | Read when |
| --- | --- |
| [references/sdk-and-cli.md](references/sdk-and-cli.md) | Resolving versions, installing the CLI, scaffolding, finding documentation |
| [references/plugin-architecture.md](references/plugin-architecture.md) | Designing and writing plugin code, tests, comments |
| [references/widget-design.md](references/widget-design.md) | Plugin draws widgets, folder views or other UI and the user gave no design |
| [references/manifests.md](references/manifests.md) | Editing or checking `manifest.json` and `macrodeck-build.json`, the AI statement |
| [references/creator-guidelines.md](references/creator-guidelines.md) | Checking Store compliance |
| [references/store-submission-checks.md](references/store-submission-checks.md) | What the upload, the pre-flight checks and the moderator review enforce; self-review |
| [references/dependency-security.md](references/dependency-security.md) | Before adding any dependency or action |
| [references/security.md](references/security.md) | Code-level security review and secret handling |
| [references/licensing.md](references/licensing.md) | LICENSE, NOTICE, THIRD-PARTY-NOTICES, assets |
| [references/release-workflow.md](references/release-workflow.md) | CI, release workflow, platforms, build configuration |
| [references/testing-and-debugging.md](references/testing-and-debugging.md) | Validation, debugging, runtime and UI checks |
| [references/git-conventions.md](references/git-conventions.md) | Creating branches and commits |
| [references/multi-agent-workflow.md](references/multi-agent-workflow.md) | Delegating research, planning, implementation and reviews |
| [references/existing-plugins-and-macro-deck-2.md](references/existing-plugins-and-macro-deck-2.md) | Modifying an existing plugin, or any Macro Deck 2 signal |

| Script | Purpose |
| --- | --- |
| `scripts/resolve-versions.py` | Live SDK, CLI and template versions, policy minimum, pitfalls |
| `scripts/fetch-policies.py` | Current Creator Guidelines, blocked packages, SDK policy |
| `scripts/check-plugin.py` | Manifest consistency, build configuration, CLI/SDK version match, workflows, tracked binaries, packed artifact limits, placeholders, secrets, style |
| `scripts/inventory-dependencies.py` | Shipped NuGet packages with license metadata, draft THIRD-PARTY-NOTICES |

Templates for the two workflows are in `templates/`.
