from apex.agents.consensus_engine import ConsensusEngine
from apex.agents.personas import PERSONAS


def test_six_personas():
    assert len(PERSONAS) == 6


def test_consensus_approves_good_edge():
    r = ConsensusEngine().evaluate(
        {"net_edge": 0.06, "settlement_match_score": 0.8}
    )
    assert r.approved
    assert len(r.votes) == 6
