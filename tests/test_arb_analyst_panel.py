from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest
from apex.core.config import Settings
from apex.domain.models import ArbOpportunity, ArbThesis
from apex.layers.l2.arb_analyst_panel import ArbAnalystPanel

@pytest.fixture
def mock_opp():
    return ArbOpportunity(
        id="test-123",
        kalshi_ticker="K-TEST",
        poly_market_id="P-TEST",
        question="Will this test pass?",
        kalshi_title="Test Pass",
        poly_title="Test Pass",
        kalshi_yes_ask=0.4,
        poly_no_ask=0.5,
        gross_spread=0.1,
        net_edge=0.08,
        settlement_match_score=0.9,
        settlement_flags=[],
        volume_kalshi=1000.0,
        volume_poly=2000.0,
    )

def test_arb_analyst_panel_evaluate(mock_opp):
    settings = Settings()
    
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_message = MagicMock()
    mock_message.content = json.dumps({
        "settlement_verdict": "SAFE",
        "divergence_reason": "Test reason",
        "net_edge_estimate": 0.08,
        "bear_case": "Test bear",
        "one_liner": "Test summary"
    })
    mock_response.choices = [MagicMock(message=mock_message)]
    mock_client.chat.completions.create.return_value = mock_response
    
    with patch.object(Settings, "get_llm_client", return_value=mock_client), \
         patch("apex.repositories.sqlite_store.SQLiteStore") as mock_store:
        
        mock_store_inst = mock_store.return_value
        mock_store_inst.get_resolved_arb_opportunities.return_value = []
        
        panel = ArbAnalystPanel(settings)
        thesis = asyncio.run(panel.evaluate(mock_opp))
        
        assert isinstance(thesis, ArbThesis)
        assert thesis.settlement_verdict == "SAFE"
        assert thesis.divergence_reason == "Test reason"
        assert thesis.net_edge_estimate == 0.08
        
        # 3 from phase 1 + 2 from phase 2
        assert mock_client.chat.completions.create.call_count == 5
