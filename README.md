# GEO Guardian

**See how visible your brand is when buyers ask an AI — and how to fix it.**

GEO Guardian is a Generative Engine Optimization (GEO) monitor. You give it a brand, a product
category and competitors; it runs realistic buyer questions through an AI assistant, measures
whether and where your brand appears versus competitors, flags factual errors, and hands you a
prioritized playbook plus a ready-to-use content brief. Built with the **OpenAI Agents SDK** for
the HCLTech–OpenAI Agentic AI Hackathon (Track 1 — an original, market-differentiated use case).

## The problem

Buyers increasingly ask AI assistants ("what's the best X for Y?") instead of searching. If your
brand isn't recommended there, you're invisible — and unlike search rankings, there's no console
telling you where you stand or why.

## What it does

- **Generates buyer questions** for your category (no brand bias).
- **Asks an AI assistant** each question, exactly as a buyer would.
- **Audits each answer**: is your brand mentioned, at what rank, with what sentiment, which
  competitors appear, and are there factual errors about you.
- **Scores visibility** (0–100) and **share of voice** vs competitors, computed deterministically.
- **Builds a remediation playbook** (prioritized by impact/effort) and turns selected actions into
  a concrete **content brief**.

## How it works

```
brand + category + competitors
   └─ ProbeAgent → (for each probe) AnswerAgent → AnalyzerAgent → score (Python) → RemediationAgent
      (questions)   (AI answer)      (mention,                    (visibility,    (playbook)
                                      rank, sentiment)             share of voice)
                                                                         │
                                                          select actions └─► BriefAgent (content brief)
```

## Tech stack

- **Backend**: Python, FastAPI, OpenAI Agents SDK; probes stream in live over Server-Sent Events.
- **Frontend**: a custom dark analytics dashboard — score ring, share-of-voice bars, per-question
  table (HTML/CSS/JS, no build step).

## Project structure

```
agents_pipeline.py   probe / answer / analyze / score / remediation / brief
server.py            FastAPI app (process, events/SSE, presets, brief)
web/                 index.html · style.css · app.js
```

## Getting started

You need an **OpenAI API key** (platform.openai.com — pay-as-you-go). A scan makes several small
calls (default model `gpt-4o-mini`), costing cents.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # set OPENAI_API_KEY
python server.py
```

Open http://127.0.0.1:8030.

## Using it

1. Pick a quick-start preset (Acme Analytics, NimbusPay, FernRoast) to fill the form — or type
   your own brand, category and competitors and choose the number of probes.
2. Press **Run visibility scan** and watch the probes resolve live.
3. Read the dashboard: visibility score, share of voice vs competitors, the per-question table
   (mention / rank / sentiment), detected errors, and the remediation playbook.
4. Tick the actions you want and **Generate content brief**.

## Bring your own API key

No key in your `.env`? Click **Add API key** in the top bar and paste your own OpenAI key. It is
stored only in your browser (localStorage) and sent to your local server with each request; the
server falls back to its `.env` key if none is set. Never commit your key to the repo.

## Notes

Preset target brands are fictional. Results are **illustrative** — they reflect one model's answers
at scan time, which naturally vary between runs.
