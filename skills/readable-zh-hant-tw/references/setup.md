# Setup: whether to apply globally

`<skill folder>` is this skill's folder (see SKILL.md). Commands use `python3`; if `python3` can't be found, tell the user that applying globally requires Python 3, then follow the rules in SKILL.md for this conversation only.

1. If the user invokes the skill with words like 「移除」「取消全域」「uninstall」: first run `python3 -I <skill folder>/scripts/install.py --uninstall --dry-run` to show them what will change, and after they agree, run it again without `--dry-run`. Once done, tell them: a new session needs to be started for the original settings to be restored.
2. Otherwise, run `python3 -I <skill folder>/scripts/install.py --status`. If `installed` is `true`, skip the rest of this file; if this conversation already has a previous reply, treat the invocation as 「看不懂」 and follow `<skill folder>/references/re-pitch.md`.
3. If this conversation already has a previous reply, restate it following `<skill folder>/references/re-pitch.md`, follow the rules in SKILL.md for this conversation only, and skip the rest of this file without asking anything.
4. Otherwise, ask the user a single question to choose between:
   - **Apply globally**: from now on, every new session's replies, Chinese documents written to files, and subagents will follow this rule set, and two automatic-check hooks will also be installed. This will modify `~/.claude/settings.json` and `~/.claude/CLAUDE.md`, backing them up first. To remove this later, run `/readable-zh-hant-tw 移除全域套用`.
   - **Use for this conversation only**: no settings will be changed.
5. If they choose to apply globally: first run `python3 -I <skill folder>/scripts/install.py --dry-run` to show them what will change, and after they agree, run it again without `--dry-run`. Once done, tell them: a new session needs to be started for it to take effect.
6. If they choose to use it for this conversation only: follow the rules in SKILL.md, and don't ask again in this conversation. If the user invokes the skill again later in this conversation, treat it as 「看不懂」 and follow `<skill folder>/references/re-pitch.md`.
