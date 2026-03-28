import asyncio
import logging
import httpx
import config

logger = logging.getLogger(__name__)


async def send_message(recipient: str, responses: list[dict]) -> dict:
    """Función de bajo nivel. Llama POST /sendResponses. Reintenta 1 vez si falla."""
    payload = {
        "channelId": config.WOZTELL_CHANNEL_ID,
        "recipientId": recipient,
        "response": responses,
    }
    headers = {"Authorization": f"Bearer {config.WOZTELL_ACCESS_TOKEN}"}

    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(config.WOZTELL_BOT_API_URL, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                if data.get("ok") != 1:
                    raise ValueError(f"Woztell error: {data}")
                logger.info(f"[WOZTELL] send_message ok → recipient={recipient}")
                return data
        except Exception as e:
            logger.error(f"[WOZTELL] Intento {attempt + 1} fallido: {e}")
            if attempt == 0:
                await asyncio.sleep(config.WOZTELL_RETRY_DELAY_SECONDS)

    return {"ok": 0, "err": "max retries exceeded"}


async def send_text(recipient: str, text: str) -> dict:
    """Envía mensaje de texto simple."""
    logger.info(f"[WOZTELL] send_text → {recipient}: {text[:60]}...")
    return await send_message(recipient, [{"type": "TEXT", "text": text}])


async def send_image(recipient: str, url: str, caption: str = "") -> dict:
    """Envía imagen con pie de foto opcional."""
    logger.info(f"[WOZTELL] send_image → {recipient}: {url}")
    response = {"type": "IMAGE", "url": url, "caption": caption}
    return await send_message(recipient, [response])


async def send_reply_buttons(
    recipient: str,
    body: str,
    footer: str,
    buttons: list[dict],
) -> dict:
    """
    Envía mensaje con botones de respuesta (máx 3).
    buttons: [{"payload": str, "title": str}, ...]
    """
    logger.info(f"[WOZTELL] send_reply_buttons → {recipient} con {len(buttons)} botones")
    wa_buttons = [
        {"type": "reply", "reply": {"payload": b["payload"], "title": b["title"]}}
        for b in buttons
    ]
    response = {
        "type": "WHATSAPP_REPLY_BUTTONS",
        "body": {"text": body},
        "footer": {"text": footer},
        "action": {"buttons": wa_buttons},
    }
    return await send_message(recipient, [response])


async def send_reply_buttons_image(
    recipient: str,
    image_url: str,
    body: str,
    footer: str,
    buttons: list[dict],
) -> dict:
    """
    Envía mensaje con imagen en cabecera y botones de respuesta (máx 3).
    buttons: [{"payload": str, "title": str}, ...]
    """
    logger.info(f"[WOZTELL] send_reply_buttons_image → {recipient} con imagen")
    wa_buttons = [
        {"type": "reply", "reply": {"payload": b["payload"], "title": b["title"]}}
        for b in buttons
    ]
    response = {
        "type": "WHATSAPP_REPLY_BUTTONS",
        "header": {"type": "image", "image": {"link": image_url}},
        "body": {"text": body},
        "footer": {"text": footer},
        "action": {"buttons": wa_buttons},
    }
    return await send_message(recipient, [response])
