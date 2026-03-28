import logging
import os
import tempfile
import httpx
from openai import AsyncOpenAI
import config

logger = logging.getLogger(__name__)

openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

# Posibles endpoints REST de descarga de ficheros de Woztell (se prueban en orden)
_FILE_ENDPOINTS = [
    "https://open.api.woztell.com/file/{file_id}",
    "https://bot.api.woztell.com/file/{file_id}",
    "https://open.api.woztell.com/v3/file/{file_id}",
    "https://open.api.woztell.com/files/{file_id}",
    "https://open.api.woztell.com/media/{file_id}",
]

# Posibles queries GraphQL para obtener URL del fichero
_GQL_QUERIES = [
    ("getAttachment",  'query($id:String!){getAttachment(fileId:$id){url mimeType}}'),
    ("getFile",        'query($id:String!){getFile(fileId:$id){url}}'),
    ("getInboundFile", 'query($id:String!){getInboundFile(fileId:$id){url}}'),
    ("file",           'query($id:String!){file(id:$id){url}}'),
]


async def _download_by_file_id(file_id: str) -> bytes | None:
    """
    Descarga el contenido binario de un fichero usando el fileId interno de Woztell.
    Prueba REST endpoints y luego GraphQL hasta encontrar uno que funcione.
    """
    headers = {"Authorization": f"Bearer {config.WOZTELL_ACCESS_TOKEN}"}
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:

        # 1. Intentar endpoints REST — con Bearer header Y con ?accessToken= como query param
        for endpoint in _FILE_ENDPOINTS:
            url = endpoint.format(file_id=file_id)
            for attempt_headers, params in [
                (headers, {}),
                ({}, {"accessToken": config.WOZTELL_ACCESS_TOKEN}),
            ]:
                try:
                    resp = await client.get(url, headers=attempt_headers, params=params)
                    logger.info(f"[AUDIO] REST {url} params={list(params.keys())} → {resp.status_code} ({len(resp.content)} bytes)")
                    if resp.status_code == 200 and len(resp.content) > 100:
                        return resp.content
                except Exception as e:
                    logger.warning(f"[AUDIO] REST {url} error: {e}")

        # 2. Intentar GraphQL para obtener URL y luego descargar
        for query_name, query in _GQL_QUERIES:
            try:
                resp = await client.post(
                    "https://open.api.woztell.com/v3",
                    json={"query": query, "variables": {"id": file_id}},
                    headers=headers,
                )
                data = resp.json()
                logger.info(f"[AUDIO] GraphQL {query_name} → {data}")
                file_url = (
                    data.get("data", {}).get(query_name, {}) or {}
                ).get("url")
                if file_url:
                    dl = await client.get(file_url, headers=headers)
                    if dl.status_code == 200 and len(dl.content) > 100:
                        logger.info(f"[AUDIO] Descargados {len(dl.content)} bytes via GraphQL {query_name}")
                        return dl.content
            except Exception as e:
                logger.warning(f"[AUDIO] GraphQL {query_name} error: {e}")

    logger.error(f"[AUDIO] Todos los métodos fallaron para fileId={file_id}")
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
