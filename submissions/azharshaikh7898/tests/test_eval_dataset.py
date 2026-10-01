import json
import re
from pathlib import Path

from eval.run_eval import norm

EVAL = Path(__file__).resolve().parent.parent / "eval"
QUESTIONS = json.loads((EVAL / "questions.json").read_text(encoding="utf-8"))


def doc_text(name: str) -> str:
    return norm((EVAL / "docs" / name).read_text(encoding="utf-8"))


def test_dataset_shape():
    assert len(QUESTIONS) >= 15
    assert sum(1 for q in QUESTIONS if not q["answerable"]) >= 5
    assert len({q["id"] for q in QUESTIONS}) == len(QUESTIONS)


def test_every_evidence_phrase_exists_in_its_source_documents():
    for q in QUESTIONS:
        if q["answerable"]:
            texts = [doc_text(name) for name in q["sources"]]
            assert any(norm(q["evidence"]) in t for t in texts), q["id"]


def test_answer_patterns_are_valid_and_match_the_evidence():
    for q in QUESTIONS:
        if q["answerable"]:
            assert q["answer_contains"], q["id"]
            for pattern in q["answer_contains"]:
                assert re.search(pattern, norm(q["evidence"]), re.I), (q["id"], pattern)
