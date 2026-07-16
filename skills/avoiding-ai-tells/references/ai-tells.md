---
version: 1.0.0
last_updated: 2026-07-16
---

# AI-Tells Catalog

A research-backed catalog of the patterns that make writing read as AI-generated,
each with a severity and a concrete replacement. Scan a draft against this table and
cut what you find.

Two severities:

- **`banned`** — cut on sight. These are strong, reliable tells; the sentence is
  almost always better without them.
- **`soft-flag`** — allowed only when the meaning genuinely collapses without the
  word and no better replacement exists. Flag, judge, keep sparingly.

When the word carries real content, keep it — this is a catalog of *empty* usages
(metaphorical "leverage," decorative "seamless"), not a ban on the literal senses
("a physical harness," "a robust-to-failure design"). Every replacement cell names
what to do instead.

---

## Banned + soft-flag table

The table is the canonical, scannable list. Each row is one pattern with category,
severity, replacement, and source. The bundled linter (`scripts/ai_tells_guard.py`)
parses this table directly: the header line and 7-column shape are a frozen parse
contract, so keep the column structure intact if you edit it.

Categories: `opener`, `filler-verb`, `buzzword-adjective`, `intensifier-adverb`,
`cadence-pattern`, `closer`, `structural-pattern`, `punctuation`.

| pattern | category | severity | replacement | source | added | last_verified |
|---|---|---|---|---|---|---|
| "I hope this email finds you well" | opener | banned | open with the actual question or context | craft-floor | 2026-05-30 | 2026-07-01 |
| "I hope you're doing well" | opener | banned | open with the actual question or context | craft-floor | 2026-05-30 | 2026-06-10 |
| "I came across your profile" | opener | banned | cut; get to the point | craft-floor | 2026-05-30 | 2026-06-10 |
| "In today's fast-paced world / digital landscape / business environment" | opener | banned | name the specific scenario | craft-floor | 2026-05-30 | 2026-07-01 |
| "In the ever-evolving landscape of [anything]" | opener | banned | name the specific scenario | craft-floor | 2026-05-30 | 2026-06-10 |
| "We're excited to announce [X]" | opener | banned | replace with the substance of X | craft-floor | 2026-05-30 | 2026-07-01 |
| "Certainly!" | opener | banned | scrub — LLM chat-output shape pasted into produced content | OpenAI sycophancy blog Apr 2025 | 2026-06-10 | 2026-06-10 |
| "What a thoughtful question!" | opener | banned | scrub — LLM chat-output shape | OpenAI sycophancy blog Apr 2025 | 2026-06-10 | 2026-06-10 |
| "You're absolutely right" | opener | banned | scrub — LLM chat-output shape | OpenAI sycophancy blog Apr 2025 | 2026-06-10 | 2026-06-10 |
| "That's a brilliant observation" | opener | banned | scrub — LLM chat-output shape | OpenAI sycophancy blog Apr 2025 | 2026-06-10 | 2026-06-10 |
| "What do you think?" closing a comment | opener | banned | scrub — LLM chat-output shape | OpenAI sycophancy blog Apr 2025 | 2026-06-10 | 2026-06-10 |
| Adverbial sentence openers: "Notably," "Importantly," "Interestingly," "Remarkably" starting a sentence or paragraph | opener | banned | scrub — chat residue; open with the actual claim | HumanizeMyAI 2026 | 2026-06-11 | 2026-06-11 |
| "leverage" | filler-verb | banned | use, deploy, apply, route through | craft-floor | 2026-05-30 | 2026-07-01 |
| "utilize" | filler-verb | banned | use | craft-floor | 2026-05-30 | 2026-07-01 |
| "facilitate" | filler-verb | banned | name what gets done | craft-floor | 2026-05-30 | 2026-07-01 |
| "drive" (metaphorical of intangibles, e.g., "drive engagement") | filler-verb | banned | name the action; concrete uses fine | craft-floor | 2026-05-30 | 2026-06-10 |
| "unlock" | filler-verb | banned | open, enable, expose; only if you can name the lock | craft-floor | 2026-05-30 | 2026-07-01 |
| "elevate" (metaphorical) | filler-verb | banned | name the actual change | craft-floor | 2026-05-30 | 2026-06-10 |
| "delve" / "delve into" | filler-verb | banned | examine, walk through, work through | craft-floor | 2026-05-30 | 2026-06-10 |
| "navigate" (metaphorical of decisions) | filler-verb | banned | name the decision; concrete navigation fine | craft-floor | 2026-05-30 | 2026-06-10 |
| "harness" | filler-verb | banned | use, channel; only if literal harnessing | craft-floor | 2026-05-30 | 2026-06-10 |
| "empower" | filler-verb | banned | name the action it gestures at | craft-floor | 2026-05-30 | 2026-06-10 |
| "streamline" | filler-verb | banned | name what gets faster, by what method | craft-floor | 2026-05-30 | 2026-06-10 |
| "ensure" / "ensures" / "ensuring" | filler-verb | banned | name the actual guarantee, or cut | WriteHuman 2026 80k-pair study | 2026-06-10 | 2026-06-10 |
| "highlights" (meaning "mentions" / "shows") | filler-verb | banned | use the verb that names the action | WriteHuman 2026 | 2026-06-10 | 2026-06-10 |
| "supports" (metaphorical of evidence, e.g., "supports the claim") | filler-verb | banned | name the proof | WriteHuman 2026 | 2026-06-10 | 2026-06-10 |
| "reflects" (meaning "shows" without a literal mirror) | filler-verb | banned | cut | WriteHuman 2026 | 2026-06-10 | 2026-06-10 |
| "at its core" | filler-verb | banned | cut or name the actual core; if you can't, the sentence has no content | Bloomberry 2026 (Very High frequency, all models) | 2026-06-11 | 2026-06-11 |
| "underscore" / "underscores" / "underscoring" | filler-verb | banned | name what the evidence shows | Kobak/PubMed academic-writing study 2026 | 2026-06-11 | 2026-06-11 |
| "showcase" / "showcasing" | filler-verb | banned | name what the thing demonstrates or shows | Kobak/PubMed academic-writing study 2026 | 2026-06-11 | 2026-06-11 |
| "foster" / "fostering" | filler-verb | banned | name the mechanism: builds, grows, trains, creates | Bloomberry 2026; Vollmer field guide 2026 | 2026-06-11 | 2026-06-11 |
| "needless to say" | filler-verb | banned | cut the opener and state the claim directly | Bloomberry 2026 (High frequency, all models) | 2026-06-11 | 2026-06-11 |
| "synergy" / "synergies" / "synergistic" | buzzword-adjective | soft-flag | cut | craft-floor; cross-check 2026 (both human + AI corporate writing — not a standalone signal) | 2026-05-30 | 2026-07-01 |
| "best-in-class" | buzzword-adjective | soft-flag | name what makes it best | craft-floor; cross-check 2026 (both human + AI writing — not a standalone signal) | 2026-05-30 | 2026-07-01 |
| "world-class" | buzzword-adjective | banned | name what makes it world-class | craft-floor | 2026-05-30 | 2026-06-10 |
| "cutting-edge" | buzzword-adjective | banned | name what's new | craft-floor | 2026-05-30 | 2026-06-10 |
| "robust" (meaning "good") | buzzword-adjective | banned | cut; OK in "robust to <specific failure>" | craft-floor | 2026-05-30 | 2026-06-10 |
| "seamless" / "seamlessly" | buzzword-adjective | soft-flag | name what doesn't break; be honest about tradeoffs | craft-floor; cross-check 2026 (diluted SaaS word — not a standalone signal) | 2026-05-30 | 2026-07-01 |
| "comprehensive" | buzzword-adjective | banned | name what's covered ("covers <list>") | craft-floor | 2026-05-30 | 2026-06-10 |
| "holistic" | buzzword-adjective | banned | name the components | craft-floor | 2026-05-30 | 2026-06-10 |
| "innovative" | buzzword-adjective | banned | name the innovation | craft-floor | 2026-05-30 | 2026-07-01 |
| "powerful" | buzzword-adjective | banned | name the capability | craft-floor | 2026-05-30 | 2026-06-10 |
| "tapestry" (metaphorical, e.g., "a tapestry of ideas/challenges") | buzzword-adjective | banned | name the components | Bloomberry 2026; Vollmer field guide 2026 | 2026-06-11 | 2026-06-11 |
| "pivotal" | buzzword-adjective | banned | name why it matters | Kobak/PubMed academic-writing study 2026; Bloomberry 2026 | 2026-06-11 | 2026-06-11 |
| "nuanced" / "nuances" | buzzword-adjective | banned | name the variation; if you can't, cut | Bloomberry 2026 (high frequency, all models) | 2026-06-11 | 2026-06-11 |
| "paradigm shift" / "paradigm-shifting" | buzzword-adjective | banned | name the specific change | Bloomberry 2026 (High frequency, all models) | 2026-06-11 | 2026-06-11 |
| "quiet" / "quietly" (vague poetic intensifier, e.g., "quiet confidence," "quietly growing") | buzzword-adjective | banned | name the actual quality or action; cut the adjective | Bloomberry 2026 (June update) | 2026-07-01 | 2026-07-01 |
| "signal" (abstract noun, e.g., "send the signal," "a strong signal that") | buzzword-adjective | banned | name the actual evidence or action | Bloomberry 2026 (June update); Forbes/Jodie Cook May 2026 | 2026-07-01 | 2026-07-01 |
| "testament to" / "a testament to" | buzzword-adjective | banned | name what the evidence actually shows | ZeroGPT Plus 2026 | 2026-07-01 | 2026-07-01 |
| "significantly" | intensifier-adverb | banned | name the magnitude | WriteHuman 2026 | 2026-06-10 | 2026-06-10 |
| "effectively" | intensifier-adverb | banned | name the mechanism | WriteHuman 2026 | 2026-06-10 | 2026-06-10 |
| "increasingly" | intensifier-adverb | banned | name the rate or time window | WriteHuman 2026 | 2026-06-10 | 2026-06-10 |
| "directly" | intensifier-adverb | banned | name what "direct" means here | WriteHuman 2026 | 2026-06-10 | 2026-06-10 |
| "It's not just X — it's Y" / "It's not X, it's Y" | cadence-pattern | banned | re-architect around the actual claim; negation parallelism is 6.3× over-represented vs human writing | Antislop paper; craft-floor | 2026-05-30 | 2026-07-01 |
| "X isn't just about Y. It's about Z." | cadence-pattern | banned | re-architect around the actual claim | craft-floor | 2026-05-30 | 2026-06-10 |
| "More than [a/an] X, it's a Y" | cadence-pattern | banned | re-architect around the actual claim | craft-floor | 2026-05-30 | 2026-06-10 |
| "Whether you're A, B, or C..." opener | cadence-pattern | banned | cut; almost always fluff | craft-floor | 2026-05-30 | 2026-06-10 |
| Tricolons of three vague nouns ("vision, purpose, drive") with no concrete content | cadence-pattern | banned | cut or name concretely | craft-floor | 2026-05-30 | 2026-06-10 |
| "plays a [crucial/critical/important] role in shaping" | cadence-pattern | banned | cut the clause; statistically the most formulaic AI trigram | WriteHuman 2026 | 2026-06-10 | 2026-06-10 |
| "rather than" hedging a comparison instead of making one | cadence-pattern | banned | pick the side or delete; 17k vs 6.8k occurrences in humanized pairs | WriteHuman 2026 | 2026-06-10 | 2026-06-10 |
| "when it comes to" (transition filler) | cadence-pattern | banned | cut; state the subject directly | Bloomberry 2026 (Very High frequency, all models) | 2026-06-11 | 2026-06-11 |
| "moreover" / "furthermore" / "additionally" as a paragraph or sentence opener | cadence-pattern | banned | cut; use a period and start the next thought, or "and" if you must connect | Bloomberry 2026; HumanizeMyAI 2026 | 2026-06-11 | 2026-06-11 |
| "built different" / "built for the bold" / "built to last" | cadence-pattern | banned | name the actual differentiator; cut the stock positioning line | Forbes/Jodie Cook May 2026; Bloomberry 2026 (June update) | 2026-07-01 | 2026-07-01 |
| "At the end of the day" | closer | banned | cut | craft-floor | 2026-05-30 | 2026-07-01 |
| "When all is said and done" | closer | banned | cut | craft-floor | 2026-05-30 | 2026-06-10 |
| "The bottom line is" (filler) | closer | banned | cut; fine if a literal bottom line | craft-floor | 2026-05-30 | 2026-07-01 |
| "ultimately" (resolution filler) | closer | banned | cut; state the conclusion directly | Bloomberry 2026 (all models, resolution filler) | 2026-06-11 | 2026-06-11 |
| "the key takeaway is" / "a key takeaway is" | closer | banned | state the point directly; cut the framing | Grammarly AI research 2025; HumanizeMyAI 2026 | 2026-06-11 | 2026-06-11 |
| Chatbot residue closers: "I hope this helps," "Let me know if you need anything else," "As an AI language model" | closer | banned | scrub entirely — chat-output shape that must not appear in produced content | HumanizeMyAI 2026 | 2026-06-11 | 2026-06-11 |
| Metronomic cadence (14–22 word sentences with low variance across a paragraph) | structural-pattern | banned | vary deliberately — short bursts after long sentences, fragments after dependent clauses | Vollmer field guide 2026 / GPTZero | 2026-06-10 | 2026-06-10 |
| AI Sentence DNA arc (Opening → Expansion → Contrast → Resolution repeated across paragraphs) | structural-pattern | banned | break one paragraph's shape; humans digress, abandon a thread, double back | Bloomberry 2026 | 2026-06-10 | 2026-06-10 |
| Structural symmetry (paragraphs of equal word or sentence count) | structural-pattern | banned | introduce asymmetry; humans don't write metronomically | WriteHuman 2026 | 2026-06-10 | 2026-06-10 |
| Copula avoidance ("serves as", "stands as", "marks", "boasts", "maintains") | structural-pattern | banned | use plain "is" / "has" / "shows" | Kobak/PubMed academic-writing study 2026 | 2026-06-10 | 2026-06-10 |
| Framing sandwich: restating the question in the opening sentence, then restating the conclusion in the final sentence | structural-pattern | banned | cut both bookends; start with the substance, end before the summary | HumanizeMyAI 2026 | 2026-06-11 | 2026-06-11 |
| em-dash (—) overused as the default connector | punctuation | soft-flag | prefer a period, comma, or colon; keep only where it genuinely aids the sentence — humans use em-dashes too | widely-cited AI tell; overclaimed | 2026-06-10 | 2026-07-16 |
| "tailored" / "bespoke" | buzzword-adjective | soft-flag | name the variable that adapts | craft-floor | 2026-05-30 | 2026-06-10 |
| "scalable" | buzzword-adjective | soft-flag | name the scale axis ("from 5 to 500 reps") | craft-floor | 2026-05-30 | 2026-07-01 |
| "data-driven" | buzzword-adjective | soft-flag | name the data | craft-floor | 2026-05-30 | 2026-06-10 |
| "actionable insights" | buzzword-adjective | soft-flag | name the action | craft-floor | 2026-05-30 | 2026-06-10 |
| "the work" (vague self-referential noun phrase, e.g., "trust the work," "do the work," with no named referent) | buzzword-adjective | soft-flag | name the actual task or deliverable | Bloomberry 2026 (June update) | 2026-07-01 | 2026-07-01 |

---

## The em-dash, specifically

Em-dashes are a real but overclaimed AI tell. Real humans use them all the time, so a
blanket ban misfires — it strips a legitimate punctuation mark and can flatten good
prose. Treat it as **flag-and-judge, not a hard cut**: where a period, comma, or colon
reads just as well, prefer those; where the em-dash genuinely aids clarity or rhythm,
keep it. What actually reads as AI is the *overuse* — the em-dash as the default
connector in every other sentence — not the mark itself.

## Preserve (valid craft, not AI tells)

Sentence fragments. Used for emphasis. After a complete sentence. They're a craft
device, not a glitch.

Single-sentence paragraphs in posts and emails. Channel-appropriate rhythm.

Direct second-person address ("you," "your"). Reader-focused, not an AI tell.

Specific numbers without softening qualifiers ("23% lift" not "approximately 23%").
Specificity beats softening.

---

## Replacement rule

When you delete an AI tell, the sentence usually gets shorter and more specific. If it
gets longer, you've replaced one tell with another. Re-cut.

If the sentence's meaning collapses when the AI tell is removed, the sentence had no
content; delete the whole sentence, not just the word.

---

## Self-check

Before submitting, scan the draft once for the patterns in the table above. The most
common slips:

1. "Leverage" survives the first pass because it sounds professional. It isn't. Cut.
2. "Seamless" / "seamlessly" — good writing is honest about tradeoffs; nothing is
   seamless.
3. "It's not just X, it's Y" — re-architect the sentence around the actual claim. The
   Antislop study measured negation parallelism at 6.3× over-represented in AI output
   versus human writing; this is the single highest-signal phrase-level tell.
4. Cadence-recycled openers ("In today's...") — replace with a specific scenario.
5. Sycophantic conversation residue ("Certainly!", "What a thoughtful question!") —
   strip before publishing; these are chat-output shape that landed in the draft via
   paste.
