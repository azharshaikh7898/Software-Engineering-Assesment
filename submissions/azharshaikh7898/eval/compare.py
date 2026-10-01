"""Markdown comparison table of evaluation runs.

    python -m eval.compare eval/results/baseline.json eval/results/chunk400.json
"""
import json
import sys
from pathlib import Path


def pct(m: dict) -> str:
    return "n/a" if not m["n"] else f"{m['k']}/{m['n']} ({100 * m['k'] / m['n']:.0f}%)"


def main():
    runs = [json.loads(Path(p).read_text(encoding="utf-8")) for p in sys.argv[1:]]
    if not runs:
        sys.exit(__doc__)
    lines = ["| Metric | " + " | ".join(r["config"]["name"] for r in runs) + " |",
             "|---|" + "---|" * len(runs)]
    for label, key in (("Chunk size", "chunk_size"), ("Chunk overlap", "chunk_overlap"), ("Top-k", "top_k"),
                       ("Min score", "min_score"), ("Chunks indexed", "chunks")):
        lines.append(f"| {label} | " + " | ".join(str(r["config"][key]) for r in runs) + " |")
    for label, key in (("Retrieval hit rate", "retrieval_hit"), ("Answer correctness", "answer_correct"),
                       ("Citation accuracy", "citation_ok"), ("False refusals", "false_refusal"),
                       ("Correct refusals", "correct_refusal")):
        lines.append(f"| {label} | " + " | ".join(pct(r["metrics"][key]) for r in runs) + " |")
    for label, key in (("Injection leaks", "injection_leaks"), ("Avg latency (ms)", "avg_latency_ms"),
                       ("Avg tokens", "avg_tokens"), ("LLM errors", "errors")):
        lines.append(f"| {label} | " + " | ".join(str(r["metrics"][key]) for r in runs) + " |")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
