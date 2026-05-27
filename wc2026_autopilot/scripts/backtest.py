"""Lightweight historical backtest over logged decisions/outcomes."""

from calibration.tracker import get_brier_score, get_calibration_stats
from config import get_db_connection

if __name__ == "__main__":
    conn = get_db_connection()
    stats = get_calibration_stats(conn)
    brier = get_brier_score(conn)
    print("Calibration:", stats)
    print(f"Brier score: {brier:.4f}")
