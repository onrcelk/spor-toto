# GitHub Soccer Repository Review — 2026-08-17

## Scope

60 public GitHub repository URL was scanned. 51 README files were retrievable; 9 had no directly retrievable README. Twelve high-signal candidates were cloned and inspected at code/data level.

## Adoptable ideas

### P0 — market probability and value layer

Sources: `gmalbert/mls-predictions`, `EfeBuyukarslan/Betting-Odds-Analysis-and-Soccer-Match-Outcome-Prediction`.

Adopt:
- decimal/American odds normalization where applicable;
- implied probability and overround removal;
- model probability vs market probability edge;
- EV output only when odds and model probability are observed and timestamped;
- closing-line comparison for post-match calibration.

Do not call positive EV a winning bet; require out-of-sample backtest and calibration.

### P0 — Dixon–Coles and Bayesian score distribution

Sources: `gmalbert/mls-predictions`, `BrianMuigai/Poisson-and-ML-in-Soccer`, `akmt14/soccer-score-prediction-using-bayesian-methods`.

Adopt:
- joint correct-score matrix from home/away expected goals;
- Dixon–Coles low-score correction;
- Over/Under, BTTS, 1/X/2 all derived from the same score posterior;
- fitted rho only with enough historical rows; otherwise documented default.

### P0 — calibration and self-audit

Sources: `SuFame920/WorldCup-Analysis-Skill`, `rvdmaazen/FiveThirtyEight-Soccer-Predictions`.

Adopt:
- Brier score and log-loss;
- reliability/calibration bins;
- confusion matrix and sample-size reporting;
- probability history written before kickoff and settled only after final result;
- market probability kept separate from model probability.

The WorldCup skill's explicit evidence → bounded adjustment → posterior structure is useful, but its causal language is not proof of causality and must remain a documented hypothesis.

### P1 — xG/event model enrichment

Source: `oishiqnd/Prediction-of-Expected-Goals-using-Event-Data-in-Soccer` plus existing StatsBomb parser.

Adopt:
- shot-level feature schema: distance, angle, body part, technique, assist type, counter-attack context when present;
- model xG as a separate experiment from provider-native xG;
- evaluate calibration, not only classification accuracy.

Keep provider-native xG and model-produced xG in separate fields.

### P1 — data lake and provenance

Source: `Danello1224/Football-Soccer-Data-Engineering-Project`.

Adopt conceptually:
- Bronze: raw API/web payload;
- Silver: normalized Parquet/JSONL records;
- Gold: feature tables, predictions, audits;
- source URL, fixture ID, observed_at, provider, freshness, hash, and schema version.

AWS is unnecessary for the personal project; local Parquet/JSONL is enough.

### P1 — structured evidence and analyst report

Sources: `Abdullah-568/Soccer-Match-Intelligence-Analyzer`, `jpschew/soccer-analysis-system`, `SuFame920/WorldCup-Analysis-Skill`.

Adopt:
- typed evidence records;
- separate data collection from synthesis;
- form, squad availability, tactical matchup, motivation, odds and advanced metrics as separate channels;
- LLM only for structured narrative/reporting, never as the numerical probability engine;
- confirmation vs expected lineup/news state kept separate.

### P2 — availability and injury features

Source: `zacfrappier/SoccerMon-Injury-Prediction`.

Adopt only the feature-design discipline:
- player availability state;
- position/role importance;
- days since injury/return;
- uncertainty flag.

Do not import the deep survival model or treat injury predictions as match facts. Current project state is initialization/roadmap, not a validated injury model.

### P2 — rest and context features

Source: `gmalbert/mls-predictions`.

Adopt generic features:
- rest days;
- midweek match load;
- travel only when reliable coordinates and schedule data exist;
- competition/context flag.

Do not import MLS-specific turf, conference, salary-cap, or designated-player features into Spor Toto.

### P3 — team-name normalization and historical rating

Sources: `rvdmaazen/FiveThirtyEight-Soccer-Predictions`, `vishant-mehta/ProSoccerPredictor`, `brxyxnn/European_Soccer_Analysis`.

Adopt:
- canonical team identity table;
- alias handling across TFF/API-Sports/football-data/Open Football;
- ELO update strictly before each target match;
- league/season strength adjustment.

This is high value because the current form report exposed exact-name coverage gaps.

## Useful but not immediate

- `Pringleman83/SportsBook`: source ingestion/sports data scraping ideas; no direct production code reuse.
- `Mutie886/Soccer-Results-Dataset-Builder-for-Total-Goals-Prediction`: dataset-builder/dashboard UX ideas.
- `masonwong2355/SoccerAnalysisAndPrediction`, `benwong9832/SoccerAnalysisAndPrediction`, `Abhi0010/ProSoccerPredictor`: UI/presentation inspiration only.
- `c830g420/FIFA18-Dataset-Analysis`, `obolinyte/european-soccer-match-analysis`, `rajbhuwan1510/SoccerDataAnalysis`, `DiogoAzevedoSilva/european-soccer-analysis`: historical EDA/model comparison ideas, mostly old datasets.
- `Dowon-Kim-0514/Soccer-transfer-market-analysis`, `Bilaal789/transfer-fee-project`, `mcossu28/Soccer-Player-Value-Analysis-`, `turhankilicci/FORESEEING-EURO-VALUES-OF-SOCCER-PLAYERS-BY-REGRESSION-MODELS`: transfer/player value research, not direct match prediction inputs yet.
- `storieswithsiva/Twitter-Data-Analysis`, `a-darsh/Soccer-Predictor`: sentiment/social signals remain weak, delayed, and vulnerable to leakage; keep as risk context only.

## Do not integrate as production logic

- `harshkava/PES-Player-analysis-using-Deep-learning`: PES ratings are not real match-performance data.
- `urdof7/penalty-kick-prediction`, `wsulais/PenaltyOracle`: shootout/penalty behavior is not ordinary 1/X/2 or Alt/Üst signal.
- Generic old notebooks and tutorial repos without leakage-safe temporal validation.
- Scrapers that rely on undocumented endpoints, bypassing protections, or unverified data licenses.
- Deep learning models without enough current, provider-consistent event data.

## Recommended implementation order

1. Market odds normalization, no-vig probabilities, EV and closing-line audit.
2. Dixon–Coles score posterior derived from xG.
3. Calibration report: Brier, log-loss, reliability, sample size.
4. Team identity/alias layer to repair current form coverage.
5. Structured evidence records and LLM narrative layer.
6. Availability/injury weighting with explicit uncertainty.
7. Dashboard only after the audit outputs are stable.

## Decision

Do not merge external repositories wholesale. Take small, testable, licensed ideas into the existing `/root/sportoto` pipeline. The current system already has multi-source adapters, StatsBomb event parsing, leakage-safe rolling xG/ELO features, Hedef15 handling, and post-match audit; the highest-value missing layer is calibrated market/value analysis plus Dixon–Coles score probabilities.
