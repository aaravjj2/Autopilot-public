"""Build runtime prompt from assembled context."""

from __future__ import annotations


def build_prompt(context: dict) -> tuple[str, str]:
    system = (
        "You are an expert sports prediction market analyst specializing in international soccer and the FIFA World Cup. "
        "Your job is to estimate the TRUE probability of a binary market outcome, compare it to the market-implied probability, "
        "and recommend whether to bet, and how much.\n\n"
        "Always return your response as valid JSON with exactly this schema:\n"
        '{\n  "estimated_probability": <float 0.0-1.0>,\n  "confidence": <"low"|"medium"|"high">,\n'
        '  "action": <"bet_yes"|"bet_no"|"skip">,\n  "reasoning": "<string, max 300 words>",\n'
        '  "key_factors": ["<factor 1>", "<factor 2>", "<factor 3>"],\n  "red_flags": ["<risk 1>"] or []\n}\n\n'
        "Only recommend betting when your estimated probability differs from the market by more than 5 percentage points "
        "AND you have medium or high confidence. Otherwise return action: \"skip\"."
    )

    prompt = f"""
## Market
Question: {context['question']}
Platform: {context['platform']}
Market implied probability (YES): {context['implied_prob']:.1%}
Volume: ${context['volume']:,.0f}
Time to close: {context['time_to_close_hours']:.1f} hours

## Teams

### {context['home_team']}
- World Cup record: {context['home_wc_record']['appearances']} appearances, {context['home_wc_record']['win_rate']:.0%} win rate, best finish: {context['home_wc_record']['best_finish']}
- Recent form (last 10): {context['home_recent_form']['form_string']} ({context['home_recent_form']['wins']}W {context['home_recent_form']['draws']}D {context['home_recent_form']['losses']}L)
- Tournament advancement rates: QF {context['home_stage_rates']['qf_rate']:.0%} | SF {context['home_stage_rates']['sf_rate']:.0%} | Champion {context['home_stage_rates']['win_rate']:.0%}
- Latest news:
{context['home_news']}
{context['home_injury_alerts_formatted']}

### {context['away_team']}
- World Cup record: {context['away_wc_record']['appearances']} appearances, {context['away_wc_record']['win_rate']:.0%} win rate, best finish: {context['away_wc_record']['best_finish']}
- Recent form (last 10): {context['away_recent_form']['form_string']} ({context['away_recent_form']['wins']}W {context['away_recent_form']['draws']}D {context['away_recent_form']['losses']}L)
- Tournament advancement rates: QF {context['away_stage_rates']['qf_rate']:.0%} | SF {context['away_stage_rates']['sf_rate']:.0%} | Champion {context['away_stage_rates']['win_rate']:.0%}
- Latest news:
{context['away_news']}
{context['away_injury_alerts_formatted']}

## Head-to-Head (all-time)
{context['h2h']['meetings']} meetings: {context['home_team']} {context['h2h']['team_a_wins']}W | {context['h2h']['draws']}D | {context['h2h']['team_b_wins']}W {context['away_team']}
WC-only meetings: {context['h2h']['wc_meetings_only']}

## Your Calibration
Historical accuracy on soccer markets: {context['historical_edge']['accuracy']:.1%} correct
Average edge you've identified: {context['historical_edge']['avg_edge']:+.1%}

## Portfolio
Available bankroll: ${context['bankroll']:,.2f}
Max stake per bet: ${context['max_stake']:,.2f}
Open positions: {context['open_positions_count']}

Based on all of the above, analyze this market and return your JSON decision.
""".strip()
    return system, prompt
