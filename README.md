# agents-skills

Skills for Claude Code and the Claude apps.

## Own skills

| Skill | What it does |
|---|---|
| [`video-to-skill`](.claude/skills/video-to-skill/) | Turns one or more videos or clips into a reusable skill: extracts frames and speech, pulls out procedures, exact on-screen commands, rules and anti-patterns, and merges several sources into one skill. |

## Third-party skills (vendored, pinned, reviewed)

| Skill(s) | Upstream | Licence |
|---|---|---|
| `brainstorming`, `writing-plans`, `executing-plans`, `test-driven-development`, `systematic-debugging`, `verification-before-completion` and 8 more | [obra/superpowers](https://github.com/obra/superpowers) | MIT |
| `ui-ux-pro-max` | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | MIT |
| `unslop` | [heydamir/unslop](https://github.com/heydamir/unslop) | CC BY 4.0 |
| `diagram-design` | [cathrynlavery/diagram-design](https://github.com/cathrynlavery/diagram-design) | MIT |
| `book-to-skill` | [virgiliojr94/book-to-skill](https://github.com/virgiliojr94/book-to-skill) | MIT |
| `humanizer` | [blader/humanizer](https://github.com/blader/humanizer) | MIT |

Pinned commits and what was changed: [`.claude/THIRD_PARTY_SKILLS.md`](.claude/THIRD_PARTY_SKILLS.md).
Licence texts: [`.claude/third-party-licenses/`](.claude/third-party-licenses/).

## Use

- **In this repository:** open a Claude Code session here; everything in `.claude/skills/` loads automatically.
- **In another project:** copy a skill folder into that project's `.claude/skills/`, or into `~/.claude/skills/` for all projects.
- **Claude apps:** zip a skill folder and upload it under Settings → Capabilities → Skills.

## Licence

The root [LICENSE](LICENSE) (MIT) covers the skills written for this repository.
Third-party skills remain under their own licences, listed above.
