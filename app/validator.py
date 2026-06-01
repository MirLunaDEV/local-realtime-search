from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from app.evidence import EvidenceChunk
from app.knowledge_prior import KnowledgePrior
from app.source_policy import classify_source


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    severity: str = "warning"


@dataclass(frozen=True)
class ValidationReport:
    ok: bool
    issues: list[ValidationIssue]
    cited_ids: list[int]
    missing_citation_ids: list[int]

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "issues": [asdict(issue) for issue in self.issues],
            "cited_ids": self.cited_ids,
            "missing_citation_ids": self.missing_citation_ids,
        }


_CITATION_RE = re.compile(r"\[(\d+)\]")
_LOCAL_STACK_REQUIRED = ("lm studio", "searxng", "crawl4ai")
_LOCAL_STACK_DRIFT = ("opencode", "hermes", "fastcrw", "anythingllm", "n8n")
_CACHE_REQUIRED = ("sqlite", "cache")
_CACHE_DRIFT = ("redis", "valkey", "opensearch", "elasticsearch")
_CITATION_QUALITY_REQUIRED = ("citation", "evidence")


def _citation_ids(answer: str) -> list[int]:
    ids: list[int] = []
    seen: set[int] = set()
    for match in _CITATION_RE.finditer(answer):
        value = int(match.group(1))
        if value not in seen:
            ids.append(value)
            seen.add(value)
    return ids


def validate_answer(answer: str, evidence: list[EvidenceChunk], prior: KnowledgePrior | None) -> ValidationReport:
    issues: list[ValidationIssue] = []
    evidence_by_id = {chunk.id: chunk for chunk in evidence}
    cited_ids = _citation_ids(answer)
    missing_ids = [citation_id for citation_id in cited_ids if citation_id not in evidence_by_id]

    if missing_ids:
        issues.append(
            ValidationIssue(
                code="missing_citation_ids",
                message=f"Answer cites IDs that are not present in evidence: {missing_ids}",
                severity="error",
            )
        )

    for citation_id in cited_ids:
        chunk = evidence_by_id.get(citation_id)
        if chunk is None:
            continue
        policy = classify_source(chunk.url, chunk.title)
        if policy.is_weak or policy.label == "commentary":
            issues.append(
                ValidationIssue(
                    code="weak_citation",
                    message=f"Answer cites weak/commentary source [{citation_id}]: {chunk.url}",
                    severity="warning",
                )
            )

    if prior and prior.label == "local_lm_studio_search_stack":
        lowered = answer.lower()
        missing_required = [term for term in _LOCAL_STACK_REQUIRED if term not in lowered]
        if missing_required:
            issues.append(
                ValidationIssue(
                    code="prior_required_terms_missing",
                    message=f"Answer omitted core stack components: {missing_required}",
                    severity="warning",
                )
            )
        drift_terms = [term for term in _LOCAL_STACK_DRIFT if term in lowered]
        if drift_terms:
            issues.append(
                ValidationIssue(
                    code="prior_drift_terms",
                    message=f"Answer mentions non-core stack terms that need strong evidence: {drift_terms}",
                    severity="warning",
                )
            )

    if prior and prior.label == "searxng_json_api":
        lowered = answer.lower()
        if "default_format" in lowered:
            issues.append(
                ValidationIssue(
                    code="unsupported_searxng_default_format",
                    message=(
                        "Answer mentions default_format for SearXNG JSON output. "
                        "Prefer search.formats plus format=json unless primary docs prove otherwise."
                    ),
                    severity="warning",
                )
            )
        if "format=json" not in lowered:
            issues.append(
                ValidationIssue(
                    code="searxng_format_json_missing",
                    message="Answer should mention requesting JSON with format=json.",
                    severity="warning",
                )
            )

    if prior and prior.label == "local_search_cache_strategy":
        lowered = answer.lower()
        missing_required = [term for term in _CACHE_REQUIRED if term not in lowered]
        if missing_required:
            issues.append(
                ValidationIssue(
                    code="cache_required_terms_missing",
                    message=f"Answer omitted local cache strategy terms: {missing_required}",
                    severity="warning",
                )
            )
        drift_terms = [term for term in _CACHE_DRIFT if term in lowered]
        if drift_terms:
            issues.append(
                ValidationIssue(
                    code="cache_scaleout_terms",
                    message=(
                        "Answer mentions scale-out cache/search systems that should not be core defaults "
                        f"without explicit user need: {drift_terms}"
                    ),
                    severity="warning",
                )
            )

    if prior and prior.label == "local_citation_quality":
        lowered = answer.lower()
        missing_required = [term for term in _CITATION_QUALITY_REQUIRED if term not in lowered]
        if missing_required:
            issues.append(
                ValidationIssue(
                    code="citation_quality_required_terms_missing",
                    message=f"Answer omitted citation quality terms: {missing_required}",
                    severity="warning",
                )
            )
        if "weak" not in lowered and "primary" not in lowered and "official" not in lowered:
            issues.append(
                ValidationIssue(
                    code="citation_source_quality_missing",
                    message="Answer should mention weak-source filtering or preference for primary/official sources.",
                    severity="warning",
                )
            )

    ok = not any(issue.severity == "error" for issue in issues)
    return ValidationReport(ok=ok, issues=issues, cited_ids=cited_ids, missing_citation_ids=missing_ids)
