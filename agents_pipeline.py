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


class BrandResolution(BaseModel):
    target_aliases: list[str] = Field(default_factory=list)
    competitor_aliases: dict[str, list[str]] = Field(default_factory=dict)


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
    market_category: str
    market: str
    competitors: list[str]
    probes: list[dict]
    score: dict
    remediation: dict
    brand_profile: dict = field(default_factory=dict)
    summary: dict = field(default_factory=dict)
    audit_log: list[AuditEntry] = field(default_factory=list)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def deterministic_aliases(name: str) -> list[str]:
    clean = " ".join((name or "").strip().split())
    aliases = [clean]
    compact = clean.replace(" ", "")
    if compact and compact.lower() != clean.lower():
        aliases.append(compact)
    if "." not in compact and compact:
        aliases.append(f"{compact.lower()}.com")
    return list(dict.fromkeys(a for a in aliases if len(a) > 2))


def text_mentions_any(text: str, aliases: list[str]) -> bool:
    low = (text or "").lower()
    return any(alias.lower() in low for alias in aliases if len(alias) > 2)


def normalize_aliases(base: str, proposed: list[str]) -> list[str]:
    out = deterministic_aliases(base)
    for alias in proposed or []:
        clean = " ".join(str(alias).strip().split())
        if clean and len(clean) > 2:
            out.append(clean)
    return list(dict.fromkeys(out))


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


def build_brand_resolver_agent() -> Agent:
    return Agent(
        name="BrandResolverAgent",
        model=MODEL,
        instructions=(
            "You normalize brand names before a visibility scan. Given a target brand, "
            "competitors, a market category and a country/market, propose spelling "
            "variants, common aliases, punctuation/spacing variants and obvious domain "
            "forms that should count as the same brand in an AI answer. Do not invent "
            "unrelated companies. If a competitor looks like a likely typo, include the "
            "probable intended spelling as an alias, but keep it under that competitor's "
            "original name. Return aliases only."
        ),
        output_type=BrandResolution,
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
            "to act on first. Be direct and specific; no fluff. Avoid implying the AI "
            "does not know the company exists; say the brand was not mentioned in the "
            "tested answers or tested buyer queries."
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


async def resolve_brand_profile(
    brand: str,
    competitors: list[str],
    category: str,
    market_category: str,
    market: str,
) -> BrandResolution:
    fallback = BrandResolution(
        target_aliases=deterministic_aliases(brand),
        competitor_aliases={c: deterministic_aliases(c) for c in competitors},
    )
    try:
        resolved: BrandResolution = (await Runner.run(
            build_brand_resolver_agent(),
            input=(
                f"TARGET BRAND: {brand}\n"
                f"COMPETITORS: {', '.join(competitors) or 'none'}\n"
                f"PRODUCT CATEGORY: {category}\n"
                f"MARKET CATEGORY: {market_category or 'not specified'}\n"
                f"COUNTRY / MARKET: {market or 'not specified'}"
            ),
        )).final_output
    except Exception:
        return fallback

    return BrandResolution(
        target_aliases=normalize_aliases(brand, resolved.target_aliases),
        competitor_aliases={
            c: normalize_aliases(c, resolved.competitor_aliases.get(c, []))
            for c in competitors
        },
    )


def compute_score(
    brand: str,
    competitors: list[str],
    results: list[dict],
    competitor_aliases: Optional[dict[str, list[str]]] = None,
) -> dict:
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
        aliases = (competitor_aliases or {}).get(c) or deterministic_aliases(c)
        hits = sum(
            1 for r in results
            if any(text_mentions_any(m, aliases) for m in (r.get("competitors_mentioned") or []))
            or text_mentions_any(r.get("answer") or "", aliases)
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
    market_category: str = "",
    market: str = "",
    on_progress: Optional[Callable[[str, str], None]] = None,
    on_probe: Optional[Callable[[dict], None]] = None,
) -> GeoResult:
    def notify(agent: str, status: str) -> None:
        if on_progress:
            on_progress(agent, status)

    audit: list[AuditEntry] = []
    n_probes = max(2, min(8, int(n_probes or 4)))
    notify("BrandResolverAgent", "Normalizing brand and competitor names...")
    brand_profile = await resolve_brand_profile(brand, competitors, category, market_category, market)
    aliases = brand_profile.target_aliases
    audit.append(AuditEntry(_now(), "BrandResolverAgent", f"Tracking aliases: {', '.join(aliases[:5])}"))

    context = (
        f"Product category: {category}\n"
        f"Market category: {market_category or 'not specified'}\n"
        f"Country / market: {market or 'global / not specified'}"
    )

    # 1) Probes — use the user's own questions if given, else generate them.
    custom = [p.strip() for p in (custom_probes or []) if p and p.strip()]
    if custom:
        probes = custom[:8]
        audit.append(AuditEntry(_now(), "ProbeAgent", f"Using {len(probes)} custom questions"))
    else:
        notify("ProbeAgent", f"Generating {n_probes} buyer questions for the category...")
        pset = (await Runner.run(
            build_probe_agent(),
            input=(
                f"{context}\n"
                f"Generate exactly {n_probes} buyer questions. If a country/market is "
                "specified, make the questions clearly about that market. Do not mention "
                "the target brand."
            ),
        )).final_output
        probes = [p for p in pset.probes if p.strip()][:n_probes]
        audit.append(AuditEntry(_now(), "ProbeAgent", f"Generated {len(probes)} probes"))

    # 2) Run each probe: answer + analyze. Probes are independent, so run a
    # small batch concurrently to keep hosted demos inside function timeouts.
    answer_agent = build_answer_agent()
    analyzer_agent = build_analyzer_agent()
    gate = asyncio.Semaphore(3)

    async def run_one_probe(i: int, q: str) -> dict:
        notify("ProbeRunner", f"Querying ({i}/{len(probes)}): {q}")
        async with gate:
            answer = str((await Runner.run(
                answer_agent,
                input=(
                    f"{context}\n"
                    f"Buyer question: {q}\n\n"
                    "Answer the buyer question in this category. If the question asks for "
                    "options, vendors, tools or companies, name specific options. If a "
                    "country/market is specified, answer for that market."
                ),
            )).final_output)
            assess: ProbeAssessment = (await Runner.run(
                analyzer_agent,
                input=(
                    f"TARGET BRAND: {brand}\n"
                    f"TARGET BRAND ALIASES: {', '.join(aliases)}\n"
                    f"COMPETITORS: {json.dumps(brand_profile.competitor_aliases, ensure_ascii=False)}\n"
                    f"{context}\n\n"
                    f"QUESTION:\n{q}\n\nASSISTANT ANSWER:\n{answer}"
                ),
            )).final_output
        row = {"query": q, "answer": answer, **assess.model_dump()}
        if not row.get("mentioned") and text_mentions_any(answer, aliases):
            row["mentioned"] = True
            row["sentiment"] = row.get("sentiment") if row.get("sentiment") != "absent" else "neutral"
            row["snippet"] = row.get("snippet") or aliases[0]
        if on_probe:
            on_probe(row)
        return row

    results = await asyncio.gather(
        *(run_one_probe(i, q) for i, q in enumerate(probes, 1))
    )

    # 3) Score (Python)
    notify("ScoreAgent", "Scoring visibility and share-of-voice...")
    score = compute_score(brand, competitors, results, brand_profile.competitor_aliases)
    audit.append(AuditEntry(_now(), "ScoreAgent", f"Visibility {score['visibility_score']}/100; mention rate {score['mention_rate']}%"))

    # 4) Remediation
    notify("RemediationAgent", "Building the GEO remediation playbook...")
    missed = [r["query"] for r in results if not r.get("mentioned")]
    summary = {
        "brand": brand, "category": category,
        "market_category": market_category,
        "market": market,
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
        "market_category": market_category,
        "market": market,
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
        market_category=market_category,
        market=market,
        competitors=competitors,
        probes=results,
        score=score,
        remediation=remediation.model_dump(),
        brand_profile=brand_profile.model_dump(),
        summary=exec_summary.model_dump(),
        audit_log=audit,
    )


async def make_brief(
    brand: str,
    category: str,
    actions: list[str],
    market_category: str = "",
    market: str = "",
) -> ContentBrief:
    agent = build_brief_agent()
    res = await Runner.run(
        agent,
        input=(
            f"BRAND: {brand}\n"
            f"PRODUCT CATEGORY: {category}\n"
            f"MARKET CATEGORY: {market_category or 'not specified'}\n"
            f"COUNTRY / MARKET: {market or 'not specified'}\n\n"
            "SELECTED ACTIONS:\n- "
            + "\n- ".join(actions)
        ),
    )
    return res.final_output
