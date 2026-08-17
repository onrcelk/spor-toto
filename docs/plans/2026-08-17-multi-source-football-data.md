# Çoklu Kaynak Futbol Veri Sistemi Uygulama Planı

> **For Hermes:** Implement task-by-task with strict TDD.

**Goal:** API-Sports, football-data.org ve Open Football kaynaklarını ortak, denetlenebilir maç verisi şemasında birleştirmek.

**Architecture:** Her kaynak ayrı bir read-only adapter olarak çalışacak. Adapter çıktıları ortak `MatchRecord` şemasına normalize edilecek; kaynak adı, çekim zamanı, durum ve ham veri özeti korunacak. API anahtarları yalnızca `.env` üzerinden okunacak; Open Football ham GitHub JSON dosyaları anahtarsız kullanılacak.

**Tech Stack:** Python 3.10+, stdlib `urllib`, dataclasses, JSONL, pytest, mevcut CLI.

---

### Task 1: Define normalized source records

**Files:**
- Create: `src/sportoto/multi_source.py`
- Test: `tests/test_multi_source.py`

Define immutable normalized records for matches and source fetch reports. Required behavior: normalize `1/X/2`, total goals, Alt/Üst 2.5, and preserve `source`, `source_match_id`, `fetched_at`, `status`.

### Task 2: Add API-Sports adapter

**Files:**
- Modify: `src/sportoto/multi_source.py`
- Test: `tests/test_multi_source.py`

Read `API_SPORTS_KEY` and `API_SPORTS_BASE_URL` from environment or explicit dependency. Support fixture date query and normalize fixture response. Never print or persist the token.

### Task 3: Add football-data.org adapter

**Files:**
- Modify: `src/sportoto/multi_source.py`
- Test: `tests/test_multi_source.py`

Use `X-Auth-Token` and `/v4/matches`. Normalize finished and scheduled matches. Missing scores remain null rather than becoming zero.

### Task 4: Add Open Football JSON adapter

**Files:**
- Modify: `src/sportoto/multi_source.py`
- Test: `tests/test_multi_source.py`

Accept a local JSON payload or URL and normalize `team1/team2`, `score.ht`, and `score.ft`. Support malformed/missing score fields explicitly.

### Task 5: Add CLI source refresh command

**Files:**
- Modify: `src/sportoto/cli.py`
- Test: `tests/test_cli.py`

Add a read-only `refresh-sources` command that accepts date and optional Open Football URL, calls configured adapters, writes a JSON report under `data/live/multi_source/`, and exits non-zero only when every requested source fails.

### Task 6: Verify with real APIs and repository checks

Run:
- `pytest tests/test_multi_source.py tests/test_cli.py -q`
- `pytest -q`
- `ruff check src tests`
- Real API calls with `.env` loaded, reporting counts and source errors without secrets.
- `git diff --check` and push only non-secret files.

Acceptance criteria:
- Unit tests cover success, missing token, HTTP error, malformed score, and source disagreement inputs.
- Real API calls prove API-Sports and football-data.org are reachable.
- Open Football sample URL parses successfully.
- No `.env` or token appears in tracked files or command output.
