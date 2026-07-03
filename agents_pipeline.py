"""
GEO Guardian - measure how visible a brand is in AI assistant answers, and how
to improve it (Generative Engine Optimization).

Pipeline (built with the OpenAI Agents SDK):
  ProbeAgent     -> generates realistic buyer questions for the category
  AnswerAgent    -> answers each question like a generic AI assistant (the thing
                    we are measuring) — it is NOT told which brand we care about
  AnalyzerAgent  -> for each answer, assesses whether/where the brand appears,
                    sentiment, competitors mentioned and factual issues
  (Python)       -> computes the visibility score and share-of-voice
  RemediationAgent -> a GEO playbook of concrete actions

100% synthetic target brands recommended. Data is illustrative.
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from agents import Agent, Runner

load_dotenv()

MODEL = os.getenv("GEO_MODEL", "gpt-4o-mini")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class ProbeSet(BaseModel):
    probes: list[str] = Field(description="Buyer/research questions for the category")


class ProbeAssessment(BaseModel):
    mentioned: bool = Field(description="Is the target brand recommended/mentioned?")
    rank: Optional[int] = Field(
        default=None, description="1-based position of the brand among recommendations, null if absent"
    )
    sentiment: str = Field(description="positive | neutral | negative | absent")
    competitors_mentioned: list[str] = Field(default_factory=list)
    snippet: str = Field(description="Short quote from the answer (about the brand if present, else the top pick)")
    issues: list[str] = Field(
        default_factory=list, description="Factual errors or outdated claims about the brand, if any"
    )


class RemediationItem(BaseModel):
    action: str
    rationale: str
    impact: str = Field(description="high | medium | low")
    effort: str = Field(description="high | medium | low")


class Remediation(BaseModel):
    items: list[RemediationItem] = Field(default_factory=list)


class ContentBrief(BaseModel):
    title: str
    audience: str
    target_queries: list[str] = Field(default_factory=list)
    key_points: list[str] = Field(default_factory=list)
    outline: list[str] = Field(default_factory=list)


class ExecSummary(BaseModel):
    headline: str = Field(description="One punchy sentence on the brand's AI visibility right now")
    key_findings: list[str] = Field(default_factory=list, description="2-4 concrete findings from the scan")
    top_priority: str = Field(description="The single most important action to take first")


@dataclass
class AuditEntry:
    timestamp: str
    agent: str
    summary: str


@dataclass
class GeoResult:
    brand: str
    category: str
    competitors: list[str]
    probes: list[dict]
    score: dict
    remediation: dict
    summary: dict = field(default_factory=dict)
    audit_log: list[AuditEntry] = field(default_factory=list)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------
def build_probe_agent() -> Agent:
    return Agent(
        name="ProbeAgent",
        model=MODEL,
        instructions=(
            "You generate realistic questions a buyer or researcher would type into an "
            "AI assistant when exploring a product category, the kind of question whose "
            "answer would naturally recommend specific brands or products. Vary intent "
            "(best-of, comparisons, use-case fit, budget, alternatives). Do NOT mention "
            "any specific target brand. Return only the questions."
        ),
        output_type=ProbeSet,
    )


def build_answer_agent() -> Agent:
    return Agent(
        name="AnswerAgent",
        model=MODEL,
        instructions=(
            "You are a helpful, knowledgeable AI assistant. Answer the user's question "
            "naturally and concisely, recommending specific named products or brands as "
            "you normally would, with brief reasons. Do not hedge by refusing to name "
            "options. Keep it under 180 words."
        ),
    )


def build_analyzer_agent() -> Agent:
    return Agent(
        name="AnalyzerAgent",
        model=MODEL,
        instructions=(
            "You audit an AI assistant's answer for brand visibility. Given the target "
            "brand, its competitors, the question and the assistant's answer, determine: "
            "whether the target brand is mentioned/recommended; its 1-based rank among "
            "the recommendations (null if absent); the sentiment toward the brand "
            "(positive/neutral/negative, or 'absent' if not mentioned); which of the "
            "listed competitors appear; a short snippet; and any factual errors or "
            "outdated claims about the brand. Judge only from the answer text."
        ),
        output_type=ProbeAssessment,
    )


def build_remediation_agent() -> Agent:
    return Agent(
        name="RemediationAgent",
        model=MODEL,
        instructions=(
            "You are a Generative Engine Optimization (GEO) strategist. Given a brand, "
            "its category and the findings of a visibility scan (which questions missed "
            "the brand, competitors that dominate, and any factual errors), propose a "
            "prioritized playbook of concrete actions to improve how AI assistants "
            "represent and recommend the brand (e.g. authoritative comparison content, "
            "structured data, third-party presence, fixing wrong facts). For each item "
            "give a rationale and rate impact and effort as high/medium/low."
        ),
        output_type=Remediation,
    )


def build_summary_agent() -> Agent:
    return Agent(
        name="SummaryAgent",
        model=MODEL,
        instructions=(
            "You are a GEO analyst briefing a marketing lead. Given a brand, its "
            "category and the results of an AI-visibility scan (visibility score, "
            "mention rate, share of voice vs competitors, the questions that missed "
            "the brand, any factual errors, and the top recommended actions), write a "
            "crisp executive summary: a one-sentence headline on where the brand "
            "stands, 2-4 concrete key findings (name the competitors that dominate and "
            "the questions where the brand is invisible), and the single top priority "
            "to act on first. Be direct and specific; no fluff."
        ),
        output_type=ExecSummary,
    )


def build_brief_agent() -> Agent:
    return Agent(
        name="BriefAgent",
        model=MODEL,
        instructions=(
            "You turn selected GEO remediation actions into a single concrete content "
            "brief that, if published, would improve the brand's visibility in AI "
            "answers. Include a title, the audience, the target buyer queries it should "
            "rank for, key points to cover, and an outline."
        ),
        output_type=ContentBrief,
    )


# ---------------------------------------------------------------------------
# Scoring (deterministic, in Python)
# ---------------------------------------------------------------------------
def _rank_factor(rank: Optional[int]) -> float:
    if rank is None:
        return 0.6
    return {1: 1.0, 2: 0.75, 3: 0.55}.get(rank, 0.4)


def _sentiment_factor(s: str) -> float:
    return {"positive": 1.0, "neutral": 0.85, "negative": 0.45, "absent": 0.0}.get(
        (s or "").lower(), 0.7
    )


def compute_score(brand: str, competitors: list[str], results: list[dict]) -> dict:
    n = max(1, len(results))
    mentions = [r for r in results if r.get("mentioned")]
    points = 0.0
    for r in results:
        if r.get("mentioned"):
            points += _rank_factor(r.get("rank")) * _sentiment_factor(r.get("sentiment"))
    visibility = round(100 * points / n)

    sov = []
    brand_hits = sum(1 for r in results if r.get("mentioned"))
    sov.append({"name": brand, "pct": round(100 * brand_hits / n), "is_brand": True})
    for c in competitors:
        hits = sum(
            1 for r in results
            if any(c.lower() == m.lower() for m in (r.get("competitors_mentioned") or []))
        )
        sov.append({"name": c, "pct": round(100 * hits / n), "is_brand": False})
    sov.sort(key=lambda x: x["pct"], reverse=True)

    issues = []
    for r in results:
        for i in (r.get("issues") or []):
            if i not in issues:
                issues.append(i)

    return {
        "visibility_score": visibility,
        "mention_rate": round(100 * len(mentions) / n),
        "probes_total": len(results),
        "mentions": len(mentions),
        "share_of_voice": sov,
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
async def run_pipeline(
    brand: str,
    category: str,
    competitors: list[str],
    n_probes: int = 4,
    custom_probes: Optional[list[str]] = None,
    on_progress: Optional[Callable[[str, str], None]] = None,
    on_probe: Optional[Callable[[dict], None]] = None,
) -> GeoResult:
    def notify(agent: str, status: str) -> None:
        if on_progress:
            on_progress(agent, status)

    audit: list[AuditEntry] = []
    n_probes = max(2, min(8, int(n_probes or 4)))

    # 1) Probes — use the user's own questions if given, else generate them.
    custom = [p.strip() for p in (custom_probes or []) if p and p.strip()]
    if custom:
        probes = custom[:8]
        audit.append(AuditEntry(_now(), "ProbeAgent", f"Using {len(probes)} custom questions"))
    else:
        notify("ProbeAgent", f"Generating {n_probes} buyer questions for the category...")
        pset = (await Runner.run(
            build_probe_agent(),
            input=f"Category: {category}\nGenerate exactly {n_probes} questions.",
        )).final_output
        probes = [p for p in pset.probes if p.strip()][:n_probes]
        audit.append(AuditEntry(_now(), "ProbeAgent", f"Generated {len(probes)} probes"))

    # 2) Run each probe: answer + analyze
    answer_agent = build_answer_agent()
    analyzer_agent = build_analyzer_agent()
    results: list[dict] = []
    for i, q in enumerate(probes, 1):
        notify("ProbeRunner", f"Querying ({i}/{len(probes)}): {q}")
        answer = str((await Runner.run(answer_agent, input=q)).final_output)
        assess: ProbeAssessment = (await Runner.run(
            analyzer_agent,
            input=(
                f"TARGET BRAND: {brand}\nCOMPETITORS: {', '.join(competitors) or 'none given'}\n\n"
                f"QUESTION:\n{q}\n\nASSISTANT ANSWER:\n{answer}"
            ),
        )).final_output
        row = {"query": q, "answer": answer, **assess.model_dump()}
        results.append(row)
        if on_probe:
            on_probe(row)

    # 3) Score (Python)
    notify("ScoreAgent", "Scoring visibility and share-of-voice...")
    score = compute_score(brand, competitors, results)
    audit.append(AuditEntry(_now(), "ScoreAgent", f"Visibility {score['visibility_score']}/100; mention rate {score['mention_rate']}%"))

    # 4) Remediation
    notify("RemediationAgent", "Building the GEO remediation playbook...")
    missed = [r["query"] for r in results if not r.get("mentioned")]
    summary = {
        "brand": brand, "category": category,
        "visibility_score": score["visibility_score"],
        "missed_queries": missed,
        "share_of_voice": score["share_of_voice"],
        "issues": score["issues"],
    }
    remediation: Remediation = (await Runner.run(
        build_remediation_agent(),
        input="Findings:\n" + json.dumps(summary, ensure_ascii=False, indent=2),
    )).final_output
    audit.append(AuditEntry(_now(), "RemediationAgent", f"{len(remediation.items)} actions proposed"))

    # 5) Executive summary
    notify("SummaryAgent", "Writing the executive summary...")
    exec_input = {
        "brand": brand, "category": category,
        "visibility_score": score["visibility_score"],
        "mention_rate": score["mention_rate"],
        "share_of_voice": score["share_of_voice"],
        "missed_queries": missed,
        "issues": score["issues"],
        "top_actions": [it.action for it in remediation.items[:3]],
    }
    exec_summary: ExecSummary = (await Runner.run(
        build_summary_agent(),
        input="Scan results:\n" + json.dumps(exec_input, ensure_ascii=False, indent=2),
    )).final_output
    audit.append(AuditEntry(_now(), "SummaryAgent", "Executive summary written"))

    notify("Manager", "Scan complete.")
    return GeoResult(
        brand=brand,
        category=category,
        competitors=competitors,
        probes=results,
        score=score,
        remediation=remediation.model_dump(),
        summary=exec_summary.model_dump(),
        audit_log=audit,
    )


async def make_brief(brand: str, category: str, actions: list[str]) -> ContentBrief:
    agent = build_brief_agent()
    res = await Runner.run(
        agent,
        input=(
            f"BRAND: {brand}\nCATEGORY: {category}\n\nSELECTED ACTIONS:\n- "
            + "\n- ".join(actions)
        ),
    )
    return res.final_output
