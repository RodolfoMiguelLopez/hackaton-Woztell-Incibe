import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o-mini"

WOZTELL_ACCESS_TOKEN = os.getenv("WOZTELL_ACCESS_TOKEN", "")
WOZTELL_CHANNEL_ID = os.getenv("WOZTELL_CHANNEL_ID", "")
WOZTELL_BOT_API_URL = "https://bot.api.woztell.com/sendResponses"

TELEFONO_USUARIO = os.getenv("TELEFONO_USUARIO", "")
TELEFONO_FAMILIAR = os.getenv("TELEFONO_FAMILIAR", "")
NOMBRE_USUARIO = os.getenv("NOMBRE_USUARIO", "Antonio")
NOMBRE_FAMILIAR = os.getenv("NOMBRE_FAMILIAR", "María")

USE_MOCK_AI = os.getenv("USE_MOCK_AI", "false").lower() == "true"
WOZTELL_RETRY_DELAY_SECONDS = 1
PORT = int(os.getenv("PORT", "8000"))

BASE_URL = os.getenv("BASE_URL", "https://hack-production-435a.up.railway.app")
