import threading
import os
import time

def _start_api():
    import uvicorn
    uvicorn.run("service:app", host="0.0.0.0", port=8002, log_level="info")


def _start_bot():
    # Import here so FastAPI/uvicorn deps don't interfere with discord client
    from main import ZenTradingBot
    import dotenv
    dotenv.load_dotenv()
    TOKEN = os.getenv("DISCORD_USER_TOKEN")
    if not TOKEN:
        print("DISCORD_USER_TOKEN not set — bot will not start")
        return
    client = ZenTradingBot()
    client.run(TOKEN)


if __name__ == "__main__":
    # Start API in a background thread
    t = threading.Thread(target=_start_api, daemon=True)
    t.start()
    print("🔌 Discord service API started on :8002")

    # Small delay to let API bind before bot starts
    time.sleep(1)

    # Start the Discord bot (blocking)
    _start_bot()
