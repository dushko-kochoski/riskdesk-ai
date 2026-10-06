import json
from pathlib import Path


def test_vercel_routes_api_before_frontend_catch_all() -> None:
    repository_root = Path(__file__).parents[2]
    config = json.loads((repository_root / "vercel.json").read_text(encoding="utf-8"))

    assert config["services"]["backend"] == {
        "root": "backend/",
        "framework": "fastapi",
        "installCommand": "python -m pip install --require-hashes -r requirements.lock",
        "entrypoint": "main:app",
    }
    assert config["services"]["frontend"]["root"] == "frontend/"
    assert config["rewrites"] == [
        {"source": "/api", "destination": {"service": "backend"}},
        {"source": "/api/(.*)", "destination": {"service": "backend"}},
        {"source": "/(.*)", "destination": {"service": "frontend"}},
    ]
