import logging
import os
import tempfile
import httpx
from openai import AsyncOpenAI
import config

logger = logging.getLogger(__name__)

openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)


async def transcribe_audio(audio_url: str) -> str:
    """
    Descarga el audio desde audio_url (OGG/Opus de WhatsApp) y lo transcribe con Whisper.
    Retorna el texto transcrito o "" en caso de error.
    """
    tmp_path = None
    try:
        headers = {"Authorization": f"Bearer {config.WOZTELL_ACCESS_TOKEN}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(audio_url, headers=headers)
            response.raise_for_status()
            audio_bytes = response.content

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        with open(tmp_path, "rb") as audio_file:
            transcription = await openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="es",
            )

        text = transcription.text.strip()
        logger.info(f"[AUDIO] Transcripción: '{text}'")
        return text

    except Exception as e:
        logger.error(f"[AUDIO] Error al transcribir audio: {e}")
        return ""

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
