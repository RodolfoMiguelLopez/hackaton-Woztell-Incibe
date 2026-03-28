import json
import logging
from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

import config
from woztell import send_text, send_reply_buttons, send_image, send_reply_buttons_image
from ai_processor import detect_intent, generate_shopping_list, modify_list, INTENT_PURCHASE
from audio_processor import transcribe_audio
from conversation import get_state, set_state, get_lista, set_lista, reset
from shopping_list import get_lista_completa, format_summary
from actividades import (
    RUTAS, EVENTOS,
    detectar_tipo_actividad, detectar_eleccion_ruta, detectar_eleccion_evento,
    evento_por_payload, msg_notif_familiar,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Asistente de Compras WhatsApp")
app.mount("/img", StaticFiles(directory="img"), name="img")

# Almacena los últimos 10 payloads para debug
_debug_payloads: list[dict] = []

BOTONES_MENU = [
    {"payload": "OPCION_COMPRA",       "title": "🛒 Hacer la compra"},
    {"payload": "OPCION_PENDIENTES",   "title": "📋 Cosas pendientes"},
    {"payload": "OPCION_ACTIVIDADES",  "title": "💡 Qué hacer hoy"},
]

BOTONES_CONFIRMACION = [
    {"payload": "CONFIRMAR_COMPRA", "title": "✅ Confirmar"},
    {"payload": "MODIFICAR_COMPRA", "title": "✏️ Modificar"},
    {"payload": "CANCELAR_COMPRA",  "title": "❌ Cancelar"},
]

_DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
_MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
          "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _fecha_entrega() -> str:
    """Retorna la fecha del día siguiente en formato 'martes 29 de marzo'."""
    manana = datetime.now() + timedelta(days=1)
    return f"{_DIAS[manana.weekday()]} {manana.day} de {_MESES[manana.month - 1]}"


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/debug/payloads")
async def debug_payloads():
    """Devuelve los últimos payloads recibidos — útil para ver qué manda Woztell."""
    return {"payloads": _debug_payloads}


@app.get("/debug/file/{file_id}")
async def debug_file(file_id: str):
    """Prueba la descarga de un fichero de Woztell por fileId — diagnóstico."""
    import httpx
    headers = {"Authorization": f"Bearer {config.WOZTELL_ACCESS_TOKEN}"}
    results = {}

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        # REST
        for url_tpl in [
            "https://open.api.woztell.com/file/{id}",
            "https://bot.api.woztell.com/file/{id}",
        ]:
            url = url_tpl.format(id=file_id)
            try:
                r = await client.get(url, headers=headers)
                results[url] = {"status": r.status_code, "bytes": len(r.content), "body": r.text[:200]}
            except Exception as e:
                results[url] = {"error": str(e)}

        # GraphQL
        gql = '{ apiViewer { file(fileId: "%s") { url } } }' % file_id
        try:
            r = await client.post("https://open.api.woztell.com/v3", json={"query": gql}, headers=headers)
            results["graphql"] = r.json()
        except Exception as e:
            results["graphql"] = {"error": str(e)}

    return results


@app.post("/make/trigger")
async def make_trigger(request: Request):
    """Stub para futura integración con Make como orquestador."""
    body = await request.json()
    logger.info(f"[MAKE] Trigger recibido: {json.dumps(body)}")
    return {"ok": True, "state": "stub"}


@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()
    logger.info(f"[WEBHOOK] Payload: {json.dumps(body)}")

    # Guardar para debug
    _debug_payloads.append(body)
    if len(_debug_payloads) > 10:
        _debug_payloads.pop(0)

    # Ignorar eventos de estado (confirmaciones de entrega de mensajes nuestros)
    if body.get("type", "").upper() in ("SENT", "DELIVERED", "READ", "FAILED"):
        logger.info(f"[WEBHOOK] Evento de estado '{body.get('type')}' — ignorando")
        return {"ok": True}

    # --- Parsing defensivo ---
    phone = (
        body.get("from")
        or body.get("sender", {}).get("phone")
        or body.get("member")
    )
    if not phone:
        logger.warning("[WEBHOOK] Sin teléfono — ignorando")
        return {"ok": True}

    msg_type = body.get("type", "").upper()
    data = body.get("data", {})

    text = (
        data.get("text")
        or body.get("text")
        or body.get("message", {}).get("text")
        or data.get("body")
    )

    # URL directa del audio (si Woztell la manda)
    audio_url = (
        data.get("url")
        or data.get("audio", {}).get("url")
        or data.get("voice", {}).get("url")
        or data.get("link")
    )

    # fileId interno de Woztell (formato real: {"type":"AUDIO","data":{"opus":true,"fileId":"..."}})
    file_id = data.get("fileId")

    # waMediaId como fallback
    wa_media_id = None
    attachments = data.get("attachments", [])
    if attachments:
        first = attachments[0]
        if first.get("type") in ("audio", "voice", "ptt"):
            wa_media_id = first.get("waMediaId") or first.get("id")
    if not wa_media_id:
        wa_media_id = data.get("waMediaId")

    button_payload = (
        data.get("interactive", {}).get("button_reply", {}).get("id")
        or data.get("payload")
        or data.get("button_reply", {}).get("id")
        or body.get("payload")
        or body.get("postback", {}).get("payload")
    )

    is_audio = (
        file_id
        or audio_url
        or wa_media_id
        or msg_type in ("AUDIO", "VOICE", "PTT")
        or (msg_type == "MISC" and attachments and attachments[0].get("type") in ("audio", "voice", "ptt"))
    )

    # --- Enrutamiento ---
    if button_payload:
        await _handle_button(phone, button_payload)
    elif is_audio:
        logger.info(f"[AUDIO] Detectado — fileId={file_id} url={audio_url} waMediaId={wa_media_id} (phone: {phone})")
        transcribed = await transcribe_audio(audio_url=audio_url, wa_media_id=wa_media_id, file_id=file_id)
        logger.info(f"[AUDIO] Transcripción para {phone}: '{transcribed}'")
        if transcribed:
            await _handle_text(phone, transcribed)
        else:
            await send_text(
                phone,
                "Lo siento, no he podido escuchar bien el audio. "
                "¿Puedes repetirlo o escribirlo? 🙏",
            )
    elif text:
        await _handle_text(phone, text)
    else:
        logger.warning(f"[WEBHOOK] UNPARSED_PAYLOAD (phone: {phone}): {body}")

    return {"ok": True}


async def _mostrar_rutas(phone: str) -> None:
    for ruta in RUTAS:
        await send_image(phone, ruta["imagen"], ruta["caption"])
    await send_text(
        phone,
        f"¿Cuál de las dos rutas te apetece, {config.NOMBRE_USUARIO}? Dímelo cuando quieras. 😊",
    )


async def _mostrar_eventos(phone: str) -> None:
    for evento in EVENTOS:
        await send_reply_buttons_image(
            phone,
            image_url=evento["imagen"],
            body=evento["detalle"],
            title=evento["nombre"],
            buttons=[{"payload": evento["payload"], "title": evento["boton"]}],
        )
    await send_text(
        phone,
        f"¿Cuál de estos planes te apetece, {config.NOMBRE_USUARIO}? "
        "Dímelo y aviso a María en cuanto lo confirmes. 😊",
    )


async def _handle_text(phone: str, text: str) -> None:
    state = get_state(phone)["state"]
    logger.info(f"[{state}] → handle_text: '{text[:40]}' (phone: {phone})")

    if state == "IDLE":
        await send_reply_buttons(
            phone,
            body=f"¡Hola {config.NOMBRE_USUARIO}! 😊 ¿En qué puedo ayudarte hoy?",
            footer="Elige una opción",
            buttons=BOTONES_MENU,
        )
        logger.info(f"[IDLE] → menú enviado (phone: {phone})")

    elif state == "MODIFYING":
        lista_actual = get_lista(phone)
        nueva_lista = await modify_list(lista_actual, text)
        set_lista(phone, nueva_lista)
        set_state(phone, "AWAITING_CONFIRMATION")
        summary = format_summary(nueva_lista)
        await send_reply_buttons(
            phone,
            body=f"He actualizado tu lista 📝\n\n{summary}",
            footer="¿Confirmamos el pedido?",
            buttons=BOTONES_CONFIRMACION,
        )
        logger.info(f"[MODIFYING] → AWAITING_CONFIRMATION (phone: {phone})")

    elif state == "ACTIVIDADES_ELIGIENDO":
        tipo = detectar_tipo_actividad(text)
        if tipo == "PASEO":
            await _mostrar_rutas(phone)
            set_state(phone, "ACTIVIDADES_PASEO")
            logger.info(f"[ACTIVIDADES_ELIGIENDO] → ACTIVIDADES_PASEO (phone: {phone})")
        elif tipo == "EVENTO":
            await _mostrar_eventos(phone)
            set_state(phone, "ACTIVIDADES_EVENTO")
            logger.info(f"[ACTIVIDADES_ELIGIENDO] → ACTIVIDADES_EVENTO (phone: {phone})")
        else:
            await send_text(
                phone,
                f"No te he entendido bien, {config.NOMBRE_USUARIO} 😊 "
                "¿Prefieres un paseo por tu zona o ver qué eventos hay hoy cerca?",
            )

    elif state == "ACTIVIDADES_PASEO":
        idx = detectar_eleccion_ruta(text)
        if idx is not None:
            ruta = RUTAS[idx]
            await send_text(
                phone,
                f"¡Perfecto! Que disfrutes del paseo por {ruta['nombre']} 🚶‍♂️\n\n"
                f"Aquí tienes cómo llegar:\n{ruta['maps']}",
            )
            await send_text(config.TELEFONO_FAMILIAR, msg_notif_familiar(ruta["notif_familiar"]))
            reset(phone)
            logger.info(f"[ACTIVIDADES_PASEO] → IDLE (ruta: {ruta['nombre']}) (phone: {phone})")
        else:
            await send_text(
                phone,
                f"No te he entendido bien, {config.NOMBRE_USUARIO} 😊 "
                "¿Quieres ir al Parque Tierno Galván o al Centro Cultural Casa del Reloj?",
            )

    elif state == "ACTIVIDADES_EVENTO":
        idx = detectar_eleccion_evento(text)
        if idx is not None:
            evento = EVENTOS[idx]
            await send_text(phone, f"¡Genial! Que disfrutes de {evento['nombre']} 🎉")
            await send_text(config.TELEFONO_FAMILIAR, msg_notif_familiar(evento["notif_familiar"]))
            reset(phone)
            logger.info(f"[ACTIVIDADES_EVENTO] → IDLE (evento: {evento['nombre']}) (phone: {phone})")
        else:
            await send_text(
                phone,
                f"No te he entendido bien, {config.NOMBRE_USUARIO} 😊 "
                "¿Cuál de los planes te apetece? La exposición en el Matadero, "
                "la charla en Las Doroteas o el concurso de bachata.",
            )

    else:
        # AWAITING_CONFIRMATION recibe texto — ignorar, esperar botón
        logger.info(f"[{state}] texto ignorado, esperando botón (phone: {phone})")


async def _handle_button(phone: str, payload: str) -> None:
    state = get_state(phone)["state"]
    logger.info(f"[{state}] → button: {payload} (phone: {phone})")

    if payload == "OPCION_COMPRA":
        lista = await generate_shopping_list("hacer la compra", get_lista_completa())
        set_lista(phone, lista)
        set_state(phone, "AWAITING_CONFIRMATION")
        summary = format_summary(lista)
        await send_reply_buttons(
            phone,
            body=f"¡Aquí está tu lista habitual, {config.NOMBRE_USUARIO}! 😊\n\n{summary}",
            footer="¿Quieres confirmar este pedido?",
            buttons=BOTONES_CONFIRMACION,
        )
        logger.info(f"[IDLE] → AWAITING_CONFIRMATION via menú (phone: {phone})")

    elif payload == "OPCION_PENDIENTES":
        from pendientes import get_pendientes_msg
        await send_text(phone, get_pendientes_msg(config.NOMBRE_USUARIO))
        reset(phone)
        logger.info(f"[IDLE] → pendientes (phone: {phone})")

    elif payload == "OPCION_ACTIVIDADES":
        await send_text(
            phone,
            f"Hoy hace buena temperatura, {config.NOMBRE_USUARIO} 😊 ¿Qué te apetece?\n\n"
            "Puedo prepararte un paseo por tu zona, o si prefieres te cuento qué eventos "
            "hay hoy cerca. Dímelo cuando quieras.",
        )
        set_state(phone, "ACTIVIDADES_ELIGIENDO")
        logger.info(f"[IDLE] → ACTIVIDADES_ELIGIENDO (phone: {phone})")

    elif payload == "CONFIRMAR_COMPRA" and state == "AWAITING_CONFIRMATION":
        fecha = _fecha_entrega()
        msg_usuario = (
            f"¡Perfecto, {config.NOMBRE_USUARIO}! 🛒 Tu pedido está confirmado.\n"
            f"El repartidor lo dejará en tu domicilio mañana {fecha} "
            f"entre las 10:00 y las 12:00.\n"
            f"¡Asegúrate de estar en casa! 😊"
        )
        msg_familiar = (
            f"Hola {config.NOMBRE_FAMILIAR} 👋 {config.NOMBRE_USUARIO} acaba de confirmar "
            f"su pedido de la compra.\nSe lo entregarán mañana {fecha} entre las 10:00 y "
            f"las 12:00 en su domicilio.\nPor si quieres pasarte a ayudarle con las bolsas. "
            f"¡Gracias! 😊"
        )
        await send_text(phone, msg_usuario)
        await send_text(config.TELEFONO_FAMILIAR, msg_familiar)
        reset(phone)
        logger.info(f"[AWAITING_CONFIRMATION] → IDLE (confirmado) (phone: {phone})")

    elif payload == "CANCELAR_COMPRA":
        await send_text(
            phone,
            f"De acuerdo, {config.NOMBRE_USUARIO}. He cancelado el pedido.\n"
            f"Si en otro momento quieres hacer la compra, ¡aquí estaré! 😊",
        )
        reset(phone)
        logger.info(f"[{state}] → IDLE (cancelado) (phone: {phone})")

    elif payload == "MODIFICAR_COMPRA" and state == "AWAITING_CONFIRMATION":
        await send_text(
            phone,
            f"¡Claro! ¿Qué te gustaría cambiar de la lista, {config.NOMBRE_USUARIO}? "
            f"Puedes decirme, por ejemplo: \"sin yogures\" o \"añade más leche\". 🛒",
        )
        set_state(phone, "MODIFYING")
        logger.info(f"[AWAITING_CONFIRMATION] → MODIFYING (phone: {phone})")

    elif payload in ("LLEGAR_MATADERO", "LLEGAR_DOROTEAS", "LLEGAR_PARAISO"):
        evento = evento_por_payload(payload)
        await send_text(phone, f"Aquí tienes cómo llegar a {evento['nombre']}:\n\n{evento['maps']}")
        logger.info(f"[{state}] → directions {payload} (phone: {phone})")

    else:
        logger.warning(f"[{state}] payload inesperado: {payload} (phone: {phone})")
