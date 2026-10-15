# SDK, CLI and scaffolding

Everything here is a procedure for finding current facts. The facts themselves are not stored.

## Resolve versions first

```bash
python3 $SKILL_DIR/scripts/resolve-versions.py
```

It reads NuGet and the Store's SDK dependency policy and prints, per package: latest stable, latest
listed prerelease by publish date, highest listed by SemVer, highest including unlisted (what a
floating range can resolve to), and the recommendation. Rules it applies, which you must also apply
by hand if the script cannot run:

1. Use the latest **stable** version when one is listed.
2. If no stable exists, use the **most recently published listed prerelease**. A prerelease is then
   technically necessary. Tell the user in the final report. Do not choose a prerelease when a stable
   exists, unless the user explicitly asks.
3. Do not trust SemVer order or `--prerelease` to find the newest build. Prerelease labels were not
   published in alphabetical order (SemVer sorts `beta` before `preview`), and unlisted versions can
   still win a floating range. Observed in a real scaffold: the floating default resolved to an older
   preview that was below the Store's minimum SDK version.
4. The version must satisfy `minimumSdkVersion` from the SDK dependency policy. Below it, the
   Creator Portal refuses the build.
5. All `MacroDeck.*` packages in a plugin use one version (the template drives this with the
   `MacroDeckSdkVersion` property in `Directory.Packages.props`). Pin it explicitly to the resolved
   version. Do not leave a floating range such as `3.0.0-*`.
6. The CLI version is resolved the same way and **must equal the SDK version**. It is written into
   the release workflow (`cli-version`) and the CI workflow. If the latest CLI and SDK differ, use
   the SDK version for both after confirming the CLI package of that exact version exists.
7. Compare versions the way the Creator Portal does for the minimum SDK: release stages rank
   `alpha` < `preview` < `beta` < `rc` < release, so `3.0.0-preview.10` is older than
   `3.0.0-beta.4`. NuGet's own ordering is alphabetical and disagrees.

Use previews for a stable-seeking plugin only with that reasoning recorded. Re-run the script when
resuming a task days later.

## Installing the CLI

The CLI is the .NET tool `MacroDeck.Plugin.Cli` (command `macrodeck-plugin`). Install the resolved
version, not `--prerelease`:

```bash
dotnet tool install --global MacroDeck.Plugin.Cli --version <resolved>
```

Prefer a tool path or a local tool manifest when the user does not want a global install:
`dotnet tool install MacroDeck.Plugin.Cli --tool-path <dir> --version <resolved>`. If a CLI is
already installed, compare `macrodeck-plugin --version` with the resolved version and update when
older. The CLI needs the ASP.NET Core shared framework (`run` and `test` start a real local host).
Never guess CLI arguments: run `macrodeck-plugin --help` and `macrodeck-plugin <command> --help`
and use what they print. If help and the documentation disagree, the installed tool wins for
syntax and you report the discrepancy.

Commands that exist at the time of writing (verify with `--help`): `new`, `build`, `validate`,
`inspect`, `pack`, `merge`, `icon-pack`, `run`, `test`, `keygen`, `sign`, `verify`. `keygen`, `sign`
and `verify` are not part of Store publishing; never create or store signing keys, the Store signs
packages.

## Scaffolding a new plugin

`macrodeck-plugin new` installs the official template package `MacroDeck.Plugin.Templates` through
`dotnet new` (a machine-level side effect; tell the user) and generates the project.

1. Choose the values: display name, id, publisher, repository, description, license, platforms.
   - **id**: reverse-domain with **at least three** dot-separated parts (the Creator Portal
     requires three even though the manifest schema allows two), derived from the publisher, for
     example `com.<publisher>.<plugin>`.
     It must not use `macro-deck`/`MacroDeck` as namespace or publisher identity and must not use
     a third-party company's namespace for a plugin integrating that company's service
     (`com.<publisher>.<service>` instead). Template defaults such as `com.example.*` are
     placeholders.
   - **project name** must not start with `MacroDeck.`.
   - **platforms**: see [release-workflow.md](release-workflow.md#platforms).
2. Pin the template version to the resolved one. The CLI's default selects the template by
   SemVer order and can pick a stale template (observed: it chose an older preview whose generated
   files differed from the current template):

   ```bash
   macrodeck-plugin new --name "<Display Name>" --id <id> --publisher "<Publisher>" \
     --repository <url> --description "<description>" --license <SPDX> \
     --platform win-x64 --platform osx-arm64 --platform linux-x64 \
     --template-version <resolved template version> --output <dir> --non-interactive
   ```

   Verify option names with `macrodeck-plugin new --help` first.
3. Inspect everything the template produced. Read the generated `AGENTS.md` and `README.md`
   completely, then clean up:
   - Replace placeholders: description, `LICENSE` copyright holder (the template carries
     "Macro Deck Contributors", which is wrong for a third-party plugin), icon, localization keys,
     README. `LogMessageAction` is an example to replace with the real first action.
   - Remove anything that belongs to the template repository rather than a plugin: template
     workflows (`.github/workflows/ci.yml`, `publish.yml` that pack the template), `.template.config/`,
     `packaging/`, and unneeded sample content. A fresh `new` may not generate them; check anyway.
   - Keep `AGENTS.md` and keep a host pointer file such as `CLAUDE.md` only if it merely points to `AGENTS.md`. Do not add
     other agent instruction files. Update `AGENTS.md` when a rule in it stops matching the plugin.
   - Pin `MacroDeckSdkVersion` in `Directory.Packages.props` to the resolved SDK version.
   - Remove all local NuGet feeds: delete the `local` source (`./local-feed`) and its comment from
     `NuGet.config` so only nuget.org remains, delete the `local-feed/` folder (including its
     `.gitkeep`) if present, and remove the "Building against a local SDK build" passage from the
     README and `AGENTS.md`. Do the same for any other file or folder based source and for
     `RestoreSources` properties. Local feeds are flagged in the Store review.
   - Keep `MacroDeck.Plugin.Analyzers` (`PrivateAssets="all"`) and the strict `Directory.Build.props`.
     Do not relax nullable, analysis level or warnings-as-errors to make a build pass.
   - Initialize Git only if the user wants a repository created; keep the existing identity.
4. Restore, build and test the unmodified scaffold (`dotnet build -c Release -warnaserror`,
   `dotnet test -c Release`) before writing feature code, so later failures are yours.
5. Run `python3 $SKILL_DIR/scripts/check-plugin.py <repo>` to list what still needs work.

If the CLI or template cannot be installed (offline, policy), fall back to cloning
`https://github.com/Macro-Deck-App/Macro-Deck-Plugin-Template` and following its README rename steps
(id, name, description, publisher, repository, project, namespace and `AssemblyName` together with
the `entrypoints` paths, icon), and tell the user the official CLI path was not used.

## Documentation map

Resolve details from these, in this order of authority for behavior: installed tool help, SDK source
and XML docs, then docs pages. Where the generated project's `AGENTS.md` conflicts with older
knowledge, `AGENTS.md` wins; where the Creator Guidelines conflict with it, the guidelines win.

| Topic | Source |
| --- | --- |
| Docs site (all pages below) | https://docs.macro-deck.app |
| Features, one page per capability (actions, variables, events, setup flows, localization, logging, music, weather, profiles, devices, testing, settings migrations) | `/features/` |
| Macro Deck UI, widgets, config views, developer preview | `/ui/` |
| Manifest reference | `/reference/manifest/` (schema: `https://docs.macro-deck.app/schemas/plugin-manifest-v1.schema.json`, verify it returns JSON; fallback `docs/public/schemas/plugin-manifest-v1.schema.json` in the Macro Deck repository) |
| Plugin hosting, protocol, capability parity, analyzers, conformance | `/reference/` |
| CLI | `/cli/` and `macrodeck-plugin --help` |
| Publishing and release workflow inputs | `/guides/publishing/`, `/creator-portal/release-workflow/` |
| Compatibility, deprecations, migrations | `/policies/` |
| Source of docs and SDK | https://github.com/Macro-Deck-App/Macro-Deck (`docs/`, `sdk/`) |
| Template | https://github.com/Macro-Deck-App/Macro-Deck-Plugin-Template (`AGENTS.md`, `README.md`) |
| Worked examples per capability | https://github.com/Macro-Deck-App/Macro-Deck-Sample-Plugins |
| Release workflow source | https://github.com/Macro-Deck-App/GitHub-Actions |
| Store policy documents | `scripts/fetch-policies.py` (API at `https://api.macro-deck.app/api/v1/public/`) |

For uncertain APIs, read the SDK source or the sample plugins rather than reasoning from names.
The docs site, repository and template can be fetched with whatever web or `gh` access the host has;
cloning the repositories shallowly into a scratch directory is the most reliable way to grep them.
Pages and file layouts move: if a path 404s, search the repository instead of guessing.

Real-world references: the sample plugins (one per capability area, laid out exactly like a
scaffolded plugin) and the Store listings of existing plugins. Use them for shape and idioms,
never copy code without checking its license (see [licensing.md](licensing.md)).
