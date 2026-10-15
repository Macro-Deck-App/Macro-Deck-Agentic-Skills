# Creator Store Guidelines and Store gate

Never reconstruct the guidelines from memory or from this file. They are versioned and change.

## Fetch

```bash
python3 $SKILL_DIR/scripts/fetch-policies.py <directory outside the repository>
```

This downloads and prints:

- Creator Guidelines (Markdown), with the `X-Creator-Guidelines-Version` header.
- Blocked packages (JSON): `packagePattern`, `versionPattern` (`null` blocks every version), `reason`.
- SDK policy (JSON): `minimumSdkVersion` and `allowedMacroDeckPackages`.

URLs, in case the script cannot run:
`https://api.macro-deck.app/api/v1/public/creator-guidelines`,
`.../dependency-policy/blocked-packages`, `.../dependency-policy/sdk`.

If any document cannot be fetched, say so and stop on the parts that depend on it. Do not assume it
still says what it said last time. Fetch at the start (research), give the full text to the
reviewer, and fetch again right before declaring the work done. Read the whole guidelines document,
not only the sections that seem relevant. Where this skill or the generated `AGENTS.md` disagrees with
the guidelines, the guidelines win; report the conflict.

## Store gate

All of these hold before the work is done. Report the guidelines version checked.

1. The plugin follows the whole current guidelines (checklist below).
2. No blocked package appears anywhere in the full dependency graph:
   `dotnet list <project> package --include-transitive`. Match by `packagePattern` and
   `versionPattern`. Fix by replacing the package or restructuring. Never work around a block by
   vendoring, renaming or loading the package another way.
3. The Macro Deck SDK version is at least `minimumSdkVersion`, in every build that is released
   (floating ranges, a pinned property and a local feed can each break this).
4. Every package whose id starts with `MacroDeck.` matches an entry of `allowedMacroDeckPackages`
   (entries may contain `*` wildcards, matched ignoring case).
5. The manifest names its author, license and repository (see [manifests.md](manifests.md)).
6. The plugin passes the conformance suite on every declared platform
   (`macrodeck-plugin test`); no Required check fails. The Platform's own upload, pre-flight and
   moderator rules are in [store-submission-checks.md](store-submission-checks.md). The publish workflow runs it on a stub host
   per platform; never disable it.

## Checklist by guideline area

Map each area of the current document to concrete evidence in the repository. The topics below are
the ones that have been stable; add any new section the fetched version contains.

| Area | Evidence to produce |
| --- | --- |
| Open source and repository | Public GitHub repository, OSI-approved license, a valid `LICENSE` file, source corresponds to what is distributed, the author has the right to publish all code |
| Dependencies and third-party code | No precompiled third-party DLLs or compiled assemblies bundled; dependencies referenced as public NuGet packages from legitimate sources; bundled code complies with its license; `references/dependency-security.md` passed |
| Intellectual property and content licensing | Every icon, image, font, sound, music file, text and code snippet has a license or permission you can name; attribution conditions followed; `THIRD-PARTY-NOTICES` and `NOTICE` accurate |
| Security and malicious software | No credential or token theft, hidden actions, unexpected network access or unrelated behavior; behavior matches the description; `references/security.md` passed |
| Naming and branding | Id and namespace do not use Macro Deck or a third-party company/service as own identity; names do not imply official status ("X Plugin for Macro Deck" is fine, "Official X Plugin" is not); no Macro Deck logo as primary identity |
| Quality and functionality | Does what the listing says; maintained; destructive behavior guarded |
| Legal compliance | No content or function that facilitates illegal activity, bypasses security, or violates privacy law |
| Privacy and data handling | Only necessary data, documented network communication and external services in README, credentials only for a clear purpose, minimal permissions |
| AI features and generated content | Accurate `ai` declaration (see [manifests.md](manifests.md)), user notification, provenance preserved, deepfake labeling, services and data disclosed |
| Store information | Accurate name, description, screenshots; README has install and usage instructions, limitations, required services, configuration steps; no impersonation |
| Updates and maintenance | Breaking changes documented, no needless breakage of existing configs, ids persisted in user data stay stable |

In the final review, produce an explicit line per area (met, not applicable with reason, or not
met with the fix). A review that only says "compliant" is not accepted.
