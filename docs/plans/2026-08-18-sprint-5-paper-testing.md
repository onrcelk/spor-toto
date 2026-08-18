# Sprint 5 — Daily Paper Testing & Evaluation Implementation Plan

> **For Hermes:** Use the Sport Toto orchestration workflow and strict TDD. Keep Hermes as the provider-neutral orchestrator; all probabilities and policy decisions remain deterministic project code.

**Goal:** Build a reproducible daily 15-match paper-test loop that freezes pre-match decisions, collects final results, audits the Decision Journal/H15 coupon, and reports calibrated metrics without changing the model during the observation window.

**Architecture:** Add a paper-test domain layer around the existing `sportoto_run`/Decision Journal path. A daily run writes an immutable run manifest and 15 match records; a result collector updates only post-match fields in a new versioned audit artifact; an evaluator aggregates match, coupon, H15-filter, calibration, market, and source-reliability metrics over configurable rolling windows. Existing prediction, risk, coupon, and MCP contracts remain unchanged.

**Tech Stack:** Python 3.10+, dataclasses/JSONL, existing Sport Toto workflow, pytest, deterministic calibration metrics.

---

## Acceptance criteria

- A daily run requires exactly 15 unique fixtures in official order and writes a frozen run manifest.
- Each match record preserves raw, calibrated, ensemble, risk, decision, evidence IDs, option set, banko state, and provenance.
- Empty `evidence_ids` is represented as an explicit coverage state (`none`/`partial`/`confirmed`), never treated as successful research.
- Final-result collection is idempotent, distinguishes `final_verified`, `live`, `not_started`, `postponed`, and `unknown`, and never audits unresolved matches as misses.
- Match audit records include actual, hit/miss, and a deterministic error type.
- H15 audit separately reports option-set coverage, banko hit, double hit, triple hit, scenario coverage, and filter survival; a coverage failure can eliminate all columns.
- Brier and log-loss use the calibrated probabilities and only final verified results.
- Rolling reports support 5/10/20/30 completed days/weeks and expose sample size/coverage.
- Market comparison and source reliability are descriptive first; no weight/model change is made in Sprint 5.
- Full tests and `git diff --check` pass before the sprint is declared complete.

## Data contracts

### Daily run manifest

`data/paper/runs/<run_id>.json`

```json
{
  "schema_version": "1.0",
  "run_id": "2026-08-18",
  "run_type": "daily_paper_test",
  "created_at": "...",
  "official_order": ["M01", "...", "M15"],
  "prediction_artifact": "...",
  "journal_path": "...",
  "evidence_coverage": {"confirmed": 0, "partial": 0, "none": 15},
  "status": "frozen_pre_match"
}
```

### Match audit record

`data/paper/audits/<run_id>.jsonl`

Required fields: `run_id`, `match_id`, `match_index`, fixture identity, `prediction.raw`, `prediction.calibrated`, `ensemble`, `risk`, `decision`, `coupon.option_set`, `coupon.banko`, `research.evidence_ids`, `research.evidence_coverage`, `actual`, `result_status`, `hit`, `error_type`, `audited_at`, and source provenance.

Allowed error types: `wrong_direction`, `missed_draw`, `missed_upset`, `coverage_failure`, `banko_miss`, `overconfidence`, `data_quality_error`, `pending`, `postponed`.

## Tasks

### Task 1: Freeze a validated daily run

**Files:**
- Create: `src/sportoto/paper_testing.py`
- Create: `tests/test_paper_testing.py`

Write failing tests first for exact 15-fixture validation, unique match IDs, official ordering, and an immutable run manifest. Implement the smallest `freeze_daily_run(...)` API that calls the existing workflow result and stores a manifest without rewriting generated journal JSONL.

Run:
```bash
uv run pytest tests/test_paper_testing.py -q
```

### Task 2: Normalize evidence coverage

**Files:**
- Modify: `src/sportoto/journal_finalizer.py`
- Modify: `src/sportoto/research_orchestration.py`
- Test: `tests/test_journal_finalizer.py`, `tests/test_research_orchestration.py`

Add an explicit coverage classification derived from evidence IDs and validated evidence (`none`, `partial`, `confirmed`). Preserve `evidence_ids: []` for compatibility, but expose the classification in the journal. Test that an empty list is not silently interpreted as successful research and that unverified/one-source evidence cannot enable banko.

### Task 3: Add deterministic result ingestion and post-match audit

**Files:**
- Modify: `src/sportoto/paper_testing.py`
- Create: `tests/test_paper_result_audit.py`

Implement `audit_final_results(...)` over normalized final-result rows. Require explicit final status or an injected final-verification contract; keep pending/postponed rows out of accuracy denominators. Make repeated ingestion produce the same audit output and preserve the frozen pre-match record.

### Task 4: Audit H15 coverage and filter survival

**Files:**
- Modify: `src/sportoto/h15.py` only if a reusable helper is missing
- Modify: `src/sportoto/paper_testing.py`
- Create: `tests/test_paper_h15_audit.py`

Compute option-set coverage, banko/double/triple hit, filtered-scenario survival, filter rejection reason, and first-elimination match. Use actual column intersection, not per-match coverage counts. Add regression tests for the known failure mode where one missing result eliminates all columns.

### Task 5: Add calibration and rolling aggregate reports

**Files:**
- Create: `src/sportoto/paper_evaluation.py`
- Create: `tests/test_paper_evaluation.py`

Aggregate only final verified rows. Report sample sizes, accuracy, banko accuracy, coverage accuracy, Brier, log-loss, confusion matrix, error-type counts, H15 coverage, filter survival, and rolling windows of 5/10/20/30 runs. Reject malformed probability vectors and never calculate a metric from missing actuals.

### Task 6: Add market and source-reliability descriptive benchmarks

**Files:**
- Modify: `src/sportoto/paper_evaluation.py`
- Create: `tests/test_paper_benchmarks.py`

Compare calibrated ensemble probabilities with available vig-removed market probabilities and calculate descriptive hit/Brier/log-loss slices by market availability and source coverage. Track source-level verified hit/Brier/log-loss only after minimum sample thresholds. Do not alter ensemble weights.

### Task 7: Wire CLI commands and safe artifact paths

**Files:**
- Modify: `src/sportoto/cli.py`
- Create: `tests/test_paper_cli.py`
- Modify: `README.md`

Add read-only/reporting commands with explicit paths, for example:

```text
sportoto paper-run --fixtures ... --predictions ... --journal ... --run-id ...
sportoto paper-audit --run ... --results ...
sportoto paper-report --runs-dir data/paper/runs --audits-dir data/paper/audits --windows 5,10,20,30
```

Generated paper data remains outside source commits unless explicitly requested. Commands must print output paths and verified counts.

### Task 8: End-to-end Sprint 5 checkpoint

**Files:**
- Create: `tests/test_paper_e2e.py`
- Modify: `docs/` only for final usage notes

Run one deterministic 15-match fixture/prediction/result fixture through freeze → audit → H15 audit → report. Verify journal evidence coverage, result-status handling, metric denominators, and idempotence. Then run:

```bash
uv run pytest -q
git diff --check
git status --short
```

Do not commit generated weekly JSONL or raw provider dumps. Commit only scoped source/tests/docs after the existing uncommitted E2E artifacts are reviewed separately.

## Explicit non-goals for Sprint 5

- No model retraining.
- No ensemble-weight optimization.
- No new provider integration unless required to satisfy the existing normalized result/evidence contract.
- No automatic betting, publishing, or external write-back.
- No claim that paper-test performance implies profitability; report profitability only as a later, separately verified analysis.

## Checkpoint policy

At each daily run, freeze the prediction/journal before kickoff. After results are final, append a post-match audit artifact and generate a report. Do not revise the frozen coupon or retroactively replace `main_option_sets` with `main_line`. Revisit model/config only after the agreed 30–60 day observation window and a documented rolling evaluation.
