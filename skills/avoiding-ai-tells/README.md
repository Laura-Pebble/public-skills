# avoiding-ai-tells

A portable [Agent Skill](https://agentskills.io) that strips the patterns which make
prose read as AI-generated — giveaway openers, filler verbs, buzzword adjectives,
hedging cadences, chatbot residue, and structural monotony — and replaces each with
something shorter and more specific.

It's a **catalog + a method + an optional linter**, not an AI-detector. It doesn't score
text; it removes the tells and tells you what to write instead.

## What's in here

```
avoiding-ai-tells/
├── SKILL.md                     # the skill: when it triggers + the clean-up procedure
├── references/
│   └── ai-tells.md              # the catalog: ~80 tells, each with severity + replacement
└── scripts/
    ├── ai_tells_guard.py        # optional linter: validate the catalog, scan a draft
    └── test_ai_tells_guard.py   # tests for the linter (no dependencies)
```

## Install

Drop the whole `avoiding-ai-tells/` folder into your agent's skills directory — for
Claude Code that's `.claude/skills/avoiding-ai-tells/`. The agent reads `SKILL.md`'s
frontmatter at startup and triggers it when you ask to de-slop, humanize, or edit a
draft for voice.

## Use it two ways

**1. As a skill (judgment pass — authoritative).** Hand the agent a draft and ask it to
"remove the AI tells" or "make this sound human." It loads the catalog and rewrites
against it, respecting the soft-flag / preserve rules so it doesn't flatten good writing.

**2. As a linter (mechanical backstop).** With Python 3:

```bash
# scan a draft — exits 1 if any `banned` tell is present (usable as a CI gate)
python3 scripts/ai_tells_guard.py scan path/to/draft.md

# validate the catalog after you edit it
python3 scripts/ai_tells_guard.py lint

# run the tests
python3 scripts/test_ai_tells_guard.py
```

The scanner is best-effort: it matches the literal quoted phrases in the catalog and
reports how many structural/descriptive patterns (sentence-cadence, paragraph shape) it
can't check mechanically. The judgment pass is what actually cleans a draft; the linter
just backstops it and guards the catalog's format.

## The catalog

`references/ai-tells.md` is a 7-column Markdown table — `pattern | category | severity |
replacement | source | added | last_verified`. Two severities:

- **`banned`** — cut on sight; strong, reliable tells.
- **`soft-flag`** — allowed only when the meaning collapses without the word (e.g.
  `seamless`, `synergy` — these show up in human writing too).

Edit it freely to fit your own voice; run `ai_tells_guard.py lint` afterward to confirm
it still parses. The linter blocks URLs and instruction-shaped text from the
`replacement`/`source` cells on purpose — an agent reads those cells verbatim, so they
must stay inert editorial text.

## License

[MIT](../../LICENSE), matching the repository.

## Note on sources

The `source` column cites AI-writing-detection research and field guides by name.
`craft-floor` marks general editorial-craft entries with no single external source.
Treat the catalog as a living floor: AI writing drifts, so the tells do too.
