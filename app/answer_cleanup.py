from __future__ import annotations

from app.knowledge_prior import KnowledgePrior


_CACHE_SCALEOUT_TERMS = ("redis", "valkey", "opensearch", "elasticsearch")
_SCALEOUT_QUESTION_TERMS = ("scale", "scale-out", "distributed", "redis", "valkey", "opensearch", "elasticsearch")


def cleanup_answer_for_prior(answer: str, question: str, prior: KnowledgePrior | None) -> str:
    if prior is None or prior.label != "local_search_cache_strategy":
        return answer
    lowered_question = question.lower()
    if any(term in lowered_question for term in _SCALEOUT_QUESTION_TERMS):
        return answer

    cleaned_lines = []
    for line in answer.splitlines():
        lowered_line = line.lower()
        if any(term in lowered_line for term in _CACHE_SCALEOUT_TERMS):
            continue
        cleaned_lines.append(line)

    cleaned = "\n".join(cleaned_lines)
    while "\n\n\n" in cleaned:
        cleaned = cleaned.replace("\n\n\n", "\n\n")
    return cleaned.strip()
