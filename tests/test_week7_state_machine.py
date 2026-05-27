from apex.execution.state_machine import ArbExecutionStateMachine
from apex.execution.scratch import submit_scratch_close


def test_state_machine_happy_path():
    sm = ArbExecutionStateMachine("arb-1")
    ctx = sm.run_paper_flow(
        leg1_fill=lambda: "k1",
        leg2_fill=lambda: "p1",
    )
    assert ctx.state == "fully_hedged"
    assert len(ctx.history) >= 4


def test_state_machine_mev_fallback():
    sm = ArbExecutionStateMachine("arb-2")
    ctx = sm.run_paper_flow(leg1_fill=lambda: "k", leg2_fill=lambda: "p", simulate_mev=True)
    assert ctx.state == "tradfi_hedge_filled"


def test_scratch():
    r = submit_scratch_close("KX-TEST")
    assert r["status"] == "paper_scratch"
