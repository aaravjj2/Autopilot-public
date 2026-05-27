from features.market_features import kelly_fraction, parse_market_teams
from features.news_features import detect_injury_keywords, summarize_news
from features.team_features import (
    get_confederation_strength,
    get_h2h_record,
    get_recent_form,
    get_team_tournament_stage_rates,
    get_wc_record,
)


def test_wc_record_argentina(db):
    rec = get_wc_record("Argentina")
    assert rec["appearances"] >= 5


def test_wc_record_unknown_team():
    rec = get_wc_record("NotARealTeamXYZ")
    assert rec["appearances"] == 0


def test_h2h_symmetry(db):
    ab = get_h2h_record("Argentina", "France")
    ba = get_h2h_record("France", "Argentina")
    assert ab["team_a_wins"] == ba["team_b_wins"]


def test_h2h_known_rivalry(db):
    h = get_h2h_record("Brazil", "Germany")
    assert h["meetings"] >= 1


def test_h2h_record_no_meetings(db):
    r = get_h2h_record("Haiti", "Curaçao")
    assert r["meetings"] >= 0


def test_recent_form_length(db):
    r = get_recent_form("Argentina", n=10)
    assert len(r["form_string"]) <= 10


def test_form_string_format(db):
    r = get_recent_form("Brazil", n=10)
    assert set(r["form_string"]) <= set("WDLNA/")


def test_recent_form_fewer_than_n_games(db):
    r = get_recent_form("Haiti", n=10)
    assert len(r["form_string"]) <= 10


def test_stage_rates_sum_to_plausible_range(db):
    rates = get_team_tournament_stage_rates("Brazil")
    assert 0.0 <= rates["qf_rate"] <= 1.0
    assert 0.0 <= rates["sf_rate"] <= 1.0
    assert rates["qf_rate"] >= rates["sf_rate"]
    assert rates["sf_rate"] >= rates["final_rate"]
    assert rates["final_rate"] >= rates["win_rate"]


def test_confederation_strength_known_team(db):
    r = get_confederation_strength("Brazil")
    assert r["confederation"] == "CONMEBOL"


def test_confederation_strength_unknown_team(db):
    r = get_confederation_strength("Atlantis FC")
    assert "confederation" in r


def test_kelly_fraction_positive_edge():
    assert kelly_fraction(0.1, odds=1.0) > 0


def test_kelly_fraction_negative_edge():
    assert kelly_fraction(-0.05, odds=1.0) == 0


def test_kelly_fraction_cap():
    assert kelly_fraction(0.9, odds=1.0) <= 0.05


def test_parse_market_teams_argentina_france():
    assert parse_market_teams("Will Argentina beat France?") == ("Argentina", "France")


def test_parse_market_teams_championship():
    assert parse_market_teams("Will Brazil win the 2026 World Cup?") == ("Brazil", None)


def test_injury_keyword_detection():
    arts = [{"title": "Mbappe ruled out for France clash", "description": "", "source": "x", "published_at": ""}]
    found = detect_injury_keywords(arts, "France")
    assert any("Mbappe" in f for f in found)


def test_news_summary_max_items():
    arts = [{"title": f"T{i}", "source": "S", "published_at": "P", "url": str(i)} for i in range(20)]
    text = summarize_news(arts, max_items=5)
    assert text.count("•") == 5
