# Skills in `.claude/skills/`

Claude Code loads these automatically in sessions opened on this repository. To use one elsewhere, copy its folder into another project's `.claude/skills/` or into `~/.claude/skills/`.
Third-party skills are vendored copies pinned to the commit below; update by re-copying from upstream after review.

| Skill(s) | Source | Commit | Licence | Notes |
|---|---|---|---|---|
| `brainstorming`, `writing-plans`, `executing-plans`, `subagent-driven-development`, `dispatching-parallel-agents`, `test-driven-development`, `systematic-debugging`, `verification-before-completion`, `requesting-code-review`, `receiving-code-review`, `using-git-worktrees`, `finishing-a-development-branch`, `writing-skills`, `using-superpowers` | github.com/obra/superpowers | `22f0b46` | MIT | Skills only. The plugin's SessionStart hook and `diagnosing-superpowers` are not included. |
| `ui-ux-pro-max` | github.com/nextlevelbuilder/ui-ux-pro-max-skill | `8db3633` | MIT | Main skill only; script paths rewritten from `${CLAUDE_PLUGIN_ROOT}` to `.claude/skills/ui-ux-pro-max/`; upstream tests omitted. |
| `unslop` | github.com/heydamir/unslop | `620163e` | CC BY 4.0 | By Damir Sokolovsky. |
| `diagram-design` | github.com/cathrynlavery/diagram-design | `1acb877` | MIT | |
| `book-to-skill` | github.com/virgiliojr94/book-to-skill | `79b3fa6` | MIT | `SKILL.md`, extractor package, `references/`, generated-skill scanner. |
| `humanizer` | github.com/blader/humanizer | `a32f244` | MIT | |
| `video-to-skill` | this repository | — | MIT | Modelled on `book-to-skill`; needs `ffmpeg`, optional `faster-whisper`. |

Licence texts: `.claude/third-party-licenses/`.
