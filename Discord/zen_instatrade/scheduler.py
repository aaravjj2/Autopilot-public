import schedule
import time
from exit_manager import check_and_exit_trades, print_portfolio_summary

def run_exit_check():
    """Run the exit manager check"""
    try:
        check_and_exit_trades()
    except Exception as e:
        print(f"❌ Exit check failed: {e}")

def run_portfolio_summary():
    """Print portfolio summary"""
    try:
        print_portfolio_summary()
    except Exception as e:
        print(f"❌ Portfolio summary failed: {e}")

if __name__ == "__main__":
    print("🤖 Trade Scheduler Started")
    
    # Check for exits every 5 minutes during market hours (9:30 AM - 4:00 PM ET)
    schedule.every(5).minutes.do(run_exit_check)
    
    # Print summary every 30 minutes
    schedule.every(30).minutes.do(run_portfolio_summary)
    
    print("⏰ Schedule configured:")
    print("   • Exit check: Every 5 minutes")
    print("   • Portfolio summary: Every 30 minutes")
    
    while True:
        schedule.run_pending()
        time.sleep(1)
