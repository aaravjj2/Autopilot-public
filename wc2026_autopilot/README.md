# FIFA World Cup 2026 Prediction Market Autopilot

A production-oriented Python autopilot that ingests free public soccer + market data, assembles structured context, routes to an available LLM brain (Groq/Gemini/OpenRouter/Ollama/Anthropic/shell), and outputs bet/no-bet recommendations with Kelly-based stake sizing.

## Setup

```bash
cd /home/aarav/Aarav/Autopilot/wc2026_autopilot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

The project auto-loads credentials from parent `/home/aarav/Aarav/Autopilot/keys.env` and `.env`, then local `.env`.

## Seed DB

```bash
PYTHONPATH=src python scripts/seed_db.py
```

Expected ranges:
- `wc_matches`: ~900
- `international_results`: 40,000+
- `fixtures_2026`: parser-dependent (openfootball source + fallback)

## Run tests

```bash
PYTHONPATH=src pytest tests/ -v --cov=src --cov-report=term-missing
```

To skip live API tests:

```bash
WC_SKIP_LIVE=1 PYTHONPATH=src pytest tests/ -v
```

## Dry run autopilot

```bash
PYTHONPATH=src python autopilot.py --bankroll 1000 --dry-run
```

## LLM routing

Set `WC_LLM_BRAIN=auto` (default):
1. Groq (`GROQ_API_KEY`)
2. Gemini (`GEMINI_API_KEY` or `GOOGLE_API_KEY`)
3. OpenRouter (`OPENROUTER_KEY`)
4. Ollama (`OLLAMA_HOST`, `OLLAMA_MODEL`)
5. Anthropic (`ANTHROPIC_API_KEY`)
6. Shell terminal brain (`WC_SHELL_BRAIN_CMD`)

Shell brain example:

```bash
export WC_LLM_BRAIN=shell
export WC_SHELL_BRAIN_CMD="ollama run llama3.2:3b"
```
