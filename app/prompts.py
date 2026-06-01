from __future__ import annotations

from app.evidence import EvidenceChunk, format_evidence
from app.knowledge_prior import KnowledgePrior


SYSTEM_PROMPT = """You answer using the provided project prior and web evidence.
Use the project prior for architecture, terminology, and stable design judgment.
Use web evidence to verify freshness, current support, URLs, docs, versions, and claims that may have changed.
If evidence is weak, stale, blocked, or conflicting, say so clearly.
Use concise citations like [1], [2] after claims.
Do not cite a source unless the claim is supported by that source.
Prefer official, primary, or documentation sources over SEO blogs, social posts, or generic commentary.
Do not introduce tools as recommendations when they appear only in weak or tangential evidence.
Prefer dates when the user asks about recent or changing information."""


def _format_prior(prior: KnowledgePrior | None) -> str:
    if prior is None:
        return "None."
    return f"{prior.label}: {prior.text}"


def _prior_specific_rules(prior: KnowledgePrior | None) -> str:
    if prior is None:
        return "None."
    if prior.label == "local_search_cache_strategy":
        return (
            "For this cache-strategy question, keep the answer focused on the local SQLite design. "
            "Do not mention external cache-service, search-cluster, or vector-index product names unless "
            "the user's question explicitly asks for scale-out options. Forbidden terms for this default "
            "answer: Redis, Valkey, OpenSearch, Elasticsearch."
        )
    if prior.label == "local_citation_quality":
        return (
            "For this citation-quality question, explicitly cover citation ID validation, weak-source filtering, "
            "primary/official source preference, and visible warnings for thin or conflicting evidence."
        )
    return "None."


def build_answer_messages(
    question: str,
    evidence: list[EvidenceChunk],
    prior: KnowledgePrior | None = None,
    answer_style: str = "",
) -> list[dict[str, str]]:
    evidence_text = format_evidence(evidence)
    user_prompt = f"""Question:
{question}

Project prior:
{_format_prior(prior)}

Prior-specific output rules:
{_prior_specific_rules(prior)}

Answer style:
{answer_style or "Use an appropriate level of detail."}

Evidence:
{evidence_text}

Write a helpful answer. Use the project prior as the stable frame, but cite web evidence for current facts."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


FINALIZER_SYSTEM_PROMPT = """You are the final answer channel.
Do not show reasoning.
Do not think step by step.
Return only the final user-facing answer.
Use only the provided evidence and cite sources like [1], [2]."""


def build_finalizer_messages(
    question: str,
    evidence: list[EvidenceChunk],
    prior: KnowledgePrior | None = None,
    answer_style: str = "",
) -> list[dict[str, str]]:
    evidence_text = format_evidence(evidence)
    user_prompt = f"""Produce the final answer now.

Question:
{question}

Project prior:
{_format_prior(prior)}

Prior-specific output rules:
{_prior_specific_rules(prior)}

Answer style:
{answer_style or "Use an appropriate level of detail."}

Evidence:
{evidence_text}

Rules:
- Output final answer only.
- No analysis section.
- No hidden reasoning.
- If evidence is insufficient, say that directly.
- Keep the answer concise and cite supporting evidence."""
    return [
        {"role": "system", "content": FINALIZER_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
