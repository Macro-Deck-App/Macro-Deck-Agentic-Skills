# Testing, debugging and runtime validation

Validate for real. Report what ran and what passed, and say precisely what could not be run.

## Validation list

Run what applies, in this order, from the repository root. Substitute the paths and the installed
CLI's actual syntax (check `--help`).

| Check | How |
| --- | --- |
| Restore | `dotnet restore` (restores only declared dependencies) |
| Build, warnings as errors | `dotnet build -c Release -warnaserror`; analyzers (`MDP*`, `MDLOC*`) and nullable warnings are fixed, not suppressed; a suppression has the narrowest scope and a reason |
| Unit tests | `dotnet test -c Release --no-build`; run them on each supported OS in CI |
| Conformance | `macrodeck-plugin test --project <source>` quickly, and `--artifact` on the packed package for the host platform; a failed Required check blocks; skipped checks are explained by capabilities the plugin does not declare |
| Package build | `macrodeck-plugin build --source <source> --output ./artifacts` then `inspect` and `validate --level publication --artifact ...` |
| Manifest and build manifest | `python3 $SKILL_DIR/scripts/check-plugin.py <repo>` plus the schema check above; read both files side by side against the table in [manifests.md](manifests.md) |
| Non-self-contained | check-plugin plus a look at the packed artifact size and file list |
| Release and CI workflow | check-plugin, `actionlint` when available, compare with the current publish workflow inputs |
| Dependency inventory | `dotnet list <project> package --include-transitive`, `--vulnerable`, `--deprecated`; compare against blocked and allowed lists and the minimum SDK ([creator-guidelines.md](creator-guidelines.md)) |
| Dependency provenance | each new package passed [dependency-security.md](dependency-security.md) and was approved |
| Licenses and notices | `scripts/inventory-dependencies.py <publish dir>`; `LICENSE`, `NOTICE`, `THIRD-PARTY-NOTICES` match it and the asset list |
| Secrets | check-plugin secret scan, `git diff`, untracked files; no value is ever printed |
| Style | check-plugin warnings for em dashes, emojis, banners; English comments and docs |

If a check fails: find the root cause, fix it, rerun that check and everything it could have
affected. Do not stop at the first build error, do not delete or weaken a test or an analyzer to
get green, do not pin a version only to dodge an error without understanding it.

## CLI test loop and the conformance suite

Use the plugin CLI for every step below (verify syntax with `macrodeck-plugin <command> --help`).
Run the loop until it is clean, and again after every later change to capabilities, cancellation
handling, manifests or dependencies.

1. `macrodeck-plugin test --list-checks`: learn the check ids, categories and requirement levels once.
2. `macrodeck-plugin test --project <source> --report json --output <file outside the repo>`: a first
   run against the project (`test` builds it). Read the report, not just the exit code (0 conformant,
   1 the plugin is wrong, 2 usage error, 3 the subject could not be built, launched or read, 4 cancelled).
3. For every failed check: read its id and message, look it up in `/reference/conformance/` and the
   SDK source, fix the root cause in the plugin, then rerun only that check
   (`--check <id>` or `--category <name>`) before the full run. Repeat until no Required check fails.
   A failed Recommended check is allowed but fix it when reasonable. Inspect every `SKIP`: a skip
   that says no capability was declared is fine; a skip that says the suite could not observe
   behavior (for example no action produced log output) may mean the plugin lacks something to test.
4. Pack the real artifact: `macrodeck-plugin build --source <source> --output ./artifacts`, then
   `macrodeck-plugin validate --level publication --artifact <file>`,
   `macrodeck-plugin inspect --artifact <file>` (no runtime or framework files, only the expected
   runtimes, assemblies and assets), and `macrodeck-plugin test --artifact <file> --required-only`.
   The artifact needs an entrypoint for the machine's platform. This is what the publish workflow
   runs on a stub host for each declared platform; a Required failure blocks the release.
5. `macrodeck-plugin run --artifact <file> --stub-host` streams until interrupted, so never run it
   in the foreground without a limit. Run it in the background or under a timeout, wait for the
   "Session established" line and the plugin's initialization log line, then stop it (an exit code 4
   or a killed process after the stop is expected). `macrodeck-plugin test` is the bounded
   equivalent and is what gates a release.
6. Fix and loop. Do not skip, filter out or weaken a failing Required check, and do not edit the
   report. If a failure cannot be fixed, report the check id, the message and what you tried.
7. Finish with `python3 $SKILL_DIR/scripts/check-plugin.py <repo> --artifact <file>` and the
   self-review in [store-submission-checks.md](store-submission-checks.md#self-review-procedure).

Keep reports and artifacts outside version control. Put the CI-relevant parts (build, tests, pack,
validate) in `.github/workflows/ci.yaml`; the conformance run on every platform is done by the
release workflow's stub host.

## Debugging

- Read the whole build error list first: the plugin builder reports every local configuration
  problem at once (`PluginConfigurationException`), analyzer diagnostics carry ids that the docs
  explain (`/reference/analyzers/`, `/features/localization/` for `MDLOC*`).
- Localization shows `[[plugin:<id>:Key]]` at runtime when the catalog was not registered or a key
  is missing in every culture.
- `entrypoint-missing` after a rename: `AssemblyName` and the manifest entrypoints disagree.
- Health check failing silently: a custom listener URL was set.
- Initialization seems skipped: it runs only after the connection is established and may run
  repeatedly.
- Hanging or starved invocations: a blocking call in an executor, or a missing cancellation token.
- Conformance failures: read the check id and message in `/reference/conformance/` and fix the
  contract violation rather than the symptom.
- Stub host session never established: run
  `macrodeck-plugin run --project <source> --stub-host` and read the plugin's own output.
- For a repeated failure, form a hypothesis, test it, record the result. Do not apply the same fix
  twice.

## Runtime and UI validation

Prefer actually running the plugin. Use the strongest level the environment allows and record which
level was reached.

1. **In-process tests** with the SDK test harness (fast, always).
2. **Stub host**: `macrodeck-plugin run --project <source> --stub-host` (a disposable in-process
   host, no Macro Deck needed) and `macrodeck-plugin test`. Check that the session is established
   and initialization ran.
3. **Widget previews**: for plugins with widgets, `macrodeck-plugin preview render` renders every
   `[UiPreview]` scenario to PNG without a running Macro Deck or a sign-in, and is the primary loop
   while developing widgets ([widget-design.md](widget-design.md#develop-with-the-preview-cli)).
4. **Real local Macro Deck**: when a desktop installation is running on the same machine, pair the
   plugin with it using `macrodeck-plugin run --project <source>` (no `--stub-host`), so the plugin
   is registered with the running Macro Deck. Add `--watch` while iterating on UI: text and layout
   edits are hot reloaded, open developer previews rebuild in place and other changes trigger a
   full rebuild. Verify the options with `macrodeck-plugin run --help`.
   - `run` streams until interrupted: start it in the background, read its output (`[plugin]`,
     `[plugin:stderr]`) and stop it when done (exit code 4 is expected after the stop).
   - Ask the user first. Starting the plugin against their Macro Deck, pairing and any
     interaction with their desktop UI need their explicit consent. State what will happen and wait
     for a clear yes.
   - Pairing needs Developer Mode enabled in Macro Deck and an approval in Macro Deck. `run` prints
     `developer-mode-disabled` or `pairing-prompt-expected` when something is missing. Ask the user
     to enable Developer Mode and to approve the pairing prompt, or to allow you to approve it in the
     UI. Do not use an enrollment token on the command line unless the user supplies one for this
     purpose; command line tokens are visible in plaintext.
   - Credentials and sign-in belong to the user. If the desktop UI requires a sign-in, the user signs
     in, or approves a password manager hand-off if the host offers one. Never type, guess or store
     a password, token or key yourself.
   - Credentials the plugin itself needs for an external service come only from local user
     secrets, never from the repository.
5. **Visual and interactive inspection in the Macro Deck Desktop UI**: with the plugin paired and
   the user's consent, open the Macro Deck Desktop UI in the host's browser pane (or other browser
   automation or MCP browser tool). The default address is `http://127.0.0.1:8193`. If it does not
   respond, ask the user for the address instead of guessing other ports. Then place the widget on a deck
   or open the developer preview, operate the UI yourself (add the widget, open config views, press,
   toggle, drag sliders), take screenshots, read them with vision and check the application logs.
   Stay inside what the task needs: do not change other profiles, devices or settings, do not delete
   user data, and revert test content you added (a test widget, a temporary profile) when done,
   or tell the user what remains. If no browser tool exists, or the user declines, say so and ask the
   user for screenshots or to look themselves.

Check these states and sizes, and iterate on problems found:

- rendering and correctness of values, text overflow and ellipsis, layout and alignment, icons and
  artwork, content under rounded corners
- tile shapes (1x1, 2x1, 1x2, 2x2 and larger), responsive layouts switching
- both light and dark themes, contrast
- states: loading, not configured, unavailable or offline, error, empty, long text, extreme values
- interactions: press, long press, sliders, toggles, config views and flows (setup, validation errors,
  re-run), cancellation
- update behavior: values change in place without flicker or layout jump, no busy loops
- localization: another language, long translations
- performance: no excessive redraws, CPU use at idle, no expensive effects
  ([widget-design.md](widget-design.md#performance-and-visual-effects))

Real external services: use the user's own test account only with their consent and credentials
supplied through local secret mechanisms; never commit them; automated tests never hit real services.
