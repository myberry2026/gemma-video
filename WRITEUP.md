# I Put Gemma 4's 2B Model on My Phone to Distill a Day of Screenshots Into a Recap

▶ **Watch the 1-minute demo**: https://youtube.com/shorts/W_pw4Lqcz14

## The Problem That Won't Go Away

I just spent six hours on my phone today. I can't tell you a single thing I did.

I know I scrolled TikTok. I know I added something to my Amazon cart and never bought it. I know I watched a YouTube video about a topic I now can't remember. My phone watched all of it — captured every pixel, technically — but the only thing left in *my* head is a vague feeling that I wasted the day.

I call this **digital amnesia**. You probably have it too.

I kept wishing my phone could just *tell me* what I did. Like a little daily recap, every morning. *"Yesterday you browsed Amazon for shoes, watched a video about RC cars, and didn't reply to your mom."*

The problem with that wish: nobody is going to build it at a level of privacy I'd be comfortable with. Not Google. Not Apple. Definitely not whatever cloud AI startup is going to vacuum up my screenshots.

Then **Gemma-4-E2B** dropped. 2.4 gigabytes. Multimodal. Reasoning. Runs on a phone.

That was the *aha* moment. Why am I wishing for this? Why don't I just build it RIGHT NOW?

## What I Built: AetherLens

A daily recap of your digital life — built entirely from screenshots your phone already takes, curated by Gemma-4-E2B running **on the phone itself**. No cloud. No laptop. No "share data for analytics".

**How you use it**: install the app, grant Accessibility permission once, and forget about it. AetherLens hooks into Android's **accessibility tree** to detect app switches and auto-captures a screen every 15 seconds in the background. Open the app whenever you want to see your day — the Storyboard tab shows the Gemma-4-curated highlights, the Album tab shows the raw screenshots, and the Settings tab has a "Trigger Manual Recap" button if you want to force curation right now instead of waiting for the next pass.

```
   AccessibilityService grabs a screen every 15 seconds, all day
              │
              ▼
   ┌────────── Real-time dedup as it captures ──────────┐
   │  Pass 1: pHash pixel filter   (drop the obvious)    │
   │  Pass 2: Gemma-4 visual sim   (decide the unclear)  │
   └─────────────────────────────────────────────────────┘
              │
              ▼   (only diverse frames hit disk)
        /sdcard/AetherLens/raw/  ← your day, deduped
              │
              ▼
   ┌────────── End-of-day distillation ─────────┐
   │  Pass 3: Gemma-4 narrative curation         │
   │          20 → 7 + one-sentence summary      │
   └─────────────────────────────────────────────┘
              │
              ▼
        Storyboard tab on the phone
        7 narrative highlights per app
        + Gemma-4 summary line each
```

The captures live in `/sdcard/AetherLens/raw/`. The 2.4 GB Gemma-4-E2B model lives in `/sdcard/Download/`. The OpenAI-compatible inference server lives **inside the app itself**, listening on `localhost:8080`.

That's the whole stack. **Three layers. One model. Fully on the phone.**

## Why Gemma-4-E2B Specifically

When I started, I tried every model in the family:

- **Gemma-4 31B (dense)** — beautiful captions, but 60+ GB. Never going to live on a phone.
- **Gemma-4 26B-A4B (MoE)** — Same, too big to fit in my phone.
- **Gemma-4 E4B** — slightly better than E2B, but significantly slow.
- **Gemma-4 E2B** — 2.4 GB. Multimodal. Reasoning. **The fastest model in the family on a phone, and the only one that fits.**

E2B is the only variant where I didn't have to compromise on any of:

1. Lives on the phone
2. Sees pixels (not OCR text)
3. Has the "thinking" reasoning mode so it can explain *why* it picked specific frames
4. Inference fast enough that a daily recap doesn't drain the battery

That's why the title says "Gemma 4's 2B model". Everything else is a different product.

## The Dedup Pipeline (where Gemma-4 actually earns its keep)

Curation is the hard part. Twenty screenshots of the Amazon homepage all look similar. The user doesn't want twenty homepage thumbnails — they want **the seven moments that actually mattered**.

Three passes do the work. The first two run **continuously, in real time**, as new screens come in:

### Pass 1 — Perceptual Hash (local, ~1 ms)
Resize each incoming frame to 64×64 grayscale, take a pixel diff against the previous kept frame. Cheap and stupid, but kills the "you sat on the same screen for 15 seconds" case before Gemma even sees it.

### Pass 2 — Gemma-4 Visual Similarity (borderline cases only)
When pHash says "kinda similar" (0.85–0.98), the answer is ambiguous. Gemma-4 takes over and makes a semantic call — *"is this the same screen, or just a similar layout?"* Cheaper than running it on every pair; smart enough to handle the cases pHash can't.

### Pass 3 — Gemma-4 Narrative Curation
This is the end-of-day headline pass. We hand Gemma-4-E2B the deduped frames from one app's session in a single multimodal call, and ask it to pick the seven most diverse, narrative-worthy moments and write a one-sentence summary. The "thinking" mode lets the model reason explicitly about diversity vs. redundancy.

You get back something like:

> *"The session involved browsing specific products, exploring fashion and home goods categories, checking pet wellness items, and engaging with multiple seasonal sales promotions."*
> Selected frames: 0, 1, 3, 5, 6, 7, 18.

Real output. Real Gemma. All on the phone.

## The Stack

```
Android app (Kotlin)
 ├── AccessibilityService — hooks the OS accessibility tree,
 │                           captures one screen every 15 s
 ├── LlmInferenceManager  — wraps com.google.ai.edge.litertlm
 ├── EmbeddedLlmServer    — NanoHTTPD, OpenAI-compatible /v1/chat
 │                           served on the device at localhost:8080
 └── MemoryBridgeService  — real-time dedup + end-of-day curation
       │
       ▼
   localhost:8080 hosted by EmbeddedLlmServer  →  Gemma-4-E2B (2.4 GB on /sdcard)
```

Three layers. One model. **No cloud, No laptop.**

> *(Optional power mode: if you want faster curation, the same Settings toggle can point the app at a workstation running the byte-identical Gemma-4-E2B over your home network. Same model, same prompts — just faster. But everything works fully on the phone by default, and the demo video runs on-device only.)*

## What Actually Works (the demo)

For the submission, I ran AetherLens against 9 real apps on a real phone (Motorola Edge 2025). Real Gemma-4-E2B inference. Zero heuristic fallbacks fired.

| App | Gemma-4-E2B summary |
| --- | --- |
| Amazon    | "Browsing specific products, fashion/home goods, pet wellness, seasonal sales" |
| Chrome    | "Searching for info, tech deals and financial market news, sponsored content" |
| Calendar  | "Navigating from empty view through dense schedules, future planning" |
| YouTube   | "Lifestyle, sponsored ads, sports highlights, social, DIY" |
| TikTok    | "Comedy, DIY, lifestyle vlogs, pet content, relationship dynamics, travel" |
| Photos    | "Initiates and completes the Google Photos backup setup" |
| Maps      | "Initiated a search but no updates were found in the area" |
| Messaging | "Viewing Google Messages with verification codes and a Gemini AI prompt" |
| Settings  | "Navigating main settings — security, location, parental controls" |

**9 apps. 180 raw frames in. 63 curated highlights out. All real Gemma. All on the phone.**

## What's Next

- **Multi-day rollup** — chain daily recaps into a weekly mosaic
- **Voice query** — "What was I doing on Tuesday?" — feed the storyboard back into Gemma-4 as context
- **Per-app privacy mode** — never capture from banking or password apps
- **NPU variants** — drop in a vendor-compiled E2B for extra speed without changing any other code

## Try It

GitHub: https://github.com/myberry2026/gemma-video

The whole thing is one Kotlin app and a handful of scripts. Clone, run `./install.sh <device-id>`, point it at a Gemma-4-E2B model file, and you have your own private daily-recap engine in fifteen minutes.

I built this because I was tired of forgetting my own day. Maybe you are too.

— Powered entirely by Gemma 4, on the device in your pocket.
