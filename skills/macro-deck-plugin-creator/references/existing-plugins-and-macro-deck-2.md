# Existing plugins and Macro Deck 2

## Existing Macro Deck 3 plugin

A repository with `manifest.json` next to `macrodeck-build.json` is a Macro Deck 3 plugin. Modify it
in place. Never run the scaffold again and never restructure it for taste.

1. Read `AGENTS.md` fully, the README, `git log` for conventions, and ask nothing that the repository
   answers.
2. Inspect: architecture and capability set, SDK and CLI versions used (compare with
   `scripts/resolve-versions.py` and the policy minimum), `Directory.Packages.props`, manifests and
   their consistency, dependencies, `LICENSE`, `NOTICE`, `THIRD-PARTY-NOTICES`, workflows, tests, the
   README's claims, the `ai` declaration.
3. Run `python3 $SKILL_DIR/scripts/check-plugin.py <repo>` and the validation list to learn the
   baseline. Separate pre-existing problems from yours. Report them; fix them only when the task
   covers them or the user agrees. A pre-existing blocking Store issue (below the minimum SDK, a
   blocked package, self-contained publishing, a secret) is always reported.
4. Preserve the repository's conventions (indentation, naming, structure, test framework, localization
   layout). Where `AGENTS.md` conflicts with current docs or the guidelines, say so.
5. Change only what the task needs: the smallest appropriate diff, tests for the change, README and
   notices updated when behavior or dependencies change.
6. Upgrading the SDK is its own decision: check the compatibility, deprecation and migration pages
   (`/policies/`), read analyzer diagnostics, change deprecated usage the build reports, and test.
   Do it when the user asks or the Store requires it (minimum SDK), not as a side effect.
7. Run the phases that apply: plan (short for small changes), plan review for non-trivial changes,
   implementation, validation, final review of the diff.
8. Do not rewrite history, force-push, reformat unrelated files, or touch changes that were in the
   working tree before you started.

## Macro Deck 2 detection

Macro Deck 2 plugins and Macro Deck 3 plugins are different products with different SDKs. Treat the
following as Macro Deck 2 signals (verify what you find; none is guaranteed):

- A project referencing the NuGet package `SuchByte.MacroDeck` (the Macro Deck 2 plugin API package)
- An `ExtensionManifest.json` and a class deriving from the Macro Deck 2 plugin base type, Windows
  Forms or `System.Windows.Forms` UI, a `.dll`-only plugin layout
- The user saying "Macro Deck 2", "v2", or asking to port or migrate an old plugin

When any signal appears:

1. Do not treat it as an ordinary new plugin and do not run the Macro Deck 3 scaffold over it.
2. Do not invent migration rules. Check the current official guidance:
   - `/features/settings-migrations/` documents importing a user's Macro Deck 2 settings (buttons,
     connections, credentials) into an integration of a Macro Deck 3 plugin. That is about user data,
     not about porting plugin code.
   - `/policies/migrations/` covers SDK and protocol migrations inside Macro Deck 3.
   - Search the docs and the Macro Deck repository for a plugin porting guide. If a reliable one
     exists, follow it.
3. If no reliable porting guidance exists, say so, explain that migration-specific behavior needs
   to be handled separately, and offer options: (a) a new Macro Deck 3 plugin that re-implements the
   functionality from the user's description, using the old code only as a behavior reference and
   respecting its license; (b) adding the settings migration provider to the new plugin once it
   exists; (c) leaving the Macro Deck 2 plugin untouched. Let the user choose.
4. Never modify a Macro Deck 2 project with Macro Deck 3 conventions, and never change its manifest
   toward the Macro Deck 3 schema.
