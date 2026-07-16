---
name: avoiding-ai-tells
description: >
  When the user is writing, editing, or reviewing prose that should not read as
  AI-generated — marketing copy, emails, posts, articles, docs — scan it against a
  research-backed catalog of AI writing tells and cut them. Use when the user says
  "make this sound human", "does this sound like AI", "remove the AI tells",
  "de-slop this", "humanize this draft", "clean up this copy", "edit this for voice",
  or hands over generated text to polish. Catches giveaway openers, filler verbs,
  buzzword adjectives, hedging cadences, chatbot residue, and structural monotony —
  each with a concrete replacement, not just a flag. Ships an optional linter to scan
  a draft mechanically and to validate the catalog itself.
triggers:
  - "make this sound human"
  - "does this sound like AI"
  - "remove the AI tells"
  - "de-slop this"
  - "humanize this draft"
  - "clean up this copy"
  - "edit this for voice"
  - "why does this read like ChatGPT wrote it"
version: 1.0.0
last_updated: 2026-07-16
license: MIT
---

# SKILL: Avoiding AI Tells

## Purpose

- **What this skill enables**: Consistently strip the patterns that make prose read as
  machine-generated, and replace each with something shorter and more specific — rather
  than relying on a general "make it sound human" instruction that varies run to run.
- **Success criteria**: The output contains none of the `banned` patterns in
  `references/ai-tells.md`; every `soft-flag` that survives does so because its meaning
  would collapse without it; and no valid craft (fragments, second person, specific
  numbers) was flattened in the process.
- **Non-goals**: This does not detect AI text with a probability score (it is not a
  classifier), and it does not rewrite for a specific brand voice — it removes generic
  tells. A brand's own style rules layer on top.

## Inputs & Preconditions

- **Required inputs**: A draft (pasted text or a file path) that the user wants cleaned.
- **Optional inputs**: A brand/style guide, if the user has one — its rules override
  this catalog wherever they conflict (a brand may ban or allow things this floor does
  not).
- **Preconditions**:
  - **Target Surface**: surface-agnostic. The Procedure's scan/replace pass is pure
    judgment and runs anywhere (Claude.ai, Claude Code, API). The optional linter
    (step 6) needs a shell with Python 3 and the files on disk — skip it on surfaces
    without Bash and rely on the reading pass, which is authoritative.
- **Assumptions**: The catalog reflects tells known as of its `last_updated`; AI writing
  drifts, so treat the list as a living floor, not a finished one.

## Tools & Permissions

- **Allowed tools**: Read (the draft and the catalog); Edit/Write (to return a cleaned
  draft); Bash (optional — to run the linter).
- **Disallowed tools**: None.
- **Required permissions**: File read on the draft and this skill's `references/` and
  `scripts/`; write only if returning a file rather than inline text.
- **Safety notes**: The `replacement` and `source` cells of the catalog are read
  verbatim into the model's context. The bundled linter's `lint` mode blocks URLs and
  instruction shapes from those cells for exactly this reason — keep it that way if you
  edit the catalog.

## Procedure

1. **Load the catalog.** Read `references/ai-tells.md` in full. The table is the
   authoritative list; the prose sections below it (the em-dash note, Preserve,
   Replacement rule, Self-check) carry the judgment calls.

2. **Scan the draft against the table, pattern by pattern.** For every `banned` row,
   cut or rewrite each occurrence using that row's `replacement`. For every `soft-flag`
   row, keep the word only if the sentence's meaning genuinely collapses without it and
   no better replacement exists — otherwise cut it too.

3. **Apply the Replacement rule.** When you remove a tell, the sentence should get
   *shorter and more specific*. If it got longer, you swapped one tell for another —
   re-cut. If the sentence's meaning collapses once the tell is gone, the sentence had
   no content: delete the whole sentence, not just the word.

4. **Check the structural rows.** Some tells are not phrases but shapes — metronomic
   sentence length, the Opening→Expansion→Contrast→Resolution arc repeated every
   paragraph, paragraphs of equal length, the framing sandwich. These need a human/model
   read, not a find-and-replace. Vary sentence length deliberately; let one paragraph
   break shape.

5. **Respect the Preserve list.** Do not "correct" valid craft into blandness: sentence
   fragments for emphasis, single-sentence paragraphs, direct second person ("you"),
   and specific unhedged numbers are features, not tells. Over-correction is its own
   failure mode.

6. **(Optional, deterministic) Run the linter.** On a surface with a shell:
   - Scan a draft mechanically for the literal-phrase tells:
     ```
     python3 scripts/ai_tells_guard.py scan path/to/draft.md
     ```
     It prints each hit with line number, severity, and replacement; exits `1` if any
     `banned` tell is present (so it works as a CI gate), `0` otherwise. It is
     best-effort — it matches only the quoted literal phrases and reports how many
     structural/descriptive rows it could not check mechanically.
   - Validate the catalog itself after editing it:
     ```
     python3 scripts/ai_tells_guard.py lint
     ```

7. **Return the cleaned draft**, and briefly note the highest-value changes (the two or
   three tells that were doing the most damage), so the user learns the pattern.

## Gotchas

- **The scanner is a helper, not the authority.** `scan` catches literal phrases only.
  It will miss an inflection the catalog doesn't list explicitly (it lists `ensure` /
  `ensures` / `ensuring` as separate entries, but for `empower` only the base form —
  so `empowers` slips past). The reading pass in steps 2–5 is what actually cleans the
  draft; the linter just backstops it.
- **`soft-flag` is not `banned`.** Words like `seamless`, `synergy`, and `scalable`
  show up in ordinary human writing too and are no longer reliable standalone signals.
  Cut them when they're empty; keep them when they carry real meaning. Treating every
  soft-flag as a hard cut produces stilted prose.
- **Em-dashes are overclaimed.** Humans use them constantly. Do not strip them on
  sight — see the em-dash note in the catalog. What reads as AI is the *overuse* as a
  default connector, not the mark.
- **A brand guide wins.** If the user has their own style rules, those override this
  catalog. This is a generic floor, not a house style.
- **Deleting a tell can leave a hollow sentence.** If a sentence is *only* tells
  ("We're excited to leverage our world-class, cutting-edge solution"), the fix is to
  delete it and ask the user what it was trying to say — not to word-swap it into a
  slightly less obvious version of nothing.

## Edge Cases & Failure Modes

- **No draft provided**: Ask for the text or a file path. Do not invent a draft to clean.
- **Draft is already clean**: Say so plainly. Report zero banned tells rather than
  manufacturing changes to look busy.
- **User wants a probability/score ("is this AI?")**: Clarify that this skill removes
  tells, it doesn't classify. Offer to run `scan` for a count of literal tells present,
  but note that a low count is not proof a human wrote it.
- **Catalog edited and the linter fails**: Read the error. A `7 cells` failure means a
  stray or missing pipe; an `unknown severity/category` means a typo against the enum;
  a `replacement`/`source` block means a URL or instruction shape leaked into a cell —
  rewrite it as plain editorial text.
- **Draft in a language other than English**: The catalog is English-specific. Flag
  that the literal phrases won't transfer; the structural principles (vary cadence,
  avoid the arc) still apply.

## Examples

**Input** — user pastes:
> "In today's fast-paced world, we leverage cutting-edge tools to unlock value. Our
> seamless platform empowers teams. It's not just software, it's a paradigm shift."

**Steps**
- Load `references/ai-tells.md` (step 1).
- Scan (step 2): `In today's fast-paced world` (opener, banned), `leverage` (banned),
  `cutting-edge` (banned), `unlock` (banned), `seamless` (soft-flag), `empowers`
  (banned base form `empower`), `It's not just X, it's Y` (cadence, banned),
  `paradigm shift` (banned).
- Apply replacements + the Replacement rule (steps 2–3): most of the sentence is tells,
  so cut to substance and ask what the tool actually does.
- Optionally confirm with `python3 scripts/ai_tells_guard.py scan draft.md` (step 6).

**Expected Output** — a rewrite anchored in specifics, e.g.:
> "Our scheduling tool cuts rep onboarding from three weeks to four days." (plus a note
> that the original was ~90% filler and needs the real numbers from the user).

## Verification

- Run `python3 scripts/ai_tells_guard.py scan <cleaned-draft>` — it should report
  `0 banned`. Any remaining soft-flags should each survive on purpose.
- Run `python3 scripts/ai_tells_guard.py lint` — exits `0` (catalog well-formed).
- Run `python3 scripts/test_ai_tells_guard.py` — prints `all tests passed`.
- Read the cleaned draft against the Preserve list: confirm no fragment, second-person
  address, or specific number was flattened in the cleanup.

## Deliverables

- **Files created/modified**: The cleaned draft (returned inline, or written back to
  the user's file if they gave a path). This skill's own files are not modified during
  a normal run.
- **Output format**: Same format as the input draft (Markdown, plain text, etc.).
- **What to return to the user**: The cleaned draft plus a short note on the two or
  three highest-value tells removed.

## Quality Bar Checklist

- [ ] Catalog loaded before scanning (step 1)
- [ ] Every `banned` tell in the draft removed or rewritten via its replacement
- [ ] Surviving `soft-flag`s each justified (meaning would collapse without them)
- [ ] Replacement rule applied — sentences got shorter/more specific, not longer
- [ ] Structural rows considered, not just phrase rows
- [ ] Preserve list respected — no valid craft flattened
- [ ] `scan` reports `0 banned` on the cleaned draft (where a shell is available)
- [ ] User told the highest-value changes, not just handed a diff

## Related Skills

**Standalone:** This skill has no upstream or downstream skill dependencies.
