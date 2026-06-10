from .config import USERNAME, PASSWORD, BASE_URL, HEADLESS
from .selenium_bot import GladiatusBot
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", help="Override username")
    parser.add_argument("--password", help="Override password")
    parser.add_argument("--base-url", help="Override base URL")
    parser.add_argument("--headless", choices=["true", "false"], help="Override headless setting")
    parser.add_argument("--no-close", action="store_true", help="Keep browser open on error")
    args = parser.parse_args()

    username = args.username or USERNAME
    password = args.password or PASSWORD
    base_url = args.base_url or BASE_URL
    headless = HEADLESS if args.headless is None else (args.headless.lower() == "true")

    if not username or not password or not base_url:
        print("Missing credentials: provide USERNAME, PASSWORD, BASE_URL via .env or CLI arguments.")
        return

    bot = GladiatusBot(headless=headless)
    try:
        ok = bot.login(base_url, username, password)
        if not ok:
            print("Login failed. Check selectors or credentials.")
            if args.no_close:
                print("Browser kept open. Press Enter to close...")
                input()
            else:
                bot.quit()
            return
        print("Login successful.")
        if not args.no_close:
            bot.quit()
        else:
            print("Browser kept open. Press Enter to close...")
            input()
            bot.quit()
    except Exception as e:
        print(f"Error: {e}")
        if args.no_close:
            print("Browser kept open. Press Enter to close...")
            input()
        bot.quit()


if __name__ == "__main__":
    main()
