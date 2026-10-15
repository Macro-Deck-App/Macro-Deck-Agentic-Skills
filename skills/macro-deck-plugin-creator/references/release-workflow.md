# CI, release workflow, platforms and build configuration

A plugin repository gets two workflows: a small CI that builds and tests on GitHub, and a release
workflow that publishes through the Macro Deck Creator Portal. Templates are in `templates/`.

## Verify before generating

Do not generate the release workflow from memory. Read, at task time:

1. `https://github.com/Macro-Deck-App/GitHub-Actions` (`README.md`, `.github/workflows/publish-plugin.yml`
   inputs and header comments).
2. `https://docs.macro-deck.app/creator-portal/release-workflow/` and `/guides/publishing/`.
3. The generated project's `AGENTS.md` and README, if they mention publishing.

Compare what you read with `templates/release.yaml` and follow the sources where they differ
(workflow file name, input names, required permissions, defaults). Tell the user about differences.

## Release workflow

Create `.github/workflows/release.yaml` from `templates/release.yaml`:

- Trigger: `release` with type `published`.
- Call `Macro-Deck-App/GitHub-Actions/.github/workflows/publish-plugin.yml` with `uses:` at the
  current major tag (`@v1` at the time of writing; confirm). It must be a tag, not a commit SHA or
  branch: the Platform accepts the build only from that workflow at a `v*` tag. Never copy its steps
  into the plugin repository.
- Permissions on the calling job: `contents: read` and `id-token: write`, nothing else. No secrets
  and no signing keys; authentication is the run's OIDC token and the Store signs the package.
- `version: ${{ github.event.release.tag_name }}`: the tag is the version (one leading `v` is dropped)
  and is written into the manifest by the workflow.
- `source`: the plugin project directory relative to the repository root, the directory that
  contains both `manifest.json` and `macrodeck-build.json` (for the scaffold,
  `src/<ProjectName>`). Resolve it by locating the files, not by assuming.
- `cli-version`: **exactly the Macro Deck SDK version** the plugin builds against (the packages share
  one version line; Creator Portal moderators block a mismatch or a missing value). Resolve both with
  `scripts/resolve-versions.py`, confirm that CLI version exists on nuget.org, and use the same one for
  scaffolding and CI. The workflow default is "newest prerelease", which resolves by SemVer order and
  can select an older build, so always pin it. Keep the short comment explaining why. Whenever the SDK
  version is bumped, bump `cli-version` and the CI install step in the same change.
- `changelog: ${{ github.event.release.body }}`.
- Leave `run-tests` and `run-stub-host` enabled. Use optional inputs only when needed:
  `test-path` when the root has no or several solutions, `build-per-platform` only for targets that
  build natively (a `net10.0-windows` target, native libraries), `runners` to override a runner,
  `upload-artifact` to keep the package on the run.
- Do not retain the template's workflows (`ci.yml`, `publish.yml` that pack the template package) or
  any workflow that does not belong to this plugin.

What only the user can do, to mention in the report: create the Project in the Creator Portal with a
Package ID equal to the manifest `id`, connect the public repository, make `publisher.name` match the
Portal owner, accept the Creator Guidelines, publish a GitHub release (the build lands in the
Portal's build library), then in the Portal create the release from that build, add it to a
submission and submit it for review (declaring AI use there if the manifest does not). Never create a
release or tag yourself without explicit approval, because it starts a build upload to the Portal.

## CI workflow

Create `.github/workflows/ci.yaml` from `templates/ci.yaml`. Small and fast:

- Triggers: `pull_request` and `push` to the default branch. `permissions: contents: read`.
- Job `test`: matrix over the operating systems the plugin supports (see Platforms), checkout without
  persisted credentials, `actions/setup-dotnet` with the SDK major the project targets
  (`global.json` if the repository has one), `dotnet build -c Release -warnaserror`,
  `dotnet test -c Release --no-build`, then the pinned CLI and
  `macrodeck-plugin test --project <source> --required-only`, so conformance is proven on every
  supported platform before a release does it.
- Job `package` (Linux): install the CLI at the pinned version, `macrodeck-plugin build`,
  `macrodeck-plugin validate --level publication`. This catches manifest and build-configuration
  drift before a release. Keep it only if it stays quick and reliable.
- Fill `<SOLUTION>` (the `.slnx`/`.sln` path), `<SOURCE>`, `<CLI_VERSION>` and the action refs. Pin
  actions to a full commit SHA with a version comment. Resolve current values, then verify the SHA
  belongs to the tag (annotated tags must be dereferenced):

  ```bash
  gh api repos/actions/checkout/releases/latest --jq .tag_name
  gh api repos/actions/checkout/git/ref/tags/<tag> --jq .object
  ```

  Same for `actions/setup-dotnet`. Verify the owner is the official `actions` organization. If `gh`
  is missing or unauthenticated, use the public GitHub REST API with `curl`
  (`https://api.github.com/repos/actions/checkout/releases/latest`).
- No secrets, no deployment, no caching tricks unless build time demands it. Lint the YAML with
  `actionlint` if it is installed; otherwise at least parse it.
- Do not run it against the user's GitHub without being asked to push. Locally, run the same
  commands the workflow runs.

## Platforms

Macro Deck ships for Windows x64, macOS arm64 and Linux x64 (the CLI also accepts `win-arm64`,
`osx-x64`, `linux-arm64`).

1. **No platform-specific code** (the normal case): declare `win-x64`, `osx-arm64` and `linux-x64`
   in `entrypoints` and `macrodeck-build.json` and run CI on `windows-latest`, `macos-latest` and
   `ubuntu-latest`. The Linux release runner cross-builds all three. Do not ask the user.
2. **Platform-specific code or native dependencies**: ask the user whether the plugin should be
   limited to the current platform so it can be tested, or should implement each platform (then
   isolate the OS code behind an interface, one implementation per OS, tested where possible).
   Whatever is decided, `entrypoints`, `macrodeck-build.json`, the CI matrix and the README's
   supported-platform statement must list exactly the same platforms. Do not declare a platform
   nothing has built or tested.
3. A platform-specific plugin that will be tested on this machine must declare an entrypoint for
   the host's own platform; `macrodeck-plugin test --artifact` launches the package for the machine's
   platform and fails with an entrypoint error otherwise (use `--project` for a quick local run).
4. `win-arm64` falls back to `win-x64` and `osx-arm64` to `osx-x64`. There is no `any` key.

## Build configuration

Framework-dependent, never self-contained: see [manifests.md](manifests.md#build-configuration).
`scripts/check-plugin.py` and the final review check project files, `Directory.Build.*`,
`macrodeck-build.json` and workflows for `SelfContained`, single-file, trimming and AOT settings.

Before a release, build the package the way the workflow does and inspect it:

```bash
macrodeck-plugin build --source <source> --output ./artifacts
macrodeck-plugin inspect --artifact ./artifacts/<id>-<version>.macroDeckPlugin
macrodeck-plugin validate --level publication --artifact ./artifacts/<id>-<version>.macroDeckPlugin
```

Do not commit `artifacts/`, `bin/`, `obj/`, `.macrodeck-dev-state/` or policy snapshots.
