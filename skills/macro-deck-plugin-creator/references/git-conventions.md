# Git: branches and commits

Applies to every repository the skill works in, unless the project's `AGENTS.md` or existing history
clearly says otherwise (then follow the project).

## Branches

- Never commit directly to the default branch. If you are on it, create a branch first.
- Name: `<type>/<short-kebab-description>`, with the type one of `fix/`, `feature/`, `chore/`
  and, where it fits better, `refactor/`, `docs/` or `ci/`. Add an issue number at the end when one
  exists. Examples: `feature/initial-plugin`, `fix/reconnect-after-token-expiry`,
  `chore/update-sdk-version`, `ci/add-test-workflow`.
- A harness-generated branch name that does not follow this is renamed (`git branch -m`) before the
  first commit; if it was already pushed, ask first.
- Do not push or open a pull request unless the user asked.

## Commit messages

- One line only, no body, no trailers.
- At most 50 characters, imperative mood, sentence case, no trailing period.
- No type prefix: not `feat:`, `fix:`, `chore:` or a scope in parentheses. The branch carries the type.
- Describe the actual change, concisely: `Add reconnect handling`, `Pin SDK and CLI to beta 14`.
- No AI attribution of any kind: no `Co-authored-by`, `Generated-by` or tool trailer, no mention of
  the agent, and do not alter the Git author identity. Keep the repository's existing identity.

Check the length before committing, for example:

```bash
msg="Add reconnect handling"; [ ${#msg} -le 50 ] || echo too long
```

## Splitting commits

Commit in small, coherent steps that each build and make sense alone, not one large commit:

- one logical change per commit; tests go with the behavior they cover
- separate commits for unrelated concerns: scaffold, a feature or action, README and docs,
  license and notices, CI and release workflows, dependency changes, refactors
- keep mechanical changes (renames, formatting) apart from behavior changes
- never mix in files unrelated to the task; stage deliberately (`git add <paths>` or `git add -p`),
  not `git add -A` blindly, and review `git diff --staged` before each commit
- for a new plugin a sensible order is: scaffold as generated and cleaned up, each capability with its
  tests, README, LICENSE and notices, CI and release workflows
- do not rewrite or squash existing history, and do not touch changes that were in the working tree
  before you started

Commit only when the user asked for it or the task includes it.
