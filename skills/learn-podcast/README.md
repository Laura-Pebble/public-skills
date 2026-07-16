# `learn-podcast` — a Claude skill

A Claude skill that builds you a personalized teaching podcast on any topic. Audio only. You bring the topic and the sources you trust; the skill scaffolds an audio pipeline + scheduled workflow into your repo.

## What it does

1. **Interviews you** (~10 questions, 3-5 min) about what you want to learn, who you are as a learner, what sources you already trust, and how you want it delivered.
2. **Resolves your sources** to RSS feeds (Substacks, podcast feeds, YouTube channels, blogs).
3. **Optionally writes a 12-lesson curriculum** for you, calibrated to your starting point and goal — you approve or edit it before it ships.
4. **Scaffolds an audio pipeline** into `learn_podcast/` in your repo: RSS discovery → LLM curation → LLM-written spoken script → Edge TTS → optional podcast RSS feed.
5. **Drops a scheduled GitHub Actions workflow** (off by default — you turn it on after a local test) on your chosen cadence: daily / Mon-Wed-Fri / weekly.

## What it produces

```
learn_podcast/
├── config.yaml
├── curriculum.yaml          # only if you picked a structured curriculum
├── requirements.txt
├── pipeline/
│   ├── main.py              # orchestrator
│   ├── discover.py
│   ├── curate.py
│   ├── script.py
│   ├── tts.py
│   ├── feed.py
│   ├── notify.py
│   └── llm.py
└── .github/workflows/learn-podcast.yml
```

## Delivery options (pick any combination)

- **Local MP3** — every run drops a file. Always on.
- **Push notification** — ntfy.sh sends to your phone, free, no account.
- **Public podcast feed** — uploads MP3 + feed.xml to S3-compatible storage (Cloudflare R2, AWS S3, Backblaze B2). You paste the feed URL into Apple/Spotify Podcasts.

## LLM providers supported

- Anthropic Claude (recommended for script quality)
- Google Gemini (generous free tier)
- OpenAI

You pick one; only that provider's SDK needs to be installed.

## Install the skill

Copy `skills/learn-podcast/` into your project's `.claude/skills/` directory, or place it under `~/.claude/skills/` to use across all your projects.

Then in Claude Code:

```
/learn-podcast
```

…and Claude will walk you through the interview.

## Credits

Derived from the `src/teacher/` pipeline in [pebble-marketing/dispatch](https://github.com/laura-pebble/dispatch) — Laura McAliley's personal AI-marketing learning podcast — genericized for any topic and stripped of video / Notion / project-specific dependencies. Audio-only.
