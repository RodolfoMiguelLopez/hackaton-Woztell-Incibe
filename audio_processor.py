import logging
import os
import tempfile
import httpx
from openai import AsyncOpenAI
import config

logger = logging.getLogger(__name__)

openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

# URL de la API de WhatsApp Cloud (Meta) para obtener la URL de descarga del media
_WA_MEDIA_URL = "https://graph.facebook.com/v19.0/{media_id}"


async def _get_download_url(wa_media_id: str) -> str | None:
    """
    Convierte un waMediaId en URL de descarga.
    Intenta primero la API de Woztell, luego la de Meta directamente.
    """
    # Intento 1: Woztell Open API (GraphQL) — proxy de media
    try:
        query = """
        query GetMediaUrl($mediaId: String!, $channelId: String!) {
          getWAMediaInfo(waMediaId: $mediaId, channelId: $channelId) {
            url
          }
        }
        """
        headers = {"Authorization": f"Bearer {config.WOZTELL_ACCESS_TOKEN}"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://open.api.woztell.com/v3",
                json={
                    "query": query,
                    "variables": {"mediaId": wa_media_id, "channelId": config.WOZTELL_CHANNEL_ID},
                },
                headers=headers,
            )
            data = resp.json()
            url = (
                data.get("data", {}).get("getWAMediaInfo", {}).get("url")
                or data.get("data", {}).get("mediaInfo", {}).get("url")
            )
            if url:
                logger.info(f"[AUDIO] URL obtenida via Woztell Open API: {url[:60]}...")
                return url
    except Exception as e:
        logger.warning(f"[AUDIO] Woztell Open API falló: {e}")

    # Intento 2: Meta Graph API directamente usando token de Woztell
    try:
        headers = {"Authorization": f"Bearer {config.WOZTELL_ACCESS_TOKEN}"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                _WA_MEDIA_URL.format(media_id=wa_media_id),
                headers=headers,
            )
            data = resp.json()
            url = data.get("url")
            if url:
                logger.info(f"[AUDIO] URL obtenida via Meta Graph API: {url[:60]}...")
                return url
    except Exception as e:
        logger.warning(f"[AUDIO] Meta Graph API falló: {e}")

    logger.error(f"[AUDIO] No se pudo obtener URL para waMediaId={wa_media_id}")
    return None


async def transcribe_audio(audio_url: str | None = None, wa_media_id: str | None = None) -> str:
    """
    Descarga el audio y lo transcribe con Whisper.
    Acepta una URL directa o un waMediaId para descarga en dos pasos.
    Retorna el texto transcrito o "" en caso de error.
    """
    tmp_path = None
    try:
        # Resolver URL si solo tenemos waMediaId
        if not audio_url and wa_media_id:
            audio_url = await _get_download_url(wa_media_id)
        if not audio_url:
            logger.error("[AUDIO] Sin URL ni waMediaId válido — imposible transcribir")
            return ""

        # Descargar el audio
        headers = {"Authorization": f"Bearer {config.WOZTELL_ACCESS_TOKEN}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(audio_url, headers=headers)
            response.raise_for_status()
            audio_bytes = response.content

        logger.info(f"[AUDIO] Descargados {len(audio_bytes)} bytes")

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
