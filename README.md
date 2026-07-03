# GEO Guardian

**See how visible your brand is when buyers ask an AI — and how to fix it.**

GEO Guardian is a Generative Engine Optimization (GEO) monitor. You give it a brand, a product
category and competitors; it runs realistic buyer questions through an AI assistant, measures
whether and where your brand appears versus competitors, flags factual errors, scores your
visibility, and hands you a prioritized playbook and a ready-to-use content brief — with an
executive summary up top and a one-click report. Built with the **OpenAI Agents SDK** for the
HCLTech–OpenAI Agentic AI Hackathon (Track 1 — an original, market-differentiated use case).

## The problem

Buyers increasingly ask an AI assistant ("what's the best X for Y?") instead of searching, and
that answer decides which brands they even consider. If your brand isn't recommended there, you're
invisible — and unlike search, there's no console telling you where you stand, who's winning the
answer, or whether the model is stating wrong facts about you.

## What it does

- **Runs buyer questions** through an AI assistant (auto-generated, or your own).
- **Audits each answer**: is your brand mentioned, at what rank, with what sentiment, which
  competitors appear, and any factual errors — with the AI's **actual answer** kept as evidence.
- **Scores visibility (0–100)** and **share of voice** deterministically (computed in code, not by
  the model), with an in-app "how is this scored?" breakdown.
- **Executive summary**: a headline, key findings and the single top priority, written by an agent.
- **Remediation playbook** prioritized by impact/effort, and a **content brief** from the actions
  you select.
- **Trend over time**: re-scan a brand and see a ▲/▼ delta vs the previous scan.
- **Download report**: export the whole scan as Markdown to share.

## Agents

```
ProbeAgent        generates buyer questions for the category (or you supply your own)
AnswerAgent       answers each like a generic AI assistant (the thing we measure)
AnalyzerAgent     audits each answer: mention, rank, sentiment, competitors, errors
(scoring)         visibility score + share of voice, computed deterministically in Python
RemediationAgent  a prioritized GEO playbook
SummaryAgent      the executive summary (headline, key findings, top priority)
BriefAgent        turns selected actions into a content brief
```

## How it differs

Unlike a document-in / approve-out workflow, GEO Guardian is a **monitoring dashboard**: configure
a scan, watch probes run live, then read the executive summary, visibility score, share-of-voice
bars, a clickable per-question table (open the AI's full answer), the playbook, and a report.

## Tech stack

- **Backend**: Python, FastAPI, OpenAI Agents SDK (structured outputs); probes stream in live over
  Server-Sent Events. Headline metrics computed deterministically in Python.
- **Frontend**: a custom dark analytics dashboard (HTML/CSS/JS, no build step).

## Getting started

You need an **OpenAI API key** (platform.openai.com). A scan makes several small model calls
(default `gpt-4o-mini`), costing cents.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # set OPENAI_API_KEY
python server.py
```

Open http://127.0.0.1:8030.

## Using it

1. Click a quick-start preset (Acme Analytics, NimbusPay, FernRoast) to fill the form — or type
   your own brand, category, competitors and probe count. Optionally add **your own questions**.
2. Press **Run visibility scan** and watch the probes resolve live.
3. Read the executive summary and dashboard; **click any question row** to see the AI's full answer;
   tick remediation actions and **Generate content brief**; and **Download report**.
4. Re-scan the same brand later to see the trend delta.

## Bring your own API key

No key in your `.env`? Click **Add API key** in the top bar and paste your own OpenAI key. It is
stored only in your browser (localStorage) and sent to your local server with each request; the
server falls back to its `.env` key if none is set. Never commit your key to the repo.

## Note

Preset target brands are fictional. Results are **illustrative** — they reflect one model's answers
at scan time, which naturally vary between runs; GEO Guardian is a monitoring/trend tool.
