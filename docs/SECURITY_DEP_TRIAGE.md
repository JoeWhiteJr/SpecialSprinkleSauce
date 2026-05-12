# Dependency CVE Triage Runbook

**Last triage:** 2026-05-11
**Triggered by:** PR #36 (`chore/ci-dep-vuln-scan`) — pip-audit surfaced 63 CVEs across 12 backend packages.
**Outcome:** 37 CVEs resolved by version bumps; 26 deferred via allowlist (16 by 2026-06-10, 10 by 2026-05-25 via task #51).

---

## Decision matrix

| Package | From | To | Status | CVEs cleared | Notes |
|---|---|---|---|---|---|
| `fastapi` | 0.115.6 | 0.119.1 | bumped | 0 direct (enables starlette) | Stayed in 0.11x family. Code uses only stable APIs (`APIRouter`, `HTTPException`, `Query`, `Depends`, `CORSMiddleware`). |
| `starlette` | 0.41.3 | 0.48.0 | bumped (new explicit pin) | 1 (CVE-2025-54121) | Max allowed by fastapi 0.119.1 (`<0.49.0`). Last CVE blocked — see allowlist. |
| `python-dotenv` | 1.0.1 | 1.2.2 | bumped | 1 (CVE-2026-28684) | Patch bump, no API changes. |
| `python-multipart` | 0.0.18 | 0.0.27 | bumped | 3 (CVE-2026-40347, CVE-2026-42561, CVE-2026-24486) | Used internally by fastapi `UploadFile`; no direct imports in code. |
| `langgraph` | 0.2.0 | 0.2.0 | **allowlisted** | 0 (deferred) | Cluster moved together — see Category D. Bumping requires StateGraph + node-signature port. Tracked as task #51 (revisit 2026-05-25). |
| `langchain-core` | 0.2.43 | 0.2.43 | **allowlisted** | 0 (deferred) | Rides with langgraph cluster (task #51). |
| `langgraph-checkpoint` | 1.0.12 | 1.0.12 | **allowlisted** | 0 (deferred) | Rides with langgraph cluster (task #51). |
| `langsmith` | 0.1.147 | 0.1.147 | **allowlisted** | 0 (deferred) | Rides with langgraph cluster (task #51). |
| `mlflow` | 2.10.0 | 2.22.4 | bumped | ~19 of 35 | Stayed in 2.x per triage guidance (3.x is breaking). Used as tracking client only with graceful degradation in `src/intelligence/quant_models/mlflow_tracking.py`. |
| `gunicorn` | 21.2.0 | 22.0.0 | bumped (new explicit pin) | 2 (CVE-2024-6827, CVE-2024-1135) | Transitive of mlflow. |
| `protobuf` | 4.25.9 | 5.29.6 | bumped (new explicit pin) | 1 (CVE-2026-0994) | Transitive of mlflow. Major bump but well-supported. |
| `pyarrow` | 15.0.2 | 17.0.0 | bumped (new explicit pin) | 1 (PYSEC-2024-161) | Transitive of mlflow. |
| `transformers` | 4.57.6 | 4.57.6 | held | 0 | Fix is `5.0.0rc3` (RC, blocked by no-RC rule). See allowlist. |

**Total resolved by bumps: 37/63 (58.7%).** Remaining 26 allowlisted; see `.github/pip-audit-allowlist.txt`.

---

## Allowlist summary (26 entries — 16 revisit 2026-06-10, 10 revisit 2026-05-25)

### Category A — mlflow tracking-server CVEs (14 entries)

We use mlflow only as a **Python tracking client** (logging metrics, params, artifacts to a tracking URI). We do **not** run `mlflow server` or `mlflow ui` in production. All 14 deferred mlflow CVEs are server-side (path traversal, SSRF, RCE in the web app). Not exploitable in our threat model.

Fix path is mlflow 3.x (forbidden as a major bump per triage instructions) or unreleased RC versions (forbidden by no-RC rule).

### Category B — starlette 1 entry

`CVE-2025-62727` fix is in starlette 0.49.1, but fastapi 0.119.1 caps starlette at `<0.49.0`. Bumping fastapi to `>=0.124.0` would unblock; deferred to a separate scoped PR to keep this triage limited to dep bumps only.

### Category C — transformers 1 entry

`CVE-2026-1839` affects the HuggingFace `Trainer` class. We use sentence-transformers only for embeddings (`SentenceTransformerEmbeddingFunction` in `src/intelligence/wasden_watch/vector_store.py`) — no `Trainer` import anywhere. Fix is `5.0.0rc3` (RC). Hold until 5.0.0 GA.

### Category D — langgraph cluster 10 entries (deferred to task #51)

`langgraph` (1 CVE), `langchain-core` (6 CVEs), `langgraph-checkpoint` (2 CVEs), and `langsmith` (1 CVE) must move together. langgraph 0.2 → 1.0.10 changes the StateGraph API and node signatures, requiring code edits in `src/pipeline/decision_pipeline.py` and `src/pipeline/streaming_pipeline.py` plus verification that the 9 tests in `test_pipeline.py` and 4 in `test_pipeline_stream.py` still pass.

The current pipeline code does not yet import langgraph (despite the docstring naming) — but that's separate from the cluster bump, which we're treating as a coordinated port to avoid forcing a breaking-change pin without the migration. Tracked as task #51 in TODO.md.

**Why not bump anyway?** Even though the lib isn't imported today, pre-bumping forces whoever does the eventual integration to work from a major-version constraint without having read the upstream migration guide. Better to do the port deliberately as its own scoped PR.

---

## Revisit calendar

| Date | Action |
|---|---|
| 2026-05-25 | Task #51 deadline — langgraph cluster port (Category D) lands or deadline gets a documented extension. |
| 2026-06-10 | All Category A/B/C entries hit revisit-by. Re-run pip-audit and prune entries that have a stable fix path. |
| 2026-06-10 | Open follow-up PR: bump fastapi `>=0.124.0` to clear CVE-2025-62727. |
| When transformers 5.0.0 GA ships | Bump transformers, drop CVE-2026-1839 from allowlist. |
| When mlflow tracking-server CVEs see 2.x backports OR we choose to commit to a 3.x migration | Re-evaluate Category A. |

---

## Verification

Local reproduction of the CI gate:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install --upgrade pip pip-audit
# Build the same --ignore-vuln flags the CI does:
IGNORE_FLAGS=""
while IFS= read -r line; do
  entry="$(printf '%s\n' "$line" | sed -e 's/#.*$//' -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
  [ -n "$entry" ] && IGNORE_FLAGS="$IGNORE_FLAGS --ignore-vuln $entry"
done < ../.github/pip-audit-allowlist.txt
pip-audit -r requirements.txt --strict --vulnerability-service osv $IGNORE_FLAGS
```

Expected output: `No known vulnerabilities found, 26 ignored`.

---

## Follow-up tickets (suggested)

1. **Task #51 — Port pipeline code to LangGraph 1.x and bump deps** (HARD DEADLINE 2026-05-25).
   Read upstream migration guide → bump pins (langgraph 0.2 → 1.0.10, plus langchain-core, langgraph-checkpoint, langsmith) → update `src/pipeline/decision_pipeline.py` + `src/pipeline/streaming_pipeline.py` → confirm all 9 tests in `test_pipeline.py` + 4 in `test_pipeline_stream.py` still pass → confirm Wasden VETO short-circuit, 5-5 escalation, debate agreement paths all behave identically. Single dedicated PR.
2. **Bump fastapi to >=0.124.0** to clear remaining starlette CVE-2025-62727 (1-day effort, low risk).
3. **Decide on mlflow 2.x vs 3.x migration roadmap** — major version bump with API changes; 14 server CVEs deferred indefinitely otherwise.
4. **Re-run dep audit weekly** via Dependabot or scheduled workflow to catch new CVEs early.
