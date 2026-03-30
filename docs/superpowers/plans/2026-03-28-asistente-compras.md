# Asistente de Compras WhatsApp — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Servidor FastAPI que recibe mensajes de WhatsApp (texto o audio) a través de Woztell, gestiona un flujo de compra con IA (OpenAI GPT-4o-mini + Whisper) y notifica al usuario y a un familiar al confirmar el pedido.

**Architecture:** Servidor monolítico single-process con estado en memoria (dict Python). Un endpoint `/webhook` recibe todos los mensajes de Woztell; la lógica de negocio se distribuye en módulos con contratos claros. El endpoint `/make/trigger` existe como stub preparado para integración futura con Make.

**Tech Stack:** Python 3.11, FastAPI, uvicorn, httpx, openai SDK (GPT-4o-mini + Whisper), Woztell Bot API REST

---

## File Map

| Fichero | Responsabilidad |
|---|---|
| `config.py` | Constantes y credenciales. Sin lógica. |
| `shopping_list.py` | Lista ficticia hardcodeada + `format_summary()` + `calcular_total()` |
| `conversation.py` | Estado de conversación por teléfono en dict en memoria |
| `woztell.py` | Cliente HTTP Woztell: `send_text()`, `send_reply_buttons()` |
| `audio_processor.py` | Descarga audio de Woztell + transcripción con Whisper |
| `ai_processor.py` | Detección de intención + generación/modificación de lista con GPT-4o-mini |
| `main.py` | FastAPI app: endpoints, parsing defensivo del webhook, orquestación del flujo |
| `requirements.txt` | Dependencias Python |
| `README.md` | Instrucciones de setup para la demo |
| `tests/test_shopping_list.py` | Tests de `shopping_list.py` |
| `tests/test_conversation.py` | Tests de `conversation.py` |
| `tests/test_woztell.py` | Tests del cliente Woztell (mock HTTP) |
| `tests/test_ai_processor.py` | Tests del procesador de IA (modo mock) |
| `tests/test_audio_processor.py` | Tests del procesador de audio (mock Whisper) |
| `tests/test_main.py` | Tests de integración del webhook |

---

## Task 1: Scaffolding — estructura base del proyecto

**Files:**
- Create: `requirements.txt`
- Create: `config.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Crear `requirements.txt`**

```
fastapi
uvicorn[standard]
httpx
openai
pytest
pytest-asyncio
```

- [ ] **Step 2: Crear `config.py`**

```python
# config.py
OPENAI_API_KEY = "sk-proj-..."
OPENAI_MODEL = "gpt-4o-mini"

WOZTELL_ACCESS_TOKEN = "eyJ..."
WOZTELL_CHANNEL_ID = "your-channel-id"
WOZTELL_BOT_API_URL = "https://bot.api.woztell.com/sendResponses"

TELEFONO_USUARIO = "34XXXXXXXXX"
TELEFONO_FAMILIAR = "34YYYYYYYYY"
NOMBRE_USUARIO = "Antonio"
NOMBRE_FAMILIAR = "María"

USE_MOCK_AI = False
WOZTELL_RETRY_DELAY_SECONDS = 1
PORT = 8000
```

- [ ] **Step 3: Crear `pytest.ini`** (necesario para pytest-asyncio >= 0.21)

```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 4: Crear directorio de tests y `.gitignore`**

```bash
mkdir -p tests
touch tests/__init__.py
```

Crear `.gitignore`:
```
__pycache__/
*.pyc
.pytest_cache/
config.py
```

> Nota: `config.py` está en `.gitignore` para no subir credenciales a un repo público. Para el equipo, compartir el fichero manualmente.

- [ ] **Step 5: Instalar dependencias**

```bash
pip install -r requirements.txt
```

Expected: instalación sin errores.

- [ ] **Step 6: Commit**

```bash
git init
git add requirements.txt config.py pytest.ini tests/__init__.py .gitignore
git commit -m "feat: scaffolding inicial — config y dependencias"
```

---

## Task 2: `shopping_list.py` — lista ficticia y utilidades

**Files:**
- Create: `shopping_list.py`
- Create: `tests/test_shopping_list.py`

- [ ] **Step 1: Escribir tests que fallen**

```python
# tests/test_shopping_list.py
import pytest
from shopping_list import get_lista_completa, format_summary, calcular_total

def test_get_lista_completa_devuelve_productos():
    lista = get_lista_completa()
    assert len(lista) > 0
    assert all("nombre" in p and "cantidad" in p and "precio" in p and "categoria" in p for p in lista)

def test_calcular_total_suma_correctamente():
    lista = [
        {"nombre": "Leche", "cantidad": 2, "precio": 0.89, "categoria": "Lácteos"},
        {"nombre": "Pan", "cantidad": 1, "precio": 1.20, "categoria": "Panadería"},
    ]
    assert calcular_total(lista) == round(2 * 0.89 + 1.20, 2)

def test_format_summary_contiene_total():
    lista = get_lista_completa()
    summary = format_summary(lista)
    assert "Total" in summary or "total" in summary
    assert "€" in summary

def test_format_summary_contiene_productos():
    lista = [{"nombre": "Leche", "cantidad": 2, "precio": 0.89, "categoria": "Lácteos"}]
    summary = format_summary(lista)
    assert "Leche" in summary
```

- [ ] **Step 2: Verificar que los tests fallan**

```bash
pytest tests/test_shopping_list.py -v
```

Expected: `ModuleNotFoundError: No module named 'shopping_list'`

- [ ] **Step 3: Implementar `shopping_list.py`**

```python
# shopping_list.py

LISTA_HABITUAL = {
    "Lácteos": [
        {"nombre": "Leche semidesnatada", "cantidad": 2, "precio": 0.89},
        {"nombre": "Yogures naturales (pack 8)", "cantidad": 1, "precio": 2.10},
    ],
    "Panadería": [
        {"nombre": "Pan integral", "cantidad": 1, "precio": 1.20},
        {"nombre": "Magdalenas", "cantidad": 1, "precio": 1.50},
    ],
    "Frutas y verduras": [
        {"nombre": "Plátanos (1kg)", "cantidad": 1, "precio": 1.35},
        {"nombre": "Manzanas (1kg)", "cantidad": 1, "precio": 1.89},
        {"nombre": "Tomates (1kg)", "cantidad": 1, "precio": 1.99},
        {"nombre": "Cebollas (malla)", "cantidad": 1, "precio": 1.10},
    ],
    "Proteínas": [
        {"nombre": "Huevos (docena)", "cantidad": 1, "precio": 2.30},
        {"nombre": "Pechuga de pollo (bandeja)", "cantidad": 1, "precio": 3.50},
    ],
    "Despensa": [
        {"nombre": "Aceite de oliva (1L)", "cantidad": 1, "precio": 5.99},
        {"nombre": "Arroz (1kg)", "cantidad": 1, "precio": 1.15},
        {"nombre": "Pasta (500g)", "cantidad": 1, "precio": 0.85},
    ],
    "Limpieza e higiene": [
        {"nombre": "Papel higiénico (pack 12)", "cantidad": 1, "precio": 3.99},
        {"nombre": "Jabón de manos", "cantidad": 1, "precio": 1.50},
    ],
}


def get_lista_completa() -> list[dict]:
    """Devuelve todos los productos de LISTA_HABITUAL como lista plana con campo 'categoria'."""
    productos = []
    for categoria, items in LISTA_HABITUAL.items():
        for item in items:
            productos.append({**item, "categoria": categoria})
    return productos


def calcular_total(lista: list[dict]) -> float:
    """Suma precio × cantidad para cada producto. Retorna float redondeado a 2 decimales."""
    return round(sum(p["precio"] * p["cantidad"] for p in lista), 2)


def format_summary(lista: list[dict]) -> str:
    """Genera texto legible para WhatsApp con la lista agrupada por categoría y el total."""
    por_categoria: dict[str, list[dict]] = {}
    for p in lista:
        cat = p.get("categoria", "Otros")
        por_categoria.setdefault(cat, []).append(p)

    lines = ["🛒 *Tu lista de la compra:*\n"]
    for cat, productos in por_categoria.items():
        items_str = ", ".join(
            f"{p['nombre']} x{p['cantidad']}" for p in productos
        )
        lines.append(f"• *{cat}:* {items_str}")

    total = calcular_total(lista)
    lines.append(f"\n💰 *Total estimado: {total:.2f} €*")
    return "\n".join(lines)
```

- [ ] **Step 4: Ejecutar tests y verificar que pasan**

```bash
pytest tests/test_shopping_list.py -v
```

Expected: 4 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add shopping_list.py tests/test_shopping_list.py
git commit -m "feat: shopping_list con lista habitual y utilidades de formato"
```

---

## Task 3: `conversation.py` — gestión de estado en memoria

**Files:**
- Create: `conversation.py`
- Create: `tests/test_conversation.py`

- [ ] **Step 1: Escribir tests que fallen**

```python
# tests/test_conversation.py
import pytest
from conversation import get_state, set_state, get_lista, set_lista, reset

def test_estado_inicial_es_idle():
    state = get_state("111111")
    assert state["state"] == "IDLE"
    assert state["current_list"] == []

def test_set_state_cambia_estado():
    set_state("222222", "AWAITING_CONFIRMATION")
    assert get_state("222222")["state"] == "AWAITING_CONFIRMATION"

def test_set_lista_y_get_lista():
    lista = [{"nombre": "Leche", "cantidad": 1, "precio": 0.89, "categoria": "Lácteos"}]
    set_lista("333333", lista)
    assert get_lista("333333") == lista

def test_reset_vuelve_a_idle_y_limpia_lista():
    set_state("444444", "MODIFYING")
    set_lista("444444", [{"nombre": "Pan", "cantidad": 1, "precio": 1.20, "categoria": "Panadería"}])
    reset("444444")
    assert get_state("444444")["state"] == "IDLE"
    assert get_lista("444444") == []
```

- [ ] **Step 2: Verificar que los tests fallan**

```bash
pytest tests/test_conversation.py -v
```

Expected: `ModuleNotFoundError: No module named 'conversation'`

- [ ] **Step 3: Implementar `conversation.py`**

```python
# conversation.py
from datetime import datetime

# Estado en memoria. Single-process obligatorio.
# Reiniciar el proceso borra todas las conversaciones activas.
_conversations: dict[str, dict] = {}

_DEFAULT = {"state": "IDLE", "current_list": [], "timestamp": None}


def _ensure(phone: str) -> None:
    if phone not in _conversations:
        _conversations[phone] = {**_DEFAULT, "current_list": []}


def get_state(phone: str) -> dict:
    _ensure(phone)
    return _conversations[phone]


def set_state(phone: str, state: str) -> None:
    _ensure(phone)
    _conversations[phone]["state"] = state
    _conversations[phone]["timestamp"] = datetime.now()


def get_lista(phone: str) -> list:
    _ensure(phone)
    return _conversations[phone]["current_list"]


def set_lista(phone: str, lista: list) -> None:
    _ensure(phone)
    _conversations[phone]["current_list"] = lista


def reset(phone: str) -> None:
    _conversations[phone] = {**_DEFAULT, "current_list": []}
```

- [ ] **Step 4: Ejecutar tests**

```bash
pytest tests/test_conversation.py -v
```

Expected: 4 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add conversation.py tests/test_conversation.py
git commit -m "feat: conversation state manager en memoria"
```

---

## Task 4: `woztell.py` — cliente de mensajería

**Files:**
- Create: `woztell.py`
- Create: `tests/test_woztell.py`

- [ ] **Step 1: Escribir tests que fallen**

```python
# tests/test_woztell.py
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from woztell import send_text, send_reply_buttons, send_message

PHONE = "34XXXXXXXXX"

@pytest.mark.asyncio
async def test_send_message_llama_a_woztell():
    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": 1}
    mock_response.raise_for_status = MagicMock()

    with patch("woztell.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        result = await send_message(PHONE, [{"type": "TEXT", "text": "Hola"}])
        assert result["ok"] == 1
        assert mock_client.post.called

@pytest.mark.asyncio
async def test_send_text_construye_payload_correcto():
    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": 1}
    mock_response.raise_for_status = MagicMock()

    with patch("woztell.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        await send_text(PHONE, "Texto de prueba")
        call_kwargs = mock_client.post.call_args
        payload = call_kwargs[1]["json"]
        assert payload["recipientId"] == PHONE
        assert payload["response"][0]["type"] == "TEXT"
        assert payload["response"][0]["text"] == "Texto de prueba"
```

- [ ] **Step 2: Verificar que los tests fallan**

```bash
pytest tests/test_woztell.py -v
```

Expected: `ModuleNotFoundError: No module named 'woztell'`

- [ ] **Step 3: Implementar `woztell.py`**

```python
# woztell.py
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
    logger.info(f"[WOZTELL] send_text → {recipient}: {text[:50]}...")
    return await send_message(recipient, [{"type": "TEXT", "text": text}])


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
```

**Nota importante:** En `send_message` hay una línea duplicada de `resp = client.post(...)` — borra la primera (sin await). Es un error en el plan; el código correcto usa solo la línea con `await`.

- [ ] **Step 4: Ejecutar tests**

```bash
pytest tests/test_woztell.py -v
```

Expected: 2 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add woztell.py tests/test_woztell.py
git commit -m "feat: woztell client con send_text y send_reply_buttons"
```

---

## Task 5: `audio_processor.py` — transcripción con Whisper

**Files:**
- Create: `audio_processor.py`
- Create: `tests/test_audio_processor.py`

- [ ] **Step 1: Escribir tests que fallen**

```python
# tests/test_audio_processor.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock, mock_open
from audio_processor import transcribe_audio

@pytest.mark.asyncio
async def test_transcribe_audio_retorna_texto():
    mock_audio_content = b"fake ogg audio bytes"

    mock_http_response = MagicMock()
    mock_http_response.content = mock_audio_content

    mock_transcription = MagicMock()
    mock_transcription.text = "quiero hacer la compra"

    with patch("audio_processor.httpx.AsyncClient") as mock_client_class, \
         patch("audio_processor.openai_client.audio.transcriptions.create", new_callable=AsyncMock) as mock_whisper:

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_http_response)
        mock_client_class.return_value = mock_client
        mock_whisper.return_value = mock_transcription

        result = await transcribe_audio("https://fake-url/audio.ogg")
        assert result == "quiero hacer la compra"

@pytest.mark.asyncio
async def test_transcribe_audio_devuelve_vacio_si_falla():
    with patch("audio_processor.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=Exception("network error"))
        mock_client_class.return_value = mock_client

        result = await transcribe_audio("https://fake-url/audio.ogg")
        assert result == ""
```

- [ ] **Step 2: Verificar que los tests fallan**

```bash
pytest tests/test_audio_processor.py -v
```

Expected: `ModuleNotFoundError: No module named 'audio_processor'`

- [ ] **Step 3: Implementar `audio_processor.py`**

```python
# audio_processor.py
import logging
import tempfile
import os
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
        # 1. Descargar el audio
        headers = {"Authorization": f"Bearer {config.WOZTELL_ACCESS_TOKEN}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(audio_url, headers=headers)
            response.raise_for_status()
            audio_bytes = response.content

        # 2. Guardar en fichero temporal
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        # 3. Transcribir con Whisper
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
```

- [ ] **Step 4: Ejecutar tests**

```bash
pytest tests/test_audio_processor.py -v
```

Expected: 2 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add audio_processor.py tests/test_audio_processor.py
git commit -m "feat: audio_processor con transcripción Whisper"
```

---

## Task 6: `ai_processor.py` — intención y generación de lista con GPT-4o-mini

**Files:**
- Create: `ai_processor.py`
- Create: `tests/test_ai_processor.py`

- [ ] **Step 1: Escribir tests que fallen**

```python
# tests/test_ai_processor.py
import pytest
import config
config.USE_MOCK_AI = True  # forzar modo mock para tests

from ai_processor import detect_intent, generate_shopping_list, modify_list, INTENT_PURCHASE, INTENT_UNKNOWN
from shopping_list import get_lista_completa

@pytest.mark.asyncio
async def test_detect_intent_compra():
    assert await detect_intent("quiero hacer la compra") == INTENT_PURCHASE

@pytest.mark.asyncio
async def test_detect_intent_unknown():
    assert await detect_intent("hola buenos días") == INTENT_UNKNOWN

@pytest.mark.asyncio
async def test_detect_intent_necesito():
    assert await detect_intent("necesito algunas cosas del mercado") == INTENT_PURCHASE

@pytest.mark.asyncio
async def test_generate_shopping_list_devuelve_productos():
    lista = await generate_shopping_list("quiero hacer la compra", get_lista_completa())
    assert len(lista) > 0
    assert all("nombre" in p for p in lista)

@pytest.mark.asyncio
async def test_modify_list_mas_incrementa_cantidad():
    lista = [{"nombre": "Leche", "cantidad": 1, "precio": 0.89, "categoria": "Lácteos"}]
    result = await modify_list(lista, "quiero más leche")
    assert result[0]["cantidad"] == 2

@pytest.mark.asyncio
async def test_modify_list_sin_reduce_lista():
    lista = [
        {"nombre": "Leche", "cantidad": 1, "precio": 0.89, "categoria": "Lácteos"},
        {"nombre": "Pan", "cantidad": 1, "precio": 1.20, "categoria": "Panadería"},
    ]
    result = await modify_list(lista, "sin el primero")
    assert len(result) == 1  # el mock elimina el primer elemento por índice
```

- [ ] **Step 2: Verificar que los tests fallan**

```bash
pytest tests/test_ai_processor.py -v
```

Expected: `ModuleNotFoundError: No module named 'ai_processor'`

- [ ] **Step 3: Implementar `ai_processor.py`**

```python
# ai_processor.py
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
```

- [ ] **Step 4: Ejecutar tests**

```bash
pytest tests/test_ai_processor.py -v
```

Expected: 6 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add ai_processor.py tests/test_ai_processor.py
git commit -m "feat: ai_processor con GPT-4o-mini y modo mock"
```

---

## Task 7: `main.py` — FastAPI app y orquestación del flujo

**Files:**
- Create: `main.py`
- Create: `tests/test_main.py`

- [ ] **Step 1: Escribir tests de integración del webhook**

```python
# tests/test_main.py
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
import config
config.USE_MOCK_AI = True

from main import app

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

@pytest.mark.asyncio
async def test_webhook_texto_compra_envia_botones():
    payload = {
        "from": "34600000001",
        "type": "TEXT",
        "data": {"text": "quiero hacer la compra"},
    }
    with patch("main.send_reply_buttons", new_callable=AsyncMock) as mock_buttons:
        mock_buttons.return_value = {"ok": 1}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/webhook", json=payload)
    assert resp.status_code == 200
    assert mock_buttons.called

@pytest.mark.asyncio
async def test_webhook_confirmar_compra_envia_dos_mensajes():
    from conversation import set_state, set_lista
    phone = "34600000002"
    set_state(phone, "AWAITING_CONFIRMATION")
    set_lista(phone, [{"nombre": "Leche", "cantidad": 1, "precio": 0.89, "categoria": "Lácteos"}])

    payload = {
        "from": phone,
        "type": "INTERACTIVE",
        "data": {"interactive": {"button_reply": {"id": "CONFIRMAR_COMPRA"}}},
    }
    with patch("main.send_text", new_callable=AsyncMock) as mock_text:
        mock_text.return_value = {"ok": 1}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/webhook", json=payload)
    assert resp.status_code == 200
    assert mock_text.call_count == 2  # usuario + familiar

@pytest.mark.asyncio
async def test_webhook_sin_phone_retorna_200():
    payload = {"type": "UNKNOWN", "data": {}}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/webhook", json=payload)
    assert resp.status_code == 200
```

- [ ] **Step 2: Verificar que los tests fallan**

```bash
pytest tests/test_main.py -v
```

Expected: `ModuleNotFoundError: No module named 'main'`

- [ ] **Step 3: Implementar `main.py`**

```python
# main.py
import json
import logging
from datetime import datetime, timedelta
from fastapi import FastAPI, Request

import config
from woztell import send_text, send_reply_buttons
from ai_processor import detect_intent, generate_shopping_list, modify_list, INTENT_PURCHASE
from audio_processor import transcribe_audio
from conversation import get_state, set_state, get_lista, set_lista, reset
from shopping_list import get_lista_completa, format_summary

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Asistente de Compras WhatsApp")

BOTONES_CONFIRMACION = [
    {"payload": "CONFIRMAR_COMPRA", "title": "✅ Confirmar"},
    {"payload": "MODIFICAR_COMPRA", "title": "✏️ Modificar"},
    {"payload": "CANCELAR_COMPRA",  "title": "❌ Cancelar"},
]


def _fecha_entrega() -> str:
    """Retorna la fecha del día siguiente en formato 'martes 29 de marzo'."""
    mañana = datetime.now() + timedelta(days=1)
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
             "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    return f"{dias[mañana.weekday()]} {mañana.day} de {meses[mañana.month - 1]}"


@app.get("/health")
async def health():
    return {"status": "ok"}


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

    text = (
        body.get("data", {}).get("text")
        or body.get("text")
        or body.get("message", {}).get("text")
        or body.get("data", {}).get("body")
    )

    audio_url = (
        body.get("data", {}).get("url")
        or body.get("data", {}).get("audio", {}).get("url")
        or body.get("data", {}).get("voice", {}).get("url")
        or body.get("data", {}).get("link")
    )

    button_payload = (
        body.get("data", {}).get("interactive", {}).get("button_reply", {}).get("id")
        or body.get("data", {}).get("payload")
        or body.get("data", {}).get("button_reply", {}).get("id")
        or body.get("payload")
        or body.get("postback", {}).get("payload")
    )

    # --- Enrutamiento ---
    if button_payload:
        await _handle_button(phone, button_payload)
    elif audio_url or msg_type in ("AUDIO", "VOICE"):
        transcribed = await transcribe_audio(audio_url or "")
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


async def _handle_text(phone: str, text: str) -> None:
    state = get_state(phone)["state"]
    logger.info(f"[{state}] → handle_text: '{text[:40]}' (phone: {phone})")

    if state == "IDLE":
        intent = await detect_intent(text)
        logger.info(f"[{state}] → detect_intent → {intent} (phone: {phone})")
        if intent == INTENT_PURCHASE:
            lista = await generate_shopping_list(text, get_lista_completa())
            set_lista(phone, lista)
            set_state(phone, "AWAITING_CONFIRMATION")
            summary = format_summary(lista)
            await send_reply_buttons(
                phone,
                body=f"¡Hola {config.NOMBRE_USUARIO}! 😊 Aquí está tu lista habitual:\n\n{summary}",
                footer="¿Quieres confirmar este pedido?",
                buttons=BOTONES_CONFIRMACION,
            )
            logger.info(f"[IDLE] → AWAITING_CONFIRMATION (phone: {phone})")
        else:
            await send_text(
                phone,
                f"¡Hola {config.NOMBRE_USUARIO}! 😊 Puedo ayudarte a hacer la compra. "
                "Dime cuándo quieras empezar.",
            )

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

    else:
        # AWAITING_CONFIRMATION recibe texto libre — ignorar, esperar botón
        logger.info(f"[{state}] texto ignorado, esperando botón (phone: {phone})")


async def _handle_button(phone: str, payload: str) -> None:
    state = get_state(phone)["state"]
    logger.info(f"[{state}] → button: {payload} (phone: {phone})")

    if payload == "CONFIRMAR_COMPRA" and state == "AWAITING_CONFIRMATION":
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

    else:
        logger.warning(f"[{state}] payload inesperado: {payload} (phone: {phone})")
```

- [ ] **Step 4: Ejecutar todos los tests**

```bash
pytest tests/ -v
```

Expected: todos los tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "feat: main.py con webhook, flujo completo y manejo de audio"
```

---

## Task 8: `README.md` y verificación final

**Files:**
- Create: `README.md`

- [ ] **Step 1: Crear README con instrucciones de setup**

```markdown
# Asistente de Compras WhatsApp — Hackathon

## Setup rápido

1. Instalar dependencias:
   pip install -r requirements.txt

2. Editar `config.py` con tus credenciales (ya configurado).

3. Arrancar el servidor:
   uvicorn main:app --reload --port 8000

4. Exponer con ngrok:
   ngrok http 8000

5. Copiar la URL de ngrok (ej: https://abc123.ngrok.io) y configurarla
   como webhook en el panel de Woztell para el canal de WhatsApp.

## Ejecutar tests

pytest tests/ -v

## Flujo de la demo

1. Enviar por WhatsApp: "Quiero hacer la compra" (texto o audio de voz)
2. El bot responde con la lista y 3 botones
3. Pulsar ✅ Confirmar → confirmación al usuario + notificación al familiar
4. O pulsar ✏️ Modificar → escribir cambios → nueva lista → confirmar
5. O pulsar ❌ Cancelar → mensaje amable
```

- [ ] **Step 2: Ejecutar suite completa de tests**

```bash
pytest tests/ -v --tb=short
```

Expected: todos los tests PASSED.

- [ ] **Step 3: Arrancar el servidor y verificar health**

```bash
uvicorn main:app --port 8000
```

En otra terminal:
```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 4: Commit final**

```bash
git add README.md
git commit -m "docs: README con instrucciones de setup y demo"
```

---

## Resumen de commits esperados

```
feat: scaffolding inicial — config y dependencias
feat: shopping_list con lista habitual y utilidades de formato
feat: conversation state manager en memoria
feat: woztell client con send_text y send_reply_buttons
feat: audio_processor con transcripción Whisper
feat: ai_processor con GPT-4o-mini y modo mock
feat: main.py con webhook, flujo completo y manejo de audio
docs: README con instrucciones de setup y demo
```
