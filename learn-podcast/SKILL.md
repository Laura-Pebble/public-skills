---
name: learn-podcast
description: Build a personalized teaching podcast for any topic the user wants to learn. Use when the user wants to set up a recurring audio learning feed — "make me a podcast that teaches me X", "I want a daily/weekly briefing on Y", "build me a tutor for Z". Interviews the user about their topic, level, goals, and trusted sources, then scaffolds a source-first audio pipeline (RSS / LinkedIn / podcast-guest sources → LLM-curated lesson → grounded spoken script → claim-verified rewrite → text-to-speech MP3 → optional podcast feed) into their repo with a scheduled GitHub Actions workflow.
---

# Learn Podcast

This skill builds a personalized teaching podcast — audio only, no video — for whatever the user wants to learn. The user supplies the topic, their starting point, and 5-15 sources they trust. The skill scaffolds a **source-first** pipeline: on each scheduled run it pulls fresh content from those sources, asks the LLM what's actually teachable from this week's haul, writes a grounded spoken-word script, verifies every claim against the sources (rewriting any that drift), renders to MP3, and (optionally) publishes to an Apple/Spotify-compatible podcast feed.

The user is *not* expected to know every option. Walk them through the interview, suggest defaults, let them say "you pick."

## When to invoke

Trigger phrases:
- "make me a podcast that teaches me ___"
- "I want a recurring learning briefing on ___"
- "build me an AI tutor for ___"
- "set up a personalized learning feed"
- the user explicitly asks for `/learn-podcast`

Do **not** invoke for one-off summarization, generic "research X" requests, or anything that isn't a *recurring* audio learning artifact. For one-off deep research, use `deep-research`.

## What this skill produces

When the interview finishes, the skill writes these files into the user's repo:

```
learn_podcast/
├── config.yaml                  # the interview output, machine-readable
├── curriculum.yaml              # 12 lessons (only if user picked Structured)
├── pending_sources.yaml         # sources not yet launched (auto-promote on detection)
├── requirements.txt
└── pipeline/
    ├── main.py                  # source-first orchestrator
    ├── discover.py              # RSS pull + full-text + filters
    ├── filters.py               # per-source author/keyword/min_words gates
    ├── resolvers.py             # rss.app / Apify LinkedIn / Podchaser-person
    ├── curate.py                # LLM ranks items against the lesson
    ├── script.py                # source-first lesson proposal + grounded script
    ├── verify.py                # claim-grounding gate + paragraph rewrite
    ├── tts.py                   # Edge TTS (free, no API key)
    ├── feed.py                  # builds podcast RSS feed
    ├── notify.py                # ntfy push + optional S3 upload
    ├── source_quality.py        # deterministic + LLM judge gates
    ├── pending.py               # weekly check for pending podcast launches
    ├── expand.py                # monthly Exa discovery + approval flow
    └── llm.py                   # Anthropic / Gemini / OpenAI provider abstraction
```

The skill copies these from `starter/` next to this SKILL.md, substituting interview answers into the templates marked `{{...}}`. See `starter/SUBSTITUTIONS.md` for the full key list.

## The interview — three phases

Run the interview using the `AskUserQuestion` tool, batching related questions. **Phases 1 and 2 are required.** Phase 3 collects delivery and infra preferences with one-click defaults.

Tell the user up front: "I'll ask ~12 questions in 3 phases. Phase 1 is what you want to learn, phase 2 is your sources, phase 3 is format and delivery. Total time: 4-6 minutes."

### Phase 1 — What you want to learn

Ask all four together:

1. **Topic in one sentence.** Free-form. Examples:
   - "AI for B2B marketing strategy"
   - "FDA regulatory pathways for medical devices"
   - "Rust systems programming for someone who knows Python"

2. **Your starting point.** Free-form, 2-3 sentences. Ask what they already know so the tutor skips it.

3. **Why you're learning it.** Free-form. How they'll apply it.

4. **Curriculum shape.** Choose:
   - **Structured** — a 12-lesson foundational curriculum that builds in order, then organic episodes. Each planned lesson is gated: if this week's sources don't cover it (≥2 sources), the lesson is **postponed** to next run and an organic episode runs instead. So a structured curriculum never forces fabrication.
   - **Organic** — every episode is whatever's freshest and most teachable in their sources this week. Best when they already have the foundation.

If they choose Structured, **after the interview** generate a proposed 12-lesson curriculum from their topic + starting point + goal, show it numbered, and ask "approve, edit, or regenerate?"

### Phase 2 — Sources (this is the moat)

5. **Your trusted sources** (5-15). Free-form. Tell them:
   > Drop whatever you've got — blog URLs, newsletter names, podcast names, expert handles on X/LinkedIn, YouTube channels, people whose podcast guest appearances are worth tracking. I'll resolve them. If you can't think of 5, say so and I'll suggest some for your topic.

   For each entry the user gives, the skill resolves a strategy:
   - **Plain URL with RSS** → `kind: blog`, `resolver: rss`. WebFetch the homepage, find `<link rel="alternate" type="application/rss+xml">` or try `/feed`, `/rss`, `/atom.xml`, `/feed.xml`, `/index.xml`.
   - **Substack name** → `https://<name>.substack.com/feed`, `resolver: rss`.
   - **WordPress author archive** → `<site>/author/<slug>/feed/`, `resolver: rss`, `filter: {author: "<name>"}`.
   - **HubSpot blog author** → `<site>/blog/author/<slug>/rss.xml`. If 403s bots: `resolver: rss_app`, user pastes an rss.app feed URL.
   - **Webflow / JS-rendered site** → `resolver: rss_app`. Tell the user to create a feed at rss.app (free for ~3 feeds, paid above) and paste the rss.app URL.
   - **YouTube channel** → `https://www.youtube.com/feeds/videos.xml?channel_id=<UC...>`, `kind: youtube`, `resolver: rss`.
   - **LinkedIn personal profile** → `kind: linkedin`, `resolver: apify_linkedin`. The user needs an `APIFY_TOKEN` (~$3-4 per 1k posts, no cookies needed, legally cleaner than scraping). Recommend weekly cadence, not daily.
   - **Person who appears as podcast guest** → `kind: person`, `resolver: podchaser_person`. Requires `PODCHASER_TOKEN` (free 25k pts/month). Tracks every podcast they guest on.
   - **Podcast by name** → `WebSearch` "<name> RSS feed", confirm one Apple Podcasts link, find the source RSS.

   For multi-author blogs, **always offer an author or keyword filter** so the user can narrow to one person's posts.

   Report each resolution back: "Resolved 11/13. Couldn't find: [X, Y]. Want me to drop them or look harder?" Never invent sources — every suggestion verified via WebFetch.

5b. **Filters per source.** When a user names a multi-author site or wants AI-only content from a generalist source, ask if they want a filter:
   - `author: "Name"` — only entries where the author field matches
   - `keyword_any: ["AI", "LLM"]` — at least one keyword in title or body
   - `keyword_all: ["agent", "tool"]` — every keyword present
   - `min_words: 300` — drop short marketing posts

5c. **Future-feed watching.** Ask:
   > Any sources you want to watch for that don't exist yet? (e.g. "Mike is launching a podcast next month.")

   Each becomes a `pending_sources.yaml` entry with name + author + earliest_launch date. The weekly `pending.py` job checks iTunes Search + PodcastIndex and auto-promotes on a fuzzy-match ≥85.

6. **Discovery on/off.** Choose:
   - **Hand-picked only** — pipeline reads only the sources from Q5.
   - **Hand-picked + monthly Exa discovery** — pipeline runs `expand.py` monthly to surface 3-10 candidates similar to the existing sources. Requires `EXA_API_KEY` (1k free/mo). Candidates land in `source_candidates.yaml` with `approved: false`; user flips to `true` to promote. Costs ~$0.01/month at typical volume.

### Phase 3 — Format & delivery

Ask all five together with defaults:

7. **Episode length.** 10 / 20 / 30 / 45 min. Default 20.

8. **Cadence.** Daily / Mon-Wed-Fri / Weekly. Default Mon-Wed-Fri.

9. **Narrator voice.** Edge TTS — list a few:
   - `en-US-AriaNeural` (female, conversational, US) — default
   - `en-US-GuyNeural` (male, conversational, US)
   - `en-US-JennyNeural` (female, warm, US)
   - `en-GB-RyanNeural` (male, UK)
   - `en-AU-NatashaNeural` (female, AU)
   - "I'll pick"

10. **Delivery channels.** Multi-select:
    - **Local MP3** — always on.
    - **Push notification** via [ntfy.sh](https://ntfy.sh) — free, no account. User picks a topic.
    - **Public podcast feed** — generates `feed.xml`, uploads MP3 + feed to S3-compatible bucket. Needs `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_PUBLIC_URL`.

11. **LLM provider.** Pick one:
    - **Anthropic Claude** (recommended). Needs `ANTHROPIC_API_KEY`.
    - **Google Gemini** (generous free tier). Needs `GEMINI_API_KEY`.
    - **OpenAI**. Needs `OPENAI_API_KEY`.

11b. **Strict verification.** Ask:
   > Should the pipeline refuse to ship an episode if the grounding check finds too many unsupported claims, or always ship after rewriting drift paragraphs?

   Default: lenient (always ship after rewriting). Strict mode useful for high-stakes domains (regulatory, medical, security).

## After the interview — assembly

Once you have all answers:

1. **Read** every file in `starter/`.
2. **Substitute** the `{{KEY}}` markers using the interview answers per `starter/SUBSTITUTIONS.md`.
3. **Write** the rendered files into the user's repo under `learn_podcast/`.
4. **For Structured curriculum**: also write `learn_podcast/curriculum.yaml` with the 12 lessons.
5. **Resolve sources**: write the deduplicated, resolved feed list into `config.yaml` under `sources:` with filters and resolvers attached. Drop unresolved entries with a comment.
6. **Write** `pending_sources.yaml` if the user answered 5c.
7. Print the final checklist:
   - Env vars / GitHub secrets to set (only the ones their choices require).
   - The `pip install -r learn_podcast/requirements.txt` command.
   - Provider SDK install (only the matching one).
   - Optional extras: `apify-client` (LinkedIn), `boto3` (S3), `exa-py + openai + numpy` (Exa discovery), `rapidfuzz` (pending watcher).
   - Test one episode locally: `python -m learn_podcast.pipeline.main`.
   - GitHub Actions workflow is **disabled by default** — uncomment `schedule:` after a local test passes.

## Hard rules

- **Audio only.** Never write any video, slides, or image-generation code. Point to `src/teacher/` of the dispatch repo if the user wants video.
- **No fabricated sources.** Every source written to `config.yaml` must have been resolved against a real fetch.
- **Don't ask for derivable info.** Cron strings, word budgets, RSS URLs — all derive from the answers.
- **No project-specific specifics.** This is a public-repo skill — never write Pebble, Laura, Notion, or any topic-specific filler unless that's literally what the user asked for.
- **One pass, then stop.** Interview, scaffold, print checklist. Don't auto-run the pipeline. Don't commit.

## If the user wants to skip the interview

Still ask Phase 1 (1-3 — not derivable) and Phase 2 (5 — the moat). Default everything else and proceed.

## If the user already has a config

If `learn_podcast/config.yaml` exists, ask: **edit** (add sources, change cadence) or **start fresh** (overwrites config, keeps past episodes in `output/`).
