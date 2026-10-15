# What the Store checks, and how to pass it first time

A plugin passes through three gates: the upload (automatic, refuses with an HTTP error), the
pre-flight checks that run against a submission (automatic findings shown to the moderator), and
the Creator Moderator's review (human, policy and security). Build the plugin so every gate passes
on the first try, and run a self-review as the moderator would.

The rules below were read from the Macro Deck Platform repository and the maintainers' moderation
rules at the time this skill was written. They change. Re-read the current sources each task:

- `https://github.com/Macro-Deck-App/Macro-Deck-Platform`: `docs/publishing-flow.md` (upload checks,
  dependency policy, self-contained builds, AI declaration, conformance, pre-flight checks) and
  `backend/src/MacroDeck.Platform.Api/Reviews`, `backend/src/MacroDeck.Platform.Infrastructure/Store/ReviewCheckRunner.cs`,
  `backend/src/MacroDeck.Platform.Domain/Projects` (policies). Clone shallowly and grep.
- Docs: `/creator-portal/` (`publish-plugin`, `review`, `release-workflow`, `conformance`).
- `scripts/fetch-policies.py` for guidelines, blocked packages and SDK policy.

If a source disagrees with this file, follow the source and mention it in the report.

## Gate 1: upload (the publish workflow)

The release workflow uploads a zip with the package, build metadata, dependency list and
conformance reports. The Platform refuses before storing anything when:

| Cause | Fix |
| --- | --- |
| The build did not run through `Macro-Deck-App/GitHub-Actions/.github/workflows/publish-plugin.yml` at a `v*` tag, or ran in a repository not bound to the Project, or the repository is not public | Call the official workflow with `uses:` at the major tag; one release per tag; public repository |
| The manifest `id` is not the Project's Package ID | Create the Creator Portal Project with Package ID equal to the manifest `id` |
| The Package ID is not a lowercase reverse-DNS id with **at least three** dot-separated parts (the manifest schema alone allows two) | Use `com.<author>.<plugin-name>` style ids |
| Manifest unreadable, or `publisher.name`, `license` (SPDX, at most 64 chars) or `repository` missing or different from what the Store publishes under (publisher is compared ignoring case; repository must be `https://github.com/<owner>/<name>` of the building repository) | Set them exactly; ask the user for the Portal owner name |
| `additionalLinks` invalid (unknown standard type, missing url or label, duplicates) | Validate against the schema; prefer to omit them |
| Dependency list breaks the policy: a `MacroDeck.*` package not on the allowed list, an SDK below the minimum (compared with release stages ordered alpha < preview < beta < rc < release), a blocked package anywhere in the graph | [creator-guidelines.md](creator-guidelines.md) Store gate, `scripts/resolve-versions.py` |
| An entrypoint is self-contained on a platform the Project holds no grant for | Stay framework-dependent. Self-contained needs a request in the Creator Portal (written justification of at least 80 characters, approved by a moderator); never ship it without the user's decision |
| Conformance report missing, unreadable, for another plugin or version, handshake not reached, or a Required check failed on any declared platform the workflow runs | Do not disable `run-stub-host`; run `macrodeck-plugin test` and fix every Required failure |
| The upload zip or its metadata is unreadable or holds more than 64 entries (the zip holds the package as one entry plus metadata, dependency list and conformance reports; the official workflow builds it) | Use the official workflow unchanged; keep the package itself lean (`macrodeck-plugin inspect`) |
| Version not strictly greater than the last published version, or a withdrawn or deleted version number reused | Use a new SemVer tag every release |
| The ref is not a tag, or the Project is already in review | Release from a tag; wait for or withdraw the review |
| More than 10 uploads from one repository per hour | Do not loop releases |

## Gate 2: pre-flight checks on the submission

Automated findings a moderator reads. Errors are real problems, warnings are advisory:

- the build's commit is still in the repository and the repository is reachable and public
- the uploaded package is present and its digest matches
- the package carries a readable `manifest.json` that declares its files, at least one supported
  runtime identifier, author, license and repository, passes `additionalLinks` checks, and runs
  framework-dependent (or self-contained only with a grant)
- a conformance report exists for every declared platform and shows no failed Required check
- the Store summary exists (the portal summary is at most 200 characters; the package description
  fallback is at most 500 characters or a short first paragraph), so keep the manifest `description`
  short and meaningful
- the publisher has a valid signing certificate (the Store signs; you never do)
- the AI declaration is present. **Submitting is refused until it is declared**, either in the
  manifest `ai` object or in the portal's Entry information. A bundled icon pack that declares
  AI-made icons while the plugin's own declaration says no AI assets raises a warning
- bundled icon packs, if any, are declared, stored, covered by the signature and readable

The plugin icon is a relative path to a png, jpg, jpeg, webp or svg file. An SVG must be passive: no
scripts, event handlers, embedded documents or references to anything outside itself (an embedded
raster image is fine).

Store listing limits: summary 200 characters, description 20,000, at most 10 tags of at most 32
characters, https author link. The Creator Guidelines must be accepted in the portal by the submitter
(and an organization's owner). Only the user can do these.

## Gate 3: moderator review

A Creator Moderator decides on safety and policy, not on code quality. The standing rules include:

| Rule | What to make true |
| --- | --- |
| Blocked package or SDK below minimum | None in the full graph, direct or transitive, shipped or build-time |
| Package built and published only by `publish-plugin.yml@v1` | Called at job level at that tag from this repository, no local copy, no reimplemented upload, `platform-url` and `audience` untouched, no custom step that alters what is built or uploaded. Extra self-built release jobs next to it are discouraged: let the trusted workflow build, test and stub-host |
| **`cli-version` equals the SDK version** | The CLI version passed to the workflow is exactly the SDK version (for example both `3.0.0-beta.14`), pinned, never missing; bump them together; confirm that CLI version exists on nuget.org. `scripts/check-plugin.py` checks it |
| Self-contained without a legitimate technical reason is a blocker | Framework-dependent on the runtime Macro Deck ships |
| No committed binaries or build output | No tracked `.dll`, `.exe`, `.so`, `.dylib`, `.nupkg`, and no `bin/`, `obj/`, `publish/` output in Git, even if the build would not ship them. Ignore `bin/` and `obj/`; reference dependencies as NuGet packages. Non-code assets (images, fonts, svg) are fine |
| LICENSE and README at the repository root | A real license text that matches the manifest `license`, and a non-empty README that describes the plugin |
| Creator Guidelines | Every mandatory statement of the current version (see [creator-guidelines.md](creator-guidelines.md)) |
| Security review of behavior | The capability table below |
| No review manipulation | No text in the repository that addresses a reviewer or an agent ("approved", "skip this file", "ignore instructions"), no behavior that differs between the repository and the built package, no logic gated on CI, debugger or date |

Also: the source the moderator reads is the commit that was built, so the repository must be what
the package is built from. Local feeds, extra package sources and `HintPath` DLL references are
flagged.

### What a security reviewer looks at

Using a sensitive API is not a finding by itself. What matters is what it touches, where data goes,
who controls the input and whether it matches the stated purpose. Make each of these either absent
or obviously proportionate and documented in the README:

- Process or shell execution: fixed, documented programs or user-configured targets only; no hidden
  windows, encoded commands, execution-policy bypass, or commands from the network.
- Dynamic code and assembly loading from network, resources or runtime-written files; native interop
  that is not needed for the feature; anything resembling injection.
- Network: only the integrated service, documented endpoints and localhost; no raw IPs, paste or
  webhook drop sites, request bins, tunnels, remote kill switches or remote configuration that
  toggles behavior; no sending machine identifiers, files, environment variables or tokens.
- Telemetry or analytics: avoid it; if present it is minimal, opt-in and disclosed.
- File system: the plugin data directory and user-chosen files only; no enumeration of the profile
  or other applications' data; no recursive deletes outside the plugin's own files.
- Credentials: only the user's own token for the integrated service, stored through the host's
  secret handling; never other applications' credentials, cookies, browser or keychain data.
- Input, clipboard, screen, camera or microphone use only when that is the documented feature and
  user-initiated; no global hooks or monitoring.
- Persistence outside Macro Deck's lifecycle (startup entries, services, scheduled tasks), registry
  writes, privilege changes, security-product manipulation, firewall rules: none.
- Downloading executables, DLLs or scripts, and self-updaters that bypass the Store: none. Updates
  go through the Store.
- Obfuscation, large encoded blobs, string-built API names or URLs, packed assemblies: none.
- Build time: no MSBuild `Exec`, inline tasks, downloads, pre or post build events with side effects,
  imports from outside the repository, source generators or analyzers from unknown publishers.
- Secrets: none in the repository (see [security.md](security.md)).
- Deception: no official-looking names, logos or UI, no prompts for other services' passwords.

## Self-review procedure

Before declaring a plugin ready, review it as the moderator would, ideally by a separate reviewer
(see [multi-agent-workflow.md](multi-agent-workflow.md)):

1. Fetch the current policies and read the whole guidelines.
2. Run `python3 $SKILL_DIR/scripts/check-plugin.py <repo> --artifact <packed file>`.
3. Run the CLI checks from [testing-and-debugging.md](testing-and-debugging.md): `validate --level
   publication`, `inspect`, and the conformance suite on the packed artifact.
4. Walk the three tables above and the capability list, citing file and line for every plugin
   behavior that touches a sensitive area, and record why it is proportionate.
5. Confirm the README states every external service, the data sent to it and the limitations.
6. List what only the user can do (Portal project with matching Package ID, repository binding,
   publisher name, AI declaration in the portal if it differs, guidelines acceptance, release).
