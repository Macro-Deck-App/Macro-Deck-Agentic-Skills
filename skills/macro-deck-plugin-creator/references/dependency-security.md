# Dependency selection and supply-chain security

Dependency choice is security-sensitive. AI agents are a target of dependency hallucination and
package-confusion attacks: attackers publish packages under names that models have invented. A
plausible name is not evidence that a package exists, is the intended one, or is safe.

## Rule

Never install, add to a manifest or lockfile, restore, run or recommend a dependency that has not
passed the checks below **and** been approved by the user. This covers NuGet, npm, pip, Cargo,
brew/apt, GitHub Actions, downloaded binaries and scripts, tools, templates and any other mechanism.

Not covered: restoring exactly what the project's manifests and lockfiles already declare, including
the test packages the official scaffold references (test SDK, NUnit and adapters, which count as
approved scaffold content), and the official Macro Deck packages the scaffold references (still check them against the allowed list and
minimum version).

## Procedure

1. **Is it necessary?** Check whether .NET, the Macro Deck SDK, ASP.NET Core (`IHttpClientFactory`,
   options, `System.Text.Json`, `System.Threading.Channels`, `System.IO.Compression`) or an existing
   dependency already does the job. Small functionality is safer written directly. Convenience or a
   name that came to mind is not a reason.
2. **Does the exact id exist on the authoritative registry?** For NuGet query nuget.org (for example
   `https://api.nuget.org/v3-flatcontainer/<lowercase-id>/index.json`, the registration API or the
   package page). Do not rely on search ranking or on a model's memory. Compare the exact id
   character by character with what you intended.
3. **Identity and provenance.** Owners and authors, a verified/prefix-reserved badge where shown,
   `repositoryUrl`/`projectUrl` that points to a real repository which in turn references the same
   package id, repository activity (commits, issues, releases), signed packages where available.
4. **Established and maintained.** Total and recent downloads, age of the first version, release
   cadence, last release, open security issues. Prefer widely used packages with clear provenance
   over obscure ones that provide trivial functionality.
5. **Suspicious signals.** Very new package with a name close to a popular one, a recent owner
   change, a sudden new version after long silence, install scripts or build targets (`.props`,
   `.targets`, analyzers, tools) that run code, missing repository link, repository that does not
   mention the package, README copied from another project, odd dependencies.
6. **Typosquat and confusion check.** Compare against the popular package it might imitate
   (hyphens, dots, plural, `.Core` suffixes, transposed letters). Check that it is not a package
   from a private or internal-looking namespace. Check the package's own dependencies the same way.
7. **License.** Read the license expression or file in the package (see [licensing.md](licensing.md)).
   It must be compatible with the plugin's license, permit redistribution, and be OSI-approved
   where the guidelines demand it. Unknown or missing license: do not use.
8. **Known vulnerabilities.** `dotnet list <project> package --vulnerable --include-transitive` and
   the registry's advisory data. Prefer a version without advisories.
9. **Blocked and allowed lists.** Compare with the Store's blocked packages (any version rule) and,
   for ids starting with `MacroDeck.`, the allowed list. See [creator-guidelines.md](creator-guidelines.md).
10. **Decide.** If legitimacy cannot be established with reasonable confidence, do not install it;
    implement the functionality directly or ask the user. Never run an install command for an
    unverified package, not even "to see if it exists".

## Asking for approval

Before adding it, tell the user: package id and version, what it is for, the registry and source,
the verification evidence (owner, repository, downloads, license, advisories), why the existing
dependencies cannot do the job. Wait for approval. A reviewed plan is not approval. Record the
decision (package, version, license, date) in the working note, and update `THIRD-PARTY-NOTICES`
and `NOTICE` in the same change.

## Pin and keep

- Pin versions through central package management (`Directory.Packages.props`), exact versions,
  no floating ranges for third-party packages. Keep transitive pinning on.
- Packages with build-time-only roles use `PrivateAssets="all"` so they are not shipped.
- Re-check when a dependency is added, updated or removed: inventory
  (`scripts/inventory-dependencies.py`), notices, vulnerabilities, blocked list.
- Do not add an alternate package source (`NuGet.config`) and do not keep local feeds. Remove the
  scaffold's `local` source and `local-feed/` folder (see [sdk-and-cli.md](sdk-and-cli.md#scaffolding-a-new-plugin))
  so only nuget.org remains; moderators flag local feeds.

## GitHub Actions and tools

Apply the same procedure. Use actions from the official `actions/*` organization or the Macro Deck
publishing workflow, pinned to a full commit SHA with a version comment (resolve the current
release tag and its SHA through the GitHub API, then verify the SHA belongs to that tag). Exception:
the Macro Deck publishing workflow must be referenced by its `v*` tag because the Platform only
accepts it from there. Do not run downloaded scripts (`curl | sh`), and install the CLI only as the
official `MacroDeck.Plugin.Cli` NuGet tool at a resolved version.
