# FIFA World Cup 2026 — External Repos & What APEX Adopted

APEX integrates **patterns and data URLs** from these open-source projects. We do **not** vendor full trees into `external/`; ingestion pulls raw files at runtime or ships small bundled JSON under `data/world_cup/`.

| Repository | Role | What APEX adopted |
|------------|------|-------------------|
| [jfjelstul/worldcup](https://github.com/jfjelstul/worldcup) | Historical WC CSVs (1930–2022) | Raw CSV URLs in `wc2026_autopilot/src/ingestion/worldcup_history.py`; normalized rows into SQLite `wc_matches` |
| [martj42/international-results](https://github.com/martj42/international-results) | International friendlies & qualifiers | `results.csv` URL fallback chain; `international_results` table for form/H2H features |
| [openfootball/worldcup](https://github.com/openfootball/worldcup) | Text/JSON fixture schedules | `2026/worldcup.txt` and supplement JSON in `wc2026_fixtures.py`; synthetic 104-match fallback when parse fails |
| [zvizdo/fifa-wc-2026-simulation](https://github.com/zvizdo/fifa-wc-2026-simulation) | Poisson regression + Dixon-Coles tournament sim | **Formulas only** in `src/apex/ml/wc_poisson.py` (score grid, ρ adjustment, outcome aggregation). No Streamlit/DuckDB/Optuna code copied |
| ESPN site API | Live scores/news (undocumented) | Endpoints in `wc2026_autopilot/src/ingestion/espn_scraper.py`; 5-minute TTL cache |
| football-data.org | Optional WC API | Optional module `football_data_org.py`; skipped when `FOOTBALL_DATA_API_KEY` unset |

## APEX core (`src/apex`)

- **Elo v1** — `world_cup_model.py` + `data/world_cup/elo_ratings_2026.json` (bundled prep ratings).
- **Poisson v1** — `wc_poisson.py`, gated by `WORLD_CUP_USE_POISSON=false` (default). When enabled, `match_winner` contracts use Dixon-Coles over Elo-derived λ.
- **Discovery** — `integrations/world_cup_markets.py` + Kalshi/Polymarket public read APIs (no repo vendoring).

## wc2026_autopilot subproject

Standalone agent loop (`wc2026_autopilot/`) uses the ingestion/features above. `features/simulation_features.py` optionally imports `apex.ml.wc_poisson.team_lambda_features` when the parent `src/` package is on `PYTHONPATH`.

## Prediction market repos (execution & calibration)

| Repository | Role | What APEX adopted |
|------------|------|-------------------|
| [erickdronski/kalshi-polymarket-trader](https://github.com/erickdronski/kalshi-polymarket-trader) | ML sports → Kalshi execution | `prediction_tiers.py`: HIGH/MID/LOW confidence gates, EV-Kelly stake sizing in `world_cup_trading.py` |
| [suislanchez/polymarket-kalshi-weather-bot](https://github.com/suislanchez/polymarket-kalshi-weather-bot) | Kelly + calibration dashboard | Kelly cap via `settings.kelly_alpha`; reference only for series-ticker discovery |
| [ImMike/polymarket-arbitrage](https://github.com/ImMike/polymarket-arbitrage) | Cross-venue arb | Existing `arb_engine.py` / risk kill-switch; no code vendored |
| [Jon-Becker/prediction-market-analysis](https://github.com/Jon-Becker/prediction-market-analysis) | Historical PM trade data | Future calibration corpus; document in backtest plans |
| [aarora4/Awesome-Prediction-Market-Tools](https://github.com/aarora4/Awesome-Prediction-Market-Tools) | Curated tool list | Operator reading list only |

## Monte Carlo tournament API

- `src/apex/ml/wc_tournament_sim.py` — lightweight group+knockout MC (default 1k sims, cap 10k via API).
- `GET /api/world-cup/simulation?n=1000` — read-only; `model_version=wc_montecarlo_v1`.

## Enable Poisson scoring

```bash
WORLD_CUP_USE_POISSON=true
```

## Explicit non-goals

- No copy of zvizdo’s trained `expanded_model.pkl`, Optuna pipelines, or 100k-sim DuckDB artifacts.
- No git submodule of jfjelstul or openfootball — only pinned raw URLs and tests against downloaded samples in CI where marked `@pytest.mark.slow`.
- No live-money execution from third-party trader bots — **paper only** (M01).
