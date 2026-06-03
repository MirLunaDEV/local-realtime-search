from __future__ import annotations

from dataclasses import asdict, dataclass

from app.freshness import infer_freshness
from app.weather import looks_weather_question


@dataclass(frozen=True)
class AnswerStrategy:
    name: str
    use_web_search: bool
    use_weather_provider: bool
    must_cite: bool
    freshness: str | None
    preferred_sources: list[str]
    guidance: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def classify_answer_strategy(
    question: str,
    *,
    requested_freshness: str | None = None,
    direct_answer_label: str | None = None,
) -> AnswerStrategy:
    freshness = infer_freshness(question, requested_freshness)
    lowered = question.lower()

    if direct_answer_label is not None:
        return AnswerStrategy(
            name=direct_answer_label,
            use_web_search=False,
            use_weather_provider=False,
            must_cite=False,
            freshness=freshness,
            preferred_sources=["local_runtime_clock"],
            guidance="Answer directly from the local runtime value. Do not invent web citations.",
        )

    if looks_weather_question(question):
        return AnswerStrategy(
            name="weather",
            use_web_search=False,
            use_weather_provider=True,
            must_cite=True,
            freshness="day",
            preferred_sources=["weather_provider", "official", "government"],
            guidance="Use the weather provider evidence first. Mention the observed time and cite the weather source.",
        )

    if "benchmark" in lowered or "벤치마크" in question:
        return AnswerStrategy(
            name="benchmark",
            use_web_search=True,
            use_weather_provider=False,
            must_cite=True,
            freshness=freshness or "month",
            preferred_sources=["official", "github_primary", "documentation", "general_web"],
            guidance="Compare recent benchmark evidence across multiple sources and surface uncertainty.",
        )

    if any(term in lowered for term in ("compare", "vs", "versus", "alternative")) or any(
        term in question for term in ("비교", "대체", "차이")
    ):
        return AnswerStrategy(
            name="comparison",
            use_web_search=True,
            use_weather_provider=False,
            must_cite=True,
            freshness=freshness,
            preferred_sources=["official", "documentation", "github_primary", "release_notes"],
            guidance="Compare options with source-backed claims and call out tradeoffs.",
        )

    if any(term in lowered for term in ("docs", "documentation", "api", "release notes", "changelog")) or any(
        term in question for term in ("문서", "공식", "릴리즈", "변경")
    ):
        return AnswerStrategy(
            name="docs_lookup",
            use_web_search=True,
            use_weather_provider=False,
            must_cite=True,
            freshness=freshness,
            preferred_sources=["official", "documentation", "release_notes", "github_primary"],
            guidance="Prefer official documentation, release notes, and primary repositories.",
        )

    if freshness is not None:
        return AnswerStrategy(
            name="current_fact",
            use_web_search=True,
            use_weather_provider=False,
            must_cite=True,
            freshness=freshness,
            preferred_sources=["official", "government", "release_notes", "documentation"],
            guidance="Verify changing facts with current web evidence and cite the source IDs.",
        )

    return AnswerStrategy(
        name="general_research",
        use_web_search=True,
        use_weather_provider=False,
        must_cite=True,
        freshness=None,
        preferred_sources=["official", "documentation", "github_primary", "general_web"],
        guidance="Answer from the provided evidence only and cite source IDs for factual claims.",
    )
