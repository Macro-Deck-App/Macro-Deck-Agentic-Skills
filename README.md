# Macro Deck Skills

Reusable agent skills for developing extensions and integrations for Macro Deck.

## Skills

### macro-deck-plugin-creator

Takes a rough idea for a Macro Deck 3 plugin through research, planning, independent reviews, implementation, testing with the plugin CLI and conformance suite, documentation, licensing and release preparation for the Macro Deck Store. It also modifies existing Macro Deck 3 plugins in place and detects Macro Deck 2 projects.

The skill resolves volatile facts (SDK and CLI versions, manifest schema, Creator Guidelines, dependency policy, workflow inputs) from the official sources every time it runs. It ships small Python helper scripts (Python 3 standard library only) for version resolution, policy download, consistency checks and dependency inventory; they are optional conveniences.

## Requirements

For installation and update management with GitHub CLI, use GitHub CLI 2.90.0 or newer. The `gh skill` commands are currently in public preview.

## Installation

Install the plugin creator skill with:

```bash
gh skill install Macro-Deck-App/Macro-Deck-Skills macro-deck-plugin-creator
```

`gh skill` can install the skill into the location expected by the selected agent host. To target a specific supported agent, use its `--agent` option.

For example:

```bash
gh skill install Macro-Deck-App/Macro-Deck-Skills macro-deck-plugin-creator --agent claude-code
```

Run `gh skill install --help` to see the agent identifiers supported by your installed GitHub CLI version.

## Manual installation

If you do not use `gh skill`, install the skill by copying its directory into the skills location of your agent host.

```bash
git clone https://github.com/Macro-Deck-App/Macro-Deck-Skills.git
```

Then copy `skills/macro-deck-plugin-creator` (the whole directory, including `references/`, `scripts/` and `templates/`) into the host's skills directory, either per user or per project. For Claude Code, for example, that is `~/.claude/skills/` or `<project>/.claude/skills/`:

```bash
cp -R Macro-Deck-Skills/skills/macro-deck-plugin-creator ~/.claude/skills/
```

The directory name must stay `macro-deck-plugin-creator`. Other hosts (Codex, OpenCode, GitHub Copilot) use their own skills locations; see the host's documentation, or run `gh skill install --help` to see the supported agents and their targets.

Restart or reload the agent so it discovers the skill. The helper scripts need Python 3 (standard library only), and building plugins needs the .NET 10 SDK and Git. To update a manual installation, pull the repository and copy the directory again.

## Updating

Skills installed through `gh skill` contain provenance metadata that allows GitHub CLI to check their source for updates.

Update this skill with:

```bash
gh skill update macro-deck-plugin-creator
```

Or update all installed, unpinned skills:

```bash
gh skill update --all
```

## Version pinning

For environments that need reproducible skill versions, install a tagged version instead of tracking the latest version.

```bash
gh skill install Macro-Deck-App/Macro-Deck-Skills macro-deck-plugin-creator@v1.0.0
```

Pinned skills are not changed by normal `gh skill update` operations.

## Agent compatibility

The skills use the portable `SKILL.md` format and intentionally avoid host-specific instructions. They are intended to work with agent hosts that support Agent Skills, including Claude Code, Codex, OpenCode, and GitHub Copilot.

Agent/subagent definitions are not part of the portable skill itself. Different agent hosts currently use different formats for custom agents and subagents. Host-specific adapters may be provided separately without changing the portable skill.

## Repository validation

Maintainers can validate the repository and its skills with:

```bash
gh skill publish --dry-run
```

GitHub CLI can also fix supported metadata issues without publishing:

```bash
gh skill publish --fix
```
