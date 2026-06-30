# GEO Guardian — Submission & video script

## Submission form answers (copy/paste)

**Agent workflow.** GEO Guardian measures how visible a brand is in AI assistant answers and how
to improve it. (1) **ProbeAgent** generates realistic buyer questions for the category (no brand
bias). (2) For each probe, **AnswerAgent** answers like a generic AI assistant — the thing we are
measuring — and **AnalyzerAgent** audits that answer: is the target brand mentioned, at what rank,
with what sentiment, which competitors appear, and any factual errors. (3) A deterministic Python
step computes the **visibility score (0–100)** and **share of voice**. (4) **RemediationAgent**
produces a prioritized GEO playbook, and **BriefAgent** turns the actions you select into a
content brief. A human reviews the dashboard and picks the actions.

**OpenAI technology stack.** OpenAI **Agents SDK** (Agent + Runner) with **structured outputs**
(Pydantic `output_type`); multi-call agent loop (probe → answer → analyze per question); scoring
in Python for determinism; results streamed live over SSE. Default model GPT-4o-mini for
cost-efficient scans. Built with **Codex**.

---

## Video script (target 4–5 min)

### Part 1 — Pitch deck (~90 seconds)

- **[Slide 1 — Title]** "Hi, I'm ⟨name⟩. This is **GEO Guardian** — how visible is your brand when
  buyers ask the AI? Built with the OpenAI Agents SDK and Codex. It's Generative Engine
  Optimization."
- **[Slide 2 — Problem]** "Buyers increasingly ask an AI assistant instead of searching. If the AI
  doesn't recommend you, you're invisible — and unlike search, there's no console telling you where
  you stand or why, and models can even state wrong facts about you."
- **[Slide 3 — How it works]** "Here's the **agent workflow**: ProbeAgent writes buyer questions,
  AnswerAgent answers each like a generic assistant, AnalyzerAgent checks mention, rank, sentiment
  and errors, we score visibility deterministically, and RemediationAgent builds the playbook."
- **[Slide 4 — What the judges see]** "You'll see the visibility score, share of voice versus
  competitors, the per-question table, and a playbook you turn into a content brief."
- **[Slide 5 — Impact & scale]** "It gives you brand visibility you couldn't see before, ranked
  against competitors, with concrete actions. It works for any brand, category or market."

### Part 2 — Live demo (~3 minutes)

1. "I open GEO Guardian at **localhost:8030** — note the dark analytics dashboard."
2. "First the key: I click **Add API key**, paste my own OpenAI key — anyone can run the repo. Dot
   turns green."
3. "I click the preset **Acme Analytics**, which fills the brand, category and competitors — no
   typing."
4. "I press **Run visibility scan**. Watch the **probes resolve live** — each buyer question is sent
   to an AI assistant and audited: you can see, per question, whether Acme was mentioned and its
   rank."
5. "Now the dashboard: the **visibility score** out of 100, the **share-of-voice bars** versus
   Mixpanel, Amplitude and PostHog, and the **per-question table** with mention, rank and
   sentiment. Down here, any factual errors the model stated about the brand."
6. "Finally the **remediation playbook**, prioritized by impact and effort. I tick a couple of
   actions and click **Generate content brief** — and the agent drafts a brief I could hand to
   marketing."
7. "That's GEO Guardian — show up when the AI answers."

> Tip: results vary between runs (they reflect the model's live answers), so do a quick dry run and
> pick the preset that demos best.
