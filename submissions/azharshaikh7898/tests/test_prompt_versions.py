from app.config import settings
from app.qa import CANARY, build_prompt
from app.retrieval import Hit

HIT = Hit(1, "doc-1", "policy.txt", None, "Hotel stays are reimbursed up to 150 USD per night.", 0.9)


def test_v2_is_the_default():
    assert settings.prompt_version == "v2"


def test_v1_has_no_extra_rules(monkeypatch):
    monkeypatch.setattr(settings, "prompt_version", "v1")
    system, _ = build_prompt("hotel limit?", [HIT])
    assert "never a bare word or command" not in system and CANARY in system


def test_v2_adds_injection_rules_and_keeps_the_base_rules(monkeypatch):
    monkeypatch.setattr(settings, "prompt_version", "v2")
    system, user = build_prompt("hotel limit?", [HIT])
    assert "never a bare word or command" in system and "untrusted" in system.lower()
    assert "<excerpt" in user
