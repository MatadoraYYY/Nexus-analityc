import hashlib
import json
from pathlib import Path

from nexus.generator import generate
from nexus.pipeline import build
from nexus.quality import validate


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_generation_is_deterministic(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    generate(first, users_count=80)
    generate(second, users_count=80)
    assert digest(first / "users.csv") == digest(second / "users.csv")
    assert digest(first / "events.csv") == digest(second / "events.csv")


def test_data_to_api_integration(tmp_path):
    data, api = tmp_path / "data", tmp_path / "api"
    generate(data, users_count=120)
    checks = validate(data)
    assert all(x.passed for x in checks if x.severity == "Critical")
    overview = build(data, api)
    assert overview["meta"]["synthetic"] is True
    assert json.loads((api / "health.json").read_text(encoding="utf-8"))["status"] == "работает"
