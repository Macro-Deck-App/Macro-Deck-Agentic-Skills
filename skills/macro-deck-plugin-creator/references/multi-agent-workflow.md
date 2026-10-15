# Multi-agent workflow

Roles are conceptual. Map each to the best mechanism the current host offers: a subagent, a
delegated task, a separate session, or, when none exists, a separate sequential phase that starts
from the written artifacts only. The point is independence and focused context, not the mechanism.

## Principles

- **Give each role only what it needs.** Do not forward the whole conversation. Summarize research
  before planning. Give the implementer the accepted plan, not the debate that produced it.
- **Reviewers must not inherit the author's assumptions.** The plan reviewer reads the request and the
  sources itself. The final reviewer receives the original user request, the accepted plan, the diff
  and access to the repository and current sources, but not the implementer's reasoning or
  self-assessment. Tell reviewers to verify claims against code and sources, and to mark anything
  they could not verify.
- **Verify, do not trust.** Delegated results are claims. Before relying on a subagent's statement
  about an API, version, license or test result, check the evidence or rerun the command.
- **Bounded loops.** At most three plan review iterations. Final review: fix, rerun the affected
  validation, re-review only the delta. When agents keep disagreeing, put the decision to the user.
- **Report everything in round one.** Ask reviewers for all findings at once, ranked, with a
  verdict, so the author fixes everything in one pass.
- **Continue, do not restart.** For follow-up rounds continue the same reviewer if the host allows
  it (it already read the code); otherwise give the new reviewer the previous findings and the
  revisions. Start a fresh reviewer only if the plan or diff was rebuilt.
- **Keep noisy output out of context.** Write build, test and log output to files and read the
  relevant lines.
- **Delegated agents follow the same rules**: current-source verification, dependency approval,
  secrets, style (English, short comments, no emojis or em dashes), no AI attribution in commits.
  Put these in the task prompt; do not assume the agent knows this skill.

## Roles and handoffs

| Role | Input | Output | Notes |
| --- | --- | --- | --- |
| Research | User idea, pointers from [sdk-and-cli.md](sdk-and-cli.md) | A compact brief: requirements, relevant capabilities with verified contracts (cite doc page or source file), similar plugins, external API facts (auth, limits, terms), candidate dependencies with verdicts and licenses, Creator Guideline implications, open questions | Fetches policies and docs itself. Marks every claim verified or unverified |
| Planning | Brief, original request | Concrete plan (see Phase 2 in SKILL.md), including a test plan | Only relevant sections. States assumptions and defaults |
| Plan review | Original request, plan, brief, repository state, current guidelines, `AGENTS.md` | Findings plus verdict `APPROVED` or `CHANGES REQUIRED` | Independent, never writes code |
| Implementation | Request, accepted plan, brief, `AGENTS.md`, style and security constraints, verified API references, dependency policy | Code, tests, docs, workflows, a list of deviations from the plan and why | Cost-efficient model if the host allows selection. Stays inside the plan |
| Runtime and UI validation | Built plugin, list of states and sizes, how to run | Observations, screenshots or logs, defects | Uses whatever browser, UI or log tooling exists |
| Final review | Request, accepted plan, diff, repository, current sources | Findings per checklist item and verdict | Independent, never writes code |

## Plan review

Give the reviewer the original user request, the plan, the research brief (to check, not to
trust), and tell it to read the actual docs, SDK source and sample plugins. It must answer:

1. Does the plan satisfy the original idea, nothing missing and nothing extra?
2. Are the named Macro Deck APIs, capabilities and manifest fields current and real? Verify each
   against docs or source.
3. Can SDK-native functionality replace custom code (config flow, host strings, logging, HTTP,
   variables, events, issues)?
4. Are dependencies necessary, trustworthy (provenance checked), license compatible, and approved?
5. Are third-party notices accounted for, for packages and assets?
6. Security concerns: secrets, input validation, network, files, processes, privacy, SSRF.
7. Missing edge cases: errors, rate limits, offline, empty data, cancellation, reconnect.
8. Lifecycle, threading and state: initialization idempotence, concurrency, catalog staleness,
   persisted ids.
9. Is the architecture unnecessarily complicated? Clean code, DRY, DI, testability.
10. Is the test plan meaningful (behavior at real seams, no coverage padding) and does it cover the
    risky parts?
11. Does it comply with the current Creator Guidelines, including naming, AI statement and platforms?
12. Are platforms and CI consistent with the plugin's actual platform dependence?

## Final review

The reviewer compares the final implementation against all of these, with evidence per item (file,
line, command output) and a verdict:

1. Original user request
2. Accepted implementation plan, and deviations
3. Current Macro Deck documentation
4. Current SDK conventions
5. Current Creator Store Guidelines, explicit line per guideline area
6. Code quality (architecture, DRY, DI, naming, resource handling, async and cancellation)
7. Tests: meaningful, maintainable, deterministic; not coverage padding
8. Security
9. Dependency trustworthiness
10. Dependency licenses
11. README
12. LICENSE
13. NOTICE
14. THIRD-PARTY-NOTICES
15. Plugin manifest
16. Build manifest
17. Manifest consistency
18. AI statement
19. Build configuration (framework-dependent), CI and release workflow, platforms
20. Documentation and comment style

Points 5, 15 to 19 include the gates in [store-submission-checks.md](store-submission-checks.md):
upload refusals, pre-flight checks and the moderator rules (CLI version equals SDK version, no
committed binaries, root LICENSE and README, trusted workflow, capability review).

It focuses on substantive issues, not taste. It must independently rerun the key commands
(restore, build, tests, check-plugin) rather than trusting reported results, and say what it could
not verify. After fixes, rerun the relevant validation and have the same reviewer check the delta.

## Task prompt skeleton

Use for every delegated role, filled with only that role's inputs:

```text
Role: <role>. Goal: <one sentence>.
Inputs: <named files or pasted summaries>.
Sources of truth: current Macro Deck docs, SDK source, installed CLI help, project AGENTS.md.
Rules: never guess APIs; verify and cite; no new dependency without verification and user approval;
no secrets in files or output; English comments, short, no emojis or em dashes; no AI attribution.
Output: <exact deliverable>. Mark claims verified or unverified. Report all findings in one pass.
```
