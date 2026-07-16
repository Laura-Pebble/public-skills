# Learn Podcast — `{{TOPIC}}`

A personalized teaching podcast, generated for you by the [`learn-podcast`](https://github.com/) Claude skill.

Every run: pulls fresh content from your trusted sources, an LLM ranks it against today's lesson, writes a {{EPISODE_MINUTES}}-minute spoken script, and renders it to MP3.

## What you need to set up once

### 1. API keys

Set the one matching your provider in your shell (and as a GitHub Actions secret with the same name):

| Provider you picked  | Env var              |
|----------------------|----------------------|
| Anthropic Claude     | `ANTHROPIC_API_KEY`  |
| Google Gemini        | `GEMINI_API_KEY`     |
| OpenAI               | `OPENAI_API_KEY`     |

### 2. Install deps

```bash
pip install -r learn_podcast/requirements.txt
# plus the provider SDK you're using:
pip install {{PROVIDER_PIP_PACKAGE}}
```

### 3. Test one episode locally

```bash
python -m learn_podcast.pipeline.main
```

You'll get `learn_podcast/output/<today>.mp3`. Play it. If it sounds right, go to step 4.

### 4. Turn on the schedule

Edit `.github/workflows/learn-podcast.yml` and uncomment the `schedule:` block. Commit and push. Your podcast will now run on **{{CRON_HUMAN}}**.

## How you'll listen

- **Local MP3** — every run writes `learn_podcast/output/<date>.mp3`. Always on.
- **Push notification** — `{{NTFY_TOPIC}}` *(if set)*. Subscribe to that topic in the [ntfy](https://ntfy.sh) app on your phone.
- **Podcast app** — *(if `delivery.podcast_feed: true`)* Paste your S3 public URL + `/feed.xml` into Apple Podcasts → Library → Add a Show by URL, or Spotify for Podcasters.

## Changing it later

- **Add or remove sources** — edit `config.yaml` → `sources:`.
- **Change cadence** — edit the cron in `.github/workflows/learn-podcast.yml`.
- **Change episode length** — edit `config.yaml` → `episode_minutes`.
- **Add a curriculum lesson** — append to `curriculum.yaml` with `status: planned`.
- **Switch provider** — change `config.yaml` → `llm.provider`, set the new API key.
- **Start over** — re-run the `learn-podcast` skill.
