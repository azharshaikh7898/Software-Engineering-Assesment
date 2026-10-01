# AI usage disclosure

**Tool:** Claude (Anthropic), used through the claude.ai chat interface. No autonomous coding agent was used. I ran
every command myself, in my own terminal, and pasted the outputs back.

**What Claude helped with**
- Proposing the architecture and stack (FastAPI, Postgres with pgvector, Redis with RQ, local embeddings,
  Caddy) and drafting `DESIGN.md`.
- Writing the first versions of the backend code, the tests, the Dockerfile and compose files, the static UI, the
  CI workflow, and the evaluation harness, question set and sample documents.
- Debugging problems I hit, for example a missing module, a port conflict, a retired model name on the LLM
  provider (404), and the model's full-width citation brackets being rejected by the citation check.
- Drafting `EVALUATION.md` from the numbers my runs produced, and the deployment steps.

**What I did myself**
- Created the fork, issues, branches and pull requests, ran the tests, builds and evaluation runs, and made the
  decision to adopt the stronger prompt after seeing the injection leak in my own results.
- Deployed the system and created the reviewer account.

**Where I verified Claude's output**
- All tests and linting pass in CI. The Docker stack was checked end to end with `scripts/smoke.sh` against real
  Postgres, Redis and the real LLM. The evaluation results in `eval/results/` are from real runs.

**Limits:** the evaluation set and documents were written with AI assistance, so they favour the system (see
EVALUATION.md, section 5).
