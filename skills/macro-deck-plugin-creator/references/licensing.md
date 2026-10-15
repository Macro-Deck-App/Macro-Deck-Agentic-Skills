# Licensing, NOTICE and THIRD-PARTY-NOTICES

Goals: the plugin is open source under an OSI-approved license, the author really holds the rights
they claim, every incorporated component and asset is attributed as its license requires, and the
notice files match what is actually shipped. Never invent licenses, license texts, copyright
holders, attribution requirements or package ownership. Not legal advice: when a case is unclear,
say so and ask the user.

## LICENSE

- Required, OSI-approved (the Creator Guidelines require it), a valid license file at the repo
  root, and the same license as the manifest's SPDX `license` field.
- If the user names a license, use it (after checking incorporated code does not forbid it). If not,
  use MIT, which the official template and many Macro Deck plugins use, unless incorporated
  copyleft code requires a compatible license. Report the default you chose.
- Take the license text from the SPDX license list or the official source, not from memory
  (`https://github.com/spdx/license-list-data`, `text/<id>.txt`).
- The copyright line names the real rights holder and the year. The template ships a placeholder
  holder ("Macro Deck Contributors"): replace it. Use the publisher or author name the user gave,
  or the Git identity if the user confirms it. Do not name a company or person that did not agree
  to it. Code written by an agent for the user is the user's to license; copied or adapted code
  keeps its original license and notices.
- The plugin may not use the Macro Deck name, logo or branding as its own identity. Macro Deck's SDK
  packages are Apache-2.0; Macro Deck's name and logo are not licensed for reuse.

## What must be checked

Everything that ships in the package or the repository, or that you copied from somewhere:

- NuGet packages (direct and transitive that reach the output), and any npm or other package
  manager content if the plugin has a web or tooling part
- Copied or adapted source code and snippets (including from the sample plugins and other plugins,
  Stack Overflow, blog posts, gists): license, author, required notice
- Icons, images, fonts, sounds, music, templates, translations, data files, bundled assets
- Generated assets: license of the generator or model output terms, see the AI statement rules in
  [manifests.md](manifests.md#ai-statement)
- Trademarks and logos of third-party services: use only to identify the integration, no implied
  endorsement, check the brand's terms; a service logo is not covered by an open license

Procedure:

1. `macrodeck-plugin build` (or `dotnet publish` for one runtime identifier), then
   `python3 $SKILL_DIR/scripts/inventory-dependencies.py <publish dir>`. It lists the packages that
   actually ship (from the published `*.deps.json`) with license expression, authors, copyright,
   repository URL, and a `needsReview` list. Build-only packages (analyzers with `PrivateAssets`)
   are not shipped and are not listed. Runtime assemblies that Macro Deck's .NET runtime provides
   are not packages and need no entry.
2. Resolve every `needsReview` item by reading the package's own license file or repository.
   Unknown license: do not ship the component.
3. Check compatibility with the plugin license and the guidelines: permissive licenses (MIT,
   Apache-2.0, BSD, ISC, Zlib, Unlicense/CC0) are fine; copyleft (GPL, AGPL, LGPL, MPL, EPL)
   needs an explicit compatibility judgment and often changes the plugin license: ask the user;
   non-commercial, no-derivatives or proprietary licenses are not acceptable for a distributed
   open-source plugin; Creative Commons assets need their attribution conditions satisfied.
4. Collect asset provenance: where each icon, image, font or sound came from, its license, author
   and URL. If the origin cannot be established, do not ship it. Prefer assets the user created or
   that have clear open licenses.

## THIRD-PARTY-NOTICES

Macro Deck's own file (https://github.com/Macro-Deck-App/Macro-Deck/blob/main/THIRD-PARTY-NOTICES) is
the format reference. It is generated from the dependency graph by a tool; a plugin's file is
smaller but follows the same layout:

```text
THIRD-PARTY SOFTWARE NOTICES AND INFORMATION
<Plugin name>

<Plugin name> includes the third-party components listed below. Each component is
provided under its own license, reproduced in the license texts section.

====...====
NuGet packages
====...====

<Package id>
  License: <SPDX expression>
  URL: <repository or project URL>
  Texts: [<n>]

====...====
Bundled assets
====...====

<Asset or set name>
  License: <SPDX id or LicenseRef-...>
  URL: <source>
  Note: <what it is used for, trademark notice if applicable>
  Texts: [<n>]

====...====
License and notice texts
====...====

[1] <Package id>
--------------------------------------------------------------------------------
<copyright line from the package metadata>

<full license text>
```

- `scripts/inventory-dependencies.py <publish dir> --notices <file> --header-name "<Plugin name>"`
  drafts the NuGet section and the texts. License texts come only from a license file inside the
  package or the SPDX list; anything else is marked `NEEDS MANUAL REVIEW`. Copyright lines come
  only from package metadata. Review the draft, remove the review markers by resolving them, and
  add bundled assets by hand from the provenance you collected. Never fill a gap by guessing.
- A plugin ships Macro Deck's SDK assemblies and their dependencies, which are Apache-2.0 at the
  time of writing, so a plugin with the standard scaffold normally has a non-empty notices file.
  Decide from the inventory, not from this sentence.
- Generated files must be reproducible. Regenerate after every dependency or asset change; do not
  hand-edit the generated part. Mention the regeneration command in the README or AGENTS.md.

## NOTICE

Create `NOTICE` only when something requires it: Apache-2.0 components that carry their own NOTICE
text (section 4(d) of that license), explicit attribution lines a license demands, or required
trademark statements. Content is copied from the upstream NOTICE files, plus the plugin's own
name and copyright line. If nothing requires it, do not create an empty or decorative `NOTICE`,
and say so in the report. Macro Deck's own `NOTICE` is the format example (product name, copyright
line, license pointer, third-party pointer, then required notices per component).

## Keep it current

Whenever a dependency or asset is added, removed or updated, re-run the inventory and re-evaluate
`NOTICE` and `THIRD-PARTY-NOTICES` in the same change. The final reviewer compares them to the real
dependency list and asset set.
