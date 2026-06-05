from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def build_config(
    *,
    project_root: Path,
    uv_path: str,
    model: str,
    timezone: str,
    searxng_base_url: str,
    auto_start_backend: bool = False,
    powershell_path: str = "powershell.exe",
) -> dict[str, object]:
    command = uv_path
    args = [
        "run",
        "--extra",
        "mcp",
        "python",
        "scripts/mcp_server.py",
    ]
    if auto_start_backend:
        command = powershell_path
        args = [
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "scripts/start_mcp_with_backend.ps1",
            "-Uv",
            uv_path,
        ]

    return {
        "mcpServers": {
            "local-realtime-search": {
                "command": command,
                "args": args,
                "cwd": str(project_root),
                "env": {
                    "LOCAL_TIMEZONE": timezone,
                    "LM_STUDIO_MODEL": model,
                    "SEARXNG_BASE_URL": searxng_base_url,
                },
            }
        }
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Print an LM Studio mcp.json config for this checkout.")
    parser.add_argument("--model", default="your-loaded-lm-studio-model-id")
    parser.add_argument("--timezone", default="Asia/Seoul")
    parser.add_argument("--searxng-base-url", default="http://127.0.0.1:8080")
    parser.add_argument(
        "--auto-start-backend",
        action="store_true",
        help="Generate a Windows config that starts Docker/SearXNG before launching the MCP server.",
    )
    parser.add_argument("--powershell-path", default=shutil.which("powershell.exe") or "powershell.exe")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    uv_path = shutil.which("uv") or "uv"
    config = build_config(
        project_root=project_root,
        uv_path=uv_path,
        model=args.model,
        timezone=args.timezone,
        searxng_base_url=args.searxng_base_url,
        auto_start_backend=args.auto_start_backend,
        powershell_path=args.powershell_path,
    )
    print(json.dumps(config, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
