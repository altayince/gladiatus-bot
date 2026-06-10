from dotenv import load_dotenv
import os
from pathlib import Path

# Load .env from project root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

USERNAME = os.getenv("GLADIATUS_USERNAME")
PASSWORD = os.getenv("GLADIATUS_PASSWORD")
BASE_URL = os.getenv("BASE_URL")
HEADLESS = os.getenv("HEADLESS", "true").lower() in ("1", "true", "yes")
