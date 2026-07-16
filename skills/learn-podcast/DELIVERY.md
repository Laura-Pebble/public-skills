# How your podcast gets to you

This skill **generates** an MP3 of your custom lesson on the schedule you pick. This page explains how the MP3 actually reaches you — i.e. how you'll listen to it. Read this before you run the interview; you'll pick a delivery option at the end.

You can pick **any combination** of the three options below. They all work side-by-side.

## TL;DR — pick one

| Option | What it feels like | Setup time | Best for |
|---|---|---|---|
| **Push notification** | Phone buzzes when episode is ready; tap to listen in browser | 30 seconds | Trying it out, "I just want to listen" |
| **Real podcast feed** | Episodes show up in Apple Podcasts / Spotify / your usual app | 15 min one-time | "I want this in my normal podcast app" |
| **Just a file** | MP3 sits in a folder; you open it manually | None | You already pipe it somewhere yourself |

---

## Option 1: Push notification (recommended for getting started)

**What you get:** when a new episode is ready, your phone buzzes with a notification. You tap it, the audio plays in your phone's browser. No podcast app involved.

**How it works:** the skill uses [ntfy.sh](https://ntfy.sh), a free push-notification service. No account, no fees, no ads.

**Setup:**

1. Install the **ntfy** app on your phone ([iOS](https://apps.apple.com/us/app/ntfy/id1625396347) / [Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy)).
2. During the skill interview, when it asks for a "ntfy topic," pick something nobody else would guess — e.g. `marcia-marketing-podcast-7x9k2`. The longer and more random, the better (your "topic" is also your password — anyone who knows it can see your notifications).
3. In the ntfy app, tap **+**, paste the same topic, tap **Subscribe**.

That's it. Next time the cron runs, you get a notification with a tap-to-listen link.

**What you can't do with this option:** episodes don't queue up like a real podcast. There's no history. If you miss a notification, the link still works as long as you saved it (the link comes through in the notification body).

---

## Option 2: Real podcast feed (Apple Podcasts, Spotify, etc.)

**What you get:** your podcast shows up in your normal podcast app, exactly like any other show you subscribe to. New episodes auto-download, play history is tracked, you can speed up/slow down, etc.

**How it works:** the skill generates a proper podcast RSS feed (the same kind of file Apple and Spotify read) and uploads both the feed and the MP3 files to a small cloud storage bucket you own. You paste the feed's URL into your podcast app once. From then on, every new episode the cron generates shows up automatically.

**What you need:**

A **Cloudflare R2** account. R2 is Cloudflare's S3-compatible cloud storage. Free for up to 10 GB of storage and 1 million reads/month — enough for years of weekly episodes. Other options work too (AWS S3, Backblaze B2), but R2 is the cheapest and easiest.

**Setup (one time, ~15 min):**

1. Go to **https://dash.cloudflare.com/sign-up** and make a free account.
2. In the sidebar, click **R2 Object Storage** → **Create bucket**. Name it something like `my-learn-podcast`.
3. After the bucket is created, go to its **Settings** tab → **Public access** → enable **Allow Access** and connect a domain (or use the auto-generated `*.r2.dev` URL Cloudflare gives you — fine for personal use).
4. Back in the R2 dashboard, click **Manage R2 API Tokens** → **Create API Token** → give it **Object Read & Write** permission on your new bucket. Cloudflare shows you four values once — copy all of them, you can't see them again:
   - Access Key ID
   - Secret Access Key
   - Endpoint URL (looks like `https://<account-id>.r2.cloudflarestorage.com`)
   - Public URL (looks like `https://pub-<random>.r2.dev` or your custom domain)
5. When the skill interview asks about delivery, say yes to "Public podcast feed" and paste those four values when prompted.

**Then, to subscribe in your podcast app:**

- **Apple Podcasts (Mac/iPhone):** open the Podcasts app → top menu **File → Follow a Show by URL** (Mac) or **Library tab → ⋯ menu → Follow a Show by URL** (iPhone) → paste `<your-public-url>/feed.xml`. Done.
- **Spotify:** Spotify won't accept arbitrary RSS feeds directly. You have to submit your feed through [Spotify for Podcasters](https://podcasters.spotify.com) — free, ~5 minutes. After they approve it (usually within a day), it appears in regular Spotify search. *Skip Spotify for personal use — Apple Podcasts is much simpler.*
- **Overcast, Pocket Casts, Castro, Antennapod, anything else:** all of them have an "Add by URL" option somewhere in the menu. Paste the same `feed.xml` URL.

**Your feed is private** in the sense that only people you give the URL to can find it. It's not searchable on Apple Podcasts unless you separately submit it to the Apple directory (which you don't need to).

---

## Option 3: Just an MP3 file (lightest weight)

**What you get:** each episode is saved as `learn_podcast/output/2026-06-29.mp3` in the GitHub repo that runs the cron. You can download it, AirDrop it, drop it into iTunes, whatever.

**When this makes sense:** you already have a workflow you trust — maybe you sync that folder to a Dropbox the rest of your team listens to, or you're building something custom on top.

**Setup:** nothing. This one is on by default. Even if you pick Options 1 and 2, the MP3 file is still saved.

---

## What does it cost?

- **The skill itself:** free. It's a script that runs in GitHub Actions, which is free for public repos and generous on private ones.
- **The LLM call** that writes each episode's script: ~5-15 cents per episode using Anthropic Claude, ~free on Google Gemini's free tier, ~5 cents on OpenAI. So roughly **$1-2/month** for a thrice-weekly podcast.
- **Edge TTS** that turns the script into spoken audio: **free.** No API key needed.
- **ntfy push notifications:** free.
- **Cloudflare R2 storage** (for Option 2): free under 10 GB / 1 million reads per month. A 20-minute MP3 is ~10 MB; you'd fit roughly 1,000 episodes in the free tier.

Realistic monthly bill for a personal weekly podcast: **under $1**. For thrice-weekly: **$2-3**.

---

## Combining options

Most people pick **ntfy + real podcast feed** together. The ntfy notification tells you a new episode dropped; the podcast feed gives you the proper listening experience. Both are filled in during the interview — just say yes to both.

---

## "It's not working" — common stumbles

- **No notification arriving (Option 1):** double-check that the topic string in the ntfy app matches the one in your `config.yaml` exactly (case-sensitive). Test by sending yourself a message: `curl -d "test" ntfy.sh/<your-topic>`.
- **Episodes not showing up in Apple Podcasts (Option 2):** open the feed URL in a browser — you should see XML. If you see "Access Denied," your R2 bucket isn't public; recheck step 3 of Option 2.
- **GitHub Actions hasn't run yet:** the workflow is **disabled by default** after you scaffold. Edit `.github/workflows/learn-podcast.yml` and uncomment the `schedule:` block. Commit and push. The next scheduled time will trigger your first run.
- **Episode generated but sounds wrong** (cut off, off-topic, garbled): check the workflow logs for the `[6/9] Verifying grounding` step. If a lot of claims were flagged as `BLOCKED`, your sources didn't actually cover the topic. Either add more relevant sources or let the next run pick something the sources do cover.

If something else is off, open an issue on the [public-skills repo](https://github.com/Laura-Pebble/public-skills/issues).
