import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

CONFIG_PATH = BASE_DIR / "config.yaml"


def load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            "config.yaml が見つかりません。config.example.yaml をコピーして "
            "config.yaml を作成し、収集したいアカウント情報を入れてください。"
        )
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


X_USERNAME = os.getenv("X_USERNAME")
X_EMAIL = os.getenv("X_EMAIL")
X_PASSWORD = os.getenv("X_PASSWORD")
TIKTOK_MS_TOKEN = os.getenv("TIKTOK_MS_TOKEN")
