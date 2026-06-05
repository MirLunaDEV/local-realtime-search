from __future__ import annotations

import json
import logging
import sys
from typing import Any


logger = logging.getLogger("local_realtime_search")


def configure_logging() -> None:
    for noisy_logger in ("httpx", "httpcore", "mcp", "mcp.server"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
    if logger.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def log_research_result(event: str, result: dict[str, Any]) -> None:
    configure_logging()
    timings = result.get("timings_ms") if isinstance(result.get("timings_ms"), dict) else {}
    strategy = result.get("answer_strategy") if isinstance(result.get("answer_strategy"), dict) else {}
    payload = {
        "event": event,
        "request_id": result.get("request_id"),
        "strategy": strategy.get("name"),
        "mode": result.get("mode"),
        "freshness": result.get("freshness"),
        "citation_count": len(result.get("citations", []) or []),
        "source_count": len(result.get("sources", []) or []),
        "warning_count": len(result.get("warnings", []) or []),
        "search_backend_status": (result.get("search_backend_status") or {}).get("status")
        if isinstance(result.get("search_backend_status"), dict)
        else None,
        "weather_provider_status": (result.get("weather_provider_status") or {}).get("status")
        if isinstance(result.get("weather_provider_status"), dict)
        else None,
        "total_ms": timings.get("total"),
    }
    logger.info(json.dumps(payload, ensure_ascii=False, sort_keys=True))
