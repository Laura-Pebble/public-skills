# Template substitutions

When the skill assembles the user's pipeline, replace every `{{KEY}}` token in
the starter files with the interview answers. Keys are listed below; types in
parentheses.

## Required (Phase 1)

| Key                | Type   | Source            |
|--------------------|--------|-------------------|
| `TOPIC`            | string | Q1 — one sentence |
| `LEVEL`            | string | Q2 — starting point (what they already know) |
| `GOAL`             | string | Q3 — how they'll apply it |
| `CURRICULUM_YAML`  | YAML   | If Structured: the 12 approved lessons, indented 2 spaces. If Organic: delete `curriculum.yaml` entirely. |

## Phase 2

| Key                    | Type | Source |
|------------------------|------|--------|
| `SOURCES_YAML`         | YAML | Resolved source list. Indented 2 spaces. See shape below. |
| `PENDING_SOURCES_YAML` | YAML | Optional list from Q5c. Empty list `[]` if user said no. |

`SOURCES_YAML` entry shape (full):

```yaml
  - name: "Mike Burch — Security Boulevard (syndicated)"
    url: "https://securityboulevard.com/author/michael-burch/feed/"
    kind: "blog"               # blog | podcast | newsletter | youtube | linkedin | person
    resolver: "rss"            # rss | rss_app | apify_linkedin | podchaser_person
    filter:
      author: "Michael Burch"
      keyword_any: ["AI", "LLM", "agent"]
    notes: "Free-form note for the human — never used by code"
```

Only `name`, `url`, `kind` are required. `resolver` defaults to `rss`. `filter` is omitted if no filter.

`PENDING_SOURCES_YAML` entry shape:

```yaml
- name: "AI Champions Podcast"
  query: '"AI Champions" Burch'
  expected_author: "Michael Burch"
  earliest_launch: "2026-07-01"
  min_confidence: 85
  notes: "Watch Buzzsprout + Apple Podcasts"
```

## Phase 3

| Key                | Type    | Source / derivation |
|--------------------|---------|---------------------|
| `EPISODE_MINUTES`  | int     | Q7 — 10/20/30/45 |
| `LOOKBACK_DAYS`    | int     | Derived from cadence: daily=2, MWF=4, weekly=8 |
| `VOICE`            | string  | Q9 — Edge TTS voice ID |
| `NTFY_TOPIC`       | string  | Q10 — empty string if push not selected |
| `PODCAST_FEED`     | bool    | Q10 — `true` if public feed picked, else `false` |
| `S3_BUCKET`        | string  | Q10 follow-up — empty if no public feed |
| `S3_ENDPOINT`      | string  | Q10 follow-up — empty if no public feed |
| `S3_PUBLIC_URL`    | string  | Q10 follow-up — empty if no public feed |
| `LLM_PROVIDER`     | string  | Q11 — `anthropic` / `gemini` / `openai` |
| `VERIFY_STRICT`    | bool    | Q11b — `true` or `false` |

## Feed metadata (only when `PODCAST_FEED` is `true`)

| Key                | Type   | Derivation |
|--------------------|--------|------------|
| `FEED_TITLE`       | string | Default to topic. Confirm. |
| `FEED_DESCRIPTION` | string | Default: `"A personalized teaching podcast on <TOPIC>."` |
| `FEED_AUTHOR`      | string | Ask. |
| `FEED_EMAIL`       | string | Ask. |

## Workflow (`.github/workflows/learn-podcast.yml`)

| Key                    | Type   | Derivation |
|------------------------|--------|------------|
| `CRON`                 | string | daily=`"0 7 * * *"`, MWF=`"0 7 * * 1,3,5"`, weekly=`"0 7 * * 1"`. |
| `CRON_HUMAN`           | string | Plain English version. |
| `PROVIDER_PIP_PACKAGE` | string | `anthropic` / `google-genai` / `openai`. |
