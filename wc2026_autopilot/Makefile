.PHONY: test test-quick

test:
	PYTHONPATH=src pytest tests/ -v --cov=src --cov-report=term-missing --cov-fail-under=90

test-quick:
	WC_SKIP_LIVE=1 PYTHONPATH=src pytest tests/ -q --cov=src --cov-report=term-missing --cov-fail-under=90
