import logging
import os
import tempfile
import httpx
from openai import AsyncOpenAI
import config

logger = logging.getLogger(__name__)

openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

# Posibles endpoints de descarga de ficheros de Woztell (se prueban en orden)
_FILE_ENDPOINTS = [
    "https://open.api.woztell.com/file/{file_id}",
    "https://bot.api.woztell.com/file/{file_id}",
    "https://open.api.woztell.com/v3/file/{file_id}",
]


async def _download_by_file_id(file_id: str) -> bytes | None:
    """
    Descarga el contenido binario de un fichero usando el fileId interno de Woztell.
    Prueba varios endpoints hasta encontrar uno que funcione.
    """
    headers = {"Authorization": f"Bearer {config.WOZTELL_ACCESS_TOKEN}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        for endpoint in _FILE_ENDPOINTS:
            url = endpoint.format(file_id=file_id)
            try:
                resp = await client.get(url, headers=headers)
                logger.info(f"[AUDIO] {url} → status {resp.status_code}")
                if resp.status_code == 200 and len(resp.content) > 100:
                    logger.info(f"[AUDIO] Descargados {len(resp.content)} bytes desde {url}")
                    return resp.content
            except Exception as e:
                logger.warning(f"[AUDIO] Error en {url}: {e}")
    return None


async def transcribe_audio(
    audio_url: str | None = None,
    wa_media_id: str | None = None,
    file_id: str | None = None,
) -> str:
    """
    Descarga el audio y lo transcribe con Whisper.
    Acepta: URL directa, waMediaId o fileId de Woztell.
    Retorna el texto transcrito o "" en caso de error.
    """
    tmp_path = None
    try:
        audio_bytes = None

        # Caso 1: fileId interno de Woztell (formato real de los webhooks)
        if file_id:
            audio_bytes = await _download_by_file_id(file_id)

        # Caso 2: URL directa
        if not audio_bytes and audio_url:
            headers = {"Authorization": f"Bearer {config.WOZTELL_ACCESS_TOKEN}"}
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(audio_url, headers=headers)
                response.raise_for_status()
                audio_bytes = response.content
                logger.info(f"[AUDIO] Descargados {len(audio_bytes)} bytes desde URL directa")

        if not audio_bytes:
            logger.error(f"[AUDIO] No se pudo obtener el audio (file_id={file_id}, url={audio_url})")
            return ""

        # Guardar en fichero temporal
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        # Transcribir con Whisper
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
        logger.error(f"[AUDIO] Error al transcribir: {e}")
        return ""

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
