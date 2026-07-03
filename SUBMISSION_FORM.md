# GEO Guardian — Submission form answers

## What's the problem this agent is trying to solve? (max 4000)
Buyers increasingly ask an AI assistant ("what's the best X for Y?") instead of searching, and the assistant's answer decides which brands they even consider. If your brand isn't recommended there, you're invisible — and unlike search, there's no console telling you where you stand, who's beating you, or whether the model is stating wrong facts about you. GEO Guardian is a Generative Engine Optimization (GEO) monitor: you give it a brand, a category and competitors; it runs realistic buyer questions through an AI assistant, measures whether and where your brand appears versus competitors, flags factual errors, and produces a prioritized remediation playbook plus a ready-to-use content brief. The goal is to make AI-answer visibility measurable and actionable, the way SEO made search visibility measurable.

## What specific friction exists that a standard linear program or a human can't solve efficiently? (max 4000)
The "data" you need doesn't exist in any feed — it only exists by asking a language model and interpreting its free-text answer. A standard program can't generate the realistic buyer questions, can't read a paragraph of prose to judge whether a brand was recommended, at what rank, with what sentiment, and which competitors appeared, and can't tell a factual error from a fair critique. A human could do it, but it's slow, subjective and unrepeatable at any useful scale — and the answers vary every time, so you need consistent, structured judgment across many probes. The part that needs an agent is exactly that: synthesize natural buyer questions, get the assistant's answer, and then read that answer like an analyst to extract mention, rank, sentiment, competitor share and factual errors — then turn the findings into concrete actions. That generation-plus-interpretation loop is what a rules engine can't do and a human can't do consistently at scale.

## Solution Architect — overview + Agent Persona (max 4000)
Persona: "The Brand Visibility Analyst Agent" — it interrogates an AI assistant the way a buyer would and reports where your brand stands. The workflow: (1) ProbeAgent generates realistic buyer/research questions for the category, with no bias toward the target brand. (2) For each probe, an AnswerAgent answers exactly like a generic AI assistant (it is not told which brand we care about — that keeps the measurement honest), and an AnalyzerAgent audits that answer: is the target brand mentioned, at what rank, with what sentiment, which listed competitors appear, and any factual errors about the brand. (3) A deterministic Python step computes the visibility score (0–100) and share of voice from the per-probe findings, so the headline numbers are reproducible rather than model-guessed. (4) RemediationAgent produces a prioritized GEO playbook (impact/effort), and a BriefAgent turns the actions the human selects into a concrete content brief. The human reads the dashboard and chooses what to act on.

## Solution Architect — The Toolset (max 4000)
Built with the OpenAI Agents SDK. The agents can trigger:
- Runner.run(agent, input): orchestrates each agent turn and structured output, including the per-probe answer+analyze loop.
- Structured outputs: typed Pydantic schemas (ProbeSet, ProbeAssessment with mention/rank/sentiment/competitors/issues, Remediation items, ContentBrief).
- Deterministic scoring functions (Python): compute the visibility score and share of voice from the assessments — no LLM guesswork on the headline metrics.
- Internal function: make_brief (selected actions -> content brief).
- Backend endpoints: GET /api/presets, POST /api/process (start a scan), GET /api/events/{id} (live SSE — probes stream in as they resolve), POST /api/brief.

## Solution Architect — The Technical Stack (max 4000)
Python 3 + FastAPI backend. OpenAI Agents SDK (Agent + Runner) on the Responses API, with structured outputs via Pydantic, driving a multi-call loop (probe -> answer -> analyze per question). Headline metrics (visibility score, share of voice) are computed deterministically in Python. Results stream live to the browser over Server-Sent Events (SSE). Frontend is a custom single-page analytics dashboard in vanilla HTML/CSS/JS — score ring, share-of-voice bars, per-question table — no framework, no build step. Default model GPT-4o-mini to keep a scan cheap (many calls). Runs fully locally; a "bring your own API key" control in the UI lets anyone run it with their own OpenAI key, falling back to the server's .env. Built with OpenAI Codex.

## Business Impact — what value does this bring? (max 4000)
It makes a brand's presence in AI answers measurable and improvable. Marketing finally gets a number for "are we recommended when buyers ask the AI?", a share-of-voice comparison against named competitors, a list of the exact questions where they're invisible, and a flag on any wrong facts the model is spreading about them. Instead of guessing at "AI SEO", they get a prioritized playbook and a ready content brief to act on. As more discovery shifts to AI assistants, this is a new, currently-blind channel — and being early to measure and fix it is a competitive advantage.

## Business Impact — quantitative & qualitative ROI (max 4000)
Illustrative (this is an emerging, hard-to-benchmark area; figures are directional):
- Visibility: a baseline visibility score and share of voice you can track over time and after each content change.
- Coverage: the specific buyer questions where the brand is absent — a concrete content backlog instead of guesswork.
- Risk: factual errors the model states about the brand, surfaced so they can be corrected at the source.
- Efficiency: replaces ad-hoc manual "ask ChatGPT and eyeball it" checks with a repeatable, structured scan plus an actionable brief.
Qualitatively: it turns an invisible channel into a managed one, gives marketing a defensible metric, and produces work that's ready to execute. Results reflect the model's live answers and naturally vary between runs, so it's positioned as a monitoring trend tool, not a single source of truth.

## Future steps — how could this scale or grow? (max 4000)
Near term: schedule recurring scans to track visibility trends over time, run the same probes across multiple AI engines (different models/assistants) for a cross-engine scorecard, and alert when a competitor overtakes you or a new factual error appears. Add automated remediation drafting that plugs into the content pipeline, and per-market/per-language scans. It scales naturally — more brands, categories and competitors are just more configured scans — and the deterministic scoring keeps comparisons stable. Longer term it becomes a continuous "GEO rank tracker" dashboard for AI discoverability, the analytics layer for a channel that's only growing.

## Future steps — who will use this solution? (max 4000)
Primary users are marketing, brand, content/SEO and competitive-intelligence teams, plus agencies managing brand presence for clients. They use it to baseline AI visibility, prioritize content, monitor competitors and catch misinformation. Target adopters: B2B SaaS and consumer brands whose buyers research with AI assistants, and the agencies that serve them. The human chooses which remediation actions to take, so the buyer is marketing leadership treating AI answers as a measurable, ownable channel.

## Demo Link (max 400)
Demo video (under 5 minutes) uploaded to HCLTech SharePoint and shared with view access to everyone within HCLTech: [paste your SharePoint link here]. It shows a live scan (probes resolving), the visibility score and share-of-voice dashboard, the per-question table, detected errors, and generating a content brief.

## Access Instructions (max 4000)
Hosted demo (Vercel): [paste your Vercel link here] — open it and click "Add API key" to paste your own OpenAI key (stored only in your browser). Preset brands are fictional and results are illustrative.

Or run it raw from the repo (the current local version):
1. Clone the repo and enter the folder.
2. python3 -m venv .venv && source .venv/bin/activate
3. pip install -r requirements.txt
4. cp .env.example .env and set OPENAI_API_KEY — OR skip and use the "Add API key" button in the app's top bar (key stored only in your browser, sent to your local server).
5. python server.py
6. Open http://127.0.0.1:8030, click a preset (e.g. Acme Analytics) to fill the form, press Run visibility scan, read the dashboard, then generate a content brief.
Note: a scan makes several small model calls (default gpt-4o-mini) costing cents on your own key.

## Live Agent Link (max 140)
Live demo (Vercel): [paste your Vercel link here] — then click "Add API key" to use your own OpenAI key.
