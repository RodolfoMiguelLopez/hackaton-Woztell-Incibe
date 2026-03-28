import json
import logging
from openai import AsyncOpenAI
import config
from shopping_list import get_lista_completa

logger = logging.getLogger(__name__)

INTENT_PURCHASE = "PURCHASE_INTENT"
INTENT_UNKNOWN = "UNKNOWN"

_PURCHASE_KEYWORDS = [
    "compra", "comprar", "necesito", "lista", "mercado",
    "super", "supermercado", "quiero", "pedir", "pedido",
]

openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)


async def detect_intent(text: str) -> str:
    """Detecta si el usuario quiere hacer la compra."""
    if config.USE_MOCK_AI:
        text_lower = text.lower()
        if any(kw in text_lower for kw in _PURCHASE_KEYWORDS):
            return INTENT_PURCHASE
        return INTENT_UNKNOWN

    try:
        resp = await openai_client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un clasificador de intenciones. "
                        "El usuario es una persona mayor que usa WhatsApp. "
                        "Si el mensaje indica que quiere hacer la compra, "
                        "pedir comida, necesitar productos del supermercado, "
                        "o cualquier variante de comprar alimentos, responde exactamente: PURCHASE_INTENT. "
                        "En cualquier otro caso responde exactamente: UNKNOWN. "
                        "Solo responde una de esas dos palabras, sin explicación."
                    ),
                },
                {"role": "user", "content": text},
            ],
            max_tokens=10,
            temperature=0,
        )
        result = resp.choices[0].message.content.strip()
        logger.info(f"[AI] detect_intent: '{text[:40]}' → {result}")
        return result if result in (INTENT_PURCHASE, INTENT_UNKNOWN) else INTENT_UNKNOWN
    except Exception as e:
        logger.error(f"[AI] Error en detect_intent: {e}")
        return INTENT_UNKNOWN


async def generate_shopping_list(user_message: str, lista_habitual: list[dict]) -> list[dict]:
    """Genera la lista de compra basada en la lista habitual."""
    if config.USE_MOCK_AI:
        return get_lista_completa()

    try:
        lista_json = json.dumps(lista_habitual, ensure_ascii=False)
        resp = await openai_client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres el asistente de compras de Antonio, una persona mayor. "
                        "Tienes su lista habitual de la compra. "
                        "Genera una lista de productos en formato JSON: "
                        'lista de objetos con campos "nombre" (str), "cantidad" (int), '
                        '"precio" (float) y "categoria" (str). '
                        "Responde SOLO con el JSON, sin explicación ni markdown."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Lista habitual: {lista_json}\n\nMensaje del usuario: {user_message}",
                },
            ],
            max_tokens=800,
            temperature=0.3,
        )
        content = resp.choices[0].message.content.strip()
        lista = json.loads(content)
        logger.info(f"[AI] generate_shopping_list: {len(lista)} productos")
        return lista
    except Exception as e:
        logger.error(f"[AI] Error en generate_shopping_list: {e}")
        return get_lista_completa()


async def modify_list(current_lista: list[dict], modification_text: str) -> list[dict]:
    """Modifica la lista según el texto del usuario."""
    if config.USE_MOCK_AI:
        text_lower = modification_text.lower()
        lista = list(current_lista)
        if ("más" in text_lower or "añade" in text_lower or "mas" in text_lower) and lista:
            lista[0] = {**lista[0], "cantidad": lista[0]["cantidad"] + 1}
        elif ("sin" in text_lower or "quita" in text_lower) and lista:
            lista = lista[1:]
        return lista

    try:
        lista_json = json.dumps(current_lista, ensure_ascii=False)
        resp = await openai_client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres el asistente de compras de Antonio. "
                        "Tienes su lista actual y el usuario quiere modificarla. "
                        "Devuelve la lista modificada en formato JSON: "
                        'lista de objetos con campos "nombre", "cantidad", "precio", "categoria". '
                        "Responde SOLO con el JSON, sin explicación ni markdown."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Lista actual: {lista_json}\n\nModificación: {modification_text}",
                },
            ],
            max_tokens=800,
            temperature=0.3,
        )
        content = resp.choices[0].message.content.strip()
        lista = json.loads(content)
        logger.info(f"[AI] modify_list: {len(lista)} productos tras modificación")
        return lista
    except Exception as e:
        logger.error(f"[AI] Error en modify_list: {e}")
        return current_lista
