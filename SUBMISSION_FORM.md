# GEO Guardian — Submission form answers

> All answers within the character limits. Synthetic/illustrative demo data.

## What's the problem this agent is trying to solve? (max 4000)
Buyers are changing how they discover products. Instead of searching and scanning a page of links, more and more of them just ask an AI assistant — "what's the best X for Y?", "cheapest tool for Z?", "alternatives to <competitor>?" — and act on whatever the assistant recommends. That answer, not a ranked list, is increasingly the shortlist. So a brand's presence inside AI answers has quietly become a make-or-break channel.

The problem is that this channel is completely blind. If your brand isn't recommended when a buyer asks, you simply don't exist for that buyer — and unlike search, there is no console, no rank tracker and no analytics telling you where you stand, which competitors are winning the answer, or whether the model is even stating wrong or outdated facts about you. Marketing teams are left guessing, occasionally opening ChatGPT and eyeballing a single answer, which is neither systematic nor repeatable.

GEO Guardian makes that blind channel measurable and actionable. You give it a brand, a product category and its competitors; it runs realistic buyer questions through an AI assistant, measures whether and where your brand appears versus competitors, flags factual errors, scores your visibility, and hands you a prioritized remediation playbook plus a ready-to-use content brief — with an executive summary at the top and a downloadable report. In short, it does for "AI answer visibility" what SEO tools did for search rankings, so a brand can actually manage its presence in the answers buyers now trust.

## What specific friction exists that a standard linear program or a human can't solve efficiently? (max 4000)
The core difficulty is that the data you need does not exist anywhere until you generate it, and the only way to generate it is to ask a language model and then interpret its free-text answer. That breaks both a rules program and a human at scale.

A standard linear/rules program cannot: (1) invent the realistic buyer questions that would naturally surface brands in a category; (2) read a paragraph of prose and judge whether a specific brand was recommended, at what rank among the options, with what sentiment, and which competitors were named alongside it; or (3) tell a genuine factual error about the brand apart from a fair critique. None of that reduces to keywords or fixed rules.

A human analyst can do all of that — but slowly, subjectively, and unrepeatably. And crucially, AI answers vary every single time you ask, so a one-off manual check is meaningless; you need consistent, structured judgment across many questions and repeated over time to see a real signal.

That is exactly the shape of problem an agentic workflow is built for: a generation step (write natural buyer questions), a simulation step (get the assistant's genuine answer, uninfluenced by knowing which brand we care about), and an interpretation step (audit the answer like an analyst). GEO Guardian then keeps the parts that must be objective — the visibility score and share of voice — out of the model's hands and computes them deterministically in Python, so the headline numbers are reproducible. That combination of language generation, honest simulation, structured judgment, and deterministic scoring is precisely what neither a linear program nor a rushed human can deliver consistently and at scale.

## Solution Architect — overview + Agent Persona (max 4000)
Persona: "The Brand Visibility Analyst Agent" — it interrogates an AI assistant the way a real buyer would, then reports, like an analyst, exactly where your brand stands and what to do about it. It is not one monolithic prompt but a team of specialized agents orchestrated in sequence, each with one job.

How it thinks and acts:
1. ProbeAgent generates realistic buyer/research questions for the category, deliberately with no bias toward the target brand (it is not told which brand we care about). Alternatively, the user can supply their own questions, which are used instead.
2. For each question, an AnswerAgent answers exactly like a generic, helpful AI assistant — again with no knowledge of the target brand, so the measurement is honest and not gamed.
3. An AnalyzerAgent then audits that answer against the target brand and competitors: is the brand mentioned, at what 1-based rank, with what sentiment, which listed competitors appear, a short snippet, and any factual errors about the brand.
4. A deterministic Python step computes the visibility score (0–100) and share of voice from those per-question assessments — no LLM guesswork on the headline metrics.
5. RemediationAgent turns the findings into a prioritized GEO playbook (each action rated by impact and effort).
6. SummaryAgent writes a crisp executive summary — a headline, 2–4 concrete findings, and the single top priority — so the reader gets the "so what" instantly.
7. On demand, a BriefAgent turns the actions the human selects into a concrete content brief.

The human stays in control throughout: they read the dashboard, drill into any question to see the AI's actual answer, choose which remediation actions to act on, download a report, and can re-scan over time to track the trend. The agent surfaces, measures and recommends; the person decides.

## Solution Architect — The Toolset (max 4000)
Built with the OpenAI Agents SDK. The agents and workflow can trigger:
- Runner.run(agent, input): orchestrates each agent turn and its structured output, including the per-question answer→analyze loop.
- Structured outputs (Pydantic schemas): ProbeSet (generated questions); ProbeAssessment (mentioned, rank, sentiment, competitors_mentioned, snippet, factual issues); Remediation (items with impact/effort); ExecSummary (headline, key findings, top priority); ContentBrief (title, audience, target queries, key points, outline).
- Deterministic scoring functions (Python, not the model): compute_score → visibility score, mention rate, share of voice per entity, and the consolidated list of factual errors, using explicit rank and sentiment weightings.
- make_brief(selected actions) → generates a ready-to-publish content brief from the actions the human ticks.
- Custom-question intake: user-supplied buyer questions are used in place of the generated ones.
- Backend endpoints the UI calls: GET /api/presets (quick-start scans); POST /api/process (start a scan with brand/category/competitors/probe-count/optional custom questions); GET /api/events/{job_id} (Server-Sent Events — probes stream in live as they resolve, then the full result); POST /api/brief (content brief from selected actions); GET /api/health.
- Client-side deliverables: a downloadable Markdown report of the full scan, a per-question evidence modal showing the AI's actual answer, and trend-vs-last-scan comparison stored in the browser.

## Solution Architect — The Technical Stack (max 4000)
Backend: Python 3 with FastAPI. Agents built on the OpenAI Agents SDK (Agent + Runner) on the Responses API, using structured outputs via Pydantic models. The scan is a multi-call agent loop (generate questions → for each, answer as a generic assistant → analyze that answer), followed by deterministic Python scoring for the visibility score and share of voice, an executive-summary agent, and an on-demand content-brief agent.

Streaming: the live agent trace and each probe result are pushed to the browser over Server-Sent Events (SSE), so the judge watches the scan happen in real time.

Frontend: a custom single-page analytics dashboard in vanilla HTML/CSS/JS — score ring, share-of-voice bars, a clickable per-question table (opens the AI's full answer), executive-summary card, remediation checklist, content-brief generation, trend indicator, methodology explainer, and a one-click Markdown report export. No framework, no build step.

Model: default GPT-4o-mini to keep a scan cheap (a scan makes several small calls); configurable via env var. Runs fully locally. A "bring your own API key" control in the UI lets anyone run it with their own OpenAI key (stored only in the browser, sent per request), falling back to the server's .env key. Built with OpenAI Codex.

## Business Impact — what value does this bring? (max 4000)
It converts a brand's presence in AI answers from an invisible unknown into a managed, measurable channel — right as buyer discovery shifts there.

For a marketing or brand team, GEO Guardian answers, for the first time and systematically: "When buyers ask an AI in our category, are we recommended? At what rank? What do we lose to — Mixpanel, Amplitude, PostHog? And is the model stating anything false about us?" Instead of a vague worry, they get a visibility score, a share-of-voice comparison against named competitors, the exact buyer questions where they're invisible, the actual answers as evidence, and any factual errors to correct at the source.

Then it closes the loop: a prioritized playbook and a ready content brief tell them what to do next, and the trend indicator lets them prove that a content change actually moved their visibility. The executive summary makes it usable by a CMO in ten seconds; the downloadable report makes it shareable. As AI-mediated discovery grows, being early to measure and fix this channel is a real competitive edge — you can't manage what you can't see, and this makes it visible.

## Business Impact — quantitative & qualitative ROI (max 4000)
This is an emerging, deliberately hard-to-benchmark area, so the figures below are directional rather than a measured pilot.

Quantitative:
- Baseline + trend: a visibility score (0–100) and share of voice you can track over time and after each content change — turning "did our GEO work?" into a number with a ▲/▼ delta versus the previous scan.
- Coverage gap: the precise set of buyer questions where the brand is absent — a concrete content backlog instead of guesswork (e.g., "invisible in 3 of 4 buyer questions; Mixpanel is named in all 4").
- Efficiency: replaces ad-hoc, non-repeatable "ask ChatGPT and eyeball one answer" checks with a structured scan across many questions plus a shareable report — minutes of setup instead of hours of manual, unrepeatable spot-checks.
- Risk avoided: factual errors the model states about the brand, surfaced so they can be corrected before they cost trust or sales.

Qualitative:
- It gives marketing a defensible metric for a channel they currently cannot see or report on.
- Every score is explainable and reproducible (computed in code, with an in-app "how is this scored?" breakdown), and every judgment is backed by the AI's actual answer as evidence — so it earns trust rather than asking for it.
- It produces work that is ready to execute (playbook + content brief), not just a diagnosis.
Because AI answers vary between runs, it is positioned as a monitoring/trend tool, not a single source of truth — which is exactly how a rank tracker is used.

## Future steps — how could this scale or grow? (max 4000)
Near term: schedule recurring scans to chart visibility trends automatically over time; run the same probe set across multiple AI engines and assistants for a cross-engine scorecard; and alert when a competitor overtakes you on a question or when a new factual error appears in an answer. Persist scan history server-side (today the trend is stored in the browser) for team dashboards and reporting.

Product depth: connect the content brief straight into the content pipeline or CMS, add automated first-draft generation for the recommended assets, support per-market and per-language scans, and let teams save and reuse question sets per persona or funnel stage.

Reach: it scales naturally — more brands, categories and competitors are simply more configured scans — and the deterministic scoring keeps comparisons stable across runs and clients. Longer term it becomes a continuous "GEO rank tracker": the analytics and monitoring layer for AI discoverability, plus an agency offering to manage AI presence for many clients from one place. Because the scoring is explicit and every judgment carries its evidence, it can be adopted gradually and trusted as the channel grows.

## Future steps — who will use this solution? (max 4000)
Primary users: marketing, brand, content and SEO/GEO teams, plus competitive-intelligence functions — the people responsible for how a brand shows up to buyers. They use it to baseline AI visibility, prioritize content against the questions where they're invisible, monitor competitors, and catch misinformation the model spreads about them.

Also: agencies and consultancies that manage brand presence for multiple clients (a natural multi-tenant offering), founders and product-marketing leads at startups who live or die by discovery, and PR/comms teams who care about factual accuracy in AI answers.

Target adopters: B2B SaaS and consumer brands whose buyers increasingly research with AI assistants, and the agencies that serve them. The human always chooses which actions to take and reads the evidence behind every number, so the buyer is marketing leadership that wants to treat AI answers as a measurable, ownable channel rather than a black box.

## Demo Link (max 400)
Demo video (<5 min) on HCLTech SharePoint, shared with view access to everyone within HCLTech: [paste your SharePoint link here]. It shows a live scan, the executive summary and visibility score, share of voice, clicking a question to see the AI's actual answer, the playbook and content brief, and the report download.

## Access Instructions (max 4000)
Hosted demo (Vercel): [paste your Vercel link here] — open it and click "Add API key" to paste your own OpenAI key (stored only in your browser; nothing is logged). Preset brands are fictional and results are illustrative and vary between runs.

Or run it raw from the repo (the current local version):
1. Clone the repo and enter the folder.
2. python3 -m venv .venv && source .venv/bin/activate
3. pip install -r requirements.txt
4. cp .env.example .env and set OPENAI_API_KEY — OR skip this and use the "Add API key" button in the app's top bar.
5. python server.py
6. Open http://127.0.0.1:8030. Click a preset (e.g. Acme Analytics) to fill the form — or type your own brand, category, competitors, probe count, and optionally your own buyer questions — then press "Run visibility scan".
7. Read the executive summary and dashboard, click any question row to see the AI's full answer, tick remediation actions and "Generate content brief", and "Download report".
Note: a scan makes several small model calls (default gpt-4o-mini), costing cents on your own key. Re-scanning the same brand shows a trend delta vs the previous run.

## Live Agent Link (max 140)
Live demo (Vercel): [paste your Vercel link here] — then click "Add API key" to use your own OpenAI key.
