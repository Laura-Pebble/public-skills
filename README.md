# Agent Skills

A small collection of [Agent Skills](https://agentskills.io) — executable playbooks that teach AI agents how to perform specific workflows consistently.

These skills are designed to work with [Claude](https://claude.ai), [Claude Code](https://claude.com/claude-code), and any other agent platform that supports the open Agent Skills specification.

## What's an Agent Skill?

A SKILL.md is a structured markdown file with YAML frontmatter that an AI agent reads to learn how to do a specific task — what triggers it, what inputs it needs, what steps to follow, and what to return. Skills are self-contained, shareable, and version-controlled.

Learn more at <https://agentskills.io/specification.md>.

## Skill Inventory

| Skill | What it does |
|---|---|
| [`ai-research-verification`](skills/ai-research-verification/) | Six-check verification protocol for AI-generated research — catches fabricated sources, distorted claims, and single-thread findings before they land in a downstream document. |
| [`avoiding-ai-tells`](skills/avoiding-ai-tells/) | Strips the patterns that make prose read as AI-generated — giveaway openers, filler verbs, buzzword adjectives, hedging cadences, chatbot residue — against a research-backed catalog of ~80 tells, each with a concrete replacement. Ships an optional linter to scan a draft or validate the catalog. |

More skills will land here over time.

## How to Use a Skill

### Claude Code

Clone this repo. Skills in `skills/` are automatically discoverable by Claude Code sessions running in that directory:

```bash
git clone https://github.com/<owner>/<repo>.git
cd <repo>
claude
```

### Claude.ai Projects

In a Claude.ai project: **Project knowledge → Add from GitHub → select this repo → select the skill folder(s) you want**. After any update to a skill, click the **Sync** icon to refresh.

### Other agents

The SKILL.md files conform to the open Agent Skills specification, so any agent platform that supports the spec can consume them directly. For platforms that don't, the SKILL.md is plain markdown — you can paste the procedure section into a system prompt.

## Contributing

Issues and pull requests welcome. If you're proposing a new skill, please:

1. Read <https://agentskills.io/specification.md> for the baseline structure.
2. Make sure your skill is self-contained — no references to private infrastructure, internal artifact paths, or org-specific roles.
3. Include at least one worked example and a Verification section.

## License

[MIT](LICENSE).
