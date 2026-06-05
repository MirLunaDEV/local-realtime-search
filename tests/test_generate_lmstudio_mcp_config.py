from pathlib import Path

from scripts.generate_lmstudio_mcp_config import build_config


def test_build_config_uses_explicit_paths_and_env() -> None:
    project_root = Path("C:/repo/local-realtime-search")
    config = build_config(
        project_root=project_root,
        uv_path="C:/Users/user/.local/bin/uv.exe",
        model="qwen-test",
        timezone="Asia/Seoul",
        searxng_base_url="http://127.0.0.1:8080",
    )

    server = config["mcpServers"]["local-realtime-search"]
    assert server["command"] == "C:/Users/user/.local/bin/uv.exe"
    assert server["cwd"] == str(project_root)
    assert server["env"]["LM_STUDIO_MODEL"] == "qwen-test"
    assert server["args"][-1] == "scripts/mcp_server.py"


def test_build_config_can_auto_start_backend() -> None:
    project_root = Path("C:/repo/local-realtime-search")
    config = build_config(
        project_root=project_root,
        uv_path="C:/Users/user/.local/bin/uv.exe",
        model="qwen-test",
        timezone="Asia/Seoul",
        searxng_base_url="http://127.0.0.1:8080",
        auto_start_backend=True,
        powershell_path="powershell.exe",
    )

    server = config["mcpServers"]["local-realtime-search"]
    assert server["command"] == "powershell.exe"
    assert server["args"][:4] == ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File"]
    assert "scripts/start_mcp_with_backend.ps1" in server["args"]
    assert "-Uv" in server["args"]
    assert "C:/Users/user/.local/bin/uv.exe" in server["args"]
